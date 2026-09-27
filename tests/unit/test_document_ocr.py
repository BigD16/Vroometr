"""Unit tests for cheap OCR enhancement (native-sufficient + vision)."""

from uuid import uuid4

import pymupdf
from app.documents.extraction import extract_page
from app.documents.ocr import (
    NATIVE_SUFFICIENT_VERSION,
    enhance_page,
)

from vroometr.ai.unconfigured import UnconfiguredVisionModel
from vroometr.ai.vision import OCR_VISION_VERSION


class FakeVision:
    model = "test-vision"

    def __init__(self, text="OCR LINE 42 Nm"):
        self.text = text
        self.calls = 0

    def describe(self, image_bytes: bytes) -> str:
        self.calls += 1
        assert image_bytes.startswith(b"\x89PNG")
        return self.text


def test_native_sufficient_completes_without_vision_call():
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        for i in range(12):
            page.draw_line((10, 10 + i * 5), (150, 10 + i * 5))
        long = "Mixing ratio 30:1 " + ("oil capacity details " * 10)
        page.insert_text((30, 150), long[:500])
        result = extract_page(pdf, 0, uuid4(), "a" * 64)
        assert result.state == "pending_provider"
        assert len(result.text.strip()) >= 120
        vision = FakeVision()
        enhanced = enhance_page(result, pdf, 0, vision)
        assert enhanced.state == "completed"
        assert enhanced.ocr_version == NATIVE_SUFFICIENT_VERSION
        assert enhanced.vision_version is None
        assert vision.calls == 0
        assert "30:1" in enhanced.text


def test_sparse_page_uses_vision_ocr():
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((30, 40), "Hi")
        for i in range(12):
            page.draw_line((10, 10 + i * 5), (200, 10 + i * 5))
        result = extract_page(pdf, 0, uuid4(), "a" * 64)
        assert result.state == "pending_provider"
        vision = FakeVision("Torque 12 Nm from OCR")
        enhanced = enhance_page(result, pdf, 0, vision)
        assert enhanced.state == "completed"
        assert enhanced.ocr_version == OCR_VISION_VERSION
        assert enhanced.vision_version == "test-vision"
        assert vision.calls == 1
        assert "12 Nm" in enhanced.text


def test_unconfigured_vision_leaves_sparse_page_pending():
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((30, 40), "Hi")
        for i in range(12):
            page.draw_line((10, 10 + i * 5), (200, 10 + i * 5))
        result = extract_page(pdf, 0, uuid4(), "a" * 64)
        assert enhance_page(result, pdf, 0, None).state == "pending_provider"
        assert enhance_page(result, pdf, 0, UnconfiguredVisionModel()).state == (
            "pending_provider"
        )
