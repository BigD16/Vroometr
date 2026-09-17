from dataclasses import dataclass
from uuid import UUID

from app.models.document_ingestion import DocumentIngestion, DocumentPage
from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class IngestionMessage:
    user_id: UUID
    document_id: UUID
    attempt_id: UUID


class DocumentIngestionRepository:
    """Internal persistence; callers authorize the document through the domain service."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, document_id: UUID) -> DocumentIngestion | None:
        return self.session.get(DocumentIngestion, document_id, populate_existing=True)

    def pages(self, document_id: UUID) -> list[DocumentPage]:
        return list(
            self.session.scalars(
                select(DocumentPage)
                .where(DocumentPage.document_id == document_id)
                .order_by(DocumentPage.page_index)
            )
        )

    def save(self, row):
        self.session.add(row)
        self.session.flush()
        return row

    def save_page(self, row: DocumentPage) -> None:
        self.session.merge(row)
        self.session.flush()

    def queue(self, row: DocumentIngestion, user_id: UUID) -> DocumentIngestion:
        self.save(row)
        self.session.info.setdefault("ingestion_messages", []).append(
            IngestionMessage(user_id, row.document_id, row.attempt_id)
        )
        return row
