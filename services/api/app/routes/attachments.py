from datetime import datetime
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, StrictBool

from app.deps import get_attachment_service, get_current_user, get_storage_quota_service
from app.errors import AppError
from app.models.user import User
from app.routes.attachment_processing import ProcessingResponse
from app.services.attachment_links import AttachmentTargetNotFound
from app.services.attachments import (
    AttachmentAccessBlocked,
    AttachmentDeletionConflict,
    AttachmentService,
)
from app.services.storage_quota import StorageQuotaService, StorageUsage
from app.services.uploads import AttachmentNotFound, UploadNotComplete, UploadStorageUnavailable

router = APIRouter(prefix="/v1", tags=["attachments"])


class AttachmentResponse(BaseModel):
    id: UUID
    file_name: str
    file_size: int
    mime_type: str
    status: str
    created_at: datetime
    link_ids: list[UUID]
    link_count: int
    deletable_after: datetime
    processing: ProcessingResponse


class DeleteAttachmentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmed: StrictBool


def _raise_attachment_error(exc: Exception) -> NoReturn:
    if isinstance(exc, AttachmentAccessBlocked):
        raise AppError("file_blocked", str(exc), status_code=403) from exc
    if isinstance(exc, (AttachmentNotFound, AttachmentTargetNotFound)):
        raise AppError("not_found", "File or bike not found", status_code=404) from exc
    if isinstance(exc, (AttachmentDeletionConflict, UploadNotComplete)):
        raise AppError("attachment_conflict", str(exc), status_code=409) from exc
    if isinstance(exc, UploadStorageUnavailable):
        raise AppError(
            "storage_unavailable", "File storage is unavailable. Try again.", status_code=503
        ) from exc
    raise exc


@router.get("/storage")
def storage_usage(
    user: Annotated[User, Depends(get_current_user)],
    quota: Annotated[StorageQuotaService, Depends(get_storage_quota_service)],
) -> StorageUsage:
    return quota.usage(user.id)


@router.get("/attachments")
def list_attachments(
    user: Annotated[User, Depends(get_current_user)],
    attachments: Annotated[AttachmentService, Depends(get_attachment_service)],
    bike_id: UUID | None = None,
    include_all: bool = False,
) -> list[AttachmentResponse]:
    try:
        summaries = attachments.list(user, bike_id, include_all=include_all)
    except AttachmentTargetNotFound as exc:
        _raise_attachment_error(exc)
    return [
        AttachmentResponse(
            id=item.attachment.id,
            file_name=item.attachment.file_name,
            file_size=item.attachment.file_size,
            mime_type=item.attachment.mime_type,
            status=item.attachment.status,
            created_at=item.attachment.created_at,
            link_ids=item.link_ids,
            link_count=item.link_count,
            deletable_after=item.deletable_after,
            processing=ProcessingResponse.from_job(item.attachment.processing),
        )
        for item in summaries
    ]


@router.get("/attachments/{attachment_id}/access")
def access_attachment(
    attachment_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    attachments: Annotated[AttachmentService, Depends(get_attachment_service)],
    response: Response,
    download: bool = True,
) -> dict[str, str]:
    response.headers["Cache-Control"] = "no-store"
    try:
        return {"url": attachments.access(user, attachment_id, download=download)}
    except (
        AttachmentNotFound,
        AttachmentAccessBlocked,
        UploadNotComplete,
        UploadStorageUnavailable,
    ) as exc:
        _raise_attachment_error(exc)


@router.delete("/attachments/{attachment_id}", status_code=204)
def delete_attachment(
    attachment_id: UUID,
    body: DeleteAttachmentBody,
    user: Annotated[User, Depends(get_current_user)],
    attachments: Annotated[AttachmentService, Depends(get_attachment_service)],
) -> Response:
    try:
        attachments.delete(user, attachment_id, confirmed=body.confirmed)
    except (AttachmentNotFound, AttachmentDeletionConflict, UploadStorageUnavailable) as exc:
        _raise_attachment_error(exc)
    return Response(status_code=204)
