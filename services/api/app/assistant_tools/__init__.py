"""Thin assistant tools that call the same domain services as HTTP.

Read-only tools ship in 5.3. Write policy (5.4) gates any future mutating tools.
The ReasoningAgent loop and ChatModel tool-calling are later Phase 5 work.
"""

from app.assistant_tools.factory import build_default_registry
from app.assistant_tools.registry import ToolRegistry
from app.assistant_tools.types import ToolContext, ToolResult, ToolSpec
from app.assistant_tools.write_policy import (
    WriteClass,
    WriteDecision,
    WritePolicyResult,
    evaluate_write_policy,
)

__all__ = [
    "ToolContext",
    "ToolRegistry",
    "ToolResult",
    "ToolSpec",
    "WriteClass",
    "WriteDecision",
    "WritePolicyResult",
    "build_default_registry",
    "evaluate_write_policy",
]
