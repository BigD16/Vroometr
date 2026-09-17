from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from app.models.attachment import Attachment
from app.models.user import User
from app.repositories.attachment_links import AttachmentLinkStore
from app.repositories.attachments import AttachmentStore
from app.repositories.bikes import BikeStore
from app.services.attachment_links import AttachmentTargetNotFound
from app.services.uploads import _PRESIGN_EXPIRES_SECONDS, AttachmentNotFound, UploadNotComplete


class AttachmentAccessBlocked(PermissionError):
    pass


class AttachmentDeletionConflict(ValueError):
    pass


class AttachmentStorage(Protocol):
    def presign_read(self, attachment: Attachment, *, download: bool, expires_in: int) -> str: ...

    def delete_object(self, object_key: str) -> None: ...


@dataclass(frozen=True)
class AttachmentSummary:
    attachment: Attachment
    link_ids: list[UUID]
    link_count: int
    deletable_after: datetime


class AttachmentService:
    def __init__(
        self,
        attachments: AttachmentStore,
        links: AttachmentLinkStore,
        bikes: BikeStore,
        storage: AttachmentStorage,
    ) -> None:
        self._attachments = attachments
        self._links = links
        self._bikes = bikes
        self._storage = storage

    @staticmethod
    def deletable_after(attachment: Attachment) -> datetime:
        # A live upload grant could otherwise recreate the object after deletion.
        return attachment.created_at + timedelta(seconds=_PRESIGN_EXPIRES_SECONDS)

    def list(
        self, user: User, bike_id: UUID | None = None, *, include_all: bool = False
    ) -> list[AttachmentSummary]:
        if bike_id is not None and self._bikes.get(bike_id, user.id) is None:
            raise AttachmentTargetNotFound
        links = self._links.list_for_user(user.id)
        result = []
        for attachment in self._attachments.list_for_user(user.id):
            file_links = [link for link in links if link.attachment_id == attachment.id]
            bike_links = [
                link.id
                for link in file_links
                if link.entity_type == "bike" and link.entity_id == bike_id
            ]
            if bike_id is not None and not include_all and not bike_links:
                continue
            result.append(
                AttachmentSummary(
                    attachment,
                    bike_links,
                    len(file_links),
                    self.deletable_after(attachment),
                )
            )
        return result

    def access(self, user: User, attachment_id: UUID, *, download: bool) -> str:
        attachment = self._attachments.get(attachment_id, user.id)
        if attachment is None:
            raise AttachmentNotFound
        if attachment.status != "uploaded":
            raise UploadNotComplete("Verify the upload before opening this file.")
        if attachment.processing is not None and attachment.processing.scan_status == "infected":
            raise AttachmentAccessBlocked("This file was flagged as infected and cannot be opened.")
        return self._storage.presign_read(attachment, download=download, expires_in=60)

    def delete(self, user: User, attachment_id: UUID, *, confirmed: bool) -> None:
        if confirmed is not True:
            raise AttachmentDeletionConflict("Confirm deletion of the file and all its links.")
        self._attachments.lock_owner(user.id)
        attachment = self._attachments.get(attachment_id, user.id)
        if attachment is None:
            raise AttachmentNotFound
        if datetime.now(UTC) < self.deletable_after(attachment):
            raise AttachmentDeletionConflict(
                "The upload grant is still active. Retry after "
                f"{self.deletable_after(attachment).isoformat()}."
            )
        # S3 delete is idempotent. Keep metadata/quota on storage failure; if DB commit
        # fails after S3 succeeds, the same request safely finishes cleanup on retry.
        self._storage.delete_object(attachment.s3_key)
        self._attachments.delete(attachment)
