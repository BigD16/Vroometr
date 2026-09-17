from datetime import datetime
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.deps import get_conversation_service, get_current_user
from app.errors import AppError
from app.models.user import User
from app.services.conversations import (
    ConversationNotFound,
    ConversationService,
    InvalidConversation,
)

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])


class CreateConversationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bike_id: UUID


class AppendMessageBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1)
    role: str = "user"


class SwitchBikeBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bike_id: UUID


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    initial_bike_id: UUID
    current_bike_id: UUID
    status: str
    rolling_summary: str | None
    summary_model_version: str | None
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    bike_context_id: UUID
    created_at: datetime


class BoundaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    conversation_id: UUID
    from_bike_id: UUID
    to_bike_id: UUID
    message_id: UUID | None
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    conversation: ConversationResponse
    messages: list[MessageResponse]
    boundaries: list[BoundaryResponse]


def raise_conversation_error(exc: Exception) -> NoReturn:
    if isinstance(exc, ConversationNotFound):
        raise AppError("not_found", "Conversation or bike not found", status_code=404) from exc
    raise AppError("invalid_conversation", str(exc), status_code=400) from exc


_ERRORS = (ConversationNotFound, InvalidConversation)


@router.get("")
def list_conversations(
    user: Annotated[User, Depends(get_current_user)],
    conversations: Annotated[ConversationService, Depends(get_conversation_service)],
    bike_id: UUID | None = None,
) -> list[ConversationResponse]:
    try:
        return [
            ConversationResponse.model_validate(item)
            for item in conversations.list(user, bike_id)
        ]
    except _ERRORS as exc:
        raise_conversation_error(exc)


@router.post("", status_code=201)
def create_conversation(
    body: CreateConversationBody,
    user: Annotated[User, Depends(get_current_user)],
    conversations: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationResponse:
    try:
        return ConversationResponse.model_validate(conversations.create(user, body.bike_id))
    except _ERRORS as exc:
        raise_conversation_error(exc)


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    conversations: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationDetailResponse:
    try:
        detail = conversations.get(user, conversation_id)
    except _ERRORS as exc:
        raise_conversation_error(exc)
    return ConversationDetailResponse(
        conversation=ConversationResponse.model_validate(detail.conversation),
        messages=[MessageResponse.model_validate(item) for item in detail.messages],
        boundaries=[BoundaryResponse.model_validate(item) for item in detail.boundaries],
    )


@router.post("/{conversation_id}/messages", status_code=201)
def append_message(
    conversation_id: UUID,
    body: AppendMessageBody,
    user: Annotated[User, Depends(get_current_user)],
    conversations: Annotated[ConversationService, Depends(get_conversation_service)],
) -> MessageResponse:
    try:
        message = conversations.append_message(
            user, conversation_id, body.content, role=body.role
        )
    except _ERRORS as exc:
        raise_conversation_error(exc)
    return MessageResponse.model_validate(message)


@router.post("/{conversation_id}/bike")
def switch_bike(
    conversation_id: UUID,
    body: SwitchBikeBody,
    user: Annotated[User, Depends(get_current_user)],
    conversations: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationDetailResponse:
    try:
        detail = conversations.switch_bike(user, conversation_id, body.bike_id)
    except _ERRORS as exc:
        raise_conversation_error(exc)
    return ConversationDetailResponse(
        conversation=ConversationResponse.model_validate(detail.conversation),
        messages=[MessageResponse.model_validate(item) for item in detail.messages],
        boundaries=[BoundaryResponse.model_validate(item) for item in detail.boundaries],
    )


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    conversations: Annotated[ConversationService, Depends(get_conversation_service)],
) -> None:
    try:
        conversations.delete(user, conversation_id)
    except _ERRORS as exc:
        raise_conversation_error(exc)
