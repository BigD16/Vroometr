from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.documents.runtime import ingestion_service
from app.errors import AppError
from app.models.user import User
from app.routes.documents import raise_document_error
from app.services.attachment_processing import ProcessingBusy
from app.services.attachments import AttachmentAccessBlocked
from app.services.documents import DocumentNotFound, InvalidDocument

router = APIRouter(prefix="/v1/documents", tags=["document-ingestion"])


def get_ingestion_service(session: Session = Depends(get_db)):
    return ingestion_service(session)


class IngestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    state: str
    page_count: int
    pipeline_version: str
    error_code: str | None
    retry_after: datetime | None


class PageResponse(BaseModel):
    page_index: int
    state: str
    processing_class: str
    visual_score: float
    visual_score_reasons: list[str]
    error_code: str | None
    text_excerpt: str
    text_truncated: bool
    extraction_version: str
    ocr_version: str | None
    vision_version: str | None


class StatusResponse(BaseModel):
    ingestion: IngestionResponse | None
    pages: list[PageResponse]


@router.get("/{document_id}/ingestion")
def status(
    document_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service=Depends(get_ingestion_service),
) -> StatusResponse:
    try:
        job, pages = service.status(user.id, document_id)
        return StatusResponse(
            ingestion=IngestionResponse.model_validate(job) if job else None,
            pages=[
                PageResponse(
                    page_index=page.page_index,
                    state=page.state,
                    processing_class=page.processing_class,
                    visual_score=page.visual_score,
                    visual_score_reasons=page.visual_score_reasons,
                    error_code=page.error_code,
                    text_excerpt=page.text[:4000],
                    text_truncated=len(page.text) > 4000,
                    extraction_version=page.extraction_version,
                    ocr_version=page.ocr_version,
                    vision_version=page.vision_version,
                )
                for page in pages
            ],
        )
    except (DocumentNotFound, AttachmentAccessBlocked) as exc:
        raise_document_error(exc)


@router.post("/{document_id}/ingestion", status_code=202)
def queue(
    document_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service=Depends(get_ingestion_service),
) -> IngestionResponse:
    try:
        return IngestionResponse.model_validate(service.queue(user.id, document_id))
    except ProcessingBusy as exc:
        raise AppError("ingestion_busy", str(exc), status_code=409) from exc
    except (DocumentNotFound, InvalidDocument, AttachmentAccessBlocked) as exc:
        raise_document_error(exc)
