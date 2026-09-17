from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.models.attachment import Attachment
from app.models.document_ingestion import DocumentIngestion, DocumentPage
from app.repositories.document_ingestion import IngestionMessage
from app.services.attachment_processing import ProcessingBusy
from app.services.attachments import AttachmentAccessBlocked
from app.services.documents import DocumentNotFound, InvalidDocument

PIPELINE_VERSION = "document-extraction-v1"


@dataclass(frozen=True)
class IngestionClaim:
    attachment: Attachment
    file_hash: str
    completed_pages: frozenset[int]


class DocumentIngestionService:
    def __init__(self, jobs, documents, attachments, lease_seconds: int):
        self.jobs = jobs
        self.documents = documents
        self.attachments = attachments
        self.lease = timedelta(seconds=lease_seconds)

    def authorize(self, user_id: UUID, document_id: UUID):
        document = self.documents.get(document_id, user_id)
        if document is None:
            raise DocumentNotFound
        attachment = self.attachments.get(document.attachment_id, user_id)
        if attachment is None:
            raise DocumentNotFound
        if attachment.processing is not None and attachment.processing.scan_status == "infected":
            raise AttachmentAccessBlocked("This file was flagged as infected.")
        return document, attachment

    def status(self, user_id: UUID, document_id: UUID):
        self.authorize(user_id, document_id)
        return self.jobs.get(document_id), self.jobs.pages(document_id)

    def queue(self, user_id: UUID, document_id: UUID):
        self.attachments.lock_owner(user_id)
        document, attachment = self.authorize(user_id, document_id)
        if document.confirmed_at is None or attachment.status != "uploaded":
            raise InvalidDocument("Confirm the uploaded document before extracting pages.")
        job = self.jobs.get(document_id)
        now = datetime.now(UTC)
        if job and job.state in {"queued", "running"} and job.retry_after > now:
            raise ProcessingBusy("Extraction is already queued or running. Retry if it stalls.")
        if job is None:
            job = DocumentIngestion(document_id=document_id, page_count=0)
        job.attempt_id = uuid4()
        job.state = "queued"
        job.pipeline_version = PIPELINE_VERSION
        job.error_code = None
        job.updated_at = now
        job.retry_after = now + self.lease
        return self.jobs.queue(job, user_id)

    def _current(self, message: IngestionMessage, state="running"):
        self.attachments.lock_owner(message.user_id)
        # Deletion and late/duplicate messages must not recreate records.
        if self.documents.get(message.document_id, message.user_id) is None:
            return None
        job = self.jobs.get(message.document_id)
        if job is None or job.attempt_id != message.attempt_id or job.state != state:
            return None
        return job

    def claim(self, message: IngestionMessage):
        job = self._current(message, "queued")
        if job is None:
            return None
        document, attachment = self.authorize(message.user_id, message.document_id)
        if document.confirmed_at is None or attachment.status != "uploaded":
            raise InvalidDocument("Document is not ready for extraction.")
        job.state = "running"
        self._heartbeat(job)
        self.jobs.save(job)
        completed = frozenset(
            page.page_index
            for page in self.jobs.pages(document.id)
            if page.state == "completed"
            and page.source_hash == document.file_hash
            and page.extraction_version == PIPELINE_VERSION
        )
        # Detach a value copy: the worker does no ORM reads outside its transaction.
        file = Attachment(
            id=attachment.id,
            s3_key=attachment.s3_key,
            file_size=attachment.file_size,
            mime_type=attachment.mime_type,
        )
        return IngestionClaim(file, document.file_hash, completed)

    def _heartbeat(self, job):
        job.updated_at = datetime.now(UTC)
        job.retry_after = job.updated_at + self.lease

    def start_pages(self, message: IngestionMessage, count: int) -> bool:
        job = self._current(message)
        if job is None:
            return False
        self.authorize(message.user_id, message.document_id)
        job.page_count = count
        self._heartbeat(job)
        self.jobs.save(job)
        return True

    def save_page(self, message: IngestionMessage, page: DocumentPage) -> bool:
        job = self._current(message)
        if job is None:
            return False
        document, _ = self.authorize(message.user_id, message.document_id)
        if (
            page.document_id != document.id
            or page.source_hash != document.file_hash
            or page.page_index < 0
            or page.page_index >= job.page_count
            or page.extraction_version != PIPELINE_VERSION
        ):
            raise InvalidDocument("Page provenance does not match the document.")
        self.jobs.save_page(page)
        self._heartbeat(job)
        self.jobs.save(job)
        return True

    def finish(self, message: IngestionMessage, *, error_code=None, queued_failure=False) -> bool:
        job = self._current(message, "queued" if queued_failure else "running")
        if job is None:
            return False
        if error_code is None:
            self.authorize(message.user_id, message.document_id)
        pages = self.jobs.pages(message.document_id)
        complete = sum(page.state == "completed" for page in pages)
        job.state = (
            "failed"
            if error_code
            else "completed"
            if complete == job.page_count and job.page_count > 0
            else "partial"
        )
        job.error_code = error_code
        job.updated_at = datetime.now(UTC)
        job.retry_after = None
        self.jobs.save(job)
        return True
