from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.deps import get_active_bike_service, get_current_user
from app.errors import AppError
from app.models.user import User
from app.services.active_bikes import (
    ActiveBikeNotFound,
    ActiveBikeService,
    ArchivedBikeCannotBeActive,
)

router = APIRouter(tags=["bikes"])


class ActiveBikeBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    bike_id: UUID


class ActiveBikeResponse(BaseModel):
    active_bike_id: UUID | None


@router.get("/v1/me/active-bike")
def get_active_bike(
    user: Annotated[User, Depends(get_current_user)],
    active_bikes: Annotated[ActiveBikeService, Depends(get_active_bike_service)],
) -> ActiveBikeResponse:
    bike = active_bikes.resolve(user)
    return ActiveBikeResponse(active_bike_id=bike.id if bike is not None else None)


@router.put("/v1/me/active-bike")
def put_active_bike(
    body: ActiveBikeBody,
    user: Annotated[User, Depends(get_current_user)],
    active_bikes: Annotated[ActiveBikeService, Depends(get_active_bike_service)],
) -> ActiveBikeResponse:
    try:
        bike = active_bikes.select(user, body.bike_id)
    except ActiveBikeNotFound as exc:
        raise AppError("not_found", "Bike not found", status_code=404) from exc
    except ArchivedBikeCannotBeActive as exc:
        raise AppError(
            "invalid_active_bike",
            "Archived bikes cannot be active",
            status_code=400,
        ) from exc
    return ActiveBikeResponse(active_bike_id=bike.id)
