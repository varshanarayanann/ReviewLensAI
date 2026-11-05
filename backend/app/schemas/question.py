from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QuestionRequest(BaseModel):
    """Only the question is accepted; target and user come from the path and auth."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=1000)


class AnswerStatus(str, Enum):
    ANSWERED = "answered"
    NO_REVIEWS = "no_reviews"


class QuestionAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target_id: UUID
    status: AnswerStatus
    answer: str | None
    review_count: int = Field(ge=0)
