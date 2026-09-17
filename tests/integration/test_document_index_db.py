import pytest
from app.config import settings
from app.documents.index_runtime import index_service
from app.repositories.attachments import AttachmentRepository
from app.services.documents import InvalidDocument
from pipelines import document_index
from tests.integration.test_document_ingestion_db import (  # noqa: F401
    document_session,
    ingestion_document,
)
from tests.integration.test_document_ingestion_db import (
    queue as queue_extraction,
)
from tests.integration.test_document_ingestion_db import (
    run as extract,
)

from vroometr.ai.unconfigured import UnconfiguredEmbeddingModel


class Embeddings:
    def __init__(self):
        self.inputs = []

    def embed(self, texts):
        self.inputs.extend(texts)
        return [[0.1] * 1536 for _ in texts]


@pytest.fixture
def indexed_source(ingestion_document, monkeypatch):  # noqa: F811
    user, doc, file, factory, storage = ingestion_document
    monkeypatch.setattr(document_index, "SessionLocal", factory)
    monkeypatch.setattr(settings, "embedding_model", "fixture-model")
    monkeypatch.setattr(settings, "embedding_version", "fixture-v1")
    assert extract(queue_extraction(factory, user, doc), storage=storage)["status"] == "completed"
    return user, doc, file, factory, storage


def queue_index(factory, user, doc):
    with factory.begin() as session:
        index_service(session).queue(user, doc)
        return session.info["index_messages"][0]


def run(message, storage, embedder):
    return document_index.process(
        str(message.user_id),
        str(message.document_id),
        str(message.attempt_id),
        storage=storage,
        embedder=embedder,
    )["status"]


def test_vector_persistence_retry_reuse_and_model_version_change(indexed_source, monkeypatch):
    user, doc, _, factory, storage = indexed_source
    embedder = Embeddings()
    first = queue_index(factory, user, doc)
    assert run(first, storage, embedder) == "completed"
    assert len(embedder.inputs) == 3
    with factory.begin() as session:
        job, stale, sections, chunks = index_service(session).status(user, doc)
        assert not stale and len(sections) == len(chunks) == 3
        assert chunks[0].embedding_model == "fixture-model"
        assert chunks[0].embedding_version == "fixture-v1"
        assert len(chunks[0].embedding) == 1536
        assert float(chunks[0].embedding[0]) == pytest.approx(0.1)
    assert run(queue_index(factory, user, doc), storage, embedder) == "completed"
    assert len(embedder.inputs) == 3
    assert run(first, storage, embedder) == "ignored"
    monkeypatch.setattr(settings, "embedding_version", "fixture-v2")
    with factory.begin() as session:
        assert index_service(session).status(user, doc)[1]
    assert run(queue_index(factory, user, doc), storage, embedder) == "completed"
    assert len(embedder.inputs) == 6


def test_missing_provider_preserves_chunks_for_retry(indexed_source):
    user, doc, _, factory, storage = indexed_source
    assert (
        run(queue_index(factory, user, doc), storage, UnconfiguredEmbeddingModel())
        == "awaiting_configuration"
    )
    with factory.begin() as session:
        job, _, _, chunks = index_service(session).status(user, doc)
        assert job.error_code == "embedding_unconfigured"
        assert len(chunks) == 3 and all(c.embedding is None for c in chunks)
    assert run(queue_index(factory, user, doc), storage, Embeddings()) == "completed"


def test_new_extraction_invalidates_inflight_embedding_writes(indexed_source):
    user, doc, _, factory, storage = indexed_source
    old = queue_index(factory, user, doc)
    messages = []

    class InterruptingEmbeddings(Embeddings):
        def embed(self, texts):
            messages.append(queue_extraction(factory, user, doc))
            return super().embed(texts)

    assert run(old, storage, InterruptingEmbeddings()) == "ignored"
    with factory.begin() as session:
        job, stale, _, chunks = index_service(session).status(user, doc)
        assert stale and all(c.embedding is None for c in chunks)
        with pytest.raises(InvalidDocument):
            index_service(session).queue(user, doc)
    assert extract(messages[0], storage=storage)["status"] == "completed"
    assert run(queue_index(factory, user, doc), storage, Embeddings()) == "completed"


def test_deletion_during_embedding_does_not_recreate_rows(indexed_source):
    user, doc, file, factory, storage = indexed_source

    class DeletingEmbeddings(Embeddings):
        def embed(self, texts):
            with factory.begin() as session:
                attachments = AttachmentRepository(session)
                attachments.delete(attachments.get(file, user))
            return super().embed(texts)

    assert run(queue_index(factory, user, doc), storage, DeletingEmbeddings()) == "ignored"
    with factory.begin() as session:
        repository = index_service(session).repository
        assert repository.get(doc) is None
        assert repository.chunks(doc) == repository.sections(doc) == []


def test_postcommit_broker_failure_and_rollback(indexed_source, monkeypatch):
    from app.documents import index_dispatch

    user, doc, _, factory, _ = indexed_source
    monkeypatch.setattr(index_dispatch, "SessionLocal", factory)
    message = queue_index(factory, user, doc)

    def fail(message):
        raise ConnectionError("test broker failure")

    index_dispatch.dispatch_indexes([message], fail)
    with factory.begin() as session:
        job = index_service(session).repository.get(doc)
        assert job.state == "failed" and job.error_code == "queue_unavailable"


def test_successful_embedding_batches_survive_provider_failure(indexed_source, monkeypatch):
    from app.services.document_index import DocumentIndexService

    from vroometr.ai.embeddings import EmbeddingFailed

    user, doc, _, factory, storage = indexed_source
    original = DocumentIndexService.pending
    monkeypatch.setattr(
        DocumentIndexService, "pending", lambda self, message: original(self, message, 2)
    )

    class FlakyEmbeddings(Embeddings):
        def embed(self, texts):
            if self.inputs:
                raise EmbeddingFailed("test interruption")
            return super().embed(texts)

    assert run(queue_index(factory, user, doc), storage, FlakyEmbeddings()) == "failed"
    with factory.begin() as session:
        chunks = index_service(session).repository.chunks(doc)
        assert [c.embedding is not None for c in chunks] == [True, True, False]
    retry = Embeddings()
    assert run(queue_index(factory, user, doc), storage, retry) == "completed"
    assert len(retry.inputs) == 1


def test_domain_owner_scope_and_infected_file(indexed_source):
    from uuid import uuid4

    from app.models.attachment_processing import AttachmentProcessing
    from app.repositories.document_index import IndexMessage
    from app.services.attachments import AttachmentAccessBlocked
    from app.services.documents import DocumentNotFound

    user, doc, file, factory, _ = indexed_source
    message = queue_index(factory, user, doc)
    with factory.begin() as session:
        service = index_service(session)
        other = uuid4()
        with pytest.raises(DocumentNotFound):
            service.status(other, doc)
        with pytest.raises(DocumentNotFound):
            service.queue(other, doc)
        assert service.claim(IndexMessage(other, doc, message.attempt_id)) is None
        from datetime import UTC, datetime

        session.add(
            AttachmentProcessing(
                attachment_id=file,
                attempt_id=uuid4(),
                state="completed",
                scan_status="infected",
                pipeline_version="fixture",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
    with factory.begin() as session:
        service = index_service(session)
        with pytest.raises(AttachmentAccessBlocked):
            service.status(user, doc)
        with pytest.raises(AttachmentAccessBlocked):
            service.claim(message)
