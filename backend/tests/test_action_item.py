from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models import ActionItem, AnalysisTarget, Base, ReviewPlatform
from app.models.action_item import (
    DEFAULT_ACTION_ITEM_PRIORITY,
    DEFAULT_ACTION_ITEM_STATUS,
)


@pytest.fixture
def sqlite_db() -> Iterator[Engine]:
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record) -> None:
        connection.execute("PRAGMA foreign_keys=ON")

    with engine.connect() as connection:
        connection.exec_driver_sql("ATTACH DATABASE ':memory:' AS auth")
        Base.metadata.create_all(connection)
        connection.commit()

    try:
        yield engine
    finally:
        engine.dispose()


def seed_target(session: Session, owner_id: UUID | None = None) -> AnalysisTarget:
    owner = owner_id or uuid4()
    session.execute(Base.metadata.tables["auth.users"].insert().values(id=owner))
    target = AnalysisTarget(
        id=uuid4(),
        owner_id=owner,
        name="Hapive Coffee",
        platform=ReviewPlatform.GOOGLE_MAPS,
        source_url="https://www.google.com/maps/place/Hapive",
        created_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
    )
    session.add(target)
    session.flush()
    return target


def test_action_item_persists_with_analysis_association(sqlite_db: Engine) -> None:
    item_id = uuid4()
    created_at = datetime(2026, 3, 4, 5, 6, 7, tzinfo=UTC)
    updated_at = datetime(2026, 3, 4, 5, 6, 8, tzinfo=UTC)

    with Session(sqlite_db) as session:
        target = seed_target(session)
        target_id = target.id
        session.add(
            ActionItem(
                id=item_id,
                target_id=target_id,
                title="Follow up on wait-time complaints",
                description="Ask the manager about peak-hour staffing.",
                priority="high",
                status="in_progress",
                created_at=created_at,
                updated_at=updated_at,
            )
        )
        session.commit()

        retrieved = session.get(ActionItem, item_id)

        assert retrieved is not None
        assert retrieved.id == item_id
        assert retrieved.target_id == target_id
        assert retrieved.title == "Follow up on wait-time complaints"
        assert retrieved.description == "Ask the manager about peak-hour staffing."
        assert retrieved.priority == "high"
        assert retrieved.status == "in_progress"
        assert retrieved.created_at == created_at.replace(tzinfo=None)
        assert retrieved.updated_at == updated_at.replace(tzinfo=None)
        assert isinstance(retrieved.id, UUID)


def test_action_item_defaults_to_open_status_and_medium_priority(
    sqlite_db: Engine,
) -> None:
    with Session(sqlite_db) as session:
        target = seed_target(session)
        item = ActionItem(target_id=target.id, title="Review parking feedback")
        session.add(item)
        session.commit()
        session.refresh(item)

        assert item.status == DEFAULT_ACTION_ITEM_STATUS
        assert item.priority == DEFAULT_ACTION_ITEM_PRIORITY
        assert item.status == "open"
        assert item.priority == "medium"
        assert item.description is None
        assert item.created_at is not None
        assert item.updated_at is not None


def test_action_item_rejects_missing_analysis(sqlite_db: Engine) -> None:
    with Session(sqlite_db) as session:
        session.add(
            ActionItem(
                target_id=uuid4(),
                title="Orphaned item",
            )
        )
        with pytest.raises(IntegrityError, match="FOREIGN KEY constraint failed"):
            session.commit()


def test_action_item_rejects_invalid_status_and_priority(sqlite_db: Engine) -> None:
    with Session(sqlite_db) as session:
        target = seed_target(session)
        session.add(
            ActionItem(
                target_id=target.id,
                title="Bad status",
                status="archived",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.add(
            ActionItem(
                target_id=target.id,
                title="Bad priority",
                priority="urgent",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_action_item_requires_usable_title(sqlite_db: Engine) -> None:
    with Session(sqlite_db) as session:
        target = seed_target(session)
        session.add(ActionItem(target_id=target.id, title="   "))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.add(
            ActionItem(
                target_id=target.id,
                title=None,  # type: ignore[arg-type]
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_deleting_analysis_removes_its_action_items(sqlite_db: Engine) -> None:
    with Session(sqlite_db) as session:
        target = seed_target(session)
        other = seed_target(session)
        kept_id = uuid4()
        session.add_all(
            [
                ActionItem(
                    id=uuid4(),
                    target_id=target.id,
                    title="Remove with analysis",
                ),
                ActionItem(
                    id=kept_id,
                    target_id=other.id,
                    title="Keep with other analysis",
                ),
            ]
        )
        session.commit()

        session.delete(target)
        session.commit()

        remaining = session.scalars(select(ActionItem)).all()
        assert [item.id for item in remaining] == [kept_id]
        assert remaining[0].title == "Keep with other analysis"
