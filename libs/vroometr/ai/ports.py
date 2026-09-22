"""Provider-neutral AI ports. Do not import vendor SDKs here."""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ChatToolCall:
    id: str
    name: str
    arguments_json: str


@dataclass(frozen=True)
class ChatCompletionTurn:
    content: str | None
    tool_calls: tuple[ChatToolCall, ...] = ()


@runtime_checkable
class ChatModel(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str: ...

    def complete_turn(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatCompletionTurn: ...


@runtime_checkable
class EmbeddingModel(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


@dataclass(frozen=True)
class RankedPassage:
    index: int
    score: float


@runtime_checkable
class Reranker(Protocol):
    def rerank(self, query: str, passages: list[str]) -> list[RankedPassage]: ...


@runtime_checkable
class VisionModel(Protocol):
    def describe(self, image_bytes: bytes) -> str: ...


@runtime_checkable
class ImageModel(Protocol):
    def generate(self, prompt: str) -> bytes: ...


@runtime_checkable
class Stt(Protocol):
    def transcribe(self, audio_bytes: bytes) -> str: ...


@runtime_checkable
class Tts(Protocol):
    def synthesize(self, text: str) -> bytes: ...
