"""Read-only assistant tools that wrap existing domain services."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from app.assistant_tools.types import ToolContext, ToolResult, ToolSpec
from app.services.bikes import BikeNotFound
from app.services.conversations import ConversationNotFound, InvalidConversation
from app.services.retrieval import InvalidSearch


def _uuid(value: Any, field: str) -> UUID:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return UUID(value.strip())
        except ValueError as exc:
            raise InvalidConversation(f"{field} must be a UUID") from exc
    raise InvalidConversation(f"{field} is required")


def _bike_payload(bike) -> dict[str, Any]:
    hours = bike.current_engine_hours
    return {
        "id": str(bike.id),
        "nickname": bike.nickname,
        "make": bike.make,
        "model": bike.model,
        "year": bike.year,
        "bike_type": bike.bike_type,
        "status": bike.status,
        "powertrain_type": bike.powertrain_type,
        "displacement": bike.displacement,
        "stroke_type": bike.stroke_type,
        "current_engine_hours": float(hours) if hours is not None else None,
        "current_engine_hours_is_estimated": bike.current_engine_hours_is_estimated,
        "unit_preference": bike.unit_preference,
    }


def _map_error(exc: Exception) -> ToolResult:
    if isinstance(exc, (BikeNotFound, ConversationNotFound)):
        return ToolResult.failure("not_found", "Bike or conversation not found")
    if isinstance(exc, (InvalidConversation, InvalidSearch, ValueError, TypeError)):
        return ToolResult.failure("invalid_arguments", str(exc))
    raise exc


GET_BIKE = ToolSpec(
    name="get_bike",
    description="Load one owned bike's identity, powertrain, and engine hours.",
    parameters_schema={
        "type": "object",
        "properties": {"bike_id": {"type": "string", "format": "uuid"}},
        "required": ["bike_id"],
        "additionalProperties": False,
    },
)


def execute_get_bike(context: ToolContext, arguments: Mapping[str, Any]) -> ToolResult:
    try:
        bike_id = _uuid(arguments.get("bike_id", context.bike_id), "bike_id")
        bike = context.bikes.get(context.user, bike_id)
        return ToolResult.success({"bike": _bike_payload(bike)})
    except Exception as exc:  # noqa: BLE001
        return _map_error(exc)


GET_COMPACT_CONTEXT = ToolSpec(
    name="get_compact_context",
    description=(
        "Load the always-on compact context pack for a conversation: bike slice, "
        "recent turns, rolling summary, and deferred domain stubs."
    ),
    parameters_schema={
        "type": "object",
        "properties": {"conversation_id": {"type": "string", "format": "uuid"}},
        "required": ["conversation_id"],
        "additionalProperties": False,
    },
)


def execute_get_compact_context(
    context: ToolContext, arguments: Mapping[str, Any]
) -> ToolResult:
    try:
        conversation_id = _uuid(
            arguments.get("conversation_id", context.conversation_id),
            "conversation_id",
        )
        pack = context.compact_context.build(context.user, conversation_id)
        return ToolResult.success({"context": pack.as_dict()})
    except Exception as exc:  # noqa: BLE001
        return _map_error(exc)


SEARCH_MANUALS = ToolSpec(
    name="search_manuals",
    description=(
        "Search the bike's indexed manuals for cited passages. "
        "Use for specifications, intervals, and procedures not in compact context."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "bike_id": {"type": "string", "format": "uuid"},
            "query": {"type": "string", "minLength": 1, "maxLength": 1200},
            "include_reference_editions": {"type": "boolean", "default": False},
        },
        "required": ["bike_id", "query"],
        "additionalProperties": False,
    },
)


def execute_search_manuals(
    context: ToolContext, arguments: Mapping[str, Any]
) -> ToolResult:
    try:
        bike_id = _uuid(arguments.get("bike_id", context.bike_id), "bike_id")
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            raise InvalidSearch("Enter a search of 1–1200 characters.")
        include_refs = arguments.get("include_reference_editions", False)
        if type(include_refs) is not bool:
            raise InvalidSearch("Reference-edition option must be true or false.")
        result = context.compact_context.search_manuals(
            context.user,
            bike_id,
            query.strip(),
            include_reference_editions=include_refs,
        )
        return ToolResult.success({"retrieval": result})
    except Exception as exc:  # noqa: BLE001
        return _map_error(exc)


GET_CONVERSATION = ToolSpec(
    name="get_conversation",
    description="Load an owned conversation with messages and bike-context boundaries.",
    parameters_schema={
        "type": "object",
        "properties": {"conversation_id": {"type": "string", "format": "uuid"}},
        "required": ["conversation_id"],
        "additionalProperties": False,
    },
)


def execute_get_conversation(
    context: ToolContext, arguments: Mapping[str, Any]
) -> ToolResult:
    try:
        conversation_id = _uuid(
            arguments.get("conversation_id", context.conversation_id),
            "conversation_id",
        )
        detail = context.conversations.get(context.user, conversation_id)
        conversation = detail.conversation
        return ToolResult.success(
            {
                "conversation": {
                    "id": str(conversation.id),
                    "initial_bike_id": str(conversation.initial_bike_id),
                    "current_bike_id": str(conversation.current_bike_id),
                    "status": conversation.status,
                    "rolling_summary": conversation.rolling_summary,
                    "summary_model_version": conversation.summary_model_version,
                },
                "messages": [
                    {
                        "id": str(message.id),
                        "role": message.role,
                        "content": message.content,
                        "bike_context_id": str(message.bike_context_id),
                        "created_at": message.created_at.isoformat(),
                    }
                    for message in detail.messages
                ],
                "boundaries": [
                    {
                        "id": str(boundary.id),
                        "from_bike_id": str(boundary.from_bike_id),
                        "to_bike_id": str(boundary.to_bike_id),
                        "message_id": str(boundary.message_id)
                        if boundary.message_id
                        else None,
                        "created_at": boundary.created_at.isoformat(),
                    }
                    for boundary in detail.boundaries
                ],
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _map_error(exc)
