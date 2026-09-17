from typing import Protocol
from uuid import UUID

from app.models.conversation import (
    Conversation,
    ConversationContextBoundary,
    ConversationMessage,
)
from sqlalchemy import or_, select
from sqlalchemy.orm import Session


class ConversationStore(Protocol):
    def get(self, conversation_id: UUID, user_id: UUID) -> Conversation | None: ...

    def list_for_user(
        self, user_id: UUID, *, bike_id: UUID | None = None
    ) -> list[Conversation]: ...

    def add(self, conversation: Conversation) -> Conversation: ...

    def save(self, conversation: Conversation) -> Conversation: ...

    def delete(self, conversation: Conversation) -> None: ...

    def list_messages(self, conversation_id: UUID) -> list[ConversationMessage]: ...

    def add_message(self, message: ConversationMessage) -> ConversationMessage: ...

    def latest_message(self, conversation_id: UUID) -> ConversationMessage | None: ...

    def list_boundaries(
        self, conversation_id: UUID
    ) -> list[ConversationContextBoundary]: ...

    def add_boundary(
        self, boundary: ConversationContextBoundary
    ) -> ConversationContextBoundary: ...


class ConversationRepository:
    """Owner-scoped conversation persistence. Lookups always include user_id."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, conversation_id: UUID, user_id: UUID) -> Conversation | None:
        statement = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        return self._session.scalars(statement).first()

    def list_for_user(
        self, user_id: UUID, *, bike_id: UUID | None = None
    ) -> list[Conversation]:
        statement = select(Conversation).where(Conversation.user_id == user_id)
        if bike_id is not None:
            statement = statement.where(
                or_(
                    Conversation.current_bike_id == bike_id,
                    Conversation.initial_bike_id == bike_id,
                )
            )
        statement = statement.order_by(Conversation.updated_at.desc())
        return list(self._session.scalars(statement).all())

    def add(self, conversation: Conversation) -> Conversation:
        self._session.add(conversation)
        self._session.flush()
        return conversation

    def save(self, conversation: Conversation) -> Conversation:
        self._session.add(conversation)
        self._session.flush()
        return conversation

    def delete(self, conversation: Conversation) -> None:
        self._session.delete(conversation)
        self._session.flush()

    def list_messages(self, conversation_id: UUID) -> list[ConversationMessage]:
        statement = (
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.asc())
        )
        return list(self._session.scalars(statement).all())

    def add_message(self, message: ConversationMessage) -> ConversationMessage:
        self._session.add(message)
        self._session.flush()
        return message

    def latest_message(self, conversation_id: UUID) -> ConversationMessage | None:
        statement = (
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(1)
        )
        return self._session.scalars(statement).first()

    def list_boundaries(
        self, conversation_id: UUID
    ) -> list[ConversationContextBoundary]:
        statement = (
            select(ConversationContextBoundary)
            .where(ConversationContextBoundary.conversation_id == conversation_id)
            .order_by(ConversationContextBoundary.created_at.asc())
        )
        return list(self._session.scalars(statement).all())

    def add_boundary(
        self, boundary: ConversationContextBoundary
    ) -> ConversationContextBoundary:
        self._session.add(boundary)
        self._session.flush()
        return boundary
