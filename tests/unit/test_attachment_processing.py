from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.models.attachment import Attachment
from app.models.user import User
from app.repositories.attachment_processing import ProcessingMessage
from app.scanning.ports import ScanResult, UnconfiguredScanner
from app.services.attachment_processing import AttachmentProcessingService, ProcessingBusy
from app.services.attachments import AttachmentAccessBlocked, AttachmentService
from app.services.uploads import (
    AttachmentNotFound,
    StoredObjectMetadata,
    UploadNotComplete,
    UploadService,
)
from tests.unit.fakes import InMemoryBikeRepository
from tests.unit.test_attachment_links import Links
from tests.unit.test_uploads import _Attachments, _Storage


class Jobs:
    def __init__(self, attachments):
        self.items = {}
        self.messages = []
        self.attachments = attachments

    def get(self, attachment_id, user_id):
        if self.attachments.get(attachment_id, user_id) is None:
            return None
        return self.items.get(attachment_id)

    def save(self, job):
        self.items[job.attachment_id] = job
        self.attachments.items[job.attachment_id].processing = job
        return job

    def queue(self, job, user_id):
        self.save(job)
        self.messages.append(ProcessingMessage(user_id, job.attachment_id, job.attempt_id))
        return job


def setup_processing():
    owner = User(id=uuid4())
    attachments = _Attachments()
    file = attachments.add(
        Attachment(
            id=uuid4(),
            user_id=owner.id,
            status="uploaded",
            s3_key="private/file.pdf",
            created_at=datetime.now(UTC),
            file_name="file.pdf",
            file_size=128,
            mime_type="application/pdf",
            retention_class="persistent",
            purpose="document",
        )
    )
    jobs = Jobs(attachments)
    service = AttachmentProcessingService(jobs, attachments, 300)
    return owner, file, attachments, jobs, service


def test_placeholder_never_claims_a_scan_passed():
    assert UnconfiguredScanner().scan("some-key") == ScanResult("not_scanned", "unconfigured")
    with pytest.raises(ValueError):
        ScanResult("invalid", "scanner-v1")


def test_queue_requires_owned_uploaded_attachment_and_complete_is_idempotent():
    owner, file, attachments, jobs, service = setup_processing()
    with pytest.raises(AttachmentNotFound):
        service.queue(uuid4(), file.id)
    file.status = "pending"
    with pytest.raises(UploadNotComplete):
        service.queue(owner.id, file.id)
    storage = _Storage()
    storage.objects[file.s3_key] = StoredObjectMetadata(128, "application/pdf", str(file.id))
    uploads = UploadService(attachments, storage, service)
    uploads.complete(owner, file.id)
    uploads.complete(owner, file.id)
    assert len(jobs.messages) == 1
    assert jobs.get(file.id, owner.id).state == "queued"


def test_claim_is_exclusive_and_completed_job_is_not_run_twice():
    owner, file, _, jobs, service = setup_processing()
    job = service.queue(owner.id, file.id)
    message = jobs.messages[-1]
    assert service.claim(message).object_key == file.s3_key
    assert service.claim(message) is None
    assert job.state == "running"
    assert service.finish(message, result=UnconfiguredScanner().scan(file.s3_key))
    assert job.state == "completed"
    assert job.scan_status == "not_scanned"
    assert job.retry_after is None
    assert service.claim(message) is None


def test_retry_fences_old_claims_and_results():
    owner, file, _, jobs, service = setup_processing()
    job = service.queue(owner.id, file.id)
    old = jobs.messages[-1]
    service.claim(old)
    with pytest.raises(ProcessingBusy):
        service.queue(owner.id, file.id, retry=True)
    job.updated_at -= timedelta(seconds=301)
    service.queue(owner.id, file.id, retry=True)
    new = jobs.messages[-1]
    assert new.attempt_id != old.attempt_id
    assert service.claim(old) is None
    assert not service.finish(old, result=ScanResult("clean", "test-scanner"))
    assert job.state == "queued"
    service.claim(new)
    service.finish(new, error_code="scanner_failed")
    assert job.state == "failed"
    assert job.scan_status == "error"
    service.queue(owner.id, file.id, retry=True)
    assert job.state == "queued"


def test_queue_failure_cannot_overwrite_started_or_new_attempt():
    owner, file, _, jobs, service = setup_processing()
    job = service.queue(owner.id, file.id)
    message = jobs.messages[-1]
    assert service.finish(message, error_code="queue_unavailable", queued_failure=True)
    assert job.state == "failed"
    service.queue(owner.id, file.id, retry=True)
    new = jobs.messages[-1]
    assert not service.finish(message, error_code="queue_unavailable", queued_failure=True)
    service.claim(new)
    assert not service.finish(new, error_code="queue_unavailable", queued_failure=True)
    assert job.state == "running"


def test_deleted_and_foreign_targets_are_noops():
    owner, file, attachments, jobs, service = setup_processing()
    service.queue(owner.id, file.id)
    message = jobs.messages[-1]
    assert service.claim(ProcessingMessage(uuid4(), file.id, message.attempt_id)) is None
    attachments.delete(file)
    assert service.claim(message) is None
    assert not service.finish(message, result=ScanResult("clean", "test-scanner"))


def test_infected_verdict_survives_unavailable_scanner_and_blocks_both_access_modes():
    owner, file, attachments, jobs, service = setup_processing()
    job = service.queue(owner.id, file.id)
    message = jobs.messages[-1]
    service.claim(message)
    service.finish(message, result=ScanResult("infected", "test-scanner"))
    access = AttachmentService(
        attachments, Links(attachments), InMemoryBikeRepository(), _Storage()
    )
    for download in [False, True]:
        with pytest.raises(AttachmentAccessBlocked):
            access.access(owner, file.id, download=download)
    for result in [None, ScanResult("not_scanned", "unconfigured")]:
        service.queue(owner.id, file.id, retry=True)
        message = jobs.messages[-1]
        assert job.scan_status == "infected"
        service.claim(message)
        service.finish(message, result=result)
        assert job.scan_status == "infected"


def test_invalid_scan_verdict_is_not_persisted_as_clean():
    with pytest.raises(ValueError):
        ScanResult("clean", "")
