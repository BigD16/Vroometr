from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class BikeType(StrEnum):
    MOTORCYCLE = "motorcycle"
    DIRT_BIKE = "dirt_bike"


class StrokeType(StrEnum):
    TWO_STROKE = "2T"
    FOUR_STROKE = "4T"


class BikeStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVE = "archive"


class UnitPreference(StrEnum):
    IMPERIAL = "imperial"
    METRIC = "metric"


class Bike(Base):
    """Owner-scoped machine. Durable facts live here, not in AI memory. No VIN, no notes."""

    __tablename__ = "bikes"
    __table_args__ = (
        CheckConstraint(
            "bike_type IN ('motorcycle', 'dirt_bike')",
            name="ck_bikes_bike_type",
        ),
        CheckConstraint("stroke_type IN ('2T', '4T')", name="ck_bikes_stroke_type"),
        CheckConstraint(
            "status IN ('active', 'inactive', 'archive')",
            name="ck_bikes_status",
        ),
        CheckConstraint(
            "unit_preference IN ('imperial', 'metric')",
            name="ck_bikes_unit_preference",
        ),
        CheckConstraint("year >= 1900", name="ck_bikes_year"),
        CheckConstraint("displacement > 0", name="ck_bikes_displacement"),
        CheckConstraint(
            "engine_hours_at_purchase IS NULL OR engine_hours_at_purchase >= 0",
            name="ck_bikes_purchase_hours",
        ),
        CheckConstraint(
            "current_engine_hours IS NULL OR current_engine_hours >= 0",
            name="ck_bikes_current_hours",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    nickname: Mapped[str] = mapped_column(String(255))
    make: Mapped[str] = mapped_column(String(255))
    model: Mapped[str] = mapped_column(String(255))
    year: Mapped[int] = mapped_column(Integer)
    displacement: Mapped[int] = mapped_column(Integer)
    bike_type: Mapped[str] = mapped_column(String(32))
    stroke_type: Mapped[str] = mapped_column(String(8))
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    engine_hours_at_purchase: Mapped[Decimal | None] = mapped_column(Numeric(8, 1), nullable=True)
    current_engine_hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 1), nullable=True)
    current_engine_hours_is_estimated: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default=BikeStatus.ACTIVE.value)
    unit_preference: Mapped[str] = mapped_column(String(32), default=UnitPreference.IMPERIAL.value)
    selected_garage_scene_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
