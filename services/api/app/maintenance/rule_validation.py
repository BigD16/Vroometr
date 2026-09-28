"""Independent rule validation — no AI. Only validated proposals may activate."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from app.maintenance.taxonomy import ACTIONS, COMPONENTS, SYSTEMS

USAGE_VARIANTS = frozenset(
    {"standard", "severe", "race", "wet", "dusty", "mud", "sand"}
)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)


def validate_proposed_rule(
    proposal: dict[str, Any],
    *,
    source_text: str | None = None,
    require_source: bool = True,
) -> ValidationResult:
    """Check taxonomy, intervals/units, condition variant, and source span."""
    errors: list[str] = []
    system = _str(proposal.get("system"))
    component = _str(proposal.get("component"))
    action = _str(proposal.get("action"))

    if system not in SYSTEMS:
        errors.append("Unknown or missing system.")
    elif component not in (COMPONENTS.get(system) or {}):
        errors.append("Unknown or missing component for system.")
    if action not in ACTIONS:
        errors.append("Unknown or missing action.")

    initial = _hours(proposal.get("initial_interval_hours"), "initial_interval_hours", errors)
    recurring = _hours(
        proposal.get("recurring_interval_hours"), "recurring_interval_hours", errors
    )
    calendar = _days(proposal.get("calendar_interval_days"), errors)
    if initial is None and recurring is None and calendar is None:
        errors.append("Need at least one hours or calendar interval.")

    variant = _str(proposal.get("usage_condition_variant")) or "standard"
    if variant not in USAGE_VARIANTS:
        errors.append("Unknown usage_condition_variant.")

    span = _str(proposal.get("source_span"))
    page = proposal.get("source_page")
    if require_source:
        if not span or len(span) < 8:
            errors.append("source_span must quote the manual text (≥8 chars).")
        if page is not None:
            try:
                page_i = int(page)
                if page_i < 1:
                    errors.append("source_page must be 1-based when present.")
            except (TypeError, ValueError):
                errors.append("source_page must be an integer.")
        if span and source_text and _normalize(span) not in _normalize(source_text):
            errors.append("source_span does not appear in the provided source text.")

    confidence = proposal.get("extraction_confidence")
    if confidence is not None:
        try:
            conf = Decimal(str(confidence))
            if conf < 0 or conf > 1:
                errors.append("extraction_confidence must be between 0 and 1.")
        except (InvalidOperation, ValueError):
            errors.append("extraction_confidence must be numeric.")

    return ValidationResult(ok=not errors, errors=errors)


def _str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _hours(value: Any, field_name: str, errors: list[str]) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        hours = Decimal(str(value))
    except (InvalidOperation, ValueError):
        errors.append(f"{field_name} must be a number of hours.")
        return None
    if hours < 0:
        errors.append(f"{field_name} cannot be negative.")
        return None
    return hours


def _days(value: Any, errors: list[str]) -> int | None:
    if value is None or value == "":
        return None
    try:
        days = int(value)
    except (TypeError, ValueError):
        errors.append("calendar_interval_days must be an integer.")
        return None
    if days < 0:
        errors.append("calendar_interval_days cannot be negative.")
        return None
    return days


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())
