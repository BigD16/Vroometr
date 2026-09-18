"""Always-load compact assistant context. Selective retrieval stays on RetrievalService."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.models.bike import Bike
from app.models.conversation import ConversationContextBoundary, ConversationMessage
from app.models.user import User
from app.repositories.bikes import BikeStore
from app.services.conversations import ConversationNotFound, ConversationService
from app.services.retrieval import RetrievalService

COMPACT_CONTEXT_VERSION = "compact-context-v1"
RECENT_TURN_LIMIT = 8
RECENT_CHAR_BUDGET = 4000
_DEFERRED_REASON = "domain_not_implemented"


class RetrievalPort(Protocol):
    def search(
        self,
        user_id: UUID,
        bike_id: UUID,
        query: str,
        include_reference_editions: bool = False,
    ) -> dict: ...


@dataclass(frozen=True, slots=True)
class RecentTurn:
    id: UUID
    role: str
    content: str
    bike_context_id: UUID
    created_at: datetime


@dataclass(frozen=True, slots=True)
class LatestBikeSwitch:
    from_bike_id: UUID
    to_bike_id: UUID
    message_id: UUID | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class BikeContextSlice:
    bike_id: UUID
    nickname: str
    make: str
    model: str
    year: int
    bike_type: str
    status: str
    powertrain_type: str
    displacement: int | None
    stroke_type: str | None
    current_engine_hours: float | None
    current_engine_hours_is_estimated: bool
    unit_preference: str


@dataclass(frozen=True, slots=True)
class ConversationContextSlice:
    conversation_id: UUID
    initial_bike_id: UUID
    current_bike_id: UUID
    status: str
    rolling_summary: str | None
    summary_model_version: str | None
    recent_turns: list[RecentTurn]
    boundary_count: int
    latest_bike_switch: LatestBikeSwitch | None


@dataclass(frozen=True, slots=True)
class DeferredDomainSlice:
    available: bool
    items: list[dict]
    reason: str | None


@dataclass(frozen=True, slots=True)
class ContextBudget:
    recent_turn_limit: int
    recent_char_budget: int
    recent_chars_used: int
    summary_chars: int
    recent_turns_included: int
    recent_turns_omitted: int


@dataclass(frozen=True, slots=True)
class CompactContextPack:
    version: str
    conversation_id: UUID
    bike_id: UUID
    bike: BikeContextSlice
    conversation: ConversationContextSlice
    modifications: DeferredDomainSlice
    maintenance: DeferredDomainSlice
    ride: DeferredDomainSlice
    budget: ContextBudget

    def as_dict(self) -> dict:
        return asdict(self)


def select_recent_turns(
    messages: list[ConversationMessage],
    *,
    turn_limit: int = RECENT_TURN_LIMIT,
    char_budget: int = RECENT_CHAR_BUDGET,
) -> tuple[list[RecentTurn], int, int]:
    """Keep the newest turns within count and character budgets.

    Truncates oldest first. Returns (turns, chars_used, omitted_count).
    """
    if turn_limit < 1 or char_budget < 1:
        return [], 0, len(messages)
    candidates = messages[-turn_limit:]
    selected: list[tuple[ConversationMessage, str]] = []
    chars = 0
    for message in reversed(candidates):
        content = message.content or ""
        next_chars = chars + len(content)
        if selected and next_chars > char_budget:
            break
        if not selected and len(content) > char_budget:
            content = content[-char_budget:]
            selected = [(message, content)]
            chars = len(content)
            break
        selected.append((message, content))
        chars = next_chars
    selected.reverse()
    turns = [
        RecentTurn(
            id=item.id,
            role=item.role,
            content=content,
            bike_context_id=item.bike_context_id,
            created_at=item.created_at,
        )
        for item, content in selected
    ]
    omitted = len(messages) - len(selected)
    return turns, chars, omitted


def _hours(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _bike_slice(bike: Bike) -> BikeContextSlice:
    return BikeContextSlice(
        bike_id=bike.id,
        nickname=bike.nickname,
        make=bike.make,
        model=bike.model,
        year=bike.year,
        bike_type=bike.bike_type,
        status=bike.status,
        powertrain_type=bike.powertrain_type,
        displacement=bike.displacement,
        stroke_type=bike.stroke_type,
        current_engine_hours=_hours(bike.current_engine_hours),
        current_engine_hours_is_estimated=bike.current_engine_hours_is_estimated,
        unit_preference=bike.unit_preference,
    )


def _latest_switch(
    boundaries: list[ConversationContextBoundary],
) -> LatestBikeSwitch | None:
    if not boundaries:
        return None
    latest = boundaries[-1]
    return LatestBikeSwitch(
        from_bike_id=latest.from_bike_id,
        to_bike_id=latest.to_bike_id,
        message_id=latest.message_id,
        created_at=latest.created_at,
    )


def _deferred() -> DeferredDomainSlice:
    return DeferredDomainSlice(available=False, items=[], reason=_DEFERRED_REASON)


class CompactContextService:
    """Assemble always-load context for a conversation turn."""

    def __init__(
        self,
        conversations: ConversationService,
        bikes: BikeStore,
        retrieval: RetrievalPort | None = None,
    ) -> None:
        self._conversations = conversations
        self._bikes = bikes
        self._retrieval = retrieval

    def build(self, user: User, conversation_id: UUID) -> CompactContextPack:
        detail = self._conversations.get(user, conversation_id)
        conversation = detail.conversation
        bike = self._bikes.get(conversation.current_bike_id, user.id)
        if bike is None:
            raise ConversationNotFound("Bike not found")
        recent, chars_used, omitted = select_recent_turns(detail.messages)
        summary = conversation.rolling_summary
        return CompactContextPack(
            version=COMPACT_CONTEXT_VERSION,
            conversation_id=conversation.id,
            bike_id=bike.id,
            bike=_bike_slice(bike),
            conversation=ConversationContextSlice(
                conversation_id=conversation.id,
                initial_bike_id=conversation.initial_bike_id,
                current_bike_id=conversation.current_bike_id,
                status=conversation.status,
                rolling_summary=summary,
                summary_model_version=conversation.summary_model_version,
                recent_turns=recent,
                boundary_count=len(detail.boundaries),
                latest_bike_switch=_latest_switch(detail.boundaries),
            ),
            modifications=_deferred(),
            maintenance=_deferred(),
            ride=_deferred(),
            budget=ContextBudget(
                recent_turn_limit=RECENT_TURN_LIMIT,
                recent_char_budget=RECENT_CHAR_BUDGET,
                recent_chars_used=chars_used,
                summary_chars=len(summary) if summary else 0,
                recent_turns_included=len(recent),
                recent_turns_omitted=omitted,
            ),
        )

    def search_manuals(
        self,
        user: User,
        bike_id: UUID,
        query: str,
        *,
        include_reference_editions: bool = False,
    ) -> dict:
        """On-demand manual retrieval for future assistant tools (5.3)."""
        if self._retrieval is None:
            raise RuntimeError("RetrievalService is not configured on CompactContextService")
        if self._bikes.get(bike_id, user.id) is None:
            raise ConversationNotFound("Bike not found")
        return self._retrieval.search(
            user.id, bike_id, query, include_reference_editions=include_reference_editions
        )


def build_retrieval_service(session) -> RetrievalService:
    """Factory helper kept next to context wiring for 5.3 tool adapters."""
    from app.config import settings
    from app.repositories.bikes import BikeRepository
    from app.repositories.retrieval import RetrievalRepository

    from vroometr.ai.factory import get_embedding_model, get_reranker

    return RetrievalService(
        BikeRepository(session),
        RetrievalRepository(session, settings.embedding_model, settings.embedding_version),
        get_embedding_model(),
        get_reranker(),
        reranker_model=settings.reranker_model,
    )
