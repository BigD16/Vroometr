"""Return AI ports. Vendor adapters are added later; this must not import them."""

from vroometr.ai.ports import (
    ChatModel,
    EmbeddingModel,
    ImageModel,
    Reranker,
    Stt,
    Tts,
    VisionModel,
)
from vroometr.ai.unconfigured import (
    UnconfiguredChatModel,
    UnconfiguredEmbeddingModel,
    UnconfiguredImageModel,
    UnconfiguredReranker,
    UnconfiguredStt,
    UnconfiguredTts,
    UnconfiguredVisionModel,
)


def get_chat_model() -> ChatModel:
    return UnconfiguredChatModel()


def get_embedding_model() -> EmbeddingModel:
    return UnconfiguredEmbeddingModel()


def get_reranker() -> Reranker:
    return UnconfiguredReranker()


def get_vision_model() -> VisionModel:
    return UnconfiguredVisionModel()


def get_image_model() -> ImageModel:
    return UnconfiguredImageModel()


def get_stt() -> Stt:
    return UnconfiguredStt()


def get_tts() -> Tts:
    return UnconfiguredTts()
