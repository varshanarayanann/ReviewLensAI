from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    target_id: Mapped[UUID] = mapped_column(ForeignKey("analysis_targets.id"))
    state: Mapped[str] = mapped_column(String(16), default="processing")
    persisted_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    target_id: Mapped[UUID] = mapped_column(ForeignKey("analysis_targets.id"))
    run_id: Mapped[UUID] = mapped_column(ForeignKey("ingestion_runs.id"))
    review_text: Mapped[str] = mapped_column(Text)
    rating: Mapped[int] = mapped_column(Integer)
    source_metadata: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
