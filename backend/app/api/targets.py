import csv
import io
import logging
from uuid import UUID, uuid4

import fastapi
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.tokens import CurrentUser
from app.db import get_db
from app.models import AnalysisTarget
from app.models.ingestion import IngestionRun, Review
from app.schemas.analysis_target import AnalysisTargetCreate
from app.schemas.ingestion_result import IngestionResult
from app.schemas.review import ReviewResponse

router = APIRouter(prefix="/api/targets", dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)


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


@router.post("", status_code=201)
def create_target(
    body: AnalysisTargetCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = AnalysisTarget(id=uuid4(), owner_id=UUID(user.id), **body.model_dump())
    db.add(target)
    db.commit()
    db.refresh(target)
    return {"id": target.id, "name": target.name, "source_url": target.source_url}


class CsvImport(BaseModel):
    csv_text: str = Field(min_length=1, max_length=1_000_000)


@router.post("/{target_id}/ingestions", response_model=IngestionResult)
def ingest(
    target_id: UUID,
    body: CsvImport,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owned(target_id, user, db)
    run = IngestionRun(target_id=target_id)
    db.add(run)
    db.commit()
    db.refresh(run)
    run_id = run.id
    try:
        reader = csv.DictReader(
            io.StringIO(body.csv_text.lstrip("\ufeff")), strict=True
        )
        if not {"rating", "review_text"}.issubset(reader.fieldnames or []):
            raise ValueError("columns")
        rows = []
        for row in reader:
            rating = int(row.get("rating") or "")
            text = (row.get("review_text") or "").strip()
            if not text or rating not in range(1, 6) or len(rows) >= 1000:
                raise ValueError("invalid record or limit")
            rows.append(
                Review(
                    target_id=target_id, run_id=run_id, review_text=text, rating=rating
                )
            )
        if not rows:
            raise ValueError("empty input")
        db.add_all(rows)
        run.state = "succeeded"
        run.persisted_count = len(rows)
        db.commit()
    except Exception as exc:
        db.rollback()
        # Do not log CSV contents, driver parameters, or raw provider errors.
        logger.warning("Ingestion %s failed (%s)", run_id, type(exc).__name__)
        run = db.get(IngestionRun, run_id)
        run.state = "failed"
        run.persisted_count = 0
        db.commit()
    return IngestionResult(
        run_id=run_id,
        target_id=target_id,
        state=run.state,
        persisted_count=run.persisted_count,
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
    )


@router.get("/{target_id}")
def read_target(
    target_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = owned(target_id, user, db)
    return {"id": target.id, "name": target.name, "source_url": target.source_url}
