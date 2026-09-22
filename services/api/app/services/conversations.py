from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.models.conversation import (
    Conversation,
    ConversationContextBoundary,
    ConversationMessage,
    ConversationStatus,
    MessageRole,
)
from app.models.user import User
from app.repositories.bikes import BikeStore
from app.repositories.conversations import ConversationStore

# Deterministic V1 rolling summary until SUMMARY_MODEL / chat adapters are wired.
_SUMMARY_MODEL_VERSION = "deterministic-v1"
_SUMMARY_CHAR_BUDGET = 2000
_SUMMARY_RECENT_TURNS = 20


class ConversationNotFound(LookupError):
    """No conversation with this id belongs to the current user."""


class InvalidConversation(ValueError):
    """Conversation fields or message content are invalid."""


@dataclass(frozen=True, slots=True)
class ConversationDetail:
    conversation: Conversation
    messages: list[ConversationMessage]
    boundaries: list[ConversationContextBoundary]


def compress_rolling_summary(messages: list[ConversationMessage]) -> str | None:
    """Compress recent turns into a bounded rolling summary without calling a chat model.

    TODO(phase-5): replace with SUMMARY_MODEL refresh once ChatModel is configured.
    """
    if not messages:
        return None
    recent = messages[-_SUMMARY_RECENT_TURNS:]
    lines = [f"{message.role}: {message.content.strip()}" for message in recent]
    text = "\n".join(lines).strip()
    if not text:
        return None
    if len(text) <= _SUMMARY_CHAR_BUDGET:
        return text
    return text[-_SUMMARY_CHAR_BUDGET:]


class ConversationService:
    """Bike-scoped threads, messages, rolling summary, and context boundaries."""

    def __init__(self, repository: ConversationStore, bikes: BikeStore) -> None:
        self._repository = repository
        self._bikes = bikes

    def create(self, user: User, bike_id: UUID) -> Conversation:
        bike = self._bikes.get(bike_id, user.id)
        if bike is None:
            raise ConversationNotFound("Bike not found")
        now = datetime.now(UTC)
        conversation = Conversation(
            user_id=user.id,
            initial_bike_id=bike.id,
            current_bike_id=bike.id,
            status=ConversationStatus.ACTIVE.value,
            created_at=now,
            updated_at=now,
        )
        return self._repository.add(conversation)

    def list(self, user: User, bike_id: UUID | None = None) -> list[Conversation]:
        if bike_id is not None and self._bikes.get(bike_id, user.id) is None:
            raise ConversationNotFound("Bike not found")
        return self._repository.list_for_user(user.id, bike_id=bike_id)

    def get(self, user: User, conversation_id: UUID) -> ConversationDetail:
        conversation = self._require(user, conversation_id)
        return ConversationDetail(
            conversation=conversation,
            messages=self._repository.list_messages(conversation.id),
            boundaries=self._repository.list_boundaries(conversation.id),
        )

    def append_message(
        self,
        user: User,
        conversation_id: UUID,
        content: str,
        *,
        role: str = MessageRole.USER.value,
        citations_json: str | list[Any] | dict[str, Any] | None = None,
    ) -> ConversationMessage:
        conversation = self._require(user, conversation_id)
        text = content.strip() if isinstance(content, str) else ""
        if not text:
            raise InvalidConversation("message content is required")
        try:
            message_role = MessageRole(role)
        except ValueError:
            allowed = ", ".join(item.value for item in MessageRole)
            raise InvalidConversation(f"invalid role: expected {allowed}") from None
        citations = citations_json
        if isinstance(citations_json, str):
            try:
                citations = json.loads(citations_json)
            except json.JSONDecodeError as exc:
                raise InvalidConversation("citations_json must be valid JSON") from exc
        now = datetime.now(UTC)
        message = ConversationMessage(
            conversation_id=conversation.id,
            role=message_role.value,
            content=text,
            citations_json=citations,
            bike_context_id=conversation.current_bike_id,
            created_at=now,
        )
        saved = self._repository.add_message(message)
        self._refresh_rolling_summary(conversation)
        conversation.updated_at = now
        self._repository.save(conversation)
        return saved

    def switch_bike(
        self, user: User, conversation_id: UUID, to_bike_id: UUID
    ) -> ConversationDetail:
        conversation = self._require(user, conversation_id)
        bike = self._bikes.get(to_bike_id, user.id)
        if bike is None:
            raise ConversationNotFound("Bike not found")
        if bike.id != conversation.current_bike_id:
            latest = self._repository.latest_message(conversation.id)
            now = datetime.now(UTC)
            self._repository.add_boundary(
                ConversationContextBoundary(
                    conversation_id=conversation.id,
                    from_bike_id=conversation.current_bike_id,
                    to_bike_id=bike.id,
                    message_id=latest.id if latest is not None else None,
                    created_at=now,
                )
            )
            conversation.current_bike_id = bike.id
            conversation.updated_at = now
            self._repository.save(conversation)
        return self.get(user, conversation.id)

    def delete(self, user: User, conversation_id: UUID) -> None:
        conversation = self._require(user, conversation_id)
        self._repository.delete(conversation)

    def _require(self, user: User, conversation_id: UUID) -> Conversation:
        conversation = self._repository.get(conversation_id, user.id)
        if conversation is None:
            raise ConversationNotFound("Conversation not found")
        return conversation

    def _refresh_rolling_summary(self, conversation: Conversation) -> None:
        messages = self._repository.list_messages(conversation.id)
        conversation.rolling_summary = compress_rolling_summary(messages)
        conversation.summary_model_version = (
            _SUMMARY_MODEL_VERSION if conversation.rolling_summary else None
        )
