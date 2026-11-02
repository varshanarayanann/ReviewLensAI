from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.analysis_target import ReviewPlatform


class AnalysisTargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    platform: ReviewPlatform
    source_url: str
    created_at: datetime
