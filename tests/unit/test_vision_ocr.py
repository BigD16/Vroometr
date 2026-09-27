"""OpenAI vision OCR adapter tests (mocked HTTP)."""

import json

import httpx
import pytest

from vroometr.ai.unconfigured import UnconfiguredError
from vroometr.ai.vision import OCR_VISION_VERSION, OpenAIVisionModel, VisionFailed


def test_vision_ocr_returns_transcription():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        assert body["model"] == "gpt-4o-mini"
        assert body["messages"][0]["content"][1]["image_url"]["detail"] == "low"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "  Oil capacity 0.75 L  "}}]},
        )

    model = OpenAIVisionModel(
        api_key="test",
        base_url="https://example.test/v1",
        model="gpt-4o-mini",
        timeout=5,
        transport=httpx.MockTransport(handler),
    )
    assert model.describe(b"\x89PNG\r\n\x1a\nfake") == "Oil capacity 0.75 L"
    assert OCR_VISION_VERSION.startswith("openai-vision")


def test_vision_requires_configuration():
    model = OpenAIVisionModel(api_key="", base_url="", model="", timeout=5)
    with pytest.raises(UnconfiguredError):
        model.describe(b"img")


def test_vision_rejects_empty_image():
    model = OpenAIVisionModel(
        api_key="k", base_url="https://example.test/v1", model="m", timeout=5
    )
    with pytest.raises(VisionFailed):
        model.describe(b"")
