"""Shared types for thin assistant tools that wrap domain services."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.assistant_tools.write_policy import WriteClass
from app.models.user import User
from app.services.bikes import BikeService
from app.services.compact_context import CompactContextService
from app.services.conversations import ConversationService
from app.services.hierarchical_memory import HierarchicalMemoryService


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    parameters_schema: dict[str, Any]
    mutates: bool = False
    write_class: WriteClass | None = None


@dataclass(frozen=True, slots=True)
class ToolResult:
    ok: bool
    data: Mapping[str, Any] | None = None
    error: str | None = None
    code: str | None = None

    @classmethod
    def success(cls, data: Mapping[str, Any]) -> ToolResult:
        return cls(ok=True, data=dict(data))

    @classmethod
    def failure(cls, code: str, error: str) -> ToolResult:
        return cls(ok=False, error=error, code=code)


@dataclass(frozen=True, slots=True)
class ToolContext:
    """Caller identity plus the same domain services HTTP uses."""

    user: User
    bikes: BikeService
    conversations: ConversationService
    compact_context: CompactContextService
    memory: HierarchicalMemoryService
    conversation_id: UUID | None = None
    bike_id: UUID | None = None
    confirmed: bool = False
    explicit_instruction: bool = False


ToolHandler = Callable[[ToolContext, Mapping[str, Any]], ToolResult]


@dataclass(slots=True)
class RegisteredTool:
    spec: ToolSpec
    handler: ToolHandler
