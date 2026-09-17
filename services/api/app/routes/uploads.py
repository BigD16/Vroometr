from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, StrictInt

from app.deps import get_current_user, get_upload_service
from app.errors import AppError
from app.models.attachment import Attachment
from app.models.user import User
from app.services.storage_quota import StorageQuotaExceeded
from app.services.uploads import (
    AttachmentNotFound,
    InvalidUpload,
    UploadNotComplete,
    UploadService,
    UploadStorageUnavailable,
    UploadVerificationFailed,
)

router = APIRouter(tags=["uploads"])


class PresignUploadBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    file_name: str
    mime_type: str
    file_size: StrictInt
    purpose: str = "document"


class PresignUploadResponse(BaseModel):
    attachment_id: UUID
    object_key: str
    method: str
    url: str
    fields: dict[str, str]
    expires_in: int


class CompleteUploadResponse(BaseModel):
    attachment_id: UUID
    file_name: str
    mime_type: str
    file_size: int
    purpose: str
    status: str


def _complete_response(attachment: Attachment) -> CompleteUploadResponse:
    return CompleteUploadResponse(
        attachment_id=attachment.id,
        file_name=attachment.file_name,
        mime_type=attachment.mime_type,
        file_size=attachment.file_size,
        purpose=attachment.purpose,
        status=attachment.status,
    )


def _raise_upload(exc: Exception) -> NoReturn:
    if isinstance(exc, StorageQuotaExceeded):
        raise AppError("storage_quota_exceeded", str(exc), status_code=409) from exc
    if isinstance(exc, InvalidUpload):
        raise AppError("invalid_upload", str(exc), status_code=400) from exc
    if isinstance(exc, AttachmentNotFound):
        raise AppError("not_found", "Attachment not found", status_code=404) from exc
    if isinstance(exc, UploadNotComplete):
        raise AppError("upload_incomplete", str(exc), status_code=409) from exc
    if isinstance(exc, UploadVerificationFailed):
        raise AppError("upload_verification_failed", str(exc), status_code=409) from exc
    if isinstance(exc, UploadStorageUnavailable):
        raise AppError(
            "storage_unavailable",
            "Object storage is unavailable",
            status_code=503,
        ) from exc
    raise exc


@router.post("/v1/uploads/presign")
def presign_upload(
    body: PresignUploadBody,
    user: Annotated[User, Depends(get_current_user)],
    uploads: Annotated[UploadService, Depends(get_upload_service)],
) -> PresignUploadResponse:
    try:
        grant = uploads.begin(
            user,
            file_name=body.file_name,
            mime_type=body.mime_type,
            file_size=body.file_size,
            purpose=body.purpose,
        )
    except (InvalidUpload, UploadStorageUnavailable, StorageQuotaExceeded) as exc:
        _raise_upload(exc)
    return PresignUploadResponse(
        attachment_id=grant.attachment.id,
        object_key=grant.attachment.s3_key,
        method="POST",
        url=grant.post.url,
        fields=grant.post.fields,
        expires_in=grant.post.expires_in,
    )


@router.post("/v1/uploads/{attachment_id}/complete")
def complete_upload(
    attachment_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    uploads: Annotated[UploadService, Depends(get_upload_service)],
) -> CompleteUploadResponse:
    try:
        attachment = uploads.complete(user, attachment_id)
    except (
        AttachmentNotFound,
        UploadNotComplete,
        UploadStorageUnavailable,
        UploadVerificationFailed,
    ) as exc:
        _raise_upload(exc)
    return _complete_response(attachment)
