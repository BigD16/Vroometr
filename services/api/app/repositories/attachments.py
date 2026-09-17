from typing import Protocol
from uuid import UUID

from app.models.attachment import Attachment
from app.models.user import User
from sqlalchemy import func, select
from sqlalchemy.orm import Session


class AttachmentStore(Protocol):
    def lock_owner(self, user_id: UUID) -> None: ...

    def storage_bytes(self, user_id: UUID) -> int: ...

    def list_for_user(self, user_id: UUID) -> list[Attachment]: ...

    def delete(self, attachment: Attachment) -> None: ...

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

    def lock_owner(self, user_id: UUID) -> None:
        self._session.execute(select(User.id).where(User.id == user_id).with_for_update()).first()

    def storage_bytes(self, user_id: UUID) -> int:
        # Pending files reserve space too. Links do not multiply account usage.
        return self._session.scalar(
            select(func.coalesce(func.sum(Attachment.file_size), 0)).where(
                Attachment.user_id == user_id,
                Attachment.retention_class == "persistent",
                Attachment.purpose != "garage_scene",
            )
        )

    def list_for_user(self, user_id: UUID) -> list[Attachment]:
        return list(
            self._session.scalars(
                select(Attachment)
                .where(
                    Attachment.user_id == user_id,
                )
                .order_by(Attachment.created_at.desc(), Attachment.id)
            )
        )

    def delete(self, attachment: Attachment) -> None:
        self._session.delete(attachment)
        self._session.flush()
