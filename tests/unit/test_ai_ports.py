from collections.abc import Callable
from typing import Any

import pytest

from vroometr.ai import (
    get_chat_model,
    get_embedding_model,
    get_image_model,
    get_reranker,
    get_stt,
    get_tts,
    get_vision_model,
)
from vroometr.ai.ports import ChatModel
from vroometr.ai.unconfigured import UnconfiguredError


def test_chat_model_port_is_unconfigured() -> None:
    model = get_chat_model()
    assert isinstance(model, ChatModel)
    with pytest.raises(UnconfiguredError):
        model.complete([{"role": "user", "content": "hello"}])


@pytest.mark.parametrize(
    ("factory", "method", "args"),
    [
        (get_embedding_model, "embed", (["hello"],)),
        (get_reranker, "rerank", ("q", ["a"])),
        (get_vision_model, "describe", (b"img",)),
        (get_image_model, "generate", ("a bike",)),
        (get_stt, "transcribe", (b"wav",)),
        (get_tts, "synthesize", ("hello",)),
    ],
)
def test_other_ports_are_unconfigured(
    factory: Callable[[], object],
    method: str,
    args: tuple[Any, ...],
) -> None:
    port = factory()
    with pytest.raises(UnconfiguredError):
        getattr(port, method)(*args)
