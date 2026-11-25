from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

ACTION_ITEM_STATUSES = ("open", "in_progress", "done")
ACTION_ITEM_PRIORITIES = ("low", "medium", "high")
DEFAULT_ACTION_ITEM_STATUS = "open"
DEFAULT_ACTION_ITEM_PRIORITY = "medium"


class ActionItem(Base):
    __tablename__ = "action_items"
    __table_args__ = (
        CheckConstraint(
            "length(trim(title)) BETWEEN 1 AND 200",
            name="action_items_title_check",
        ),
        CheckConstraint(
            "status IN ('open', 'in_progress', 'done')",
            name="action_items_status_check",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high')",
            name="action_items_priority_check",
        ),
        Index("action_items_target_created_idx", "target_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    target_id: Mapped[UUID] = mapped_column(
        ForeignKey("analysis_targets.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=DEFAULT_ACTION_ITEM_PRIORITY,
        server_default=text("'medium'"),
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=DEFAULT_ACTION_ITEM_STATUS,
        server_default=text("'open'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )
