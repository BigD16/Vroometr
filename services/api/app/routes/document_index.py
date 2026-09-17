from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.documents.index_runtime import index_service
from app.errors import AppError
from app.models.user import User
from app.routes.documents import raise_document_error
from app.services.attachment_processing import ProcessingBusy
from app.services.attachments import AttachmentAccessBlocked
from app.services.documents import DocumentNotFound, InvalidDocument

router = APIRouter(prefix="/v1/documents", tags=["document-index"])


def get_index_service(session: Session = Depends(get_db)):
    return index_service(session)


class IndexResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    state: str
    chunking_version: str
    embedding_model: str
    embedding_version: str
    error_code: str | None
    retry_after: datetime | None


class SectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    parent_section_id: UUID | None
    section_title: str
    section_order: int
    start_page: int
    end_page: int
    source_method: str


class ChunkResponse(BaseModel):
    id: UUID
    section_id: UUID
    chunk_index: int
    section_chunk_index: int
    page_start: int
    page_end: int
    cleaned_text: str
    content_type: str
    source_span: list[dict]
    embedded: bool
    embedding_model: str | None
    embedding_version: str | None


class IndexStatus(BaseModel):
    indexing: IndexResponse | None
    stale: bool
    sections: list[SectionResponse]
    chunks: list[ChunkResponse]
    total_chunks: int
    embedded_chunks: int


@router.get("/{document_id}/index")
def status(
    document_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    service=Depends(get_index_service),
) -> IndexStatus:
    try:
        job, stale, sections, chunks = service.status(user.id, document_id)
        return IndexStatus(
            indexing=IndexResponse.model_validate(job) if job else None,
            stale=stale,
            sections=[SectionResponse.model_validate(s) for s in sections],
            total_chunks=len(chunks),
            embedded_chunks=sum(c.embedding is not None for c in chunks),
            chunks=[
                ChunkResponse(
                    id=c.id,
                    section_id=c.section_id,
                    chunk_index=c.chunk_index,
                    section_chunk_index=c.section_chunk_index,
                    page_start=c.page_start,
                    page_end=c.page_end,
                    cleaned_text=c.cleaned_text,
                    content_type=c.content_type,
                    source_span=c.source_span,
                    embedded=c.embedding is not None,
                    embedding_model=c.embedding_model,
                    embedding_version=c.embedding_version,
                )
                for c in chunks[offset : offset + limit]
            ],
        )
    except (DocumentNotFound, AttachmentAccessBlocked) as exc:
        raise_document_error(exc)


@router.post("/{document_id}/index", status_code=202)
def queue(
    document_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service=Depends(get_index_service),
) -> IndexResponse:
    try:
        return IndexResponse.model_validate(service.queue(user.id, document_id))
    except ProcessingBusy as exc:
        raise AppError("index_busy", str(exc), status_code=409) from exc
    except (DocumentNotFound, InvalidDocument, AttachmentAccessBlocked) as exc:
        raise_document_error(exc)
