from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class IngestionState(str, Enum):
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class IngestionResult(BaseModel):
    """Public result contract. Construct only from recorded persistence outcomes.

    Diagnostics belong in server logs, never in this response. This contract
    does not persist an attempt or imply that an ingestion pipeline exists.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    target_id: UUID
    state: IngestionState
    persisted_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def consistent_outcome(self) -> "IngestionResult":
        if self.state != IngestionState.SUCCEEDED and self.persisted_count:
            raise ValueError("Only successful runs may report persisted reviews.")
        if self.state == IngestionState.SUCCEEDED and not self.persisted_count:
            raise ValueError("Success requires persisted reviews.")
        return self

    @computed_field
    @property
    def message(self) -> str:
        if self.state == IngestionState.PROCESSING:
            return "Collecting reviews. Please wait."
        if self.state == IngestionState.FAILED:
            return "Reviews could not be collected. Try again shortly."
        return f"Ingested {self.persisted_count} reviews."
