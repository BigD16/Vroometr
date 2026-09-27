"""Complete OCR-routed pages with native text when usable, else cheap vision OCR."""

from __future__ import annotations

import logging

import pymupdf

from app.models.document_ingestion import DocumentPage
from vroometr.ai.ports import VisionModel
from vroometr.ai.unconfigured import UnconfiguredError
from vroometr.ai.vision import OCR_VISION_VERSION, VisionFailed

logger = logging.getLogger(__name__)

# Pages with this much native text are indexable without an OCR API call.
NATIVE_SUFFICIENT_CHARS = 120
NATIVE_SUFFICIENT_VERSION = "native-sufficient-v1"
# ~150 DPI equivalent; keeps vision tokens low while remaining readable.
OCR_RENDER_MATRIX = pymupdf.Matrix(1.5, 1.5)


def enhance_page(
    page: DocumentPage,
    pdf,
    index: int,
    vision: VisionModel | None,
) -> DocumentPage:
    """Resolve pending_provider pages when native text or a vision provider is available."""
    if page.state != "pending_provider":
        return page
    native = (page.text or "").strip()
    if len(native) >= NATIVE_SUFFICIENT_CHARS:
        page.state = "completed"
        page.error_code = None
        page.ocr_version = NATIVE_SUFFICIENT_VERSION
        page.vision_version = None
        return page
    if vision is None:
        return page
    try:
        rendered = _render_png(pdf, index)
        transcribed = vision.describe(rendered).strip()
    except UnconfiguredError:
        return page
    except VisionFailed:
        logger.error("Vision OCR failed for page %s (%s)", index, page.processing_class)
        page.error_code = "ocr_failed"
        return page
    except Exception as exc:  # noqa: BLE001
        logger.error("Vision OCR render failed (%s)", type(exc).__name__)
        page.error_code = "ocr_failed"
        return page
    if not transcribed:
        page.error_code = "ocr_empty"
        return page
    # Prefer OCR when native text was too sparse to trust alone.
    page.text = transcribed if not native else f"{native}\n\n{transcribed}"
    page.state = "completed"
    page.error_code = None
    page.ocr_version = OCR_VISION_VERSION
    page.vision_version = getattr(vision, "model", None) or OCR_VISION_VERSION
    return page


def _render_png(pdf, index: int) -> bytes:
    pixmap = pdf.load_page(index).get_pixmap(matrix=OCR_RENDER_MATRIX, alpha=False)
    return pixmap.tobytes("png")
