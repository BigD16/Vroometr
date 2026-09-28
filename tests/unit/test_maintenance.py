from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from app.maintenance.taxonomy import InvalidTaxonomy, catalog, validate_record_fields
from app.models.bike import Bike
from app.models.user import User
from app.services.maintenance import (
    InvalidMaintenance,
    MaintenanceNotFound,
    MaintenanceService,
)
from tests.unit.fakes import InMemoryBikeRepository


class MemoryStore:
    def __init__(self, bikes):
        self.bikes = bikes
        self.records: dict = {}
        self.gaps: list = []
        self.rules: list = []

    def get(self, record_id):
        return self.records.get(record_id)

    def get_owned(self, record_id, user_id):
        record = self.records.get(record_id)
        if record is None:
            return None
        return record if self.bikes.get(record.bike_id, user_id) is not None else None

    def list_for_bike(self, bike_id, *, limit=100):
        rows = [r for r in self.records.values() if r.bike_id == bike_id]
        rows.sort(key=lambda r: (r.service_date, r.created_at), reverse=True)
        return rows[:limit]

    def add(self, record):
        self.records[record.id] = record
        return record

    def save(self, record):
        self.records[record.id] = record
        return record

    def delete(self, record):
        self.records.pop(record.id, None)

    def record_taxonomy_gap(self, **kwargs):
        self.gaps.append(kwargs)
        return kwargs

    def list_active_rules(self, bike_id):
        return [
            r
            for r in self.rules
            if r.bike_id == bike_id
            and r.active
            and r.validation_status in ("active", "validated")
        ]

    def list_rules(self, bike_id, *, include_inactive=False):
        rows = [r for r in self.rules if r.bike_id == bike_id]
        if not include_inactive:
            rows = [
                r
                for r in rows
                if r.active and r.validation_status in ("active", "validated")
            ]
        return rows

    def add_rule(self, rule):
        self.rules.append(rule)
        return rule

    def save_rule(self, rule):
        for index, item in enumerate(self.rules):
            if item.id == rule.id:
                self.rules[index] = rule
                return rule
        self.rules.append(rule)
        return rule

    def get_owned_rule(self, rule_id, user_id):
        for rule in self.rules:
            if rule.id == rule_id and self.bikes.get(rule.bike_id, user_id) is not None:
                return rule
        return None

    def find_active_matching(
        self, bike_id, *, system, component, action, usage_condition_variant
    ):
        return [
            r
            for r in self.rules
            if r.bike_id == bike_id
            and r.system == system
            and r.component == component
            and r.action == action
            and r.usage_condition_variant == usage_condition_variant
            and r.active
            and r.validation_status == "active"
        ]

    def delete_rule(self, rule):
        self.rules = [item for item in self.rules if item.id != rule.id]


def setup_maintenance():
    owner, other = User(id=uuid4()), User(id=uuid4())
    bikes = InMemoryBikeRepository()
    bike = bikes.add(Bike(user_id=owner.id))
    store = MemoryStore(bikes)
    return owner, other, bike, MaintenanceService(store, bikes), store


def test_taxonomy_catalog_has_locked_lists():
    data = catalog()
    assert any(item["key"] == "engine" for item in data["systems"])
    assert any(item["key"] == "replace" for item in data["actions"])
    assert any(item["key"] == "owner_reported" for item in data["evidence_types"])
    with pytest.raises(InvalidTaxonomy):
        validate_record_fields(
            system="engine",
            component="nope",
            component_detail=None,
            action="replace",
            reason="scheduled",
            performer_type="owner",
            evidence_type="owner_reported",
        )


def test_create_list_and_owner_isolation():
    owner, other, bike, service, _ = setup_maintenance()
    record = service.create(
        owner,
        bike_id=bike.id,
        service_date=date(2026, 9, 1),
        system="engine",
        component="engine_oil",
        action="replace",
        reason="scheduled",
        performer_type="owner",
        engine_hours=12.5,
    )
    assert record.engine_hours == Decimal("12.5")
    assert getattr(record, "next_due", None) is None
    assert len(service.list_for_bike(owner, bike.id)) == 1
    with pytest.raises(MaintenanceNotFound):
        service.list_for_bike(other, bike.id)
    with pytest.raises(MaintenanceNotFound):
        service.get(other, record.id)


def test_other_component_requires_detail_and_records_gap():
    owner, _, bike, service, store = setup_maintenance()
    with pytest.raises(InvalidMaintenance):
        service.create(
            owner,
            bike_id=bike.id,
            service_date=date(2026, 9, 1),
            system="engine",
            component="other",
            action="repair",
            reason="other",
            performer_type="owner",
        )
    record = service.create(
        owner,
        bike_id=bike.id,
        service_date=date(2026, 9, 1),
        system="engine",
        component="other",
        component_detail="Mystery widget",
        action="repair",
        reason="other",
        performer_type="owner",
    )
    assert record.component_detail == "Mystery widget"
    assert store.gaps[0]["submitted_term"] == "Mystery widget"


def test_recent_for_context_shape():
    owner, _, bike, service, _ = setup_maintenance()
    service.create(
        owner,
        bike_id=bike.id,
        service_date=date(2026, 9, 2),
        system="brakes",
        component="brake_pads",
        action="replace",
        reason="scheduled",
        performer_type="owner",
    )
    rows = service.recent_for_context(owner, bike.id)
    assert rows[0]["system"] == "brakes"
    assert rows[0]["action"] == "replace"


def test_create_can_sync_confirmed_hours_to_bike():
    owner, _, bike, service, _ = setup_maintenance()
    bike.current_engine_hours = Decimal("10.0")
    bike.current_engine_hours_is_estimated = True
    service.create(
        owner,
        bike_id=bike.id,
        service_date=date(2026, 9, 3),
        system="engine",
        component="engine_oil",
        action="replace",
        reason="scheduled",
        performer_type="owner",
        engine_hours=15.0,
        engine_hours_is_estimated=False,
        sync_bike_hours=True,
    )
    assert bike.current_engine_hours == Decimal("15.0")
    assert bike.current_engine_hours_is_estimated is False
