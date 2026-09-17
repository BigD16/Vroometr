"""Deterministic PDF text extraction and versioned routing heuristics, without model calls."""

import re

import pymupdf

from app.models.document_ingestion import DocumentPage
from app.services.document_ingestion import PIPELINE_VERSION


def extract_page(pdf, index, document_id, source_hash) -> DocumentPage:
    page = pdf.load_page(index)
    text = page.get_text("text", sort=True)
    area = max(page.rect.get_area(), 1)
    images = page.get_image_info()
    image_area = min(
        1.0, sum((pymupdf.Rect(image["bbox"]) & page.rect).get_area() for image in images) / area
    )
    drawings = len(page.get_drawings())
    reasons = []
    score = 0.0
    if image_area > 0.2:
        score += 0.4
        reasons.append("large_image_area")
    if len(images) >= 3:
        score += 0.15
        reasons.append("multiple_images")
    if drawings >= 10:
        score += 0.35
        reasons.append("vector_content")
    sparse = len(text.strip()) < 80
    if sparse and (images or drawings):
        score += 0.25
        reasons.append("sparse_text_with_visuals")
    if re.search(
        r"\b(figure|diagram|illustration|arrow|tighten|adjust|remove|install)\b", text, re.I
    ):
        score += 0.1
        reasons.append("instructional_or_visual_language")
    score = min(1.0, round(score, 2))
    classification = (
        "ocr_vision"
        if score >= 0.7
        else "ocr_enhanced"
        if score >= 0.35 or (sparse and images)
        else "text_only"
    )
    if not text.strip() and not images and not drawings:
        reasons.append("blank_page")
    return DocumentPage(
        document_id=document_id,
        page_index=index,
        text=text,
        visual_score=score,
        visual_score_reasons=reasons,
        processing_class=classification,
        state="completed" if classification == "text_only" else "pending_provider",
        error_code=None if classification == "text_only" else "provider_unconfigured",
        source_hash=source_hash,
        extraction_version=PIPELINE_VERSION,
        ocr_version=None,
        vision_version=None,
    )


def failed_page(index, document_id, source_hash) -> DocumentPage:
    return DocumentPage(
        document_id=document_id,
        page_index=index,
        text="",
        visual_score=0,
        visual_score_reasons=["classification_failed"],
        processing_class="text_only",
        state="failed",
        error_code="page_extraction_failed",
        source_hash=source_hash,
        extraction_version=PIPELINE_VERSION,
        ocr_version=None,
        vision_version=None,
    )
