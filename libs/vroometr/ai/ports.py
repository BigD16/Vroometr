"""Provider-neutral AI ports. Do not import vendor SDKs here."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ChatModel(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str: ...


@runtime_checkable
class EmbeddingModel(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


@runtime_checkable
class Reranker(Protocol):
    def rerank(self, query: str, passages: list[str]) -> list[str]: ...


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
