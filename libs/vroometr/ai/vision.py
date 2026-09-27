"""OpenAI-compatible vision adapter used for cheap page OCR transcription."""

from __future__ import annotations

import base64

import httpx

from vroometr.ai.unconfigured import UnconfiguredError

OCR_VISION_VERSION = "openai-vision-ocr-v1"

_OCR_PROMPT = (
    "Transcribe all readable text from this document page image. "
    "Preserve numbers, units, labels, and reading order. "
    "Do not summarize, translate, or invent missing text. "
    "Return plain text only."
)


class VisionFailed(RuntimeError):
    pass


class OpenAIVisionModel:
    """VisionModel that returns page text (OCR), not a casual image caption."""

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

    def describe(self, image_bytes: bytes) -> str:
        if not self.api_key or not self.base_url or not self.model:
            raise UnconfiguredError("Vision provider is not configured")
        if not image_bytes:
            raise VisionFailed("Image bytes are required")
        if len(image_bytes) > 8_000_000:
            raise VisionFailed("Image exceeds supported size")
        encoded = base64.b64encode(image_bytes).decode("ascii")
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _OCR_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{encoded}",
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
        }
        try:
            with httpx.Client(
                timeout=self.timeout, transport=self.transport, trust_env=False
            ) as client:
                response = client.post(
                    self.base_url.rstrip("/") + "/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise VisionFailed("Invalid vision content")
            return content.strip()
        except httpx.ProxyError as exc:
            raise VisionFailed("Vision provider request failed (proxy)") from exc
        except (
            httpx.HTTPError,
            ValueError,
            KeyError,
            TypeError,
            IndexError,
            AttributeError,
        ) as exc:
            raise VisionFailed("Vision provider request failed") from exc
