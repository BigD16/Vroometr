"""Two-layer recommendations: baseline + contextual without rewriting intervals."""

from types import SimpleNamespace
from uuid import uuid4

from app.maintenance.due_state import DueItem
from app.maintenance.recommendations import (
    apply_condition_hints,
    build_baseline,
    build_recommendations,
    enrich_contextual_with_ai,
)


def _due(**kwargs):
    base = dict(
        rule_id=uuid4(),
        system="engine",
        component="engine_oil",
        action="replace",
        usage_condition_variant="standard",
        status="due_soon",
        definitive=True,
        hours_remaining=2.0,
        days_remaining=None,
        last_service_date="2026-01-01",
        last_service_hours=5.0,
        note=None,
    )
    base.update(kwargs)
    return DueItem(**base)


def _rule(rule_id, **kwargs):
    base = dict(
        id=rule_id,
        initial_interval_hours=None,
        recurring_interval_hours=10,
        calendar_interval_days=None,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_baseline_preserves_manufacturer_intervals():
    item = _due()
    baseline = build_baseline([item], [_rule(item.rule_id)])
    assert len(baseline) == 1
    assert baseline[0].manufacturer_recurring_interval_hours == 10.0
    assert baseline[0].priority == "plan_soon"
    assert "10" in baseline[0].summary
    assert "unchanged" in baseline[0].summary or "schedule" in baseline[0].summary


def test_condition_hints_urge_earlier_without_new_intervals():
    item = _due(status="ok", hours_remaining=8.0)
    baseline = build_baseline([item], [_rule(item.rule_id)])
    contextual = apply_condition_hints(baseline, ["dust", "mud"])
    assert contextual
    assert contextual[0].consider_earlier is True
    assert contextual[0].manufacturer_intervals_unchanged is True
    assert "still stands" in contextual[0].advice


def test_ai_conflicting_interval_is_rejected():
    item = _due()
    baseline = build_baseline([item], [_rule(item.rule_id)])

    class BadChat:
        def complete(self, messages):
            return (
                f'[{{"rule_id":"{item.rule_id}",'
                '"advice":"Change oil every 3 hours instead.",'
                '"consider_earlier":true}]'
            )

    enriched = enrich_contextual_with_ai(
        baseline, [], context_tags=["dust"], chat=BadChat()
    )
    assert enriched == []


def test_ai_advisory_without_rewrite_is_kept():
    item = _due()
    baseline = build_baseline([item], [_rule(item.rule_id)])

    class GoodChat:
        def complete(self, messages):
            return (
                f'[{{"rule_id":"{item.rule_id}",'
                '"advice":"With dusty conditions, consider doing this sooner '
                'while keeping the manufacturer 10 hour interval.",'
                '"consider_earlier":true}]'
            )

    enriched = enrich_contextual_with_ai(
        baseline, [], context_tags=["dust"], chat=GoodChat()
    )
    assert len(enriched) == 1
    assert enriched[0].source == "ai"
    assert enriched[0].manufacturer_intervals_unchanged is True


def test_bundle_flag_always_true():
    item = _due(status="overdue")
    bundle = build_recommendations(
        due_items=[item],
        rules=[_rule(item.rule_id)],
        context_tags=["race"],
        include_ai=False,
    )
    assert bundle.manufacturer_intervals_unchanged is True
    assert bundle.baseline
    assert bundle.contextual
