from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.deps import get_current_user
from app.models.user import User

router = APIRouter(tags=["me"])


class MeResponse(BaseModel):
    id: UUID
    clerk_user_id: str
    role: str
    entitlement: str


@router.get("/v1/me")
def me(user: Annotated[User, Depends(get_current_user)]) -> MeResponse:
    return MeResponse(
        id=user.id,
        clerk_user_id=user.clerk_user_id,
        role=user.role,
        entitlement=user.entitlement,
    )
