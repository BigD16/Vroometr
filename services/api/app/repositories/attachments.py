from typing import Protocol
from uuid import UUID

from app.models.attachment import Attachment
from sqlalchemy import select
from sqlalchemy.orm import Session


class AttachmentStore(Protocol):
    def get(self, attachment_id: UUID, user_id: UUID) -> Attachment | None: ...

    def add(self, attachment: Attachment) -> Attachment: ...

    def save(self, attachment: Attachment) -> Attachment: ...


class AttachmentRepository:
    """Loads attachment records only through their owning user."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, attachment_id: UUID, user_id: UUID) -> Attachment | None:
        statement = select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.user_id == user_id,
        )
        return self._session.scalars(statement).first()

    def add(self, attachment: Attachment) -> Attachment:
        self._session.add(attachment)
        self._session.flush()
        return attachment

    def save(self, attachment: Attachment) -> Attachment:
        self._session.add(attachment)
        self._session.flush()
        return attachment
