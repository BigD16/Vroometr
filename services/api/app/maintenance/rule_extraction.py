"""AI proposes maintenance rules from manual passages. Validation is separate."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from vroometr.ai.ports import ChatModel
from vroometr.ai.unconfigured import UnconfiguredError

PIPELINE_VERSION = "maintenance-rule-extract-v1"
MAX_PASSAGES = 40

# Prefer pages that look like interval / service schedules to keep prompts bounded.
_INTERVAL_HINTS = re.compile(
    r"\b("
    r"hour|hours|every\s+\d+|interval|replace|inspect|lubricat|"
    r"service|maintenance|schedule|periodic|whichever|"
    r"calendar|month|months|km|mile"
    r")\b",
    re.IGNORECASE,
)

_PROPOSE_SYSTEM = """You extract motorcycle maintenance interval rules from manual text.
Return ONLY a JSON array. Each object must use these keys:
system, component, action, initial_interval_hours, recurring_interval_hours,
calendar_interval_days, whichever_comes_first, usage_condition_variant,
source_page, source_span, extraction_confidence.

Rules:
- system/component/action must match the provided taxonomy keys exactly.
- Intervals are numbers (hours or days). Use null when unknown.
- usage_condition_variant is one of: standard, severe, race, wet, dusty, mud, sand.
- source_span must be a verbatim quote from the passage (≥8 characters).
- source_page is 1-based page number from the passage header.
- extraction_confidence is 0–1.
- Do not invent intervals not supported by the text.
- If nothing extractable, return [].
"""


@dataclass(frozen=True, slots=True)
class SourcePassage:
    page: int  # 1-based for UI / provenance
    text: str
    document_id: str | None = None


def format_passages(passages: list[SourcePassage]) -> str:
    blocks: list[str] = []
    for item in passages:
        text = (item.text or "").strip()
        if not text:
            continue
        blocks.append(f"[page {item.page}]\n{text}")
    return "\n\n".join(blocks)


def select_maintenance_passages(
    pages: list[Any],
    *,
    document_id: str | None = None,
    max_passages: int = MAX_PASSAGES,
) -> list[SourcePassage]:
    """Pick completed pages likely to contain intervals. Prefers keyword hits."""
    scored: list[tuple[int, SourcePassage]] = []
    for page in pages:
        if getattr(page, "state", None) != "completed":
            continue
        text = (getattr(page, "text", None) or "").strip()
        if len(text) < 40:
            continue
        page_index = int(getattr(page, "page_index", 0))
        passage = SourcePassage(
            page=page_index + 1,
            text=text,
            document_id=document_id,
        )
        hits = len(_INTERVAL_HINTS.findall(text))
        if hits == 0:
            continue
        # Keyword hits rank first; earlier pages break ties.
        score = hits * 1000 - page_index
        scored.append((score, passage))
    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [passage for _, passage in scored[:max_passages]]
    selected.sort(key=lambda item: item.page)
    return selected


def propose_rules_from_passages(
    chat: ChatModel,
    passages: list[SourcePassage],
    *,
    taxonomy_hint: str,
) -> list[dict[str, Any]]:
    """Ask the chat model for structured proposals. Does not validate or persist."""
    body = format_passages(passages)
    if not body:
        return []
    messages = [
        {"role": "system", "content": _PROPOSE_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Taxonomy keys:\n{taxonomy_hint}\n\n"
                f"Manual passages:\n{body}\n\n"
                "Return the JSON array now."
            ),
        },
    ]
    try:
        raw = chat.complete(messages)
    except UnconfiguredError:
        raise
    return parse_proposed_rules(raw)


def parse_proposed_rules(raw: str) -> list[dict[str, Any]]:
    """Parse model JSON (array or fenced) into proposal dicts."""
    text = (raw or "").strip()
    if not text:
        return []
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        text = fenced.group(1).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start < 0 or end < start:
        return []
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    out: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict):
            out.append(item)
    return out


def taxonomy_hint() -> str:
    from app.maintenance.taxonomy import ACTIONS, COMPONENTS, SYSTEMS

    systems = []
    for key, label in SYSTEMS.items():
        comps = ", ".join(COMPONENTS.get(key, {}).keys())
        systems.append(f"- {key} ({label}): {comps}")
    actions = ", ".join(ACTIONS.keys())
    return "Systems/components:\n" + "\n".join(systems) + f"\nActions: {actions}"
