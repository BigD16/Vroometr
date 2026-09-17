from dataclasses import asdict
from types import SimpleNamespace

import pytest
from evals.manuals import grade
from evals.retrieval import passage


def response():
    source = passage(text="Verified\nfixture evidence with conditions.")
    key = (source.document_id, source.page_start)
    originals = {
        key: SimpleNamespace(
            text=source.text,
            source_hash=source.source_hash,
            extraction_version="fixture-extraction",
            state="completed",
        )
    }
    result = {"status": "ready", "passages": [{"passage": asdict(source)}]}
    case = {"expected_pages": ["fixture"], "required_text": ["Verified fixture evidence"]}
    return case, result, {key: "fixture"}, originals


def test_gold_comparison_ignores_pdf_wrapping_but_provenance_is_verbatim():
    case, result, mapping, originals = response()
    assert grade(case, result, mapping, originals)[0] == []
    result["passages"][0]["passage"]["text"] = "Verified fixture evidence with conditions."
    assert "invalid_provenance" in grade(case, result, mapping, originals)[0]


@pytest.mark.parametrize(
    "field,value",
    [("source_hash", "wrong"), ("page_start", 9), ("content_hash", "wrong"), ("page_end", 1)],
)
def test_grader_rejects_wrong_source_identity(field, value):
    case, result, mapping, originals = response()
    result["passages"][0]["passage"][field] = value
    assert grade(case, result, mapping, originals)[0]


def test_grader_rejects_missing_conditions_and_unsupported_returns():
    case, result, mapping, originals = response()
    case["required_text"] = ["condition not present"]
    assert "value_unit_or_condition_missing" in grade(case, result, mapping, originals)[0]
    case["expected_pages"] = []
    assert "unsupported_evidence_returned" in grade(case, result, mapping, originals)[0]


def test_grader_rejects_visual_pending_and_injection_sources():
    case, result, mapping, originals = response()
    for page in originals.values():
        page.state = "pending_provider"
    assert "invalid_provenance" in grade(case, result, mapping, originals)[0]
    mapping = {key: "attack" for key in mapping}
    assert "forbidden_evidence" in grade(case, result, mapping, originals)[0]


def test_grader_rejects_context_overflow():
    case, result, mapping, originals = response()
    result["passages"] *= 9
    assert "context_limit_exceeded" in grade(case, result, mapping, originals)[0]
