"""Registry for assistant tools. Invoke goes through registered handlers only."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.assistant_tools.types import RegisteredTool, ToolContext, ToolResult, ToolSpec


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, spec: ToolSpec, handler) -> None:
        if not spec.name or not spec.name.strip():
            raise ValueError("tool name is required")
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        if spec.mutates:
            raise ValueError(
                f"mutating tool {spec.name!r} is not allowed until write policy (5.4)"
            )
        self._tools[spec.name] = RegisteredTool(spec=spec, handler=handler)

    def get(self, name: str) -> RegisteredTool | None:
        return self._tools.get(name)

    def list_specs(self) -> list[ToolSpec]:
        return [item.spec for item in self._tools.values()]

    def invoke(
        self, name: str, arguments: Mapping[str, Any] | None, context: ToolContext
    ) -> ToolResult:
        registered = self._tools.get(name)
        if registered is None:
            return ToolResult.failure("unknown_tool", f"Unknown tool: {name}")
        if registered.spec.mutates:
            return ToolResult.failure(
                "writes_disabled",
                "Mutating tools are not available until write policy is implemented.",
            )
        args = dict(arguments or {})
        try:
            return registered.handler(context, args)
        except Exception as exc:  # noqa: BLE001 — map unexpected failures to tool errors
            return ToolResult.failure("tool_failed", str(exc) or type(exc).__name__)
