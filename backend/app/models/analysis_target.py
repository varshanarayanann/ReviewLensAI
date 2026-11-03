from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, Text, Uuid, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Supabase owns auth.users and migrations never create it, but the ORM must know
# the referenced key to resolve owner_id's foreign key when it orders inserts.
auth_users = Table(
    "users",
    Base.metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    schema="auth",
)


class ReviewPlatform(str, Enum):
    GOOGLE_MAPS = "google_maps"


class AnalysisTarget(Base):
    __tablename__ = "analysis_targets"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    owner_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("auth.users.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    platform: Mapped[ReviewPlatform] = mapped_column(
        SqlEnum(
            ReviewPlatform,
            name="review_platform",
            length=32,
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_values: [
                platform.value for platform in enum_values
            ],
        ),
        nullable=False,
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
