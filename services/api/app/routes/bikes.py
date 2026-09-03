from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.deps import get_bike_service, get_current_user
from app.errors import AppError
from app.models.bike import Bike
from app.models.user import User
from app.services.bikes import BikeNotFound, BikePatch, BikeService, InvalidBike

router = APIRouter(tags=["bikes"])


class BikeCreateBody(BaseModel):
    """Signed-in user is the owner. Extra fields such as user_id are ignored."""

    model_config = ConfigDict(extra="ignore")

    nickname: str
    make: str
    model: str
    year: int
    displacement: int
    bike_type: str
    stroke_type: str
    purchase_date: date | None = None
    engine_hours_at_purchase: float | None = None
    current_engine_hours: float | None = None
    current_engine_hours_is_estimated: bool = True
    status: str = "active"
    unit_preference: str = "imperial"


class BikeUpdateBody(BaseModel):
    """Partial update. Extra fields such as user_id are ignored."""

    model_config = ConfigDict(extra="ignore")

    nickname: str | None = None
    make: str | None = None
    model: str | None = None
    year: int | None = None
    displacement: int | None = None
    bike_type: str | None = None
    stroke_type: str | None = None
    purchase_date: date | None = None
    engine_hours_at_purchase: float | None = None
    current_engine_hours: float | None = None
    current_engine_hours_is_estimated: bool | None = None
    status: str | None = None
    unit_preference: str | None = None


class BikeResponse(BaseModel):
    id: UUID
    user_id: UUID
    nickname: str
    make: str
    model: str
    year: int
    displacement: int
    bike_type: str
    stroke_type: str
    purchase_date: date | None
    engine_hours_at_purchase: float | None
    current_engine_hours: float | None
    current_engine_hours_is_estimated: bool
    status: str
    unit_preference: str
    selected_garage_scene_id: UUID | None
    created_at: datetime
    updated_at: datetime


def _hours_out(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _to_response(bike: Bike) -> BikeResponse:
    return BikeResponse(
        id=bike.id,
        user_id=bike.user_id,
        nickname=bike.nickname,
        make=bike.make,
        model=bike.model,
        year=bike.year,
        displacement=bike.displacement,
        bike_type=bike.bike_type,
        stroke_type=bike.stroke_type,
        purchase_date=bike.purchase_date,
        engine_hours_at_purchase=_hours_out(bike.engine_hours_at_purchase),
        current_engine_hours=_hours_out(bike.current_engine_hours),
        current_engine_hours_is_estimated=bike.current_engine_hours_is_estimated,
        status=bike.status,
        unit_preference=bike.unit_preference,
        selected_garage_scene_id=bike.selected_garage_scene_id,
        created_at=bike.created_at,
        updated_at=bike.updated_at,
    )


def _raise_bike(exc: InvalidBike | BikeNotFound) -> NoReturn:
    if isinstance(exc, BikeNotFound):
        raise AppError("not_found", "Bike not found", status_code=404) from exc
    raise AppError("invalid_bike", str(exc), status_code=400) from exc


@router.get("/v1/bikes")
def list_bikes(
    user: Annotated[User, Depends(get_current_user)],
    bikes: Annotated[BikeService, Depends(get_bike_service)],
) -> list[BikeResponse]:
    return [_to_response(bike) for bike in bikes.list_for_user(user)]


@router.post("/v1/bikes")
def create_bike(
    body: BikeCreateBody,
    user: Annotated[User, Depends(get_current_user)],
    bikes: Annotated[BikeService, Depends(get_bike_service)],
) -> BikeResponse:
    try:
        bike = bikes.create(
            user,
            nickname=body.nickname,
            make=body.make,
            model=body.model,
            year=body.year,
            displacement=body.displacement,
            bike_type=body.bike_type,
            stroke_type=body.stroke_type,
            purchase_date=body.purchase_date,
            engine_hours_at_purchase=body.engine_hours_at_purchase,
            current_engine_hours=body.current_engine_hours,
            current_engine_hours_is_estimated=body.current_engine_hours_is_estimated,
            status=body.status,
            unit_preference=body.unit_preference,
        )
    except InvalidBike as exc:
        _raise_bike(exc)
    return _to_response(bike)


@router.get("/v1/bikes/{bike_id}")
def get_bike(
    bike_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    bikes: Annotated[BikeService, Depends(get_bike_service)],
) -> BikeResponse:
    try:
        bike = bikes.get(user, bike_id)
    except BikeNotFound as exc:
        _raise_bike(exc)
    return _to_response(bike)


@router.patch("/v1/bikes/{bike_id}")
def update_bike(
    bike_id: UUID,
    body: BikeUpdateBody,
    user: Annotated[User, Depends(get_current_user)],
    bikes: Annotated[BikeService, Depends(get_bike_service)],
) -> BikeResponse:
    patch = BikePatch(**body.model_dump(exclude_unset=True))
    try:
        bike = bikes.update(user, bike_id, patch)
    except (InvalidBike, BikeNotFound) as exc:
        _raise_bike(exc)
    return _to_response(bike)
