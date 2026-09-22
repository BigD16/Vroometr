"""OpenAI-compatible chat adapter with optional tool calls."""

from __future__ import annotations

from typing import Any

import httpx

from vroometr.ai.ports import ChatCompletionTurn, ChatToolCall
from vroometr.ai.unconfigured import UnconfiguredError


class ChatFailed(RuntimeError):
    pass


class OpenAIChatModel:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float,
        transport=None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.transport = transport

    def complete(self, messages: list[dict[str, str]]) -> str:
        turn = self.complete_turn(list(messages), tools=None)
        return (turn.content or "").strip()

    def complete_turn(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatCompletionTurn:
        if not self.api_key or not self.base_url or not self.model:
            raise UnconfiguredError("Chat provider is not configured")
        if not messages:
            raise ChatFailed("Chat messages are required")
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                response = client.post(
                    self.base_url.rstrip("/") + "/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            choice = data["choices"][0]["message"]
            content = choice.get("content")
            if content is not None and not isinstance(content, str):
                raise ChatFailed("Invalid chat content")
            tool_calls: list[ChatToolCall] = []
            for item in choice.get("tool_calls") or []:
                function = item.get("function") or {}
                call_id = item.get("id")
                name = function.get("name")
                arguments = function.get("arguments")
                if (
                    not isinstance(call_id, str)
                    or not isinstance(name, str)
                    or not isinstance(arguments, str)
                ):
                    raise ChatFailed("Invalid tool call payload")
                tool_calls.append(
                    ChatToolCall(id=call_id, name=name, arguments_json=arguments)
                )
            return ChatCompletionTurn(
                content=content,
                tool_calls=tuple(tool_calls),
            )
        except (
            httpx.HTTPError,
            ValueError,
            KeyError,
            TypeError,
            IndexError,
            AttributeError,
        ) as exc:
            # Never include provider bodies, prompts, or credential-bearing URLs.
            raise ChatFailed("Chat provider request failed") from exc
