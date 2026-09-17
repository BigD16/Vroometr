from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.models.attachment import AttachmentStatus
from app.models.attachment_link import AttachmentLink
from app.models.user import User
from app.repositories.attachment_links import AttachmentLinkStore
from app.repositories.attachments import AttachmentStore
from app.repositories.bikes import BikeStore
from app.services.uploads import AttachmentNotFound, UploadNotComplete


class InvalidAttachmentLink(ValueError):
    pass


class AttachmentTargetNotFound(LookupError):
    pass


class AttachmentLinkNotFound(LookupError):
    pass


class AttachmentLinkService:
    def __init__(
        self,
        links: AttachmentLinkStore,
        attachments: AttachmentStore,
        bikes: BikeStore,
    ) -> None:
        self._links = links
        self._attachments = attachments
        self._bikes = bikes

    def _require_target(self, user: User, entity_type: str, entity_id: UUID) -> None:
        # Add each new domain here only alongside its owner-scoped repository check.
        if entity_type != "bike":
            raise InvalidAttachmentLink("unsupported attachment target")
        if self._bikes.get(entity_id, user.id) is None:
            raise AttachmentTargetNotFound

    def create(
        self,
        user: User,
        *,
        attachment_id: UUID,
        entity_type: str,
        entity_id: UUID,
        relationship_type: str,
    ) -> AttachmentLink:
        if not isinstance(relationship_type, str) or not 1 <= len(relationship_type.strip()) <= 32:
            raise InvalidAttachmentLink("relationship_type must contain 1–32 characters")
        self._attachments.lock_owner(user.id)
        self._require_target(user, entity_type, entity_id)
        attachment = self._attachments.get(attachment_id, user.id)
        if attachment is None:
            raise AttachmentNotFound
        if attachment.status != AttachmentStatus.UPLOADED.value:
            raise UploadNotComplete("verify the upload before attaching it")
        return self._links.add(
            AttachmentLink(
                id=uuid4(),
                attachment_id=attachment_id,
                entity_type=entity_type,
                entity_id=entity_id,
                relationship_type=relationship_type.strip(),
                created_at=datetime.now(UTC),
            )
        )

    def list_for_entity(
        self,
        user: User,
        *,
        entity_type: str,
        entity_id: UUID,
    ) -> list[AttachmentLink]:
        self._require_target(user, entity_type, entity_id)
        return self._links.list_for_entity(entity_type, entity_id, user.id)

    def delete(self, user: User, link_id: UUID) -> None:
        self._attachments.lock_owner(user.id)
        link = self._links.get(link_id, user.id)
        if link is None:
            raise AttachmentLinkNotFound
        self._require_target(user, link.entity_type, link.entity_id)
        # Unlinking never deletes the attachment or other uses of the same file.
        self._links.delete(link)
