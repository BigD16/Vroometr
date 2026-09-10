from uuid import UUID

import pytest
from app.models.attachment import Attachment
from app.services.uploads import (
    AttachmentNotFound,
    InvalidUpload,
    PresignedPost,
    StoredObjectMetadata,
    StoredObjectNotFound,
    UploadNotComplete,
    UploadService,
    UploadVerificationFailed,
)
from app.services.users import UserService
from tests.unit.fakes import InMemoryUserRepository


class _Attachments:
    def __init__(self) -> None:
        self.items: dict[UUID, Attachment] = {}

    def get(self, attachment_id: UUID, user_id: UUID) -> Attachment | None:
        attachment = self.items.get(attachment_id)
        if attachment is None or attachment.user_id != user_id:
            return None
        return attachment

    def add(self, attachment: Attachment) -> Attachment:
        self.items[attachment.id] = attachment
        return attachment

    def save(self, attachment: Attachment) -> Attachment:
        self.items[attachment.id] = attachment
        return attachment


class _Storage:
    def __init__(self) -> None:
        self.presign_calls: list[dict[str, object]] = []
        self.objects: dict[str, StoredObjectMetadata] = {}

    def presign_post(self, **kwargs) -> PresignedPost:
        self.presign_calls.append(kwargs)
        return PresignedPost(
            url="http://object-storage/upload",
            fields={"policy": "signed-policy"},
            expires_in=kwargs["expires_in"],
        )

    def head_object(self, object_key: str) -> StoredObjectMetadata:
        try:
            return self.objects[object_key]
        except KeyError as exc:
            raise StoredObjectNotFound from exc


def _service() -> tuple[UploadService, _Attachments, _Storage]:
    attachments = _Attachments()
    storage = _Storage()
    return UploadService(attachments, storage), attachments, storage


def test_begin_creates_owner_scoped_pending_attachment_and_exact_upload_policy() -> None:
    uploads, attachments, storage = _service()
    owner = UserService(InMemoryUserRepository()).create("user_clerk_upload")

    grant = uploads.begin(
        owner,
        file_name="manual.pdf",
        mime_type="application/pdf",
        file_size=1234,
        purpose="document",
    )

    attachment = grant.attachment
    assert attachments.get(attachment.id, owner.id) is attachment
    assert attachment.status == "pending"
    assert attachment.retention_class == "persistent"
    assert attachment.s3_key == f"users/{owner.id}/attachments/{attachment.id}.pdf"
    assert grant.post.expires_in == 900
    assert storage.presign_calls == [
        {
            "object_key": attachment.s3_key,
            "mime_type": "application/pdf",
            "file_size": 1234,
            "attachment_id": attachment.id,
            "expires_in": 900,
        }
    ]


@pytest.mark.parametrize(
    ("file_name", "mime_type", "file_size"),
    [
        ("manual.exe", "application/octet-stream", 100),
        ("manual.jpg", "application/pdf", 100),
        ("../manual.pdf", "application/pdf", 100),
        ("manual.pdf", "application/pdf", 0),
        ("manual.pdf", "application/pdf", 100 * 1024 * 1024 + 1),
        ("photo.jpg", "image/jpeg", 15 * 1024 * 1024 + 1),
    ],
)
def test_begin_rejects_unsafe_file_metadata(
    file_name: str,
    mime_type: str,
    file_size: int,
) -> None:
    uploads, _, _ = _service()
    owner = UserService(InMemoryUserRepository()).create("user_clerk_invalid_upload")
    with pytest.raises(InvalidUpload):
        uploads.begin(
            owner,
            file_name=file_name,
            mime_type=mime_type,
            file_size=file_size,
            purpose="document",
        )


def test_complete_verifies_s3_metadata_and_is_idempotent() -> None:
    uploads, _, storage = _service()
    owner = UserService(InMemoryUserRepository()).create("user_clerk_complete_upload")
    attachment = uploads.begin(
        owner,
        file_name="bike.png",
        mime_type="image/png",
        file_size=256,
        purpose="document",
    ).attachment

    with pytest.raises(UploadNotComplete):
        uploads.complete(owner, attachment.id)

    storage.objects[attachment.s3_key] = StoredObjectMetadata(
        content_length=256,
        content_type="image/png",
        attachment_id=str(attachment.id),
    )
    completed = uploads.complete(owner, attachment.id)
    assert completed.status == "uploaded"
    assert uploads.complete(owner, attachment.id) is completed


def test_complete_rejects_metadata_mismatch_and_hides_other_owners() -> None:
    uploads, _, storage = _service()
    users = UserService(InMemoryUserRepository())
    owner = users.create("user_clerk_attachment_owner")
    other = users.create("user_clerk_attachment_other")
    attachment = uploads.begin(
        owner,
        file_name="manual.pdf",
        mime_type="application/pdf",
        file_size=512,
        purpose="document",
    ).attachment
    storage.objects[attachment.s3_key] = StoredObjectMetadata(
        content_length=511,
        content_type="application/pdf",
        attachment_id=str(attachment.id),
    )

    with pytest.raises(UploadVerificationFailed):
        uploads.complete(owner, attachment.id)
    with pytest.raises(AttachmentNotFound):
        uploads.complete(other, attachment.id)
