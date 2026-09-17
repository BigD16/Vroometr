from typing import Protocol
from uuid import UUID

from app.models.bike import Bike
from app.models.document import Document
from sqlalchemy import select, update
from sqlalchemy.orm import Session


class DocumentStore(Protocol):
    def get(self, document_id: UUID, user_id: UUID) -> Document | None: ...
    def list_for_bike(self, bike_id: UUID, user_id: UUID) -> list[Document]: ...
    def matching_hash(self, file_hash: str, user_id: UUID) -> list[Document]: ...
    def add(self, document: Document) -> Document: ...
    def save(self, document: Document) -> Document: ...
    def clear_primary(self, bike_id: UUID) -> None: ...


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, document_id: UUID, user_id: UUID) -> Document | None:
        return self._session.scalars(
            select(Document)
            .join(Bike)
            .where(
                Document.id == document_id,
                Bike.user_id == user_id,
            )
        ).first()

    def list_for_bike(self, bike_id: UUID, user_id: UUID) -> list[Document]:
        return list(
            self._session.scalars(
                select(Document)
                .join(Bike)
                .where(
                    Document.bike_id == bike_id,
                    Bike.user_id == user_id,
                )
                .order_by(Document.created_at.desc(), Document.id)
            )
        )

    def matching_hash(self, file_hash: str, user_id: UUID) -> list[Document]:
        return list(
            self._session.scalars(
                select(Document)
                .join(Bike)
                .where(
                    Document.file_hash == file_hash,
                    Bike.user_id == user_id,
                )
            )
        )

    def add(self, document: Document) -> Document:
        self._session.add(document)
        self._session.flush()
        return document

    def save(self, document: Document) -> Document:
        self._session.add(document)
        self._session.flush()
        return document

    def clear_primary(self, bike_id: UUID) -> None:
        self._session.execute(
            update(Document).where(Document.bike_id == bike_id).values(is_primary=False)
        )
        self._session.flush()
