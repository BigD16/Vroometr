from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from app.models.bike import Bike, BikeStatus, BikeType, StrokeType, UnitPreference
from app.models.user import User
from app.repositories.bikes import BikeStore

_HOURS_QUANTUM = Decimal("0.1")
_WRITABLE = frozenset(
    {
        "nickname",
        "make",
        "model",
        "year",
        "displacement",
        "bike_type",
        "stroke_type",
        "purchase_date",
        "engine_hours_at_purchase",
        "current_engine_hours",
        "current_engine_hours_is_estimated",
        "status",
        "unit_preference",
    }
)


class InvalidBike(ValueError):
    """Bike fields are missing or not a locked V1 value."""


class BikeNotFound(LookupError):
    """No bike with this id belongs to the current user."""


def _enum(cls: type[StrEnum], value: str, field: str) -> StrEnum:
    try:
        return cls(value)
    except ValueError:
        allowed = ", ".join(item.value for item in cls)
        raise InvalidBike(f"invalid {field}: expected {allowed}") from None


def _required_text(value: str, field: str) -> str:
    text = value.strip()
    if not text:
        raise InvalidBike(f"{field} is required")
    return text


def _hours(value: Decimal | float | int | None) -> Decimal | None:
    if value is None:
        return None
    hours = Decimal(str(value))
    if hours < 0:
        raise InvalidBike("engine hours cannot be negative")
    return hours.quantize(_HOURS_QUANTUM, rounding=ROUND_HALF_UP)


class BikeService:
    """Create/list/get/update bikes for the signed-in user only."""

    def __init__(self, repository: BikeStore, *, today: date | None = None) -> None:
        self._repository = repository
        self._today = today

    def _today_utc(self) -> date:
        return self._today or datetime.now(UTC).date()

    def list_for_user(self, user: User) -> list[Bike]:
        return self._repository.list_for_user(user.id)

    def get(self, user: User, bike_id: UUID) -> Bike:
        bike = self._repository.get(bike_id, user.id)
        if bike is None:
            raise BikeNotFound
        return bike

    def create(
        self,
        user: User,
        *,
        nickname: str,
        make: str,
        model: str,
        year: int,
        displacement: int,
        bike_type: str,
        stroke_type: str,
        purchase_date: date | None = None,
        engine_hours_at_purchase: Decimal | float | int | None = None,
        current_engine_hours: Decimal | float | int | None = None,
        current_engine_hours_is_estimated: bool = True,
        status: str = BikeStatus.ACTIVE.value,
        unit_preference: str = UnitPreference.IMPERIAL.value,
    ) -> Bike:
        now = datetime.now(UTC)
        bike = Bike(
            user_id=user.id,
            nickname=_required_text(nickname, "nickname"),
            make=_required_text(make, "make"),
            model=_required_text(model, "model"),
            year=self._year(year),
            displacement=self._displacement(displacement),
            bike_type=_enum(BikeType, bike_type, "bike_type").value,
            stroke_type=_enum(StrokeType, stroke_type, "stroke_type").value,
            purchase_date=self._purchase_date(purchase_date),
            engine_hours_at_purchase=_hours(engine_hours_at_purchase),
            current_engine_hours=_hours(current_engine_hours),
            current_engine_hours_is_estimated=current_engine_hours_is_estimated,
            status=_enum(BikeStatus, status, "status").value,
            unit_preference=_enum(UnitPreference, unit_preference, "unit_preference").value,
            created_at=now,
            updated_at=now,
        )
        return self._repository.add(bike)

    def update(self, user: User, bike_id: UUID, changes: dict[str, Any]) -> Bike:
        bike = self.get(user, bike_id)
        unknown = set(changes) - _WRITABLE
        if unknown:
            raise InvalidBike(f"cannot update fields: {', '.join(sorted(unknown))}")
        if "nickname" in changes:
            bike.nickname = _required_text(str(changes["nickname"]), "nickname")
        if "make" in changes:
            bike.make = _required_text(str(changes["make"]), "make")
        if "model" in changes:
            bike.model = _required_text(str(changes["model"]), "model")
        if "year" in changes:
            bike.year = self._year(int(changes["year"]))
        if "displacement" in changes:
            bike.displacement = self._displacement(int(changes["displacement"]))
        if "bike_type" in changes:
            bike.bike_type = _enum(BikeType, str(changes["bike_type"]), "bike_type").value
        if "stroke_type" in changes:
            bike.stroke_type = _enum(StrokeType, str(changes["stroke_type"]), "stroke_type").value
        if "purchase_date" in changes:
            bike.purchase_date = self._purchase_date(changes["purchase_date"])
        if "engine_hours_at_purchase" in changes:
            bike.engine_hours_at_purchase = _hours(changes["engine_hours_at_purchase"])
        if "current_engine_hours" in changes:
            bike.current_engine_hours = _hours(changes["current_engine_hours"])
        if "current_engine_hours_is_estimated" in changes:
            bike.current_engine_hours_is_estimated = bool(
                changes["current_engine_hours_is_estimated"]
            )
        if "status" in changes:
            bike.status = _enum(BikeStatus, str(changes["status"]), "status").value
        if "unit_preference" in changes:
            bike.unit_preference = _enum(
                UnitPreference, str(changes["unit_preference"]), "unit_preference"
            ).value
        bike.updated_at = datetime.now(UTC)
        return self._repository.save(bike)

    def _year(self, year: int) -> int:
        latest = self._today_utc().year + 1
        if year < 1900 or year > latest:
            raise InvalidBike(f"year must be between 1900 and {latest}")
        return year

    def _displacement(self, displacement: int) -> int:
        if displacement <= 0:
            raise InvalidBike("displacement must be a positive cc value")
        return displacement

    def _purchase_date(self, purchase_date: date | None) -> date | None:
        if purchase_date is None:
            return None
        if purchase_date > self._today_utc():
            raise InvalidBike("purchase_date cannot be in the future")
        return purchase_date
