"""Citation and safety policy for assistant answers (DESIGN §7 and §13).

This module does not generate answers. It decides whether an exact critical value
may be stated, how citations should be shaped, and when mechanic escalation is
appropriate. The future ReasoningAgent calls these helpers after retrieval.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class ClaimRisk(StrEnum):
    """How bad it is if an exact value is wrong."""

    SAFETY_CRITICAL = "safety_critical"
    LOWER_RISK = "lower_risk"


class AnswerAction(StrEnum):
    PROVIDE_WITH_CITATION = "provide_with_citation"
    WITHHOLD_EXACT_VALUE = "withhold_exact_value"
    PROVIDE_LABELED_NON_AUTHORITATIVE = "provide_labeled_non_authoritative"
    ESCALATE = "escalate"


class EscalationReason(StrEnum):
    IMMEDIATE_SAFETY_RISK = "immediate_safety_risk"
    UNVERIFIABLE_CRITICAL_SPEC = "unverifiable_critical_spec"
    BRAKE_STEERING_STRUCTURAL_FUEL_FIRE = "brake_steering_structural_fuel_fire"
    NARROW_TOLERANCE_TOOLING = "narrow_tolerance_tooling"
    PERSISTENT_UNCERTAINTY = "persistent_uncertainty"


@dataclass(frozen=True, slots=True)
class Citation:
    """Layered source chip payload for UI / answer drafts."""

    kind: str
    label: str
    document_id: str | None = None
    attachment_id: str | None = None
    document_type: str | None = None
    section_title: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    is_primary: bool | None = None
    file_name: str | None = None
    incomplete: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ClaimAnswerDecision:
    action: AnswerAction
    code: str
    reason: str
    citations: tuple[Citation, ...] = ()
    escalate: bool = False
    escalation_reasons: tuple[EscalationReason, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "code": self.code,
            "reason": self.reason,
            "citations": [item.as_dict() for item in self.citations],
            "escalate": self.escalate,
            "escalation_reasons": [item.value for item in self.escalation_reasons],
        }


def is_authoritative_manual_passage(passage: Mapping[str, Any]) -> bool:
    """Manufacturer manuals (especially primary) count as authoritative for specs."""
    document_type = passage.get("document_type")
    if document_type == "manufacturer_manual":
        return True
    return bool(passage.get("is_primary"))


def citations_from_retrieval_passages(
    passages: Sequence[Mapping[str, Any]],
) -> list[Citation]:
    """Build expandable Sources entries from retrieval passage dicts.

    Accepts either flat Passage dicts or RetrievalService Match dicts
    (`{"passage": {...}, "confidence": ...}`).
    """
    citations: list[Citation] = []
    for raw in passages:
        passage = _coerce_passage(raw)
        if passage is None:
            continue
        page_start = passage.get("page_start")
        page_end = passage.get("page_end")
        # Chunk page indexes are 0-based; Sources labels use 1-based PDF pages.
        label_start = page_start + 1 if isinstance(page_start, int) else None
        label_end = page_end + 1 if isinstance(page_end, int) else None
        section = passage.get("section_title") or "Section"
        if label_start is not None and label_end is not None and label_start != label_end:
            pages = f"pp. {label_start}-{label_end}"
        elif label_start is not None:
            pages = f"p. {label_start}"
        else:
            pages = "page unknown"
        label = f"{section} · {pages}"
        file_name = passage.get("file_name")
        if file_name:
            label = f"{file_name} · {label}"
        citations.append(
            Citation(
                kind="manual",
                label=label,
                document_id=_str_or_none(passage.get("document_id")),
                attachment_id=_str_or_none(passage.get("attachment_id")),
                document_type=_str_or_none(passage.get("document_type")),
                section_title=_str_or_none(passage.get("section_title")),
                page_start=page_start if isinstance(page_start, int) else None,
                page_end=page_end if isinstance(page_end, int) else None,
                is_primary=bool(passage.get("is_primary"))
                if "is_primary" in passage
                else None,
                file_name=_str_or_none(file_name),
                incomplete=bool(passage.get("incomplete", False)),
            )
        )
    return citations


def evaluate_claim_answer(
    *,
    risk: ClaimRisk,
    authoritative_sources_found: bool,
    citations: Sequence[Citation] = (),
    escalation_reasons: Sequence[EscalationReason] = (),
) -> ClaimAnswerDecision:
    """Decide whether an exact value may be stated for a claim.

    LOCKED:
    - authoritative source found → provide value + citation
    - no authoritative source + safety/engine-critical → withhold exact number
    - no authoritative source + lower-risk → labeled non-authoritative guidance OK
    """
    reasons = tuple(escalation_reasons)
    cite = tuple(citations)
    if reasons:
        return ClaimAnswerDecision(
            action=AnswerAction.ESCALATE,
            code="escalate",
            reason=_escalation_message(reasons),
            citations=cite,
            escalate=True,
            escalation_reasons=reasons,
        )
    if authoritative_sources_found:
        return ClaimAnswerDecision(
            action=AnswerAction.PROVIDE_WITH_CITATION,
            code="provide_with_citation",
            reason="Authoritative source found; state the value with citation.",
            citations=cite,
        )
    if risk is ClaimRisk.SAFETY_CRITICAL:
        return ClaimAnswerDecision(
            action=AnswerAction.WITHHOLD_EXACT_VALUE,
            code="withhold_exact_value",
            reason=(
                "No authoritative source for a safety/engine-critical value. "
                "Withhold the exact number and say what is missing."
            ),
            citations=cite,
            escalate=True,
            escalation_reasons=(EscalationReason.UNVERIFIABLE_CRITICAL_SPEC,),
        )
    return ClaimAnswerDecision(
        action=AnswerAction.PROVIDE_LABELED_NON_AUTHORITATIVE,
        code="labeled_non_authoritative",
        reason=(
            "No authoritative source for a lower-risk topic. "
            "Guidance may be offered only when clearly labeled non-authoritative."
        ),
        citations=cite,
    )


def evaluate_escalation(
    *,
    immediate_safety_risk: bool = False,
    unverifiable_critical_spec: bool = False,
    brake_steering_structural_fuel_fire: bool = False,
    narrow_tolerance_tooling: bool = False,
    persistent_uncertainty: bool = False,
) -> tuple[EscalationReason, ...]:
    """Risk/evidence escalation only. Difficulty alone is not a reason."""
    reasons: list[EscalationReason] = []
    if immediate_safety_risk:
        reasons.append(EscalationReason.IMMEDIATE_SAFETY_RISK)
    if unverifiable_critical_spec:
        reasons.append(EscalationReason.UNVERIFIABLE_CRITICAL_SPEC)
    if brake_steering_structural_fuel_fire:
        reasons.append(EscalationReason.BRAKE_STEERING_STRUCTURAL_FUEL_FIRE)
    if narrow_tolerance_tooling:
        reasons.append(EscalationReason.NARROW_TOLERANCE_TOOLING)
    if persistent_uncertainty:
        reasons.append(EscalationReason.PERSISTENT_UNCERTAINTY)
    return tuple(reasons)


def decide_from_retrieval(
    *,
    risk: ClaimRisk,
    retrieval: Mapping[str, Any],
    immediate_safety_risk: bool = False,
    brake_steering_structural_fuel_fire: bool = False,
    narrow_tolerance_tooling: bool = False,
    persistent_uncertainty: bool = False,
) -> ClaimAnswerDecision:
    """Convenience: build citations from a RetrievalService-style payload and decide."""
    passages = extract_retrieval_passages(retrieval)
    citations = citations_from_retrieval_passages(passages)
    authoritative = any(is_authoritative_manual_passage(item) for item in passages)
    escalation = evaluate_escalation(
        immediate_safety_risk=immediate_safety_risk,
        unverifiable_critical_spec=(
            risk is ClaimRisk.SAFETY_CRITICAL and not authoritative
        ),
        brake_steering_structural_fuel_fire=brake_steering_structural_fuel_fire,
        narrow_tolerance_tooling=narrow_tolerance_tooling,
        persistent_uncertainty=persistent_uncertainty,
    )
    # evaluate_claim_answer already escalates on unverifiable critical; avoid double-counting
    # by only passing non-redundant explicit escalation flags when sources exist or risk is lower.
    if authoritative or risk is ClaimRisk.LOWER_RISK:
        return evaluate_claim_answer(
            risk=risk,
            authoritative_sources_found=authoritative,
            citations=citations,
            escalation_reasons=tuple(
                reason
                for reason in escalation
                if reason is not EscalationReason.UNVERIFIABLE_CRITICAL_SPEC
            ),
        )
    return evaluate_claim_answer(
        risk=risk,
        authoritative_sources_found=False,
        citations=citations,
        escalation_reasons=(),
    )


def extract_retrieval_passages(retrieval: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Normalize RetrievalService Match payloads into flat passage dicts."""
    passages: list[dict[str, Any]] = []
    for item in retrieval.get("passages") or []:
        passage = _coerce_passage(item)
        if passage is not None:
            passages.append(passage)
    return passages


def _coerce_passage(item: Mapping[str, Any] | Any) -> dict[str, Any] | None:
    if not isinstance(item, Mapping):
        return None
    if "passage" in item and isinstance(item["passage"], Mapping):
        return dict(item["passage"])
    # Flat passage dicts already have text / page_start; Match wrappers do not.
    if "page_start" in item or "text" in item or "section_title" in item:
        return dict(item)
    return None


def _escalation_message(reasons: Sequence[EscalationReason]) -> str:
    labels = ", ".join(reason.value for reason in reasons)
    return (
        "Escalate to a professional mechanic for: "
        f"{labels}. Still explain what is suspected, ruled out, and what to check next."
    )


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
