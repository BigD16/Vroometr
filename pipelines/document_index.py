"""Build source-bound sections/chunks, then embed batches outside database transactions."""

import hashlib
import logging
from uuid import UUID

import pymupdf
from app.db import SessionLocal
from app.documents.chunking import build_chunks
from app.documents.index_runtime import index_service
from app.documents.runtime import document_storage
from app.repositories.document_index import IndexMessage
from app.services.attachments import AttachmentAccessBlocked

from vroometr.ai.embeddings import EmbeddingFailed
from vroometr.ai.factory import get_embedding_model
from vroometr.ai.unconfigured import UnconfiguredError

logger = logging.getLogger(__name__)


class SourceChanged(ValueError):
    pass


def process(user_id, document_id, attempt_id, *, storage=None, embedder=None):
    message = IndexMessage(UUID(user_id), UUID(document_id), UUID(attempt_id))
    claimed = False
    try:
        with SessionLocal.begin() as session:
            claim = index_service(session).claim(message)
        if claim is None:
            return {"status": "ignored"}
        claimed = True
        content = (storage or document_storage()).read_attachment(claim.attachment)
        if hashlib.sha256(content).hexdigest() != claim.source_hash:
            raise SourceChanged
        with pymupdf.open(stream=content, filetype="pdf") as pdf:
            plan = build_chunks(message.document_id, claim.pages, pdf.get_toc())
        with SessionLocal.begin() as session:
            if not index_service(session).prepare(message, plan):
                return {"status": "ignored"}
        model = embedder or get_embedding_model()
        while True:
            with SessionLocal.begin() as session:
                batch = index_service(session).pending(message)
            if batch is None:
                return {"status": "ignored"}
            if not batch:
                break
            vectors = model.embed([text for _, text in batch])
            with SessionLocal.begin() as session:
                if not index_service(session).save_embeddings(
                    message, [key for key, _ in batch], vectors
                ):
                    return {"status": "ignored"}
        with SessionLocal.begin() as session:
            service = index_service(session)
            if not service.finish(message):
                return {"status": "ignored"}
            return {"status": service.repository.get(message.document_id).state}
    except Exception as exc:
        code = (
            "embedding_unconfigured"
            if isinstance(exc, UnconfiguredError)
            else "embedding_failed"
            if isinstance(exc, EmbeddingFailed)
            else "file_blocked"
            if isinstance(exc, AttachmentAccessBlocked)
            else "source_changed"
            if isinstance(exc, SourceChanged)
            else "index_failed"
        )
        logger.error("Document indexing failed (%s)", type(exc).__name__)
        with SessionLocal.begin() as session:
            applied = index_service(session).finish(
                message, error_code=code, queued_failure=not claimed
            )
            job = index_service(session).repository.get(message.document_id) if applied else None
            return {"status": job.state if job else "ignored"}
