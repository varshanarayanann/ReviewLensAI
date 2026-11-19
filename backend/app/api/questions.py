import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.targets import owned
from app.auth.dependencies import get_current_user
from app.auth.tokens import CurrentUser
from app.db import get_db
from app.models import AnalysisTarget, QuestionExchange
from app.qa.context import ContextTooLargeError
from app.qa.llm import LLMClient, LLMUnavailableError
from app.qa.service import TargetNotFoundError, answer_question
from app.schemas.question import QuestionAnswer, QuestionExchangeRead, QuestionRequest

router = APIRouter(prefix="/api/targets", dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)


def get_llm_client(request: Request) -> LLMClient:
    return request.app.state.llm_client


def history_unavailable(db: Session, target_id: UUID, exc: SQLAlchemyError) -> None:
    try:
        db.rollback()
    except SQLAlchemyError as rollback_error:
        logger.error("Q&A history rollback failed (%s)", type(rollback_error).__name__)
    logger.warning(
        "Q&A history for target %s failed (%s)", target_id, type(exc).__name__
    )
    raise HTTPException(
        503, "Analysis history could not be accessed or changed. Try again shortly."
    ) from None


@router.get("/{target_id}/questions", response_model=list[QuestionExchangeRead])
def list_questions(
    target_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        owned(target_id, user, db)
        return db.scalars(
            select(QuestionExchange)
            .join(AnalysisTarget, QuestionExchange.target_id == AnalysisTarget.id)
            .where(
                QuestionExchange.target_id == target_id,
                AnalysisTarget.owner_id == UUID(user.id),
            )
            .order_by(QuestionExchange.created_at, QuestionExchange.id)
            .limit(limit)
            .offset(offset)
        ).all()
    except SQLAlchemyError as exc:
        history_unavailable(db, target_id, exc)


@router.delete("/{target_id}/questions", status_code=204)
def clear_questions(
    target_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    try:
        target = db.scalar(
            select(AnalysisTarget)
            .where(
                AnalysisTarget.id == target_id,
                AnalysisTarget.owner_id == UUID(user.id),
            )
            .with_for_update()
        )
        if target is None:
            raise HTTPException(404, "Analysis target not found.")
        db.execute(
            delete(QuestionExchange).where(QuestionExchange.target_id == target.id)
        )
        db.commit()
    except SQLAlchemyError as exc:
        history_unavailable(db, target_id, exc)
    return Response(status_code=204)


@router.post("/{target_id}/questions", response_model=QuestionAnswer)
def ask_question(
    target_id: UUID,
    body: QuestionRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
):
    try:
        return answer_question(db, UUID(user.id), target_id, body.question, llm)
    except TargetNotFoundError:
        raise HTTPException(404, "Analysis target not found.") from None
    except ContextTooLargeError:
        raise HTTPException(
            422,
            "This target has too much review data for Q&A. "
            "Use a target with a smaller dataset.",
        ) from None
    except LLMUnavailableError as exc:
        # Never log the question, review text, or model output.
        logger.warning("Q&A for target %s failed (%s)", target_id, type(exc).__name__)
        raise HTTPException(
            503, "ReviewLens could not answer right now. Try again shortly."
        ) from None
    except SQLAlchemyError as exc:
        history_unavailable(db, target_id, exc)
