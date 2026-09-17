from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.deps import get_attachment_processing_service, get_current_user
from app.errors import AppError
from app.models.attachment_processing import AttachmentProcessing
from app.models.user import User
from app.services.attachment_processing import AttachmentProcessingService, ProcessingBusy
from app.services.uploads import AttachmentNotFound, UploadNotComplete

router = APIRouter(tags=["attachments"])


class ProcessingResponse(BaseModel):
    state: str = "not_started"
    scan_status: str = "not_scanned"
    error_code: str | None = None
    pipeline_version: str | None = None
    scanner_version: str | None = None
    updated_at: datetime | None = None
    retry_after: datetime | None = None

    @classmethod
    def from_job(cls, job: AttachmentProcessing | None) -> "ProcessingResponse":
        if job is None:
            return cls()
        return cls(
            state=job.state,
            scan_status=job.scan_status,
            error_code=job.error_code,
            pipeline_version=job.pipeline_version,
            scanner_version=job.scanner_version,
            updated_at=job.updated_at,
            retry_after=job.retry_after,
        )


@router.post("/v1/attachments/{attachment_id}/processing", status_code=202)
def retry_processing(
    attachment_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    processing: Annotated[AttachmentProcessingService, Depends(get_attachment_processing_service)],
) -> ProcessingResponse:
    try:
        job = processing.queue(user.id, attachment_id, retry=True)
    except AttachmentNotFound as exc:
        raise AppError("not_found", "File not found", status_code=404) from exc
    except (UploadNotComplete, ProcessingBusy) as exc:
        raise AppError("processing_conflict", str(exc), status_code=409) from exc
    return ProcessingResponse.from_job(job)
