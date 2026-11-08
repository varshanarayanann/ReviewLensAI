import logging
from collections.abc import Mapping
from uuid import UUID, uuid4

import fastapi
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.tokens import CurrentUser
from app.db import get_db
from app.models import AnalysisTarget
from app.models.ingestion import IngestionRun, Review
from app.reviews.csv_source import ReviewSourceError, parse_csv_reviews
from app.reviews.normalization import normalize_reviews
from app.schemas import target_list
from app.schemas.analysis_target import AnalysisTargetCreate, AnalysisTargetRead
from app.schemas.ingestion_result import IngestionResult
from app.schemas.review import ReviewResponse
from app.schemas.review_summary import ReviewSummary

router = APIRouter(prefix="/api/targets", dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)
INGESTION_UNAVAILABLE_DETAIL = (
    "Ingestion could not be recorded. Please try again shortly."
)


def rollback_safely(db: Session, target_id: UUID, run_id: UUID, stage: str) -> None:
    try:
        db.rollback()
    except SQLAlchemyError as exc:
        logger.error(
            "Ingestion %s for target %s rollback failed during %s (%s)",
            run_id,
            target_id,
            stage,
            type(exc).__name__,
        )


def owned(target_id: UUID, user: CurrentUser, db: Session) -> AnalysisTarget:
    target = db.scalar(
        select(AnalysisTarget).where(
            AnalysisTarget.id == target_id, AnalysisTarget.owner_id == UUID(user.id)
        )
    )
    if target is None:
        raise HTTPException(404, "Analysis target not found.")
    return target


@router.get("/{target_id}/reviews", response_model=list[ReviewResponse])
def list_reviews(
    target_id: UUID,
    limit: int = fastapi.Query(default=50, ge=1, le=100),
    offset: int = fastapi.Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = owned(target_id, user, db)
    return db.scalars(
        select(Review)
        .where(Review.target_id == target.id)
        .order_by(Review.id)
        .limit(limit)
        .offset(offset)
    ).all()


@router.get("/{target_id}/reviews/summary", response_model=ReviewSummary)
def review_summary(
    target_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = owned(target_id, user, db)
    review_count, average_rating = db.execute(
        select(func.count(Review.id), func.avg(Review.rating)).where(
            Review.target_id == target.id
        )
    ).one()
    return ReviewSummary(
        target_id=target.id,
        review_count=review_count,
        average_rating=average_rating,
    )


@router.post("", status_code=201)
def create_target(
    body: AnalysisTargetCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Ownership comes only from verified auth; copy editable fields explicitly.
    target = AnalysisTarget(
        id=uuid4(),
        owner_id=UUID(user.id),
        name=body.name,
        platform=body.platform,
        source_url=body.source_url,
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return {"id": target.id, "name": target.name, "source_url": target.source_url}


class CsvImport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    csv_text: str = Field(min_length=1, max_length=1_000_000)


@router.post("/{target_id}/ingestions", response_model=IngestionResult)
def ingest(
    target_id: UUID,
    body: CsvImport,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Child records inherit ownership from this authorized, persisted target.
    target = owned(target_id, user, db)
    try:
        records = parse_csv_reviews(body.csv_text)
    except ReviewSourceError:
        raise HTTPException(
            422,
            "Provide a CSV with rating and review_text columns and 1–1,000 "
            "reviews (maximum 1 MB).",
        ) from None
    run = IngestionRun(target_id=target.id)
    db.add(run)
    try:
        db.commit()
        db.refresh(run)
    except SQLAlchemyError as exc:
        logger.error(
            "Ingestion %s for target %s run creation failed (%s)",
            run.id,
            target.id,
            type(exc).__name__,
        )
        rollback_safely(db, target.id, run.id, "run creation")
        raise HTTPException(503, INGESTION_UNAVAILABLE_DETAIL) from None
    run_id = run.id
    try:
        route_records: list[object] = []
        for record in records:
            if isinstance(record, Mapping) and "rating" in record:
                record = dict(record)
                try:
                    record["rating"] = int(record.get("rating") or "")
                except (TypeError, ValueError):
                    # Preserve the route's integer-form rating contract.
                    record["rating"] = None
            route_records.append(record)

        normalized = normalize_reviews(route_records)
        rows = [
            Review(
                target_id=target.id,
                run_id=run_id,
                review_text=review.review_text,
                rating=review.rating,
            )
            for review in normalized.reviews
        ]
        if rows:
            db.add_all(rows)
        run.state = (
            "failed" if not rows else "partial" if normalized.rejected else "succeeded"
        )
        run.persisted_count = len(rows)
        run.rejected_count = len(normalized.rejected)
        db.commit()
    except SQLAlchemyError as exc:
        rollback_safely(db, target.id, run_id, "review persistence")
        # Do not log CSV contents, driver parameters, or raw provider errors.
        logger.warning("Ingestion %s failed (%s)", run_id, type(exc).__name__)
        try:
            run = db.get(IngestionRun, run_id)
            run.state = "failed"
            run.persisted_count = 0
            run.rejected_count = 0
            db.commit()
        except SQLAlchemyError as recovery_error:
            logger.error(
                "Ingestion %s for target %s failure outcome could not be recorded (%s)",
                run_id,
                target.id,
                type(recovery_error).__name__,
            )
            rollback_safely(db, target.id, run_id, "failure outcome")
            raise HTTPException(503, INGESTION_UNAVAILABLE_DETAIL) from None
    return IngestionResult(
        run_id=run_id,
        target_id=target_id,
        state=run.state,
        persisted_count=run.persisted_count,
        rejected_count=run.rejected_count,
    )


@router.get("/{target_id}/ingestions/latest", response_model=IngestionResult | None)
def latest(
    target_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owned(target_id, user, db)
    run = db.scalar(
        select(IngestionRun)
        .where(IngestionRun.target_id == target_id)
        .order_by(IngestionRun.created_at.desc(), IngestionRun.id.desc())
    )
    if run is None:
        return None
    return IngestionResult(
        run_id=run.id,
        target_id=target_id,
        state=run.state,
        persisted_count=run.persisted_count,
        rejected_count=run.rejected_count,
    )


@router.get("/{target_id}", response_model=AnalysisTargetRead)
def read_target(
    target_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = owned(target_id, user, db)
    return target


@router.get("", response_model=list[target_list.AnalysisTargetResponse])
def list_targets(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(AnalysisTarget)
        .where(AnalysisTarget.owner_id == UUID(user.id))
        .order_by(AnalysisTarget.created_at.desc(), AnalysisTarget.id.desc())
    ).all()
