from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.models.attachment import Attachment
from app.models.bike import Bike
from app.models.user import User
from app.services.attachment_links import AttachmentLinkService, AttachmentTargetNotFound
from app.services.attachments import AttachmentDeletionConflict, AttachmentService
from app.services.storage_quota import (
    ACCOUNT_STORAGE_LIMIT_BYTES,
    StorageQuotaExceeded,
    StorageQuotaService,
)
from app.services.uploads import (
    AttachmentNotFound,
    UploadNotComplete,
    UploadService,
    UploadStorageUnavailable,
)
from tests.unit.fakes import InMemoryBikeRepository
from tests.unit.test_attachment_links import Links
from tests.unit.test_uploads import _Attachments, _Storage


class FileStorage(_Storage):
    def __init__(self):
        super().__init__()
        self.deleted = []
        self.reads = []
        self.fail_delete = False

    def delete_object(self, key):
        if self.fail_delete:
            raise UploadStorageUnavailable()
        self.deleted.append(key)
        self.objects.pop(key, None)

    def presign_read(self, attachment, *, download, expires_in):
        self.reads.append((attachment.id, download, expires_in))
        return "https://storage.example/signed"


def make_management():
    owner, other = User(id=uuid4()), User(id=uuid4())
    attachments = _Attachments()
    links = Links(attachments)
    bikes = InMemoryBikeRepository()
    bike = bikes.add(Bike(user_id=owner.id))
    foreign = bikes.add(Bike(user_id=other.id))
    storage = FileStorage()
    now = datetime.now(UTC)
    file = attachments.add(
        Attachment(
            id=uuid4(),
            user_id=owner.id,
            file_name="manual.pdf",
            file_size=128,
            mime_type="application/pdf",
            status="uploaded",
            retention_class="persistent",
            purpose="document",
            s3_key="private/file.pdf",
            created_at=now - timedelta(hours=1),
        )
    )
    service = AttachmentService(attachments, links, bikes, storage)
    link_service = AttachmentLinkService(links, attachments, bikes)
    return owner, other, attachments, links, bike, foreign, storage, file, service, link_service


def test_quota_counts_pending_once_and_excludes_temporary_and_generated(management):
    owner, _, attachments, _, bike, _, _, file, _, linking = management
    for relationship in ["reference", "evidence"]:
        linking.create(
            owner,
            attachment_id=file.id,
            entity_type="bike",
            entity_id=bike.id,
            relationship_type=relationship,
        )
    quota = StorageQuotaService(attachments)
    assert quota.usage(owner.id).used_bytes == 128
    for retention, purpose in [("temporary", "troubleshooting"), ("persistent", "garage_scene")]:
        attachments.add(
            Attachment(
                id=uuid4(),
                user_id=owner.id,
                file_size=900,
                retention_class=retention,
                purpose=purpose,
                status="uploaded",
            )
        )
    assert quota.usage(owner.id).used_bytes == 128
    file.status = "pending"
    assert quota.usage(owner.id).used_bytes == 128


def test_quota_exact_boundary_and_rejection_before_storage(management):
    owner, other, attachments, _, _, _, storage, file, _, _ = management
    file.file_size = ACCOUNT_STORAGE_LIMIT_BYTES - 128
    uploads = UploadService(attachments, storage)
    values = dict(
        file_name="manual.pdf", mime_type="application/pdf", file_size=128, purpose="document"
    )
    uploads.begin(owner, **values)
    with pytest.raises(StorageQuotaExceeded):
        uploads.begin(owner, **values)
    assert len(storage.presign_calls) == 1
    uploads.begin(other, **values)
    assert len(storage.presign_calls) == 2


def test_list_scopes_to_bike_and_keeps_unlinked_account_files_accessible(management):
    owner, other, _, _, bike, foreign, _, file, service, linking = management
    assert service.list(owner, bike.id) == []
    assert service.list(owner, bike.id, include_all=True)[0].attachment.id == file.id
    link = linking.create(
        owner,
        attachment_id=file.id,
        entity_type="bike",
        entity_id=bike.id,
        relationship_type="reference",
    )
    record = service.list(owner, bike.id)[0]
    assert record.link_ids == [link.id]
    assert record.link_count == 1
    with pytest.raises(AttachmentTargetNotFound):
        service.list(owner, foreign.id, include_all=True)
    assert service.list(other) == []
    linking.delete(owner, link.id)
    assert service.list(owner, bike.id) == []
    assert service.list(owner)[0].attachment.id == file.id


def test_access_checks_ownership_upload_state_and_short_expiry(management):
    owner, other, _, _, _, _, storage, file, service, _ = management
    with pytest.raises(AttachmentNotFound):
        service.access(other, file.id, download=False)
    assert not storage.reads
    service.access(owner, file.id, download=True)
    assert storage.reads == [(file.id, True, 60)]
    file.status = "pending"
    with pytest.raises(UploadNotComplete):
        service.access(owner, file.id, download=False)


def test_delete_requires_confirmation_expired_grant_and_ownership(management):
    owner, other, attachments, _, _, _, storage, file, service, _ = management
    with pytest.raises(AttachmentNotFound):
        service.delete(other, file.id, confirmed=True)
    with pytest.raises(AttachmentDeletionConflict):
        service.delete(owner, file.id, confirmed=False)
    file.created_at = datetime.now(UTC)
    with pytest.raises(AttachmentDeletionConflict):
        service.delete(owner, file.id, confirmed=True)
    assert attachments.get(file.id, owner.id) is file
    assert not storage.deleted


def test_storage_failure_preserves_quota_and_retry_completes_deletion(management):
    owner, _, attachments, _, _, _, storage, file, service, _ = management
    storage.fail_delete = True
    with pytest.raises(UploadStorageUnavailable):
        service.delete(owner, file.id, confirmed=True)
    assert StorageQuotaService(attachments).usage(owner.id).used_bytes == 128
    storage.fail_delete = False
    service.delete(owner, file.id, confirmed=True)
    assert attachments.get(file.id, owner.id) is None
    assert StorageQuotaService(attachments).usage(owner.id).used_bytes == 0


def test_database_failure_after_object_deletion_is_retryable(management, monkeypatch):
    owner, _, attachments, _, _, _, storage, file, service, _ = management
    original_delete = attachments.delete

    def fail_delete(attachment):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(attachments, "delete", fail_delete)
    with pytest.raises(RuntimeError):
        service.delete(owner, file.id, confirmed=True)
    assert attachments.get(file.id, owner.id) is file
    monkeypatch.setattr(attachments, "delete", original_delete)
    service.delete(owner, file.id, confirmed=True)
    assert storage.deleted == [file.s3_key, file.s3_key]


@pytest.fixture
def management():
    return make_management()
