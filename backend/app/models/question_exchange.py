from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class QuestionExchange(Base):
    __tablename__ = "question_exchanges"
    __table_args__ = (
        CheckConstraint("length(trim(question)) BETWEEN 1 AND 1000"),
        CheckConstraint(
            "status IN ('answered', 'insufficient_evidence', 'out_of_scope', "
            "'no_reviews')"
        ),
        CheckConstraint("review_count >= 0"),
        CheckConstraint(
            "(status = 'no_reviews' AND answer IS NULL AND review_count = 0) OR "
            "(status <> 'no_reviews' AND answer IS NOT NULL "
            "AND length(trim(answer)) > 0 AND review_count > 0)"
        ),
        Index("question_exchanges_target_history_idx", "target_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    target_id: Mapped[UUID] = mapped_column(
        ForeignKey("analysis_targets.id", ondelete="CASCADE")
    )
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))
    review_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
