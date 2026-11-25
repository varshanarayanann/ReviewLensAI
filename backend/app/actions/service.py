from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import ActionItem, AnalysisTarget
from app.schemas.action_item import ActionItemCreate, ActionItemRead, ActionItemUpdate


class ActionNotFoundError(Exception):
    """Parent is inaccessible or the action does not belong to that parent."""


def authorize_target(
    db: Session, owner_id: UUID, target_id: UUID, *, lock: bool = False
) -> None:
    query = select(AnalysisTarget.id).where(
        AnalysisTarget.id == target_id, AnalysisTarget.owner_id == owner_id
    )
    if lock:
        query = query.with_for_update()
    if db.scalar(query) is None:
        raise ActionNotFoundError


def list_actions(
    db: Session, owner_id: UUID, target_id: UUID, status: str | None
) -> list[ActionItemRead]:
    authorize_target(db, owner_id, target_id)
    query = (
        select(ActionItem)
        .join(AnalysisTarget, ActionItem.target_id == AnalysisTarget.id)
        .where(ActionItem.target_id == target_id, AnalysisTarget.owner_id == owner_id)
        .order_by(ActionItem.created_at, ActionItem.id)
    )
    if status is not None:
        query = query.where(
            ActionItem.status == ("done" if status == "resolved" else status)
        )
    return [ActionItemRead.model_validate(item) for item in db.scalars(query)]


def create_action(
    db: Session, owner_id: UUID, target_id: UUID, body: ActionItemCreate
) -> ActionItemRead:
    authorize_target(db, owner_id, target_id, lock=True)
    item = ActionItem(target_id=target_id, status="open", **body.model_dump())
    db.add(item)
    return save_action(db, item)


def owned_action(
    db: Session, owner_id: UUID, target_id: UUID, action_id: UUID
) -> ActionItem:
    authorize_target(db, owner_id, target_id, lock=True)
    item = db.scalar(
        select(ActionItem).where(
            ActionItem.id == action_id, ActionItem.target_id == target_id
        )
    )
    if item is None:
        raise ActionNotFoundError
    return item


def update_action(
    db: Session,
    owner_id: UUID,
    target_id: UUID,
    action_id: UUID,
    body: ActionItemUpdate,
) -> ActionItemRead:
    item = owned_action(db, owner_id, target_id, action_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    item.updated_at = datetime.now(UTC)
    return save_action(db, item)


def save_action(db: Session, item: ActionItem) -> ActionItemRead:
    db.flush()
    result = ActionItemRead.model_validate(item)
    db.commit()
    return result


def delete_action(
    db: Session, owner_id: UUID, target_id: UUID, action_id: UUID
) -> None:
    item = owned_action(db, owner_id, target_id, action_id)
    # S3-025 evidence links must FK-cascade from action_items, never delete reviews.
    db.execute(
        delete(ActionItem).where(
            ActionItem.id == item.id, ActionItem.target_id == target_id
        )
    )
    db.commit()
