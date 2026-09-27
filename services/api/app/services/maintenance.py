"""Owner-scoped maintenance records. Due dates are never stored here."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.maintenance.due_state import DueItem, derive_due_items
from app.maintenance.taxonomy import (
    ACTIONS,
    COMPONENTS,
    SYSTEMS,
    InvalidTaxonomy,
    is_other_component,
    validate_record_fields,
)
from app.models.maintenance import MaintenanceRecord, MaintenanceRule
from app.models.user import User
from app.repositories.bikes import BikeStore
from app.repositories.maintenance import MaintenanceStore


class MaintenanceNotFound(LookupError):
    pass


class InvalidMaintenance(ValueError):
    pass


class MaintenanceService:
    def __init__(self, records: MaintenanceStore, bikes: BikeStore) -> None:
        self._records = records
        self._bikes = bikes

    def _require_bike(self, user: User, bike_id: UUID):
        bike = self._bikes.get(bike_id, user.id)
        if bike is None:
            raise MaintenanceNotFound("Bike not found")
        return bike

    def list_for_bike(
        self, user: User, bike_id: UUID, *, limit: int = 100
    ) -> list[MaintenanceRecord]:
        self._require_bike(user, bike_id)
        return self._records.list_for_bike(bike_id, limit=min(max(limit, 1), 200))

    def get(self, user: User, record_id: UUID) -> MaintenanceRecord:
        record = self._records.get_owned(record_id, user.id)
        if record is None:
            raise MaintenanceNotFound("Maintenance record not found")
        return record

    def get_owned(self, record_id: UUID, user_id: UUID) -> MaintenanceRecord | None:
        """Attachment-link target check — same owner isolation as get()."""
        return self._records.get_owned(record_id, user_id)

    def create(
        self,
        user: User,
        *,
        bike_id: UUID,
        service_date: date,
        system: str,
        component: str,
        action: str,
        reason: str,
        performer_type: str,
        evidence_type: str = "owner_reported",
        component_detail: str | None = None,
        engine_hours: Decimal | float | None = None,
        engine_hours_is_estimated: bool = True,
        service_type: str | None = None,
        reason_details: str | None = None,
        performer_name: str | None = None,
        parts: str | None = None,
        fluids: str | None = None,
        cost: Decimal | float | None = None,
        source: str | None = None,
        linked_conversation_id: UUID | None = None,
        details: str | None = None,
    ) -> MaintenanceRecord:
        self._require_bike(user, bike_id)
        detail = _optional_text(component_detail, 500)
        try:
            validate_record_fields(
                system=system,
                component=component,
                component_detail=detail,
                action=action,
                reason=reason,
                performer_type=performer_type,
                evidence_type=evidence_type,
            )
        except InvalidTaxonomy as exc:
            raise InvalidMaintenance(str(exc)) from exc
        hours = _optional_hours(engine_hours)
        now = datetime.now(UTC)
        record = MaintenanceRecord(
            id=uuid4(),
            bike_id=bike_id,
            service_date=service_date,
            engine_hours=hours,
            engine_hours_is_estimated=bool(engine_hours_is_estimated),
            system=system,
            component=component,
            component_detail=detail,
            action=action,
            service_type=_optional_text(service_type, 64),
            reason=reason,
            reason_details=_optional_text(reason_details, 2000),
            performer_type=performer_type,
            performer_name=_optional_text(performer_name, 120),
            parts=_optional_text(parts, 2000),
            fluids=_optional_text(fluids, 2000),
            cost=_optional_cost(cost),
            evidence_type=evidence_type,
            source=_optional_text(source, 120),
            linked_conversation_id=linked_conversation_id,
            details=_optional_text(details, 4000),
            created_at=now,
            updated_at=now,
        )
        saved = self._records.add(record)
        if is_other_component(component) and detail:
            self._records.record_taxonomy_gap(
                taxonomy_type="component",
                submitted_term=detail,
                bike_id=bike_id,
                mapped_system=system,
            )
        return saved

    def update(
        self,
        user: User,
        record_id: UUID,
        **fields,
    ) -> MaintenanceRecord:
        record = self.get(user, record_id)
        system = fields.get("system", record.system)
        component = fields.get("component", record.component)
        detail = fields.get("component_detail", record.component_detail)
        if "component_detail" in fields:
            detail = _optional_text(detail, 500)
        action = fields.get("action", record.action)
        reason = fields.get("reason", record.reason)
        performer_type = fields.get("performer_type", record.performer_type)
        evidence_type = fields.get("evidence_type", record.evidence_type)
        try:
            validate_record_fields(
                system=system,
                component=component,
                component_detail=detail,
                action=action,
                reason=reason,
                performer_type=performer_type,
                evidence_type=evidence_type,
            )
        except InvalidTaxonomy as exc:
            raise InvalidMaintenance(str(exc)) from exc

        if "service_date" in fields:
            record.service_date = fields["service_date"]
        if "engine_hours" in fields:
            record.engine_hours = _optional_hours(fields["engine_hours"])
        if "engine_hours_is_estimated" in fields:
            record.engine_hours_is_estimated = bool(fields["engine_hours_is_estimated"])
        record.system = system
        record.component = component
        record.component_detail = detail
        record.action = action
        record.reason = reason
        record.performer_type = performer_type
        record.evidence_type = evidence_type
        for key, cleaner in (
            ("service_type", lambda v: _optional_text(v, 64)),
            ("reason_details", lambda v: _optional_text(v, 2000)),
            ("performer_name", lambda v: _optional_text(v, 120)),
            ("parts", lambda v: _optional_text(v, 2000)),
            ("fluids", lambda v: _optional_text(v, 2000)),
            ("source", lambda v: _optional_text(v, 120)),
            ("details", lambda v: _optional_text(v, 4000)),
        ):
            if key in fields:
                setattr(record, key, cleaner(fields[key]))
        if "cost" in fields:
            record.cost = _optional_cost(fields["cost"])
        if "linked_conversation_id" in fields:
            record.linked_conversation_id = fields["linked_conversation_id"]
        record.updated_at = datetime.now(UTC)
        saved = self._records.save(record)
        if is_other_component(component) and detail:
            self._records.record_taxonomy_gap(
                taxonomy_type="component",
                submitted_term=detail,
                bike_id=record.bike_id,
                mapped_system=system,
            )
        return saved

    def delete(self, user: User, record_id: UUID) -> None:
        record = self.get(user, record_id)
        self._records.delete(record)

    def recent_for_context(
        self, user: User, bike_id: UUID, *, limit: int = 5
    ) -> list[dict]:
        """Compact-context summary rows — no due state."""
        records = self.list_for_bike(user, bike_id, limit=limit)
        return [
            {
                "id": str(item.id),
                "service_date": item.service_date.isoformat(),
                "system": item.system,
                "component": item.component,
                "action": item.action,
                "engine_hours": float(item.engine_hours)
                if item.engine_hours is not None
                else None,
            }
            for item in records
        ]

    def list_rules(self, user: User, bike_id: UUID) -> list[MaintenanceRule]:
        self._require_bike(user, bike_id)
        return self._records.list_active_rules(bike_id)

    def create_rule(
        self,
        user: User,
        *,
        bike_id: UUID,
        system: str,
        component: str,
        action: str,
        initial_interval_hours: Decimal | float | None = None,
        recurring_interval_hours: Decimal | float | None = None,
        calendar_interval_days: int | None = None,
        whichever_comes_first: bool = True,
        usage_condition_variant: str = "standard",
    ) -> MaintenanceRule:
        self._require_bike(user, bike_id)
        if system not in SYSTEMS or component not in (COMPONENTS.get(system) or {}):
            raise InvalidMaintenance("Unknown system/component for rule.")
        if action not in ACTIONS:
            raise InvalidMaintenance("Unknown action for rule.")
        initial = _optional_hours(initial_interval_hours)
        recurring = _optional_hours(recurring_interval_hours)
        if calendar_interval_days is not None and calendar_interval_days < 0:
            raise InvalidMaintenance("Calendar interval cannot be negative.")
        if initial is None and recurring is None and calendar_interval_days is None:
            raise InvalidMaintenance("Rule needs an hours or calendar interval.")
        now = datetime.now(UTC)
        rule = MaintenanceRule(
            id=uuid4(),
            bike_id=bike_id,
            system=system,
            component=component,
            action=action,
            initial_interval_hours=initial,
            recurring_interval_hours=recurring,
            calendar_interval_days=calendar_interval_days,
            whichever_comes_first=bool(whichever_comes_first),
            usage_condition_variant=(usage_condition_variant or "standard").strip()[:64],
            validation_status="active",
            rule_version=1,
            active=True,
            created_at=now,
            updated_at=now,
        )
        return self._records.add_rule(rule)

    def delete_rule(self, user: User, rule_id: UUID) -> None:
        rule = self._records.get_owned_rule(rule_id, user.id)
        if rule is None:
            raise MaintenanceNotFound("Maintenance rule not found")
        self._records.delete_rule(rule)

    def due_state(self, user: User, bike_id: UUID, *, today: date | None = None) -> list[DueItem]:
        """Derived due items — never writes next_due."""
        bike = self._require_bike(user, bike_id)
        rules = self._records.list_active_rules(bike_id)
        records = self._records.list_for_bike(bike_id, limit=500)
        return derive_due_items(
            rules=rules,
            records=records,
            current_hours=bike.current_engine_hours,
            hours_estimated=bool(bike.current_engine_hours_is_estimated),
            today=today or date.today(),
        )


def _optional_text(value: str | None, max_len: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidMaintenance("Text fields must be strings.")
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > max_len:
        raise InvalidMaintenance(f"Text exceeds {max_len} characters.")
    return cleaned


def _optional_hours(value: Decimal | float | int | None) -> Decimal | None:
    if value is None:
        return None
    try:
        hours = Decimal(str(value))
    except Exception as exc:  # noqa: BLE001
        raise InvalidMaintenance("Engine hours must be a number.") from exc
    if hours < 0:
        raise InvalidMaintenance("Engine hours cannot be negative.")
    return hours.quantize(Decimal("0.1"))


def _optional_cost(value: Decimal | float | int | None) -> Decimal | None:
    if value is None:
        return None
    try:
        amount = Decimal(str(value))
    except Exception as exc:  # noqa: BLE001
        raise InvalidMaintenance("Cost must be a number.") from exc
    if amount < 0:
        raise InvalidMaintenance("Cost cannot be negative.")
    return amount.quantize(Decimal("0.01"))
