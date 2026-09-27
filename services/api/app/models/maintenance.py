from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MaintenanceRecord(Base):
    """Owner-scoped service history. Due state is derived — never stored here."""

    __tablename__ = "maintenance_records"
    __table_args__ = (
        CheckConstraint("engine_hours IS NULL OR engine_hours >= 0", name="ck_maint_hours"),
        CheckConstraint("cost IS NULL OR cost >= 0", name="ck_maint_cost"),
        Index("ix_maintenance_records_bike_service_date", "bike_id", "service_date"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    bike_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("bikes.id", ondelete="CASCADE"), index=True
    )
    service_date: Mapped[date] = mapped_column(Date)
    engine_hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 1))
    engine_hours_is_estimated: Mapped[bool] = mapped_column(default=True)
    system: Mapped[str] = mapped_column(String(64))
    component: Mapped[str] = mapped_column(String(64))
    component_detail: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str] = mapped_column(String(32))
    service_type: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(String(32))
    reason_details: Mapped[str | None] = mapped_column(Text)
    performer_type: Mapped[str] = mapped_column(String(32))
    performer_name: Mapped[str | None] = mapped_column(String(120))
    parts: Mapped[str | None] = mapped_column(Text)
    fluids: Mapped[str | None] = mapped_column(Text)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    evidence_type: Mapped[str] = mapped_column(String(32), default="owner_reported")
    source: Mapped[str | None] = mapped_column(String(120))
    linked_conversation_id: Mapped[UUID | None] = mapped_column(Uuid)
    details: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class TaxonomyGapEvent(Base):
    """Internal review queue when users map work to Other / unknown terms."""

    __tablename__ = "taxonomy_gap_events"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('open', 'reviewed', 'dismissed')",
            name="ck_taxonomy_gap_review_status",
        ),
        Index(
            "ix_taxonomy_gap_lookup",
            "taxonomy_type",
            "submitted_term",
            "mapped_system",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    taxonomy_type: Mapped[str] = mapped_column(String(32))
    submitted_term: Mapped[str] = mapped_column(String(200))
    bike_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("bikes.id", ondelete="SET NULL")
    )
    mapped_system: Mapped[str | None] = mapped_column(String(64))
    occurrence_count: Mapped[int] = mapped_column(default=1)
    review_status: Mapped[str] = mapped_column(String(32), default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class MaintenanceRule(Base):
    """Bike-scoped interval rule. Due dates are derived from rules + history, not stored."""

    __tablename__ = "maintenance_rules"
    __table_args__ = (
        CheckConstraint(
            "validation_status IN ('draft', 'validated', 'active', 'superseded')",
            name="ck_maint_rules_validation",
        ),
        CheckConstraint(
            "initial_interval_hours IS NULL OR initial_interval_hours >= 0",
            name="ck_maint_rules_initial_hours",
        ),
        CheckConstraint(
            "recurring_interval_hours IS NULL OR recurring_interval_hours >= 0",
            name="ck_maint_rules_recurring_hours",
        ),
        CheckConstraint(
            "calendar_interval_days IS NULL OR calendar_interval_days >= 0",
            name="ck_maint_rules_calendar_days",
        ),
        Index("ix_maintenance_rules_bike_active", "bike_id", "active"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    bike_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("bikes.id", ondelete="CASCADE"), index=True
    )
    system: Mapped[str] = mapped_column(String(64))
    component: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(32))
    initial_interval_hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 1))
    recurring_interval_hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 1))
    calendar_interval_days: Mapped[int | None] = mapped_column(Integer)
    whichever_comes_first: Mapped[bool] = mapped_column(Boolean, default=True)
    usage_condition_variant: Mapped[str] = mapped_column(String(64), default="standard")
    validation_status: Mapped[str] = mapped_column(String(32), default="active")
    rule_version: Mapped[int] = mapped_column(Integer, default=1)
    pipeline_version: Mapped[str | None] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    supersedes_rule_id: Mapped[UUID | None] = mapped_column(Uuid)
    source_document_id: Mapped[UUID | None] = mapped_column(Uuid)
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_span: Mapped[str | None] = mapped_column(Text)
    extraction_confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
