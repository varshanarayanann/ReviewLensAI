import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.tokens import CurrentUser
from app.db import get_db
from app.qa.context import ContextTooLargeError
from app.qa.llm import LLMClient, LLMUnavailableError
from app.qa.service import TargetNotFoundError, answer_question
from app.schemas.question import QuestionAnswer, QuestionRequest

router = APIRouter(prefix="/api/targets", dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)


def get_llm_client(request: Request) -> LLMClient:
    return request.app.state.llm_client


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
