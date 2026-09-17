"""Factories return provider-neutral ports; HTTP transport lives in adapters."""

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
    from vroometr.ai.embeddings import OpenAIEmbeddingModel
    from vroometr.settings import settings

    if not (
        settings.openai_api_key.get_secret_value()
        and settings.openai_base_url
        and settings.embedding_model
        and settings.embedding_version
    ):
        return UnconfiguredEmbeddingModel()
    return OpenAIEmbeddingModel(
        api_key=settings.openai_api_key.get_secret_value(),
        base_url=settings.openai_base_url,
        model=settings.embedding_model,
        timeout=settings.embedding_timeout_seconds,
    )


def get_reranker() -> Reranker:
    from vroometr.ai.reranking import OpenAIReranker
    from vroometr.settings import settings

    if not (
        settings.openai_api_key.get_secret_value()
        and settings.openai_base_url
        and settings.reranker_model
    ):
        return UnconfiguredReranker()
    return OpenAIReranker(
        api_key=settings.openai_api_key.get_secret_value(),
        base_url=settings.openai_base_url,
        model=settings.reranker_model,
        timeout=settings.reranker_timeout_seconds,
    )


def get_vision_model() -> VisionModel:
    return UnconfiguredVisionModel()


def get_image_model() -> ImageModel:
    return UnconfiguredImageModel()


def get_stt() -> Stt:
    return UnconfiguredStt()


def get_tts() -> Tts:
    return UnconfiguredTts()
