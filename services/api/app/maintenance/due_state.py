"""Pure due-state derivation. Never persists next_due."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

DUE_SOON_HOURS = Decimal("5.0")
DUE_SOON_DAYS = 14


@dataclass(frozen=True, slots=True)
class DueItem:
    rule_id: UUID
    system: str
    component: str
    action: str
    usage_condition_variant: str
    status: str  # never_serviced | ok | due_soon | overdue | unknown
    definitive: bool
    hours_remaining: float | None
    days_remaining: int | None
    last_service_date: str | None
    last_service_hours: float | None
    note: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def derive_due_items(
    *,
    rules: list[Any],
    records: list[Any],
    current_hours: Decimal | float | None,
    hours_estimated: bool,
    today: date,
) -> list[DueItem]:
    """Compute due state from active rules + history + current hours/date."""
    hours = None if current_hours is None else Decimal(str(current_hours))
    items: list[DueItem] = []
    for rule in rules:
        if not getattr(rule, "active", True):
            continue
        if getattr(rule, "validation_status", "active") not in {"active", "validated"}:
            continue
        last = _last_match(records, rule.system, rule.component, rule.action)
        items.append(
            _evaluate_rule(
                rule,
                last=last,
                hours=hours,
                hours_estimated=hours_estimated,
                today=today,
            )
        )
    order = {"overdue": 0, "due_soon": 1, "never_serviced": 2, "unknown": 3, "ok": 4}
    items.sort(key=lambda item: (order.get(item.status, 9), item.system, item.component))
    return items


def _last_match(records: list[Any], system: str, component: str, action: str):
    matches = [
        row
        for row in records
        if row.system == system and row.component == component and row.action == action
    ]
    if not matches:
        return None
    return max(matches, key=lambda row: (row.service_date, row.created_at))


def _evaluate_rule(
    rule,
    *,
    last,
    hours: Decimal | None,
    hours_estimated: bool,
    today: date,
) -> DueItem:
    recurring = rule.recurring_interval_hours
    initial = rule.initial_interval_hours
    calendar_days = rule.calendar_interval_days
    first = bool(rule.whichever_comes_first)

    if last is None:
        hour_due = _threshold_from_zero(initial if initial is not None else recurring, hours)
        day_due = None  # no calendar baseline without a service date
        status, definitive, note = _combine(
            hour_due,
            day_due,
            first=first,
            hours_estimated=hours_estimated,
            never_serviced=True,
        )
        return DueItem(
            rule_id=rule.id,
            system=rule.system,
            component=rule.component,
            action=rule.action,
            usage_condition_variant=rule.usage_condition_variant,
            status=status,
            definitive=definitive,
            hours_remaining=hour_due,
            days_remaining=day_due,
            last_service_date=None,
            last_service_hours=None,
            note=note,
        )

    hour_due = None
    interval = recurring if recurring is not None else initial
    if interval is not None and last.engine_hours is not None and hours is not None:
        hour_due = float(Decimal(str(last.engine_hours)) + Decimal(str(interval)) - hours)
    elif interval is not None and (last.engine_hours is None or hours is None):
        hour_due = None  # unknown until hours exist

    day_due = None
    if calendar_days is not None:
        target = last.service_date + timedelta(days=int(calendar_days))
        day_due = (target - today).days

    status, definitive, note = _combine(
        hour_due,
        day_due,
        first=first,
        hours_estimated=hours_estimated,
        never_serviced=False,
    )
    return DueItem(
        rule_id=rule.id,
        system=rule.system,
        component=rule.component,
        action=rule.action,
        usage_condition_variant=rule.usage_condition_variant,
        status=status,
        definitive=definitive,
        hours_remaining=hour_due,
        days_remaining=day_due,
        last_service_date=last.service_date.isoformat(),
        last_service_hours=float(last.engine_hours) if last.engine_hours is not None else None,
        note=note,
    )


def _threshold_from_zero(interval, hours: Decimal | None) -> float | None:
    if interval is None:
        return None
    if hours is None:
        return None
    return float(Decimal(str(interval)) - hours)


def _combine(
    hour_due: float | None,
    day_due: int | None,
    *,
    first: bool,
    hours_estimated: bool,
    never_serviced: bool,
) -> tuple[str, bool, str | None]:
    hour_status = _hours_status(hour_due)
    day_status = _days_status(day_due)
    statuses = [s for s in (hour_status, day_status) if s is not None]
    if not statuses:
        if never_serviced:
            return "never_serviced", True, "No matching service logged yet."
        return "unknown", False, "Need engine hours or a calendar interval to score this rule."

    if first:
        rank = {"overdue": 0, "due_soon": 1, "ok": 2}
        status = min(statuses, key=lambda s: rank[s])
    else:
        # All applicable thresholds must be due before overdue; otherwise take worst soft signal.
        if all(s == "overdue" for s in statuses) and len(statuses) > 1:
            status = "overdue"
        elif "overdue" in statuses and len(statuses) == 1:
            status = "overdue"
        elif "due_soon" in statuses or "overdue" in statuses:
            status = "due_soon" if "ok" in statuses else max(
                statuses, key=lambda s: {"ok": 0, "due_soon": 1, "overdue": 2}[s]
            )
        else:
            status = "ok"

    definitive = True
    note = None
    if status == "overdue" and hours_estimated and hour_status == "overdue" and (
        day_status is None or day_status == "ok"
    ):
        # LOCKED 6.5 intent: do not claim definitive overdue on estimates alone.
        status = "due_soon"
        definitive = False
        note = "Hours are estimated; treat as advisory, not definitive overdue."
    elif never_serviced and status == "ok":
        status = "never_serviced"
        note = "No matching service logged yet."
    return status, definitive, note


def _hours_status(remaining: float | None) -> str | None:
    if remaining is None:
        return None
    if remaining <= 0:
        return "overdue"
    if remaining <= float(DUE_SOON_HOURS):
        return "due_soon"
    return "ok"


def _days_status(remaining: int | None) -> str | None:
    if remaining is None:
        return None
    if remaining <= 0:
        return "overdue"
    if remaining <= DUE_SOON_DAYS:
        return "due_soon"
    return "ok"
