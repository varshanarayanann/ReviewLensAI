from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisTarget, QuestionExchange
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
        result = QuestionAnswer(
            target_id=target.id,
            status=AnswerStatus.NO_REVIEWS,
            answer=None,
            review_count=0,
        )
        save_exchange(db, question, result)
        return result
    response = llm.complete(
        LLMRequest(
            system_prompt=build_system_prompt(target),
            question=question,
            reviews=reviews,
        )
    )
    result = QuestionAnswer(
        target_id=target.id,
        status=AnswerStatus(response.outcome.value),
        answer=response.text,
        review_count=len(reviews),
    )
    save_exchange(db, question, result)
    return result


def save_exchange(db: Session, question: str, result: QuestionAnswer) -> None:
    db.add(
        QuestionExchange(
            target_id=result.target_id,
            question=question,
            answer=result.answer,
            status=result.status.value,
            review_count=result.review_count,
        )
    )
    # A successful response is returned only after the complete pair is durable.
    db.commit()
