from collections.abc import Iterator
from dataclasses import dataclass, fields
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from uuid import UUID

from app.models.bike import (
    Bike,
    BikeStatus,
    BikeType,
    PowertrainType,
    StrokeType,
    UnitPreference,
)
from app.models.user import User
from app.repositories.bikes import BikeStore

_HOURS_QUANTUM = Decimal("0.1")
_TEXT_FIELDS = frozenset({"nickname", "make", "model"})
_POWERTRAIN_FIELDS = frozenset({"powertrain_type", "displacement", "stroke_type"})


class _Unset:
    __slots__ = ()


_UNSET = _Unset()


@dataclass(frozen=True, slots=True)
class BikePatch:
    """Typed update command; omitted and explicitly cleared values stay distinct."""

    nickname: str | _Unset = _UNSET
    make: str | _Unset = _UNSET
    model: str | _Unset = _UNSET
    year: int | _Unset = _UNSET
    bike_type: str | _Unset = _UNSET
    powertrain_type: str | _Unset = _UNSET
    displacement: int | None | _Unset = _UNSET
    stroke_type: str | None | _Unset = _UNSET
    purchase_date: date | None | _Unset = _UNSET
    engine_hours_at_purchase: Decimal | float | int | None | _Unset = _UNSET
    current_engine_hours: Decimal | float | int | None | _Unset = _UNSET
    current_engine_hours_is_estimated: bool | _Unset = _UNSET
    status: str | _Unset = _UNSET
    unit_preference: str | _Unset = _UNSET

    def changes(self) -> Iterator[tuple[str, object]]:
        for field in fields(self):
            value = getattr(self, field.name)
            if value is not _UNSET:
                yield field.name, value


class InvalidBike(ValueError):
    """Bike fields are missing or not a locked V1 value."""


class BikeNotFound(LookupError):
    """No bike with this id belongs to the current user."""


def _enum(cls: type[StrEnum], value: object, field: str) -> StrEnum:
    if not isinstance(value, str):
        raise InvalidBike(f"{field} must be text")
    try:
        return cls(value)
    except ValueError:
        allowed = ", ".join(item.value for item in cls)
        raise InvalidBike(f"invalid {field}: expected {allowed}") from None


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise InvalidBike(f"{field} must be text")
    text = value.strip()
    if not text:
        raise InvalidBike(f"{field} is required")
    return text


def _hours(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (Decimal, float, int)):
        raise InvalidBike("engine hours must be a number")
    hours = Decimal(str(value))
    if not hours.is_finite() or hours < 0:
        raise InvalidBike("engine hours cannot be negative")
    return hours.quantize(_HOURS_QUANTUM, rounding=ROUND_HALF_UP)


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidBike(f"{field} must be an integer")
    return value


def _boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise InvalidBike(f"{field} must be true or false")
    return value


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
        bike_type: str,
        powertrain_type: str = PowertrainType.COMBUSTION.value,
        displacement: int | None = None,
        stroke_type: str | None = None,
        purchase_date: date | None = None,
        engine_hours_at_purchase: Decimal | float | int | None = None,
        current_engine_hours: Decimal | float | int | None = None,
        current_engine_hours_is_estimated: bool = True,
        status: str = BikeStatus.ACTIVE.value,
        unit_preference: str = UnitPreference.METRIC.value,
    ) -> Bike:
        now = datetime.now(UTC)
        normalized_powertrain, normalized_displacement, normalized_stroke = (
            self._normalize_powertrain_configuration(
                powertrain_type,
                displacement,
                stroke_type,
            )
        )
        bike = Bike(
            user_id=user.id,
            nickname=self._normalize_field("nickname", nickname),
            make=self._normalize_field("make", make),
            model=self._normalize_field("model", model),
            year=self._normalize_field("year", year),
            bike_type=self._normalize_field("bike_type", bike_type),
            powertrain_type=normalized_powertrain,
            displacement=normalized_displacement,
            stroke_type=normalized_stroke,
            purchase_date=self._normalize_field("purchase_date", purchase_date),
            engine_hours_at_purchase=self._normalize_field(
                "engine_hours_at_purchase", engine_hours_at_purchase
            ),
            current_engine_hours=self._normalize_field(
                "current_engine_hours", current_engine_hours
            ),
            current_engine_hours_is_estimated=self._normalize_field(
                "current_engine_hours_is_estimated", current_engine_hours_is_estimated
            ),
            status=self._normalize_field("status", status),
            unit_preference=self._normalize_field("unit_preference", unit_preference),
            created_at=now,
            updated_at=now,
        )
        return self._repository.add(bike)

    def update(self, user: User, bike_id: UUID, patch: BikePatch) -> Bike:
        bike = self.get(user, bike_id)
        changes = dict(patch.changes())
        normalized = {
            field: self._normalize_field(field, value)
            for field, value in changes.items()
            if field not in _POWERTRAIN_FIELDS
        }
        if _POWERTRAIN_FIELDS.intersection(changes):
            powertrain, displacement, stroke_type = self._normalize_powertrain_configuration(
                changes.get("powertrain_type", bike.powertrain_type),
                changes.get("displacement", bike.displacement),
                changes.get("stroke_type", bike.stroke_type),
            )
            normalized.update(
                powertrain_type=powertrain,
                displacement=displacement,
                stroke_type=stroke_type,
            )
        for field, value in normalized.items():
            setattr(bike, field, value)
        bike.updated_at = datetime.now(UTC)
        return self._repository.save(bike)

    def _normalize_field(self, field: str, value: object) -> object:
        if field in _TEXT_FIELDS:
            return _required_text(value, field)
        if field == "year":
            return self._year(_integer(value, field))
        if field == "bike_type":
            return _enum(BikeType, value, field).value
        if field == "purchase_date":
            return self._purchase_date(value)
        if field in {"engine_hours_at_purchase", "current_engine_hours"}:
            return _hours(value)
        if field == "current_engine_hours_is_estimated":
            return _boolean(value, field)
        if field == "status":
            return _enum(BikeStatus, value, field).value
        if field == "unit_preference":
            return _enum(UnitPreference, value, field).value
        raise InvalidBike(f"cannot update field: {field}")

    def _normalize_powertrain_configuration(
        self,
        powertrain_type: object,
        displacement: object,
        stroke_type: object,
    ) -> tuple[str, int | None, str | None]:
        powertrain = _enum(PowertrainType, powertrain_type, "powertrain_type").value
        if powertrain == PowertrainType.ELECTRIC.value:
            if displacement is not None or stroke_type is not None:
                raise InvalidBike("electric bikes cannot have displacement or stroke type")
            return powertrain, None, None

        if displacement is None:
            raise InvalidBike("combustion bikes require displacement")
        if stroke_type is None:
            raise InvalidBike("combustion bikes require stroke type")
        return (
            powertrain,
            self._displacement(_integer(displacement, "displacement")),
            _enum(StrokeType, stroke_type, "stroke_type").value,
        )

    def _year(self, year: int) -> int:
        latest = self._today_utc().year + 1
        if year < 1900 or year > latest:
            raise InvalidBike(f"year must be between 1900 and {latest}")
        return year

    def _displacement(self, displacement: int) -> int:
        if displacement <= 0:
            raise InvalidBike("displacement must be a positive cc value")
        return displacement

    def _purchase_date(self, purchase_date: object) -> date | None:
        if purchase_date is None:
            return None
        if not isinstance(purchase_date, date) or isinstance(purchase_date, datetime):
            raise InvalidBike("purchase_date must be a date")
        if purchase_date > self._today_utc():
            raise InvalidBike("purchase_date cannot be in the future")
        return purchase_date
