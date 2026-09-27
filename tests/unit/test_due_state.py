"""Unit tests for derived due state (no persisted next_due)."""

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.maintenance.due_state import derive_due_items


def _rule(**kwargs):
    base = dict(
        id=uuid4(),
        system="engine",
        component="engine_oil",
        action="replace",
        initial_interval_hours=Decimal("10"),
        recurring_interval_hours=Decimal("10"),
        calendar_interval_days=None,
        whichever_comes_first=True,
        usage_condition_variant="standard",
        validation_status="active",
        active=True,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def _record(**kwargs):
    base = dict(
        system="engine",
        component="engine_oil",
        action="replace",
        service_date=date(2026, 1, 1),
        engine_hours=Decimal("5"),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_overdue_by_hours():
    items = derive_due_items(
        rules=[_rule()],
        records=[_record(engine_hours=Decimal("5"))],
        current_hours=Decimal("20"),
        hours_estimated=False,
        today=date(2026, 2, 1),
    )
    assert items[0].status == "overdue"
    assert items[0].definitive is True


def test_estimated_hours_not_definitive_overdue():
    items = derive_due_items(
        rules=[_rule()],
        records=[_record(engine_hours=Decimal("5"))],
        current_hours=Decimal("20"),
        hours_estimated=True,
        today=date(2026, 2, 1),
    )
    assert items[0].status == "due_soon"
    assert items[0].definitive is False


def test_never_serviced():
    items = derive_due_items(
        rules=[_rule()],
        records=[],
        current_hours=Decimal("0"),
        hours_estimated=False,
        today=date(2026, 2, 1),
    )
    assert items[0].status == "never_serviced"


def test_calendar_overdue():
    items = derive_due_items(
        rules=[
            _rule(
                recurring_interval_hours=None,
                initial_interval_hours=None,
                calendar_interval_days=30,
            )
        ],
        records=[_record(service_date=date(2026, 1, 1))],
        current_hours=None,
        hours_estimated=True,
        today=date(2026, 3, 1),
    )
    assert items[0].status == "overdue"
    assert items[0].definitive is True
