"""Hierarchical long-term conversation memory: search summaries, expand raw spans.

V1 ranks rolling summaries with deterministic token overlap (active bike is a hard
filter). Semantic summary embeddings land when SUMMARY / embedding wiring is ready;
this service stays the single selective-memory entry point either way.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from uuid import UUID

from app.models.conversation import Conversation, ConversationMessage
from app.models.user import User
from app.repositories.bikes import BikeStore
from app.services.conversations import (
    ConversationNotFound,
    ConversationService,
    InvalidConversation,
)

MEMORY_VERSION = "hierarchical-memory-v1"
SUMMARY_HIT_LIMIT = 5
SPAN_MESSAGE_LIMIT = 12
SPAN_CHAR_BUDGET = 4000
SPAN_PAD_MESSAGES = 1
_QUERY_MAX = 1200
_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True, slots=True)
class SummaryHit:
    conversation_id: UUID
    current_bike_id: UUID
    initial_bike_id: UUID
    rolling_summary: str
    summary_model_version: str | None
    score: float
    updated_at: datetime

    def as_dict(self) -> dict:
        payload = asdict(self)
        payload["conversation_id"] = str(self.conversation_id)
        payload["current_bike_id"] = str(self.current_bike_id)
        payload["initial_bike_id"] = str(self.initial_bike_id)
        payload["updated_at"] = self.updated_at.isoformat()
        return payload


@dataclass(frozen=True, slots=True)
class SpanMessage:
    id: UUID
    role: str
    content: str
    bike_context_id: UUID
    created_at: datetime
    score: float

    def as_dict(self) -> dict:
        return {
            "id": str(self.id),
            "role": self.role,
            "content": self.content,
            "bike_context_id": str(self.bike_context_id),
            "created_at": self.created_at.isoformat(),
            "score": self.score,
        }


@dataclass(frozen=True, slots=True)
class MemorySpan:
    conversation_id: UUID
    query: str
    messages: list[SpanMessage]
    omitted_before: int
    omitted_after: int
    chars_used: int

    def as_dict(self) -> dict:
        return {
            "conversation_id": str(self.conversation_id),
            "query": self.query,
            "messages": [message.as_dict() for message in self.messages],
            "omitted_before": self.omitted_before,
            "omitted_after": self.omitted_after,
            "chars_used": self.chars_used,
        }


def tokenize(text: str) -> set[str]:
    """Lowercase alphanumeric tokens; drop single-character noise."""
    return {token for token in _TOKEN_RE.findall(text.lower()) if len(token) > 1}


def score_overlap(query: str, text: str) -> float:
    """Fraction of query tokens present in text. Zero when either side is empty."""
    query_tokens = tokenize(query)
    if not query_tokens:
        return 0.0
    text_tokens = tokenize(text)
    if not text_tokens:
        return 0.0
    return len(query_tokens & text_tokens) / len(query_tokens)


def _require_query(query: str) -> str:
    if not isinstance(query, str):
        raise InvalidConversation("query is required")
    cleaned = query.strip()
    if not cleaned or len(cleaned) > _QUERY_MAX:
        raise InvalidConversation(f"query must be 1–{_QUERY_MAX} characters")
    return cleaned


def rank_summary_hits(
    conversations: list[Conversation],
    query: str,
    *,
    exclude_conversation_id: UUID | None = None,
    limit: int = SUMMARY_HIT_LIMIT,
) -> list[SummaryHit]:
    """Score rolling summaries and return the best bike-filtered hits."""
    if limit < 1:
        return []
    hits: list[SummaryHit] = []
    for conversation in conversations:
        if exclude_conversation_id is not None and conversation.id == exclude_conversation_id:
            continue
        summary = conversation.rolling_summary
        if not summary or not summary.strip():
            continue
        score = score_overlap(query, summary)
        if score <= 0:
            continue
        hits.append(
            SummaryHit(
                conversation_id=conversation.id,
                current_bike_id=conversation.current_bike_id,
                initial_bike_id=conversation.initial_bike_id,
                rolling_summary=summary,
                summary_model_version=conversation.summary_model_version,
                score=score,
                updated_at=conversation.updated_at,
            )
        )
    hits.sort(key=lambda hit: (hit.score, hit.updated_at), reverse=True)
    return hits[:limit]


def expand_matching_span(
    messages: list[ConversationMessage],
    query: str,
    *,
    message_limit: int = SPAN_MESSAGE_LIMIT,
    char_budget: int = SPAN_CHAR_BUDGET,
    pad: int = SPAN_PAD_MESSAGES,
    around_message_id: UUID | None = None,
) -> tuple[list[SpanMessage], int, int, int]:
    """Expand a contiguous raw-message window around the best query match."""
    if not messages or message_limit < 1 or char_budget < 1:
        return [], 0, len(messages), 0

    scores = [score_overlap(query, message.content or "") for message in messages]
    if around_message_id is not None:
        anchor = next(
            (index for index, message in enumerate(messages) if message.id == around_message_id),
            None,
        )
        if anchor is None:
            raise InvalidConversation("around_message_id is not in this conversation")
    else:
        best = max(scores) if scores else 0.0
        if best <= 0:
            return [], 0, len(messages), 0
        anchor = max(range(len(messages)), key=lambda index: (scores[index], index))

    start = max(0, anchor - max(pad, 0))
    end = min(len(messages), anchor + max(pad, 0) + 1)

    # Grow outward while staying within count/char budgets, preferring higher scores.
    while end - start < message_limit:
        left = start - 1
        right = end
        left_score = scores[left] if left >= 0 else -1.0
        right_score = scores[right] if right < len(messages) else -1.0
        if left_score < 0 and right_score < 0:
            break
        grow_left = left_score >= right_score and left >= 0
        candidate_index = left if grow_left else right
        candidate = messages[candidate_index]
        used = sum(len(message.content or "") for message in messages[start:end])
        next_len = len(candidate.content or "")
        if used + next_len > char_budget and end > start:
            break
        if grow_left:
            start = left
        else:
            end = right + 1

    window = messages[start:end]
    used = 0
    selected: list[SpanMessage] = []
    for message in window:
        content = message.content or ""
        if selected and used + len(content) > char_budget:
            break
        if not selected and len(content) > char_budget:
            content = content[-char_budget:]
        selected.append(
            SpanMessage(
                id=message.id,
                role=message.role,
                content=content,
                bike_context_id=message.bike_context_id,
                created_at=message.created_at,
                score=score_overlap(query, message.content or ""),
            )
        )
        used += len(content)
        if len(selected) >= message_limit:
            break

    omitted_before = start
    omitted_after = len(messages) - (start + len(selected))
    return selected, omitted_before, max(omitted_after, 0), used


class HierarchicalMemoryService:
    """Selective long-term conversation memory for the assistant."""

    def __init__(self, conversations: ConversationService, bikes: BikeStore) -> None:
        self._conversations = conversations
        self._bikes = bikes

    def search_summaries(
        self,
        user: User,
        bike_id: UUID,
        query: str,
        *,
        exclude_conversation_id: UUID | None = None,
        limit: int = SUMMARY_HIT_LIMIT,
    ) -> dict:
        cleaned = _require_query(query)
        if self._bikes.get(bike_id, user.id) is None:
            raise ConversationNotFound("Bike not found")
        threads = self._conversations.list(user, bike_id)
        hits = rank_summary_hits(
            threads,
            cleaned,
            exclude_conversation_id=exclude_conversation_id,
            limit=limit,
        )
        return {
            "version": MEMORY_VERSION,
            "bike_id": str(bike_id),
            "query": cleaned,
            "ranking": "token_overlap_v1",
            "hits": [hit.as_dict() for hit in hits],
        }

    def expand_span(
        self,
        user: User,
        conversation_id: UUID,
        query: str,
        *,
        around_message_id: UUID | None = None,
    ) -> dict:
        cleaned = _require_query(query)
        detail = self._conversations.get(user, conversation_id)
        messages, omitted_before, omitted_after, chars_used = expand_matching_span(
            detail.messages,
            cleaned,
            around_message_id=around_message_id,
        )
        span = MemorySpan(
            conversation_id=detail.conversation.id,
            query=cleaned,
            messages=messages,
            omitted_before=omitted_before,
            omitted_after=omitted_after,
            chars_used=chars_used,
        )
        return {
            "version": MEMORY_VERSION,
            "ranking": "token_overlap_v1",
            "span": span.as_dict(),
            "rolling_summary": detail.conversation.rolling_summary,
        }
