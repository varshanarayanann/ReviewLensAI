from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisTarget
from app.qa.context import review_context
from app.qa.llm import LLMClient, LLMRequest
from app.qa.prompt import build_system_prompt
from app.schemas.question import AnswerStatus, QuestionAnswer


class TargetNotFoundError(Exception):
    """The target does not exist or belongs to another user."""


def answer_question(
    db: Session, owner_id: UUID, target_id: UUID, question: str, llm: LLMClient
) -> QuestionAnswer:
    target = db.scalar(
        select(AnalysisTarget).where(
            AnalysisTarget.id == target_id, AnalysisTarget.owner_id == owner_id
        )
    )
    if target is None:
        raise TargetNotFoundError
    reviews = review_context(db, owner_id, target.id)
    if not reviews:
        return QuestionAnswer(
            target_id=target.id,
            status=AnswerStatus.NO_REVIEWS,
            answer=None,
            review_count=0,
        )
    response = llm.complete(
        LLMRequest(
            system_prompt=build_system_prompt(target),
            question=question,
            reviews=reviews,
        )
    )
    return QuestionAnswer(
        target_id=target.id,
        status=AnswerStatus(response.outcome.value),
        answer=response.text,
        review_count=len(reviews),
    )
