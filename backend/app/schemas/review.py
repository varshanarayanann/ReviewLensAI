from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReviewResponse(BaseModel):
    """Persisted review returned only after authorizing its parent target."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target_id: UUID
    run_id: UUID
    review_text: str
    rating: int
