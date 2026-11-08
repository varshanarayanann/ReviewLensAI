from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReviewSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target_id: UUID
    review_count: int = Field(ge=0)
    average_rating: float | None
