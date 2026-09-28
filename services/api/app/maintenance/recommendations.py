"""Two-layer maintenance recommendations. Manufacturer intervals are never rewritten here."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import UUID

from app.maintenance.due_state import DueItem

# LOCKED condition factors that may justify earlier action — never new intervals.
ALLOWED_CONTEXT_TAGS = frozenset(
    {"dust", "sand", "mud", "wet", "race", "racing", "upcoming_ride", "modification", "symptom"}
)

_URGENCY = {"overdue": 0, "due_soon": 1, "never_serviced": 2, "unknown": 3, "ok": 4}


@dataclass(frozen=True, slots=True)
class BaselineRecommendation:
    rule_id: UUID
    system: str
    component: str
    action: str
    usage_condition_variant: str
    status: str
    definitive: bool
    manufacturer_initial_interval_hours: float | None
    manufacturer_recurring_interval_hours: float | None
    manufacturer_calendar_interval_days: int | None
    hours_remaining: float | None
    days_remaining: int | None
    priority: str  # act_now | plan_soon | monitor | unknown
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ContextualRecommendation:
    rule_id: UUID
    system: str
    component: str
    action: str
    advice: str
    consider_earlier: bool
    context_tags: list[str] = field(default_factory=list)
    source: str = "deterministic_hints"  # deterministic_hints | ai
    # Explicit lock: contextual layer never carries rewritten intervals.
    manufacturer_intervals_unchanged: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RecommendationBundle:
    baseline: list[BaselineRecommendation]
    contextual: list[ContextualRecommendation]
    manufacturer_intervals_unchanged: bool = True
    note: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "baseline": [item.as_dict() for item in self.baseline],
            "contextual": [item.as_dict() for item in self.contextual],
            "manufacturer_intervals_unchanged": self.manufacturer_intervals_unchanged,
            "note": self.note,
        }


def build_baseline(
    due_items: list[DueItem],
    rules: list[Any],
) -> list[BaselineRecommendation]:
    """Deterministic layer: due state + manufacturer intervals from active rules."""
    by_id = {rule.id: rule for rule in rules}
    out: list[BaselineRecommendation] = []
    for item in due_items:
        rule = by_id.get(item.rule_id)
        initial = _hours(getattr(rule, "initial_interval_hours", None) if rule else None)
        recurring = _hours(getattr(rule, "recurring_interval_hours", None) if rule else None)
        calendar = getattr(rule, "calendar_interval_days", None) if rule else None
        priority = _priority(item.status)
        out.append(
            BaselineRecommendation(
                rule_id=item.rule_id,
                system=item.system,
                component=item.component,
                action=item.action,
                usage_condition_variant=item.usage_condition_variant,
                status=item.status,
                definitive=item.definitive,
                manufacturer_initial_interval_hours=initial,
                manufacturer_recurring_interval_hours=recurring,
                manufacturer_calendar_interval_days=calendar,
                hours_remaining=item.hours_remaining,
                days_remaining=item.days_remaining,
                priority=priority,
                summary=_baseline_summary(item, recurring, calendar),
            )
        )
    out.sort(key=lambda row: (_URGENCY.get(row.status, 9), row.system, row.component))
    return out


def apply_condition_hints(
    baseline: list[BaselineRecommendation],
    context_tags: list[str],
) -> list[ContextualRecommendation]:
    """Deterministic contextual hints. May urge earlier action; never changes intervals."""
    tags = _normalize_tags(context_tags)
    if not tags or not baseline:
        return []
    harsh = tags & {"dust", "sand", "mud", "wet", "race", "racing"}
    ride = "upcoming_ride" in tags
    extra = tags & {"modification", "symptom"}
    out: list[ContextualRecommendation] = []
    for item in baseline:
        if item.status == "ok" and not (harsh or ride or extra):
            continue
        consider = bool(harsh or ride) and item.status in {
            "ok",
            "due_soon",
            "never_serviced",
            "unknown",
        }
        if item.status == "overdue":
            advice = (
                "Manufacturer interval is overdue. Condition tags do not change that interval — "
                f"address this before heavy use ({', '.join(sorted(tags))})."
            )
            consider = True
        elif consider and harsh:
            advice = (
                f"Manufacturer schedule still stands "
                f"({_interval_phrase(item)}). With {', '.join(sorted(harsh))} conditions, "
                "consider doing this sooner than the calendar/hours alone suggest."
            )
        elif consider and ride:
            advice = (
                f"Upcoming ride: manufacturer schedule still stands "
                f"({_interval_phrase(item)}). Consider completing this before you ride."
            )
        elif extra and item.status in {"due_soon", "never_serviced", "overdue"}:
            advice = (
                f"Manufacturer schedule still stands ({_interval_phrase(item)}). "
                "Modifications or symptoms may justify earlier attention — intervals are unchanged."
            )
        else:
            continue
        out.append(
            ContextualRecommendation(
                rule_id=item.rule_id,
                system=item.system,
                component=item.component,
                action=item.action,
                advice=advice,
                consider_earlier=consider,
                context_tags=sorted(tags),
                source="deterministic_hints",
            )
        )
    return out


def enrich_contextual_with_ai(
    baseline: list[BaselineRecommendation],
    existing: list[ContextualRecommendation],
    *,
    context_tags: list[str],
    chat: Any,
) -> list[ContextualRecommendation]:
    """Optional AI layer. Strips any invented intervals; keeps manufacturer schedule intact."""
    tags = _normalize_tags(context_tags)
    if not baseline:
        return existing
    payload = {
        "context_tags": sorted(tags),
        "baseline": [
            {
                "rule_id": str(item.rule_id),
                "system": item.system,
                "component": item.component,
                "action": item.action,
                "status": item.status,
                "manufacturer_recurring_interval_hours": item.manufacturer_recurring_interval_hours,
                "manufacturer_calendar_interval_days": item.manufacturer_calendar_interval_days,
                "summary": item.summary,
            }
            for item in baseline
            if item.status != "ok" or tags
        ][:12],
    }
    messages = [
        {
            "role": "system",
            "content": (
                "You add optional earlier-action advice for motorcycle maintenance. "
                "Return ONLY a JSON array of objects with keys: "
                "rule_id, advice, consider_earlier. "
                "You MUST NOT invent, change, or quote different "
                "hour/day intervals than the baseline. "
                "Manufacturer intervals are fixed. If nothing useful, return []."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(payload),
        },
    ]
    raw = chat.complete(messages)
    parsed = _parse_ai_list(raw)
    by_id = {str(item.rule_id): item for item in baseline}
    enriched: list[ContextualRecommendation] = list(existing)
    seen = {str(item.rule_id) for item in existing}
    for row in parsed:
        if not isinstance(row, dict):
            continue
        rule_id = str(row.get("rule_id") or "")
        base = by_id.get(rule_id)
        if base is None or rule_id in seen:
            continue
        advice = str(row.get("advice") or "").strip()
        if len(advice) < 12:
            continue
        if _mentions_conflicting_interval(advice, base):
            continue
        enriched.append(
            ContextualRecommendation(
                rule_id=base.rule_id,
                system=base.system,
                component=base.component,
                action=base.action,
                advice=advice[:1000],
                consider_earlier=bool(row.get("consider_earlier", True)),
                context_tags=sorted(tags),
                source="ai",
            )
        )
        seen.add(rule_id)
    return enriched


def build_recommendations(
    *,
    due_items: list[DueItem],
    rules: list[Any],
    context_tags: list[str] | None = None,
    chat: Any | None = None,
    include_ai: bool = False,
) -> RecommendationBundle:
    baseline = build_baseline(due_items, rules)
    tags = _normalize_tags(context_tags or [])
    contextual = apply_condition_hints(baseline, sorted(tags))
    note = None
    if include_ai and chat is not None and (tags or any(b.status != "ok" for b in baseline)):
        try:
            contextual = enrich_contextual_with_ai(
                baseline, contextual, context_tags=sorted(tags), chat=chat
            )
        except Exception:  # noqa: BLE001 — advisory layer must not break baseline
            note = "AI contextual layer unavailable; showing deterministic baseline and hints."
    return RecommendationBundle(
        baseline=baseline,
        contextual=contextual,
        manufacturer_intervals_unchanged=True,
        note=note,
    )


def _normalize_tags(tags: list[str]) -> set[str]:
    out: set[str] = set()
    for tag in tags:
        key = str(tag or "").strip().lower().replace(" ", "_")
        if key == "racing":
            key = "race"
        if key in ALLOWED_CONTEXT_TAGS:
            out.add(key)
    return out


def _priority(status: str) -> str:
    if status == "overdue":
        return "act_now"
    if status in {"due_soon", "never_serviced"}:
        return "plan_soon"
    if status == "ok":
        return "monitor"
    return "unknown"


def _baseline_summary(
    item: DueItem,
    recurring: float | None,
    calendar: int | None,
) -> str:
    interval = []
    if recurring is not None:
        interval.append(f"every {recurring:g} h")
    if calendar is not None:
        interval.append(f"every {calendar} days")
    schedule = " / ".join(interval) if interval else "manufacturer schedule"
    label = f"{item.action} {item.component.replace('_', ' ')}"
    if item.status == "overdue":
        suffix = "overdue vs manufacturer schedule"
        if not item.definitive:
            suffix += " (hours estimated — advisory)"
        return f"{label}: {suffix}. Interval unchanged ({schedule})."
    if item.status == "due_soon":
        return f"{label}: due soon on manufacturer schedule ({schedule})."
    if item.status == "never_serviced":
        return f"{label}: no matching service logged yet ({schedule})."
    if item.status == "ok":
        return f"{label}: within manufacturer schedule ({schedule})."
    return f"{label}: need more hours/date data ({schedule})."


def _interval_phrase(item: BaselineRecommendation) -> str:
    parts = []
    if item.manufacturer_recurring_interval_hours is not None:
        parts.append(f"{item.manufacturer_recurring_interval_hours:g} h")
    if item.manufacturer_calendar_interval_days is not None:
        parts.append(f"{item.manufacturer_calendar_interval_days} days")
    return " / ".join(parts) if parts else "published interval"


def _hours(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _parse_ai_list(raw: str) -> list[Any]:
    text = (raw or "").strip()
    if not text:
        return []
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        text = fenced.group(1).strip()
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < start:
        return []
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _mentions_conflicting_interval(advice: str, base: BaselineRecommendation) -> bool:
    """Reject AI text that asserts a different numeric interval than the baseline."""
    pattern = r"(\d+(?:\.\d+)?)\s*(?:h|hr|hour|hours)\b"
    numbers = [float(n) for n in re.findall(pattern, advice, re.I)]
    allowed = {
        v
        for v in (
            base.manufacturer_recurring_interval_hours,
            base.manufacturer_initial_interval_hours,
        )
        if v is not None
    }
    for num in numbers:
        if allowed and all(abs(num - a) > 0.05 for a in allowed):
            return True
    day_nums = [int(n) for n in re.findall(r"(\d+)\s*(?:day|days)\b", advice, re.I)]
    cal = base.manufacturer_calendar_interval_days
    if cal is not None:
        for num in day_nums:
            if num != cal:
                return True
    return False
