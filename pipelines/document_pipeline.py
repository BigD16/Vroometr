"""Hash-bound PDF snapshot -> independently committed page results -> durable outcome."""

import hashlib
import logging
from uuid import UUID

import pymupdf
from app.db import SessionLocal
from app.documents.extraction import extract_page, failed_page
from app.documents.runtime import document_storage, ingestion_service
from app.repositories.document_ingestion import IngestionMessage
from app.services.attachments import AttachmentAccessBlocked

logger = logging.getLogger(__name__)


class SourceChanged(ValueError):
    pass


def process(
    user_id: str, document_id: str, attempt_id: str, *, storage=None, extractor=None
) -> dict[str, str]:
    message = IngestionMessage(UUID(user_id), UUID(document_id), UUID(attempt_id))
    claimed = False
    try:
        with SessionLocal.begin() as session:
            claim = ingestion_service(session).claim(message)
        if claim is None:
            return {"status": "ignored"}
        claimed = True
        # One bytes snapshot for the entire attempt. Never reread mutable S3 keys per page.
        content = (storage or document_storage()).read_attachment(claim.attachment)
        if hashlib.sha256(content).hexdigest() != claim.file_hash:
            raise SourceChanged
        with pymupdf.open(stream=content, filetype="pdf") as pdf:
            if (
                not pdf.is_pdf
                or pdf.needs_pass
                or pdf.is_encrypted
                or (pdf.metadata or {}).get("encryption")
                or pdf.page_count == 0
            ):
                raise ValueError("Invalid PDF")
            with SessionLocal.begin() as session:
                if not ingestion_service(session).start_pages(message, pdf.page_count):
                    return {"status": "ignored"}
            for index in range(pdf.page_count):
                if index in claim.completed_pages:
                    continue
                try:
                    page = (extractor or extract_page)(
                        pdf, index, message.document_id, claim.file_hash
                    )
                except Exception as exc:
                    logger.error("PDF page extraction failed (%s)", type(exc).__name__)
                    page = failed_page(index, message.document_id, claim.file_hash)
                with SessionLocal.begin() as session:
                    if not ingestion_service(session).save_page(message, page):
                        return {"status": "ignored"}
        with SessionLocal.begin() as session:
            service = ingestion_service(session)
            applied = service.finish(message)
            job = service.jobs.get(message.document_id)
            state = job.state if applied else "ignored"
        return {"status": state}
    except Exception as exc:
        code = (
            "source_changed"
            if isinstance(exc, SourceChanged)
            else "file_blocked"
            if isinstance(exc, AttachmentAccessBlocked)
            else "extraction_failed"
        )
        logger.error("Document extraction failed (%s)", type(exc).__name__)
        with SessionLocal.begin() as session:
            applied = ingestion_service(session).finish(
                message, error_code=code, queued_failure=not claimed
            )
        return {"status": "failed" if applied else "ignored"}
