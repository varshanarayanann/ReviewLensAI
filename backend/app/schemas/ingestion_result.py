from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class IngestionState(str, Enum):
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
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
    rejected_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def consistent_outcome(self) -> "IngestionResult":
        if self.state == IngestionState.PROCESSING:
            if self.persisted_count or self.rejected_count:
                raise ValueError("Processing runs cannot report final record counts.")
        elif self.state == IngestionState.FAILED:
            if self.persisted_count:
                raise ValueError("Failed runs cannot report persisted reviews.")
        elif self.state == IngestionState.SUCCEEDED:
            if not self.persisted_count or self.rejected_count:
                raise ValueError("Successful runs require persisted reviews only.")
        elif not self.persisted_count or not self.rejected_count:
            raise ValueError("Partial runs require persisted and rejected reviews.")
        return self

    @computed_field
    @property
    def message(self) -> str:
        if self.state == IngestionState.PROCESSING:
            return "Collecting reviews. Please wait."
        if self.state == IngestionState.FAILED and not self.rejected_count:
            return "Reviews could not be collected. Try again shortly."
        if self.state == IngestionState.FAILED:
            return (
                f"Imported 0 reviews; rejected {self.rejected_count} "
                f"{'record' if self.rejected_count == 1 else 'records'}. "
                "Check the review text and ratings."
            )
        return (
            f"Imported {self.persisted_count} "
            f"{'review' if self.persisted_count == 1 else 'reviews'}; "
            f"rejected {self.rejected_count} "
            f"{'record' if self.rejected_count == 1 else 'records'}."
        )
