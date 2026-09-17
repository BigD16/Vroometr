from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from app.models.attachment import Attachment, AttachmentStatus, RetentionClass
from app.models.user import User
from app.repositories.attachments import AttachmentStore
from app.services.storage_quota import StorageQuotaService

_PRESIGN_EXPIRES_SECONDS = 15 * 60
_MAX_FILENAME_LENGTH = 255


@dataclass(frozen=True)
class UploadRule:
    extensions: frozenset[str]
    canonical_extension: str
    max_bytes: int


_UPLOAD_RULES = {
    "application/pdf": UploadRule(frozenset({".pdf"}), ".pdf", 100 * 1024 * 1024),
    "image/jpeg": UploadRule(frozenset({".jpg", ".jpeg"}), ".jpg", 15 * 1024 * 1024),
    "image/png": UploadRule(frozenset({".png"}), ".png", 15 * 1024 * 1024),
    "image/webp": UploadRule(frozenset({".webp"}), ".webp", 15 * 1024 * 1024),
}


class InvalidUpload(ValueError):
    pass


class AttachmentNotFound(LookupError):
    pass


class UploadNotComplete(RuntimeError):
    pass


class UploadVerificationFailed(RuntimeError):
    pass


class UploadStorageUnavailable(RuntimeError):
    pass


class StoredObjectNotFound(LookupError):
    pass


@dataclass(frozen=True)
class PresignedPost:
    url: str
    fields: dict[str, str]
    expires_in: int


@dataclass(frozen=True)
class StoredObjectMetadata:
    content_length: int
    content_type: str | None
    attachment_id: str | None


class ObjectStorage(Protocol):
    def presign_post(
        self,
        *,
        object_key: str,
        mime_type: str,
        file_size: int,
        attachment_id: UUID,
        expires_in: int,
    ) -> PresignedPost: ...

    def head_object(self, object_key: str) -> StoredObjectMetadata: ...


@dataclass(frozen=True)
class UploadGrant:
    attachment: Attachment
    post: PresignedPost


class UploadProcessing(Protocol):
    def queue(self, user_id: UUID, attachment_id: UUID) -> object: ...


class UploadService:
    def __init__(
        self,
        attachments: AttachmentStore,
        storage: ObjectStorage,
        processing: UploadProcessing | None = None,
    ) -> None:
        self._attachments = attachments
        self._storage = storage
        self._processing = processing

    def begin(
        self,
        user: User,
        *,
        file_name: str,
        mime_type: str,
        file_size: int,
        purpose: str,
    ) -> UploadGrant:
        normalized_name, normalized_mime, rule = self._validate_file(
            file_name,
            mime_type,
            file_size,
        )
        if purpose != "document":
            raise InvalidUpload("unsupported upload purpose")

        StorageQuotaService(self._attachments).reserve(user.id, file_size)
        attachment_id = uuid4()
        object_key = f"users/{user.id}/attachments/{attachment_id}{rule.canonical_extension}"
        post = self._storage.presign_post(
            object_key=object_key,
            mime_type=normalized_mime,
            file_size=file_size,
            attachment_id=attachment_id,
            expires_in=_PRESIGN_EXPIRES_SECONDS,
        )
        now = datetime.now(UTC)
        attachment = Attachment(
            id=attachment_id,
            user_id=user.id,
            s3_key=object_key,
            file_name=normalized_name,
            mime_type=normalized_mime,
            file_size=file_size,
            purpose=purpose,
            status=AttachmentStatus.PENDING.value,
            retention_class=RetentionClass.PERSISTENT.value,
            created_at=now,
            updated_at=now,
        )
        return UploadGrant(self._attachments.add(attachment), post)

    def complete(self, user: User, attachment_id: UUID) -> Attachment:
        self._attachments.lock_owner(user.id)
        attachment = self._attachments.get(attachment_id, user.id)
        if attachment is None:
            raise AttachmentNotFound
        if attachment.status == AttachmentStatus.UPLOADED.value:
            if self._processing is not None:
                self._processing.queue(user.id, attachment.id)
            return attachment

        try:
            stored = self._storage.head_object(attachment.s3_key)
        except StoredObjectNotFound as exc:
            raise UploadNotComplete("uploaded object was not found") from exc

        if (
            stored.content_length != attachment.file_size
            or stored.content_type != attachment.mime_type
            or stored.attachment_id != str(attachment.id)
        ):
            raise UploadVerificationFailed("uploaded object metadata does not match")

        attachment.status = AttachmentStatus.UPLOADED.value
        attachment.updated_at = datetime.now(UTC)
        self._attachments.save(attachment)
        if self._processing is not None:
            self._processing.queue(user.id, attachment.id)
        return attachment

    @staticmethod
    def _validate_file(
        file_name: object,
        mime_type: object,
        file_size: object,
    ) -> tuple[str, str, UploadRule]:
        if not isinstance(file_name, str):
            raise InvalidUpload("file_name must be text")
        normalized_name = file_name.strip()
        if (
            not normalized_name
            or len(normalized_name) > _MAX_FILENAME_LENGTH
            or "/" in normalized_name
            or "\\" in normalized_name
            or any(ord(character) < 32 for character in normalized_name)
        ):
            raise InvalidUpload("invalid file_name")

        if not isinstance(mime_type, str):
            raise InvalidUpload("mime_type must be text")
        normalized_mime = mime_type.strip().lower()
        rule = _UPLOAD_RULES.get(normalized_mime)
        if rule is None:
            raise InvalidUpload("file type must be PDF, JPEG, PNG, or WebP")
        if Path(normalized_name).suffix.lower() not in rule.extensions:
            raise InvalidUpload("file extension does not match its MIME type")

        if isinstance(file_size, bool) or not isinstance(file_size, int):
            raise InvalidUpload("file_size must be an integer")
        if file_size <= 0:
            raise InvalidUpload("file cannot be empty")
        if file_size > rule.max_bytes:
            raise InvalidUpload("file exceeds the allowed size")

        return normalized_name, normalized_mime, rule
