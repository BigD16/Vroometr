from uuid import uuid4

import pytest
from app.models.attachment import Attachment
from app.models.document import Document
from app.models.document_index import DocumentChunk, DocumentIndex
from app.models.document_ingestion import DocumentIngestion, DocumentPage
from app.repositories.bikes import BikeRepository
from app.repositories.retrieval import RetrievalRepository
from app.services.bikes import BikeNotFound
from app.services.retrieval import RetrievalService
from sqlalchemy import select, update
from tests.integration.test_document_index_db import (  # noqa: F401
    Embeddings,
    document_session,
    indexed_source,
    ingestion_document,
    queue_index,
    run,
)
from tests.integration.test_document_ingestion_db import queue as queue_extraction

from vroometr.ai.ports import RankedPassage


class Reranker:
    def __init__(self):
        self.inputs = []

    def rerank(self, query, passages):
        self.inputs.extend(passages)
        return [RankedPassage(i, 0.9) for i in range(len(passages))]


@pytest.fixture
def searchable(indexed_source):  # noqa: F811
    user, doc, file, factory, storage = indexed_source
    assert run(queue_index(factory, user, doc), storage, Embeddings()) == "completed"
    with factory() as session:
        bike = session.get(Document, doc).bike_id
    return user, bike, doc, file, factory


def repository(session):
    return RetrievalRepository(session, "fixture-model", "fixture-v1")


def service(session, embedder=None, reranker=None):
    return RetrievalService(
        BikeRepository(session),
        repository(session),
        embedder or Embeddings(),
        reranker or Reranker(),
        reranker_model="fixture-reranker",
    )


def test_hybrid_search_returns_exact_provenance_and_owner_scope(searchable):
    user, bike, doc, _, factory = searchable
    embedder, reranker = Embeddings(), Reranker()
    with factory() as session:
        search = service(session, embedder, reranker)
        with pytest.raises(BikeNotFound):
            search.search(uuid4(), bike, "Example")
        assert embedder.inputs == reranker.inputs == []
        result = search.search(user, bike, "Example")
        assert result["status"] == "ready"
        assert result["diagnostics"]["keyword_candidates"] == 3
        assert result["diagnostics"]["vector_candidates"] == 3
        assert len(result["passages"]) == 3
        for match in result["passages"]:
            passage = match["passage"]
            assert passage["document_id"] == doc
            span = passage["source_span"][0]
            page = session.get(DocumentPage, (doc, span["page_index"]))
            assert page.text[span["start_char"] : span["end_char"]] == passage["text"]
        assert embedder.inputs == ["Example"]
        assert repository(session).vector(uuid4(), bike, [0.1] * 1536, True) == []
        assert repository(session).keyword(user, uuid4(), "Example", True) == []


@pytest.mark.parametrize(
    "model,changes",
    [
        (DocumentIndex, {"state": "failed"}),
        (DocumentIndex, {"source_attempt_id": uuid4()}),
        (DocumentIndex, {"embedding_version": "old"}),
        (DocumentIndex, {"chunking_version": "old"}),
        (DocumentIngestion, {"state": "running"}),
        (DocumentChunk, {"embedding": None}),
        (DocumentChunk, {"embedding_model": "different-model"}),
        (DocumentChunk, {"source_hash": "x" * 64}),
        (DocumentPage, {"state": "pending_provider"}),
        (DocumentPage, {"extraction_version": "changed"}),
        (Attachment, {"status": "pending"}),
    ],
)
def test_every_read_rejects_unusable_sources(searchable, model, changes):
    user, bike, doc, file, factory = searchable
    with factory.begin() as session:
        repo = repository(session)
        original = repo.vector(user, bike, [0.1] * 1536, False)[0].passage
        key = model.id == file if model is Attachment else model.document_id == doc
        session.execute(update(model).where(key).values(**changes))
        assert not repo.has_sources(user, bike, True)
        assert repo.vector(user, bike, [0.1] * 1536, True) == []
        assert repo.keyword(user, bike, "Example", True) == []
        assert repo.neighbors(user, bike, original, True) == []
        assert repo.revalidate(user, bike, [original], True) == []
        embedder = Embeddings()
        assert (
            service(session, embedder).search(user, bike, "Example")["status"]
            == "no_indexed_sources"
        )
        assert not embedder.inputs


def test_reference_editions_are_explicit_and_supporting_active_is_default(searchable):
    user, bike, doc, _, factory = searchable
    with factory.begin() as session:
        session.execute(
            update(Document).where(Document.id == doc).values(is_primary=False, status="archived")
        )
        search = service(session)
        assert search.search(user, bike, "Example")["status"] == "no_indexed_sources"
        result = search.search(user, bike, "Example", True)
        assert result["status"] == "ready"
        assert all(m["passage"]["document_status"] == "archived" for m in result["passages"])
        session.execute(
            update(Document)
            .where(Document.id == doc)
            .values(status="active", document_type="supporting_document")
        )
        assert search.search(user, bike, "Example")["status"] == "ready"
        session.execute(update(Document).where(Document.id == doc).values(confirmed_at=None))
        assert search.search(user, bike, "Example", True)["status"] == "no_indexed_sources"


def test_sources_changed_during_reranking_are_not_returned(searchable):
    user, bike, doc, _, factory = searchable

    class ChangingReranker(Reranker):
        def rerank(self, query, passages):
            queue_extraction(factory, user, doc)
            return super().rerank(query, passages)

    with factory() as session:
        result = service(session, reranker=ChangingReranker()).search(user, bike, "Example")
        assert result["status"] == "sources_changed" and result["passages"] == []


def test_deletion_after_embedding_prevents_reranker_call(searchable):
    user, bike, _, file, factory = searchable

    class DeletingEmbedding(Embeddings):
        def embed(self, texts):
            with factory.begin() as session:
                session.delete(session.get(Attachment, file))
            return super().embed(texts)

    ranker = Reranker()
    with factory() as session:
        result = service(session, DeletingEmbedding(), ranker).search(user, bike, "Example")
        assert result["passages"] == [] and not ranker.inputs


def test_infected_source_filtered(searchable):
    from datetime import UTC, datetime

    from app.models.attachment_processing import AttachmentProcessing

    user, bike, _, file, factory = searchable
    with factory.begin() as session:
        session.add(
            AttachmentProcessing(
                attachment_id=file,
                attempt_id=uuid4(),
                state="completed",
                scan_status="infected",
                pipeline_version="fixture",
                updated_at=datetime.now(UTC),
            )
        )
        session.flush()
        assert (
            service(session).search(user, bike, "Example", True)["status"] == "no_indexed_sources"
        )


def test_fts_index_installed(searchable):
    from sqlalchemy import text

    with searchable[-1]() as session:
        definition = session.scalar(
            text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_document_chunks_fts'")
        )
        assert "USING gin" in definition and "to_tsvector" in definition


def test_neighbor_query_is_same_section_adjacent_and_partial_is_labeled(searchable):
    user, bike, doc, _, factory = searchable
    with factory.begin() as session:
        chunks = list(
            session.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == doc)
                .order_by(DocumentChunk.chunk_index)
            )
        )
        chunks[1].section_id = chunks[0].section_id
        chunks[1].section_chunk_index = 1
        session.get(DocumentIndex, doc).state = "partial"
        session.flush()
        repo = repository(session)
        passages = repo.vector(user, bike, [0.1] * 1536, False)
        base = next(c.passage for c in passages if c.passage.id == chunks[0].id)
        neighbors = repo.neighbors(user, bike, base, False)
        assert [p.id for p in neighbors] == [chunks[1].id]
        assert all(c.passage.incomplete for c in passages)
        assert repo.neighbors(uuid4(), bike, base, True) == []
