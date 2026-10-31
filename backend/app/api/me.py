from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.auth.tokens import CurrentUser

router = APIRouter(prefix="/api/me", tags=["auth"])


@router.get("")
def read_current_user(user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"id": user.id, "email": user.email}
