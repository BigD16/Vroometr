import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.documents.chunking import CHUNKING_VERSION, PageSource
from app.models.attachment import Attachment
from app.models.document_index import DocumentIndex
from app.services.attachment_processing import ProcessingBusy
from app.services.documents import InvalidDocument

from vroometr.ai.embeddings import validate_vectors


@dataclass(frozen=True)
class IndexClaim:
    attachment: Attachment
    source_hash: str
    pages: list[PageSource]
    model: str
    version: str


class DocumentIndexService:
    def __init__(self, repository, ingestion, lease_seconds, model, version):
        self.repository, self.ingestion = repository, ingestion
        self.lease = timedelta(seconds=lease_seconds)
        self.model, self.version = model, version

    def status(self, user_id, document_id):
        self.ingestion.authorize(user_id, document_id)
        job = self.repository.get(document_id)
        source = self.ingestion.jobs.get(document_id)
        stale = bool(
            job
            and (
                not source
                or source.attempt_id != job.source_attempt_id
                or job.embedding_model != self.model
                or job.embedding_version != self.version
                or job.chunking_version != CHUNKING_VERSION
            )
        )
        return (
            job,
            stale,
            self.repository.sections(document_id),
            self.repository.chunks(document_id),
        )

    def queue(self, user_id, document_id):
        self.ingestion.attachments.lock_owner(user_id)
        document, _ = self.ingestion.authorize(user_id, document_id)
        source = self.ingestion.jobs.get(document_id)
        if (
            document.confirmed_at is None
            or not source
            or source.state not in {"completed", "partial"}
        ):
            raise InvalidDocument("Extract the confirmed document before building chunks.")
        job, stale, _, _ = self.status(user_id, document_id)
        now = datetime.now(UTC)
        if job and not stale and job.state in {"queued", "running"} and job.retry_after > now:
            raise ProcessingBusy("Indexing is already queued or running. Retry if it stalls.")
        if job is None:
            job = DocumentIndex(document_id=document_id)
        job.attempt_id = uuid4()
        job.source_attempt_id = source.attempt_id
        job.state = "queued"
        job.chunking_version = CHUNKING_VERSION
        job.embedding_model, job.embedding_version = self.model, self.version
        job.error_code = None
        self._heartbeat(job)
        return self.repository.queue(job, user_id)

    def _heartbeat(self, job):
        job.updated_at = datetime.now(UTC)
        job.retry_after = job.updated_at + self.lease

    def _current(self, message, state="running"):
        self.ingestion.attachments.lock_owner(message.user_id)
        if self.ingestion.documents.get(message.document_id, message.user_id) is None:
            return None
        job = self.repository.get(message.document_id)
        source = self.ingestion.jobs.get(message.document_id)
        if (
            not job
            or job.state != state
            or job.attempt_id != message.attempt_id
            or not source
            or source.attempt_id != job.source_attempt_id
            or source.state not in {"completed", "partial"}
        ):
            return None
        return job

    def claim(self, message):
        job = self._current(message, "queued")
        if job is None:
            return None
        document, attachment = self.ingestion.authorize(message.user_id, message.document_id)
        if job.embedding_model != self.model or job.embedding_version != self.version:
            raise InvalidDocument("Embedding configuration changed. Queue a new attempt.")
        pages = self.ingestion.jobs.pages(document.id)
        if any(page.source_hash != document.file_hash for page in pages):
            raise InvalidDocument("Extracted pages do not match the source document.")
        job.state = "running"
        self._heartbeat(job)
        self.repository.save(job)
        return IndexClaim(
            Attachment(
                id=attachment.id,
                s3_key=attachment.s3_key,
                file_size=attachment.file_size,
                mime_type=attachment.mime_type,
            ),
            document.file_hash,
            [
                PageSource(p.page_index, p.text, p.source_hash, p.extraction_version, p.state)
                for p in pages
            ],
            job.embedding_model,
            job.embedding_version,
        )

    def prepare(self, message, plan):
        job = self._current(message)
        if job is None:
            return False
        document, _ = self.ingestion.authorize(message.user_id, message.document_id)
        pages = {p.page_index: p for p in self.ingestion.jobs.pages(document.id)}
        for chunk in plan.chunks:
            if len(chunk.source_span) != 1:
                raise InvalidDocument("Chunk must have one exact page span.")
            span = chunk.source_span[0]
            page = pages.get(span["page_index"])
            if (
                chunk.document_id != document.id
                or chunk.source_hash != document.file_hash
                or not page
                or page.state != "completed"
                or not (0 <= span["start_char"] < span["end_char"] <= len(page.text))
                or chunk.page_start != page.page_index
                or chunk.page_end != page.page_index
                or chunk.chunking_version != CHUNKING_VERSION
                or chunk.content_hash != hashlib.sha256(chunk.cleaned_text.encode()).hexdigest()
                or page.text[span["start_char"] : span["end_char"]] != chunk.cleaned_text
                or page.extraction_version != span["extraction_version"]
            ):
                raise InvalidDocument("Chunk provenance does not match extracted text.")
        # Reuse only this document's exact embedding inputs under the same model/version.
        cache = {
            c.content_hash: c.embedding
            for c in self.repository.chunks(document.id)
            if c.embedding is not None
            and c.embedding_model == job.embedding_model
            and c.embedding_version == job.embedding_version
        }
        for chunk in plan.chunks:
            if chunk.content_hash in cache:
                chunk.embedding = cache[chunk.content_hash]
                chunk.embedding_model, chunk.embedding_version = (
                    job.embedding_model,
                    job.embedding_version,
                )
        self.repository.replace(document.id, plan.sections, plan.chunks)
        self._heartbeat(job)
        self.repository.save(job)
        return True

    def pending(self, message, limit=16):
        job = self._current(message)
        if job is None:
            return None
        self.ingestion.authorize(message.user_id, message.document_id)
        self._heartbeat(job)
        self.repository.save(job)
        return [
            (c.id, c.cleaned_text)
            for c in self.repository.chunks(message.document_id)
            if c.embedding is None
        ][:limit]

    def save_embeddings(self, message, chunk_ids, vectors):
        job = self._current(message)
        if job is None:
            return False
        self.ingestion.authorize(message.user_id, message.document_id)
        validate_vectors(vectors, len(chunk_ids))
        chunks = {c.id: c for c in self.repository.chunks(message.document_id)}
        if len(set(chunk_ids)) != len(chunk_ids) or any(key not in chunks for key in chunk_ids):
            raise InvalidDocument("Embedding batch does not belong to this document.")
        for key, vector in zip(chunk_ids, vectors, strict=True):
            chunk = chunks[key]
            chunk.embedding = vector
            chunk.embedding_model, chunk.embedding_version = (
                job.embedding_model,
                job.embedding_version,
            )
            self.repository.save(chunk)
        self._heartbeat(job)
        self.repository.save(job)
        return True

    def finish(self, message, *, error_code=None, queued_failure=False):
        job = self._current(message, "queued" if queued_failure else "running")
        if job is None:
            return False
        if not error_code:
            self.ingestion.authorize(message.user_id, message.document_id)
        chunks = self.repository.chunks(message.document_id)
        source = self.ingestion.jobs.get(message.document_id)
        if error_code == "embedding_unconfigured":
            job.state = "awaiting_configuration"
        elif error_code:
            job.state = "failed"
        else:
            job.state = (
                "completed"
                if (
                    chunks
                    and all(c.embedding is not None for c in chunks)
                    and source.state == "completed"
                )
                else "partial"
            )
        job.error_code = error_code
        job.updated_at = datetime.now(UTC)
        job.retry_after = None
        self.repository.save(job)
        return True
