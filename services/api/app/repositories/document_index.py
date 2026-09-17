from dataclasses import dataclass
from uuid import UUID

from app.models.document_index import DocumentChunk, DocumentIndex, DocumentSection
from sqlalchemy import delete, select
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class IndexMessage:
    user_id: UUID
    document_id: UUID
    attempt_id: UUID


class DocumentIndexRepository:
    """Internal persistence. DocumentIndexService authorizes all access."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, document_id):
        return self.session.get(DocumentIndex, document_id, populate_existing=True)

    def sections(self, document_id):
        return list(
            self.session.scalars(
                select(DocumentSection)
                .where(DocumentSection.document_id == document_id)
                .order_by(DocumentSection.section_order)
            )
        )

    def chunks(self, document_id):
        return list(
            self.session.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.chunk_index)
            )
        )

    def save(self, row):
        self.session.add(row)
        self.session.flush()
        return row

    def queue(self, job, user_id):
        self.save(job)
        self.session.info.setdefault("index_messages", []).append(
            IndexMessage(user_id, job.document_id, job.attempt_id)
        )
        return job

    def replace(self, document_id, sections, chunks):
        self.session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        self.session.execute(
            delete(DocumentSection).where(DocumentSection.document_id == document_id)
        )
        # Parent rows precede their children in builder order.
        for row in sections:
            self.save(row)
        self.session.add_all(chunks)
        self.session.flush()
