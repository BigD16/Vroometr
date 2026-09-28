"""AI proposes maintenance rules from manual passages. Validation is separate."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from vroometr.ai.chat import ChatFailed
from vroometr.ai.ports import ChatModel
from vroometr.ai.unconfigured import UnconfiguredError

PIPELINE_VERSION = "maintenance-rule-extract-v1"
MAX_PASSAGES = 12
MAX_CHARS_PER_PAGE = 2500
MAX_TOTAL_CHARS = 36_000
BATCH_CHAR_BUDGET = 12_000

# Prefer pages that look like interval / service schedules to keep prompts bounded.
_INTERVAL_HINTS = re.compile(
    r"\b("
    r"hour|hours|hrs?|every\s+\d+|interval|replace|inspect|lubricat|"
    r"service|maintenance|schedule|periodic|whichever|"
    r"calendar|month|months|km|mile"
    r")\b",
    re.IGNORECASE,
)
_STRONG_INTERVAL = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b|every\s+(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_SCHEDULE_HEADER = re.compile(
    r"maintenance\s+intervals|regular\s+inspection|periodic\s+maintenance|"
    r"service\s+intervals|lubrication\s+interval",
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
    max_chars_per_page: int = MAX_CHARS_PER_PAGE,
    max_total_chars: int = MAX_TOTAL_CHARS,
) -> list[SourcePassage]:
    """Pick compact, interval-dense pages. Hard-caps prompt size for real manuals."""
    scored: list[tuple[float, SourcePassage]] = []
    for page in pages:
        if getattr(page, "state", None) != "completed":
            continue
        text = (getattr(page, "text", None) or "").strip()
        if len(text) < 40:
            continue
        strong = len(_STRONG_INTERVAL.findall(text))
        hits = len(_INTERVAL_HINTS.findall(text))
        header_bonus = 25 if _SCHEDULE_HEADER.search(text[:800] or "") else 0
        if strong == 0 and hits < 3 and header_bonus == 0:
            continue
        page_index = int(getattr(page, "page_index", 0))
        clipped = text[:max_chars_per_page]
        # Prefer dense interval pages over long keyword-stuffed chapters.
        density = (strong * 8 + hits + header_bonus) / max(len(clipped) / 400.0, 1.0)
        score = density * 1000 + strong * 50 + header_bonus * 40 - page_index * 0.01
        scored.append(
            (
                score,
                SourcePassage(
                    page=page_index + 1,
                    text=clipped,
                    document_id=document_id,
                ),
            )
        )
    scored.sort(key=lambda item: item[0], reverse=True)
    selected: list[SourcePassage] = []
    total = 0
    for _, passage in scored:
        if len(selected) >= max_passages:
            break
        size = len(passage.text)
        if total + size > max_total_chars:
            remain = max_total_chars - total
            if remain < 200:
                break
            passage = SourcePassage(
                page=passage.page,
                text=passage.text[:remain],
                document_id=passage.document_id,
            )
            size = len(passage.text)
        selected.append(passage)
        total += size
    selected.sort(key=lambda item: item.page)
    return selected


def propose_rules_from_passages(
    chat: ChatModel,
    passages: list[SourcePassage],
    *,
    taxonomy_hint: str,
) -> list[dict[str, Any]]:
    """Ask the chat model for structured proposals in prompt-sized batches."""
    if not passages:
        return []
    proposals: list[dict[str, Any]] = []
    for batch in _batches(passages, BATCH_CHAR_BUDGET):
        body = format_passages(batch)
        if not body:
            continue
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
        except ChatFailed as exc:
            raise ChatFailed(f"Rule extraction model call failed: {exc}") from exc
        proposals.extend(parse_proposed_rules(raw))
    return _dedupe_proposals(proposals)


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


def _batches(passages: list[SourcePassage], budget: int) -> list[list[SourcePassage]]:
    batches: list[list[SourcePassage]] = []
    current: list[SourcePassage] = []
    size = 0
    for passage in passages:
        piece = len(passage.text) + 24
        if current and size + piece > budget:
            batches.append(current)
            current = []
            size = 0
        current.append(passage)
        size += piece
    if current:
        batches.append(current)
    return batches


def _dedupe_proposals(proposals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    out: list[dict[str, Any]] = []
    for item in proposals:
        key = (
            item.get("system"),
            item.get("component"),
            item.get("action"),
            item.get("usage_condition_variant") or "standard",
            item.get("recurring_interval_hours"),
            item.get("initial_interval_hours"),
            item.get("calendar_interval_days"),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out
