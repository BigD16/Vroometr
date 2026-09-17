import hashlib
from uuid import uuid4

import pymupdf
import pytest
from app.documents.extraction import extract_page
from app.documents.runtime import ingestion_service
from app.models.attachment import Attachment
from app.repositories.attachments import AttachmentRepository
from app.repositories.bikes import BikeRepository
from app.repositories.documents import DocumentRepository
from app.repositories.users import UserRepository
from app.services.bikes import BikeService
from app.services.documents import DocumentService
from app.services.users import UserService
from pipelines import document_pipeline
from sqlalchemy.orm import sessionmaker
from tests.integration.test_document_repository import document_session  # noqa: F401
from tests.unit.test_documents import META


@pytest.fixture
def ingestion_document(document_session, monkeypatch):  # noqa: F811
    session = document_session
    with pymupdf.open() as pdf:
        for index in range(3):
            page = pdf.new_page()
            page.insert_text((30, 40), f"Example page {index + 1} text.")
        content = pdf.tobytes()

    class Storage:
        def read_attachment(self, attachment):
            return content

    class Inspector:
        def inspect(self, attachment):
            return hashlib.sha256(content).hexdigest()

    owner = UserService(UserRepository(session)).create(f"ingestion-{uuid4()}")
    bikes = BikeRepository(session)
    bike = BikeService(bikes).create(
        owner,
        nickname="Test",
        make="Test",
        model="Test",
        year=2024,
        bike_type="dirt_bike",
        powertrain_type="electric",
    )
    attachments = AttachmentRepository(session)
    file = attachments.add(
        Attachment(
            user_id=owner.id,
            s3_key=f"test/{uuid4()}",
            file_name="test.pdf",
            file_size=len(content),
            mime_type="application/pdf",
            status="uploaded",
            purpose="document",
            retention_class="persistent",
        )
    )
    documents = DocumentService(DocumentRepository(session), attachments, bikes, Inspector())
    document = documents.register(
        owner, bike_id=bike.id, attachment_id=file.id, metadata=META
    ).document
    documents.confirm(owner, document.id, META)
    factory = sessionmaker(bind=session.connection(), join_transaction_mode="create_savepoint")
    monkeypatch.setattr(document_pipeline, "SessionLocal", factory)
    return owner.id, document.id, file.id, factory, Storage()


def queue(factory, user_id, document_id):
    with factory.begin() as session:
        ingestion_service(session).queue(user_id, document_id)
        return session.info["ingestion_messages"][0]


def run(message, **kwargs):
    return document_pipeline.process(
        str(message.user_id), str(message.document_id), str(message.attempt_id), **kwargs
    )


def test_partial_failure_preserves_pages_and_retry_only_incomplete(ingestion_document):
    user, doc, _, factory, storage = ingestion_document
    attempted = []

    def flaky(pdf, index, document_id, source_hash):
        attempted.append(index)
        if index == 1:
            raise RuntimeError("test failure")
        return extract_page(pdf, index, document_id, source_hash)

    first = queue(factory, user, doc)
    assert run(first, storage=storage, extractor=flaky)["status"] == "partial"
    with factory.begin() as session:
        job, pages = ingestion_service(session).status(user, doc)
        assert job.page_count == 3
        assert [page.state for page in pages] == ["completed", "failed", "completed"]
        assert pages[2].page_index == 2 and "page 3" in pages[2].text
    attempted.clear()

    def record(pdf, index, document_id, source_hash):
        attempted.append(index)
        return extract_page(pdf, index, document_id, source_hash)

    retry = queue(factory, user, doc)
    assert run(first, storage=storage)["status"] == "ignored"
    assert run(retry, storage=storage, extractor=record)["status"] == "completed"
    assert attempted == [1]


def test_hash_mismatch_and_deletion_do_not_create_pages(ingestion_document):
    user, doc, file, factory, storage = ingestion_document
    message = queue(factory, user, doc)
    storage.read_attachment = lambda attachment: b"changed file bytes"
    assert run(message, storage=storage)["status"] == "failed"
    with factory.begin() as session:
        job, pages = ingestion_service(session).status(user, doc)
        assert job.error_code == "source_changed" and pages == []
    retry = queue(factory, user, doc)
    with factory.begin() as session:
        repository = AttachmentRepository(session)
        repository.delete(repository.get(file, user))
    assert run(retry, storage=storage)["status"] == "ignored"


def test_broker_failure_is_durable_and_retryable(ingestion_document, monkeypatch):
    from app.documents import dispatch

    user, doc, _, factory, _ = ingestion_document
    message = queue(factory, user, doc)
    monkeypatch.setattr(dispatch, "SessionLocal", factory)

    def unavailable(message):
        raise ConnectionError("test broker unavailable")

    dispatch.dispatch_ingestion([message], unavailable)
    with factory.begin() as session:
        job, _ = ingestion_service(session).status(user, doc)
        assert job.state == "failed" and job.error_code == "queue_unavailable"
    assert queue(factory, user, doc).attempt_id != message.attempt_id


def test_infection_during_extraction_blocks_further_page_commits(ingestion_document):
    from app.models.attachment_processing import AttachmentProcessing

    user, doc, file, factory, storage = ingestion_document
    message = queue(factory, user, doc)

    def infected(pdf, index, document_id, source_hash):
        with factory.begin() as session:
            from datetime import UTC, datetime

            now = datetime.now(UTC)
            session.add(
                AttachmentProcessing(
                    attachment_id=file,
                    attempt_id=uuid4(),
                    state="completed",
                    scan_status="infected",
                    pipeline_version="test",
                    created_at=now,
                    updated_at=now,
                )
            )
        return extract_page(pdf, index, document_id, source_hash)

    assert run(message, storage=storage, extractor=infected)["status"] == "failed"
    with factory.begin() as session:
        service = ingestion_service(session)
        assert service.jobs.get(doc).error_code == "file_blocked"
        assert service.jobs.pages(doc) == []
