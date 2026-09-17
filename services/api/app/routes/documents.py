from datetime import datetime
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, StrictInt

from app.deps import get_current_user, get_document_service
from app.documents.inspection import InvalidDocumentFile
from app.errors import AppError
from app.models.user import User
from app.services.attachments import AttachmentAccessBlocked
from app.services.documents import (
    DocumentMetadata,
    DocumentNotFound,
    DocumentService,
    InvalidDocument,
)
from app.services.uploads import AttachmentNotFound, UploadNotComplete, UploadStorageUnavailable

router = APIRouter(prefix="/v1/documents", tags=["documents"])


class MetadataBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_type: str
    make: str
    model: str
    year: StrictInt

    def metadata(self) -> DocumentMetadata:
        return DocumentMetadata(self.document_type, self.make, self.model, self.year)


class RegisterDocumentBody(MetadataBody):
    bike_id: UUID
    attachment_id: UUID
    supersedes_document_id: UUID | None = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    bike_id: UUID
    attachment_id: UUID
    document_type: str
    make: str
    model: str
    year: int
    status: str
    is_primary: bool
    version_group_id: UUID
    revision: int
    supersedes_document_id: UUID | None
    confirmed_at: datetime | None
    created_at: datetime


class RegistrationResponse(BaseModel):
    document: DocumentResponse
    duplicate_document_ids: list[UUID]
    warning: str | None


def raise_document_error(exc: Exception) -> NoReturn:
    if isinstance(exc, (DocumentNotFound, AttachmentNotFound)):
        raise AppError("not_found", "Document, bike, or file not found", status_code=404) from exc
    if isinstance(exc, AttachmentAccessBlocked):
        raise AppError("file_blocked", str(exc), status_code=403) from exc
    if isinstance(exc, UploadStorageUnavailable):
        raise AppError(
            "storage_unavailable", "Could not read the file. Try again.", status_code=503
        ) from exc
    if isinstance(exc, UploadNotComplete):
        raise AppError("upload_incomplete", str(exc), status_code=409) from exc
    raise AppError("invalid_document", str(exc), status_code=400) from exc


_ERRORS = (
    DocumentNotFound,
    AttachmentNotFound,
    AttachmentAccessBlocked,
    UploadStorageUnavailable,
    UploadNotComplete,
    InvalidDocument,
    InvalidDocumentFile,
)


@router.get("")
def list_documents(
    bike_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    documents: Annotated[DocumentService, Depends(get_document_service)],
) -> list[DocumentResponse]:
    try:
        return [DocumentResponse.model_validate(item) for item in documents.list(user, bike_id)]
    except _ERRORS as exc:
        raise_document_error(exc)


@router.post("", status_code=201)
def register_document(
    body: RegisterDocumentBody,
    user: Annotated[User, Depends(get_current_user)],
    documents: Annotated[DocumentService, Depends(get_document_service)],
) -> RegistrationResponse:
    try:
        result = documents.register(
            user,
            bike_id=body.bike_id,
            attachment_id=body.attachment_id,
            metadata=body.metadata(),
            supersedes_document_id=body.supersedes_document_id,
        )
    except _ERRORS as exc:
        raise_document_error(exc)
    return RegistrationResponse(
        document=DocumentResponse.model_validate(result.document),
        duplicate_document_ids=result.duplicate_document_ids,
        warning="An identical file is already registered in your account. Both records are kept."
        if result.duplicate_document_ids
        else None,
    )


@router.post("/{document_id}/confirm")
def confirm_document(
    document_id: UUID,
    body: MetadataBody,
    user: Annotated[User, Depends(get_current_user)],
    documents: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentResponse:
    try:
        return DocumentResponse.model_validate(
            documents.confirm(user, document_id, body.metadata())
        )
    except _ERRORS as exc:
        raise_document_error(exc)


@router.put("/{document_id}/primary")
def select_primary_document(
    document_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    documents: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentResponse:
    try:
        return DocumentResponse.model_validate(documents.select_primary(user, document_id))
    except _ERRORS as exc:
        raise_document_error(exc)
