import logging
from typing import Literal, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.actions import service
from app.auth.dependencies import get_current_user
from app.auth.tokens import CurrentUser
from app.db import get_db
from app.schemas.action_item import ActionItemCreate, ActionItemRead, ActionItemUpdate

router = APIRouter(prefix="/api/targets/{target_id}/actions")
logger = logging.getLogger(__name__)


def failure(
    db: Session, target_id: UUID, exc: service.ActionNotFoundError | SQLAlchemyError
) -> NoReturn:
    if isinstance(exc, service.ActionNotFoundError):
        raise HTTPException(404, "Analysis target or action item not found.") from None
    try:
        db.rollback()
    except SQLAlchemyError as rollback_error:
        logger.error("Action rollback failed (%s)", type(rollback_error).__name__)
    logger.warning("Actions for target %s failed (%s)", target_id, type(exc).__name__)
    raise HTTPException(
        503, "Action items are unavailable. Try again shortly."
    ) from None


@router.post("", response_model=ActionItemRead, status_code=201)
def create_action(
    target_id: UUID,
    body: ActionItemCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.create_action(db, UUID(user.id), target_id, body)
    except (service.ActionNotFoundError, SQLAlchemyError) as exc:
        failure(db, target_id, exc)


@router.get("", response_model=list[ActionItemRead])
def list_actions(
    target_id: UUID,
    status: Literal["open", "in_progress", "done", "resolved"] | None = Query(
        default=None
    ),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_actions(db, UUID(user.id), target_id, status)
    except (service.ActionNotFoundError, SQLAlchemyError) as exc:
        failure(db, target_id, exc)


@router.patch("/{action_id}", response_model=ActionItemRead)
def update_action(
    target_id: UUID,
    action_id: UUID,
    body: ActionItemUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_action(db, UUID(user.id), target_id, action_id, body)
    except (service.ActionNotFoundError, SQLAlchemyError) as exc:
        failure(db, target_id, exc)


@router.delete("/{action_id}", status_code=204)
def delete_action(
    target_id: UUID,
    action_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete_action(db, UUID(user.id), target_id, action_id)
    except (service.ActionNotFoundError, SQLAlchemyError) as exc:
        failure(db, target_id, exc)
    return Response(status_code=204)
