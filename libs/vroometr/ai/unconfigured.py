"""Stand-in adapters until a vendor is wired. No vendor SDK imports."""


from typing import NoReturn


class UnconfiguredError(RuntimeError):
    pass


def _reject(port_name: str) -> NoReturn:
    raise UnconfiguredError(
        f"{port_name} has no vendor adapter yet. Set the matching *_MODEL env var "
        "and add an adapter that implements libs/vroometr/ai/ports.py."
    )


class UnconfiguredChatModel:
    def complete(self, messages: list[dict[str, str]]) -> str:
        _reject("ChatModel")


class UnconfiguredEmbeddingModel:
    def embed(self, texts: list[str]) -> list[list[float]]:
        _reject("EmbeddingModel")


class UnconfiguredReranker:
    def rerank(self, query: str, passages: list[str]) -> list[str]:
        _reject("Reranker")


class UnconfiguredVisionModel:
    def describe(self, image_bytes: bytes) -> str:
        _reject("VisionModel")


class UnconfiguredImageModel:
    def generate(self, prompt: str) -> bytes:
        _reject("ImageModel")


class UnconfiguredStt:
    def transcribe(self, audio_bytes: bytes) -> str:
        _reject("Stt")


class UnconfiguredTts:
    def synthesize(self, text: str) -> bytes:
        _reject("Tts")
