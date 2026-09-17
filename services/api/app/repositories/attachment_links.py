from typing import Protocol
from uuid import UUID

from app.models.attachment import Attachment
from app.models.attachment_link import AttachmentLink
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session


class AttachmentLinkStore(Protocol):
    def list_for_user(self, user_id: UUID) -> list[AttachmentLink]: ...

    def get(self, link_id: UUID, user_id: UUID) -> AttachmentLink | None: ...

    def list_for_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        user_id: UUID,
    ) -> list[AttachmentLink]: ...

    def add(self, link: AttachmentLink) -> AttachmentLink: ...

    def delete(self, link: AttachmentLink) -> None: ...


class AttachmentLinkRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, link_id: UUID, user_id: UUID) -> AttachmentLink | None:
        return self._session.scalars(
            select(AttachmentLink)
            .join(Attachment)
            .where(
                AttachmentLink.id == link_id,
                Attachment.user_id == user_id,
            )
        ).first()

    def list_for_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        user_id: UUID,
    ) -> list[AttachmentLink]:
        return list(
            self._session.scalars(
                select(AttachmentLink)
                .join(Attachment)
                .where(
                    AttachmentLink.entity_type == entity_type,
                    AttachmentLink.entity_id == entity_id,
                    Attachment.user_id == user_id,
                )
                .order_by(AttachmentLink.created_at, AttachmentLink.id)
            )
        )

    def add(self, link: AttachmentLink) -> AttachmentLink:
        # Retries and concurrent requests create a single relationship.
        statement = (
            insert(AttachmentLink)
            .values(
                id=link.id,
                attachment_id=link.attachment_id,
                entity_type=link.entity_type,
                entity_id=link.entity_id,
                relationship_type=link.relationship_type,
                created_at=link.created_at,
            )
            .on_conflict_do_nothing(constraint="uq_attachment_links_relationship")
        )
        self._session.execute(statement)
        return self._session.scalars(
            select(AttachmentLink).where(
                AttachmentLink.attachment_id == link.attachment_id,
                AttachmentLink.entity_type == link.entity_type,
                AttachmentLink.entity_id == link.entity_id,
                AttachmentLink.relationship_type == link.relationship_type,
            )
        ).one()

    def delete(self, link: AttachmentLink) -> None:
        self._session.delete(link)
        self._session.flush()

    def list_for_user(self, user_id: UUID) -> list[AttachmentLink]:
        return list(self._session.scalars(select(AttachmentLink).join(Attachment).where(
            Attachment.user_id == user_id,
        )))
