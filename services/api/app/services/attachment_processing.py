from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.models.attachment_processing import AttachmentProcessing
from app.repositories.attachment_processing import ProcessingMessage, ProcessingStore
from app.repositories.attachments import AttachmentStore
from app.scanning.ports import ScanResult
from app.services.uploads import AttachmentNotFound, UploadNotComplete

PIPELINE_VERSION = "attachment-checks-v1"


class ProcessingBusy(ValueError):
    pass


@dataclass(frozen=True)
class ProcessingClaim:
    message: ProcessingMessage
    object_key: str


class AttachmentProcessingService:
    def __init__(
        self, jobs: ProcessingStore, attachments: AttachmentStore, lease_seconds: int
    ) -> None:
        self._jobs = jobs
        self._attachments = attachments
        self._lease = timedelta(seconds=lease_seconds)

    def queue(
        self, user_id: UUID, attachment_id: UUID, *, retry: bool = False
    ) -> AttachmentProcessing:
        self._attachments.lock_owner(user_id)
        attachment = self._attachments.get(attachment_id, user_id)
        if attachment is None:
            raise AttachmentNotFound
        if attachment.status != "uploaded":
            raise UploadNotComplete("Verify the upload before running checks.")
        job = self._jobs.get(attachment_id, user_id)
        now = datetime.now(UTC)
        if job is not None:
            if not retry:
                return job
            if job.state in {"queued", "running"} and now < job.updated_at + self._lease:
                raise ProcessingBusy("Checks are already queued or running. Retry if they stall.")
        else:
            job = AttachmentProcessing(
                attachment_id=attachment_id, scan_status="not_scanned", created_at=now
            )
        job.attempt_id = uuid4()
        job.state = "queued"
        job.pipeline_version = PIPELINE_VERSION
        job.error_code = None
        job.started_at = None
        job.finished_at = None
        job.updated_at = now
        job.retry_after = now + self._lease
        return self._jobs.queue(job, user_id)

    def claim(self, message: ProcessingMessage) -> ProcessingClaim | None:
        # Deleted attachments/accounts and stale messages are harmless no-ops.
        if self._attachments.get(message.attachment_id, message.user_id) is None:
            return None
        self._attachments.lock_owner(message.user_id)
        attachment = self._attachments.get(message.attachment_id, message.user_id)
        job = self._jobs.get(message.attachment_id, message.user_id)
        if attachment is None or job is None or job.attempt_id != message.attempt_id:
            return None
        if job.state != "queued" or attachment.status != "uploaded":
            return None
        job.state = "running"
        job.updated_at = job.started_at = datetime.now(UTC)
        job.retry_after = job.updated_at + self._lease
        self._jobs.save(job)
        return ProcessingClaim(message, attachment.s3_key)

    def finish(
        self,
        message: ProcessingMessage,
        *,
        result: ScanResult | None = None,
        error_code: str | None = None,
        queued_failure: bool = False,
    ) -> bool:
        if self._attachments.get(message.attachment_id, message.user_id) is None:
            return False
        self._attachments.lock_owner(message.user_id)
        job = self._jobs.get(message.attachment_id, message.user_id)
        expected = "queued" if queued_failure else "running"
        if job is None or job.attempt_id != message.attempt_id or job.state != expected:
            return False
        if result is None:
            job.state = "failed"
            job.error_code = error_code or "scan_failed"
            if job.scan_status != "infected":
                job.scan_status = "error"
        else:
            job.state = "completed"
            job.error_code = None
            # Missing scanner support must never clear a known infection.
            if job.scan_status != "infected" or result.status == "clean":
                job.scan_status = result.status
                job.scanner_version = result.scanner_version
        job.updated_at = job.finished_at = datetime.now(UTC)
        job.retry_after = None
        self._jobs.save(job)
        return True
