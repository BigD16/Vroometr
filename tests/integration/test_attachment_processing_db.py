from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.db import SessionLocal, engine
from app.models.attachment import Attachment
from app.models.attachment_processing import AttachmentProcessing
from app.models.user import User
from app.processing.dispatch import dispatch_committed
from app.processing.runtime import processing_service
from app.repositories.attachments import AttachmentRepository
from app.repositories.users import UserRepository
from app.scanning.ports import ScanResult
from app.services.users import UserService
from pipelines.attachment_processing import process
from sqlalchemy import text


@pytest.fixture
def processing_file():
    try:
        with engine.connect() as connection:
            exists = connection.execute(
                text("SELECT to_regclass('public.attachment_processing')")
            ).scalar()
    except Exception:
        pytest.skip("Postgres is not running")
    if exists is None:
        pytest.skip("Apply migration 0009_attachment_processing first")
    with SessionLocal.begin() as session:
        owner = UserService(UserRepository(session)).create(f"processing_test_{uuid4()}")
        file = AttachmentRepository(session).add(
            Attachment(
                user_id=owner.id,
                s3_key=f"processing-test/{uuid4()}.pdf",
                file_name="manual.pdf",
                file_size=128,
                mime_type="application/pdf",
                purpose="document",
                retention_class="persistent",
                status="uploaded",
                created_at=datetime.now(UTC) - timedelta(hours=1),
            )
        )
        owner_id, file_id = owner.id, file.id
    try:
        yield owner_id, file_id
    finally:
        with SessionLocal.begin() as session:
            owner = session.get(User, owner_id)
            if owner is not None:
                session.delete(owner)


def queue(owner_id, file_id, retry=False):
    with SessionLocal.begin() as session:
        processing_service(session).queue(owner_id, file_id, retry=retry)
        message = session.info["processing_messages"][-1]
    return message


def run(message, **kwargs):
    return process(
        str(message.user_id), str(message.attachment_id), str(message.attempt_id), **kwargs
    )


def test_committed_queue_pipeline_and_duplicate_delivery(processing_file):
    owner_id, file_id = processing_file
    with SessionLocal() as session:
        job = processing_service(session).queue(owner_id, file_id)
        message = session.info["processing_messages"][-1]
        with SessionLocal() as reader:
            assert reader.get(AttachmentProcessing, file_id) is None
        session.commit()
        assert job.state == "queued"

    class Publisher:
        def publish(self, received):
            with SessionLocal() as reader:
                assert reader.get(AttachmentProcessing, file_id).state == "queued"
            assert run(received) == {"status": "completed"}

    dispatch_committed([message], Publisher())
    with SessionLocal() as reader:
        job = reader.get(AttachmentProcessing, file_id)
        assert job.state == "completed"
        assert job.scan_status == "not_scanned"
        assert job.scanner_version == "unconfigured"
        assert job.started_at is not None and job.finished_at is not None
        assert reader.get(Attachment, file_id).processing.state == "completed"
    assert run(message) == {"status": "ignored"}


def test_queue_outage_persists_failure_and_retry_succeeds(processing_file):
    owner_id, file_id = processing_file
    message = queue(owner_id, file_id)

    class UnavailablePublisher:
        def publish(self, received):
            raise ConnectionError("broker unavailable")

    dispatch_committed([message], UnavailablePublisher())
    with SessionLocal() as session:
        job = session.get(AttachmentProcessing, file_id)
        assert job.state == "failed"
        assert job.error_code == "queue_unavailable"
    retry = queue(owner_id, file_id, retry=True)
    assert run(message) == {"status": "ignored"}
    assert run(retry) == {"status": "completed"}


def test_scanner_failure_is_persisted_without_raw_error(processing_file):
    owner_id, file_id = processing_file
    message = queue(owner_id, file_id)

    class FailingScanner:
        def scan(self, key):
            with SessionLocal() as session:
                assert session.get(AttachmentProcessing, file_id).state == "running"
            raise RuntimeError("do not store scanner secrets")

    assert run(message, scanner=FailingScanner()) == {"status": "failed"}
    with SessionLocal() as session:
        job = session.get(AttachmentProcessing, file_id)
        assert job.scan_status == "error"
        assert job.error_code == "scanner_failed"
        assert job.finished_at is not None


def test_deleted_during_scan_does_not_recreate_processing_state(processing_file):
    owner_id, file_id = processing_file
    message = queue(owner_id, file_id)

    class DeletingScanner:
        def scan(self, key):
            with SessionLocal.begin() as session:
                repository = AttachmentRepository(session)
                repository.lock_owner(owner_id)
                repository.delete(repository.get(file_id, owner_id))
            return ScanResult("clean", "test-scanner")

    assert run(message, scanner=DeletingScanner()) == {"status": "ignored"}
    with SessionLocal() as session:
        assert session.get(AttachmentProcessing, file_id) is None
        assert session.get(Attachment, file_id) is None


def test_stalled_worker_result_cannot_overwrite_retry(processing_file):
    owner_id, file_id = processing_file
    old = queue(owner_id, file_id)

    class LateScanner:
        def scan(self, key):
            with SessionLocal.begin() as session:
                job = session.get(AttachmentProcessing, file_id)
                job.updated_at -= timedelta(days=1)
                processing_service(session).queue(owner_id, file_id, retry=True)
            return ScanResult("clean", "test-scanner")

    assert run(old, scanner=LateScanner()) == {"status": "ignored"}
    with SessionLocal() as session:
        job = session.get(AttachmentProcessing, file_id)
        assert job.state == "queued"
        assert job.scan_status == "not_scanned"


def test_rollback_does_not_publish(monkeypatch, processing_file):
    from app import deps

    owner_id, file_id = processing_file
    published = []
    monkeypatch.setattr(deps, "dispatch_committed", lambda messages: published.extend(messages))
    dependency = deps.get_db()
    session = next(dependency)
    processing_service(session).queue(owner_id, file_id)
    with pytest.raises(RuntimeError):
        dependency.throw(RuntimeError("request failed"))
    assert published == []
    with SessionLocal() as reader:
        assert reader.get(AttachmentProcessing, file_id) is None


def test_concurrent_workers_only_claim_once(processing_file):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from app.repositories.attachment_processing import AttachmentProcessingRepository
    from app.services.attachment_processing import AttachmentProcessingService

    owner_id, file_id = processing_file
    message = queue(owner_id, file_id)
    barrier = Barrier(2)

    class ConcurrentAttachments(AttachmentRepository):
        def lock_owner(self, user_id):
            barrier.wait(timeout=10)
            super().lock_owner(user_id)

    def claim():
        with SessionLocal.begin() as session:
            service = AttachmentProcessingService(
                AttachmentProcessingRepository(session),
                ConcurrentAttachments(session),
                300,
            )
            return service.claim(message) is not None

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(claim), pool.submit(claim)]
        assert sorted(future.result() for future in futures) == [False, True]


def test_real_celery_worker_records_unscanned_result(processing_file):
    from app.config import settings
    from celery.contrib.testing.worker import start_worker
    from celery.result import allow_join_result
    from redis import Redis
    from workers.celery_app import celery_app
    from workers.tasks import process_attachment

    try:
        Redis.from_url(settings.redis_url, socket_connect_timeout=1).ping()
    except Exception:
        pytest.skip("Redis is not running")
    owner_id, file_id = processing_file
    message = queue(owner_id, file_id)
    test_queue = f"processing-test-{uuid4()}"
    # Dedicated queue prevents this test worker from consuming application jobs.
    with start_worker(
        celery_app, queues=[test_queue], perform_ping_check=False, pool="solo", shutdown_timeout=10
    ):
        result = process_attachment.apply_async(
            args=[str(owner_id), str(file_id), str(message.attempt_id)],
            queue=test_queue,
        )
        with allow_join_result():
            assert result.get(timeout=15) == {"status": "completed"}
        result.forget()
    with celery_app.connection() as connection:
        connection.default_channel.queue_delete(test_queue)
    with SessionLocal() as session:
        job = session.get(AttachmentProcessing, file_id)
        assert job.state == "completed"
        assert job.scan_status == "not_scanned"
