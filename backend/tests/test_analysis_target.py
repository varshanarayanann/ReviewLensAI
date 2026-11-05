from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    Table,
    Text,
    Uuid,
    create_engine,
    event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AnalysisTarget, Base, ReviewPlatform


@pytest.fixture
def sqlite_target_db() -> Iterator[tuple[Engine, Table]]:
    # SQLite cannot create a cross-schema FK, so mirror it as a same-schema
    # test-only constraint. This is not PostgreSQL integration coverage.
    metadata = MetaData()
    sqlite_users = Table(
        "users",
        metadata,
        Column("id", Uuid(as_uuid=True), primary_key=True),
    )
    Table(
        AnalysisTarget.__tablename__,
        metadata,
        Column("id", Uuid(as_uuid=True), primary_key=True),
        Column(
            "owner_id",
            Uuid(as_uuid=True),
            ForeignKey(sqlite_users.c.id),
            nullable=False,
        ),
        Column("name", String(120), nullable=False),
        Column(
            "platform",
            String(32),
            CheckConstraint("platform IN ('google_maps')"),
            nullable=False,
        ),
        Column("source_url", Text, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
    )
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record) -> None:
        connection.execute("PRAGMA foreign_keys=ON")

    try:
        metadata.create_all(engine)
        yield engine, sqlite_users
    finally:
        engine.dispose()


def test_analysis_target_persists_and_retrieves_with_owner(
    sqlite_target_db: tuple[Engine, Table],
) -> None:
    engine, auth_users = sqlite_target_db
    owner_id = uuid4()
    target_id = uuid4()
    created_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)

    with Session(engine) as session:
        session.execute(auth_users.insert().values(id=owner_id))
        target = AnalysisTarget(
            id=target_id,
            owner_id=owner_id,
            name="Example business",
            platform=ReviewPlatform.GOOGLE_MAPS,
            source_url="https://www.google.com/maps/place/Example",
            created_at=created_at,
        )
        session.add(target)
        session.commit()
        session.expunge(target)

        retrieved = session.get(AnalysisTarget, target_id)

    assert retrieved is not None
    assert retrieved.id == target_id
    assert retrieved.owner_id == owner_id
    assert retrieved.name == "Example business"
    assert retrieved.platform is ReviewPlatform.GOOGLE_MAPS
    assert retrieved.source_url == "https://www.google.com/maps/place/Example"
    # SQLite drops timezone metadata; PostgreSQL TIMESTAMPTZ preserves it.
    assert retrieved.created_at == created_at.replace(tzinfo=None)
    assert isinstance(retrieved.id, UUID)


def test_analysis_target_rejects_nonexistent_owner(
    sqlite_target_db: tuple[Engine, Table],
) -> None:
    engine, _auth_users = sqlite_target_db
    owner_foreign_key = next(iter(AnalysisTarget.__table__.c.owner_id.foreign_keys))

    assert owner_foreign_key.target_fullname == "auth.users.id"

    with Session(engine) as session:
        session.add(
            AnalysisTarget(
                id=uuid4(),
                owner_id=uuid4(),
                name="Example business",
                platform=ReviewPlatform.GOOGLE_MAPS,
                source_url="https://www.google.com/maps/place/Example",
                created_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
            )
        )

        with pytest.raises(IntegrityError, match="FOREIGN KEY constraint failed"):
            session.commit()


def test_owner_foreign_key_resolves_without_test_supplied_tables() -> None:
    owner_foreign_key = next(iter(AnalysisTarget.__table__.c.owner_id.foreign_keys))

    assert owner_foreign_key.column is Base.metadata.tables["auth.users"].c.id
    assert Base.metadata.sorted_tables
