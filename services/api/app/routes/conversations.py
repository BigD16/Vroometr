from datetime import datetime
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.deps import get_compact_context_service, get_conversation_service, get_current_user
from app.errors import AppError
from app.models.user import User
from app.services.compact_context import CompactContextService
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


class RecentTurnResponse(BaseModel):
    id: UUID
    role: str
    content: str
    bike_context_id: UUID
    created_at: datetime


class LatestBikeSwitchResponse(BaseModel):
    from_bike_id: UUID
    to_bike_id: UUID
    message_id: UUID | None
    created_at: datetime


class BikeContextResponse(BaseModel):
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


class ConversationContextResponse(BaseModel):
    conversation_id: UUID
    initial_bike_id: UUID
    current_bike_id: UUID
    status: str
    rolling_summary: str | None
    summary_model_version: str | None
    recent_turns: list[RecentTurnResponse]
    boundary_count: int
    latest_bike_switch: LatestBikeSwitchResponse | None


class DeferredDomainResponse(BaseModel):
    available: bool
    items: list[dict]
    reason: str | None


class ContextBudgetResponse(BaseModel):
    recent_turn_limit: int
    recent_char_budget: int
    recent_chars_used: int
    summary_chars: int
    recent_turns_included: int
    recent_turns_omitted: int


class CompactContextResponse(BaseModel):
    version: str
    conversation_id: UUID
    bike_id: UUID
    bike: BikeContextResponse
    conversation: ConversationContextResponse
    modifications: DeferredDomainResponse
    maintenance: DeferredDomainResponse
    ride: DeferredDomainResponse
    budget: ContextBudgetResponse


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


@router.get("/{conversation_id}/context")
def get_compact_context(
    conversation_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    context: Annotated[CompactContextService, Depends(get_compact_context_service)],
) -> CompactContextResponse:
    try:
        pack = context.build(user, conversation_id)
    except _ERRORS as exc:
        raise_conversation_error(exc)
    return CompactContextResponse.model_validate(pack.as_dict())


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
