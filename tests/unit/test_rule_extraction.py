"""Independent validation + versioned activation for extracted rules."""

from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from app.maintenance.rule_extraction import parse_proposed_rules, select_maintenance_passages
from app.maintenance.rule_validation import validate_proposed_rule
from tests.unit.test_maintenance import setup_maintenance

SPAN = "Replace the engine oil every 10 hours of operation."


def _good_proposal(**kwargs):
    base = {
        "system": "engine",
        "component": "engine_oil",
        "action": "replace",
        "initial_interval_hours": None,
        "recurring_interval_hours": 10,
        "calendar_interval_days": None,
        "whichever_comes_first": True,
        "usage_condition_variant": "standard",
        "source_page": 12,
        "source_span": SPAN,
        "extraction_confidence": 0.9,
    }
    base.update(kwargs)
    return base


def test_validate_requires_span_and_taxonomy():
    ok = validate_proposed_rule(_good_proposal(), source_text=SPAN)
    assert ok.ok
    bad = validate_proposed_rule(
        _good_proposal(system="nope", source_span="short"),
        source_text="short",
    )
    assert not bad.ok
    assert any("system" in e.lower() or "Unknown" in e for e in bad.errors)


def test_span_must_appear_in_source():
    result = validate_proposed_rule(
        _good_proposal(),
        source_text="Unrelated manual text about torque specs.",
    )
    assert not result.ok


def test_parse_proposed_rules_fenced_json():
    raw = '```json\n[{"system":"engine","component":"engine_oil","action":"replace"}]\n```'
    rows = parse_proposed_rules(raw)
    assert rows[0]["component"] == "engine_oil"


def test_select_maintenance_passages_prefers_interval_pages():
    pages = [
        SimpleNamespace(
            page_index=0,
            state="completed",
            text="This chapter covers safety warnings and riding tips only.",
        ),
        SimpleNamespace(
            page_index=5,
            state="completed",
            text=(
                "Periodic maintenance schedule. Replace the engine oil every 10 hours. "
                "Inspect the air filter every 5 hours of service."
            ),
        ),
        SimpleNamespace(page_index=2, state="failed", text="Replace oil every 10 hours."),
    ]
    selected = select_maintenance_passages(pages, document_id=str(uuid4()), max_passages=2)
    assert len(selected) == 1
    assert selected[0].page == 6


def test_select_maintenance_passages_caps_prompt_size():
    huge = ("Replace oil every 10 hours. " * 400) + ("service maintenance schedule " * 200)
    pages = [
        SimpleNamespace(page_index=i, state="completed", text=huge) for i in range(30)
    ]
    selected = select_maintenance_passages(pages, document_id=str(uuid4()))
    assert selected
    assert len(selected) <= 12
    assert sum(len(p.text) for p in selected) <= 36_000
    assert all(len(p.text) <= 2500 for p in selected)


def test_accept_and_activate_versions():
    owner, _, bike, service, _ = setup_maintenance()
    first = service.accept_proposals(
        owner,
        bike_id=bike.id,
        proposals=[_good_proposal()],
        source_text=SPAN,
        activate=True,
    )
    assert len(first["accepted"]) == 1
    assert first["accepted"][0].active is True
    assert first["accepted"][0].validation_status == "active"
    assert first["accepted"][0].pipeline_version == "maintenance-rule-extract-v1"

    second = service.accept_proposals(
        owner,
        bike_id=bike.id,
        proposals=[_good_proposal(recurring_interval_hours=8)],
        source_text=SPAN,
        activate=False,
    )
    pending = second["accepted"][0]
    assert pending.active is False
    assert pending.validation_status == "validated"

    activated = service.activate_rule(owner, pending.id)
    assert activated.active is True
    assert activated.validation_status == "active"
    assert activated.rule_version == 2
    assert activated.supersedes_rule_id == first["accepted"][0].id

    active = service.list_rules(owner, bike.id)
    assert len(active) == 1
    assert active[0].id == activated.id
    assert float(active[0].recurring_interval_hours) == 8.0


def test_extract_from_document_skips_when_already_extracted():
    owner, _, bike, service, _ = setup_maintenance()
    doc_id = uuid4()
    service.accept_proposals(
        owner,
        bike_id=bike.id,
        proposals=[_good_proposal()],
        source_text=SPAN,
        document_id=doc_id,
        activate=True,
    )
    pages = [
        SimpleNamespace(
            page_index=0,
            state="completed",
            text=f"Maintenance schedule. {SPAN} Inspect chain every 5 hours.",
        )
    ]

    class FakeChat:
        def complete(self, messages):
            raise AssertionError("chat should not be called when skipped")

    result = service.extract_from_document(
        owner,
        bike_id=bike.id,
        document_id=doc_id,
        pages=pages,
        chat=FakeChat(),
        activate=True,
        force=False,
    )
    assert result["skipped"] is True
    assert result["reason"] == "already_extracted"


def test_extract_from_document_auto_activates():
    owner, _, bike, service, _ = setup_maintenance()
    doc_id = uuid4()
    pages = [
        SimpleNamespace(
            page_index=11,
            state="completed",
            text=f"Periodic maintenance. {SPAN}",
        )
    ]

    class FakeChat:
        def complete(self, messages):
            return (
                '[{"system":"engine","component":"engine_oil","action":"replace",'
                '"initial_interval_hours":null,"recurring_interval_hours":10,'
                '"calendar_interval_days":null,"whichever_comes_first":true,'
                '"usage_condition_variant":"standard","source_page":12,'
                f'"source_span":"{SPAN}","extraction_confidence":0.95}}]'
            )

    result = service.extract_from_document(
        owner,
        bike_id=bike.id,
        document_id=doc_id,
        pages=pages,
        chat=FakeChat(),
        activate=True,
        force=False,
    )
    assert not result.get("skipped")
    assert len(result["accepted"]) == 1
    assert result["accepted"][0].active is True
    assert result["accepted"][0].source_document_id == doc_id


def test_rejected_proposals_not_persisted():
    owner, _, bike, service, store = setup_maintenance()
    result = service.accept_proposals(
        owner,
        bike_id=bike.id,
        proposals=[_good_proposal(action="teleport")],
        source_text=SPAN,
    )
    assert result["accepted"] == []
    assert result["rejected"]
    assert store.rules == []


def test_due_state_uses_activated_extracted_rule():
    owner, _, bike, service, _ = setup_maintenance()
    service.accept_proposals(
        owner,
        bike_id=bike.id,
        proposals=[_good_proposal()],
        source_text=SPAN,
        activate=True,
    )
    service.create(
        owner,
        bike_id=bike.id,
        service_date=date(2026, 1, 1),
        system="engine",
        component="engine_oil",
        action="replace",
        reason="scheduled",
        performer_type="owner",
        engine_hours=1,
        engine_hours_is_estimated=False,
    )
    bike.current_engine_hours = 20
    bike.current_engine_hours_is_estimated = False
    items = service.due_state(owner, bike.id, today=date(2026, 2, 1))
    assert items[0].status == "overdue"
