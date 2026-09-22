from app.assistant_tools.citations import (
    AnswerAction,
    ClaimRisk,
    EscalationReason,
    citations_from_retrieval_passages,
    decide_from_retrieval,
    evaluate_claim_answer,
    evaluate_escalation,
    is_authoritative_manual_passage,
)


def test_authoritative_source_allows_exact_value_with_citation():
    citations = citations_from_retrieval_passages(
        [
            {
                "document_id": "11111111-1111-1111-1111-111111111111",
                "attachment_id": "22222222-2222-2222-2222-222222222222",
                "document_type": "manufacturer_manual",
                "section_title": "Cylinder head",
                "page_start": 42,
                "page_end": 42,
                "is_primary": True,
                "file_name": "yz250f.pdf",
                "incomplete": False,
            }
        ]
    )
    decision = evaluate_claim_answer(
        risk=ClaimRisk.SAFETY_CRITICAL,
        authoritative_sources_found=True,
        citations=citations,
    )
    assert decision.action is AnswerAction.PROVIDE_WITH_CITATION
    assert decision.escalate is False
    assert decision.citations[0].label.startswith("yz250f.pdf")
    assert "p. 42" in decision.citations[0].label


def test_safety_critical_without_source_withholds_and_escalates():
    decision = evaluate_claim_answer(
        risk=ClaimRisk.SAFETY_CRITICAL,
        authoritative_sources_found=False,
    )
    assert decision.action is AnswerAction.WITHHOLD_EXACT_VALUE
    assert decision.code == "withhold_exact_value"
    assert decision.escalate is True
    assert EscalationReason.UNVERIFIABLE_CRITICAL_SPEC in decision.escalation_reasons


def test_lower_risk_without_source_is_labeled_non_authoritative():
    decision = evaluate_claim_answer(
        risk=ClaimRisk.LOWER_RISK,
        authoritative_sources_found=False,
    )
    assert decision.action is AnswerAction.PROVIDE_LABELED_NON_AUTHORITATIVE
    assert decision.escalate is False


def test_difficulty_alone_does_not_escalate():
    assert evaluate_escalation() == ()
    assert evaluate_escalation(persistent_uncertainty=True) == (
        EscalationReason.PERSISTENT_UNCERTAINTY,
    )


def test_decide_from_retrieval_uses_manual_passages():
    retrieval = {
        "status": "ok",
        "passages": [
            {
                "passage": {
                    "document_type": "manufacturer_manual",
                    "is_primary": True,
                    "section_title": "Torque",
                    "page_start": 10,
                    "page_end": 11,
                    "file_name": "manual.pdf",
                }
            }
        ],
    }
    decision = decide_from_retrieval(risk=ClaimRisk.SAFETY_CRITICAL, retrieval=retrieval)
    assert decision.action is AnswerAction.PROVIDE_WITH_CITATION
    assert is_authoritative_manual_passage(retrieval["passages"][0]["passage"])

    empty = decide_from_retrieval(risk=ClaimRisk.SAFETY_CRITICAL, retrieval={"passages": []})
    assert empty.action is AnswerAction.WITHHOLD_EXACT_VALUE
