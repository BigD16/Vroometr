"""Registry for assistant tools. Invoke goes through registered handlers only."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from app.assistant_tools.types import RegisteredTool, ToolContext, ToolResult, ToolSpec
from app.assistant_tools.write_policy import WriteDecision, evaluate_write_policy
from vroometr.flags import FLAG_AI_WRITES, is_enabled


class ToolRegistry:
    def __init__(
        self,
        *,
        writes_enabled: Callable[[], bool] | None = None,
    ) -> None:
        self._tools: dict[str, RegisteredTool] = {}
        self._writes_enabled = writes_enabled or (
            lambda: is_enabled(FLAG_AI_WRITES, default=True)
        )

    def register(self, spec: ToolSpec, handler) -> None:
        if not spec.name or not spec.name.strip():
            raise ValueError("tool name is required")
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        if spec.mutates:
            if spec.write_class is None:
                raise ValueError(
                    f"mutating tool {spec.name!r} requires write_class "
                    "(auto or confirm)"
                )
        elif spec.write_class is not None:
            raise ValueError(
                f"read-only tool {spec.name!r} must not set write_class"
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
            assert registered.spec.write_class is not None
            policy = evaluate_write_policy(
                write_class=registered.spec.write_class,
                writes_enabled=self._writes_enabled(),
                confirmed=context.confirmed,
                explicit_instruction=context.explicit_instruction,
            )
            if policy.decision is not WriteDecision.ALLOW:
                return ToolResult.failure(
                    policy.code or "writes_disabled",
                    policy.reason,
                )
        args = dict(arguments or {})
        try:
            return registered.handler(context, args)
        except Exception as exc:  # noqa: BLE001 — map unexpected failures to tool errors
            return ToolResult.failure("tool_failed", str(exc) or type(exc).__name__)
