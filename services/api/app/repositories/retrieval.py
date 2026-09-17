"""All candidate, neighbor, and final reads share the same ownership/freshness predicates."""

from dataclasses import fields

from app.documents.chunking import CHUNKING_VERSION
from app.models.attachment import Attachment
from app.models.attachment_processing import AttachmentProcessing
from app.models.bike import Bike
from app.models.document import Document
from app.models.document_index import DocumentChunk, DocumentIndex, DocumentSection
from app.models.document_ingestion import DocumentIngestion, DocumentPage
from app.retrieval.types import Candidate, Passage
from sqlalchemy import and_, func, literal_column, or_, select

TEXT_CONFIG = literal_column("'english'::regconfig")


class RetrievalRepository:
    def __init__(self, session, model, version):
        self.session, self.model, self.version = session, model, version

    def _eligible(self, user_id, bike_id, include_reference_editions):
        statement = (
            select(
                DocumentChunk.id,
                DocumentChunk.document_id,
                Document.attachment_id,
                DocumentChunk.section_id,
                DocumentSection.section_title,
                DocumentChunk.section_chunk_index,
                DocumentChunk.cleaned_text.label("text"),
                DocumentChunk.content_type,
                DocumentChunk.content_hash,
                DocumentChunk.source_span,
                DocumentChunk.source_hash,
                DocumentChunk.page_start,
                DocumentChunk.page_end,
                Document.document_type,
                Document.revision.label("document_revision"),
                Document.is_primary,
                Document.status.label("document_status"),
                Attachment.file_name,
                DocumentIndex.attempt_id.label("index_attempt_id"),
                or_(DocumentIndex.state == "partial", DocumentIngestion.state == "partial").label(
                    "incomplete"
                ),
            )
            .select_from(DocumentChunk)
            .join(Document, Document.id == DocumentChunk.document_id)
            .join(Bike, Bike.id == Document.bike_id)
            .join(Attachment, Attachment.id == Document.attachment_id)
            .join(DocumentSection, DocumentSection.id == DocumentChunk.section_id)
            .join(DocumentIndex, DocumentIndex.document_id == Document.id)
            .join(DocumentIngestion, DocumentIngestion.document_id == Document.id)
            .join(
                DocumentPage,
                and_(
                    DocumentPage.document_id == Document.id,
                    DocumentPage.page_index == DocumentChunk.page_start,
                ),
            )
            .outerjoin(AttachmentProcessing, AttachmentProcessing.attachment_id == Attachment.id)
            .where(
                Bike.user_id == user_id,
                Document.bike_id == bike_id,
                Attachment.user_id == user_id,
                Attachment.status == "uploaded",
                Document.confirmed_at.is_not(None),
                Document.status.in_(["active", "archived"]),
                or_(
                    AttachmentProcessing.scan_status.is_(None),
                    AttachmentProcessing.scan_status != "infected",
                ),
                DocumentIndex.state.in_(["completed", "partial"]),
                DocumentIngestion.state.in_(["completed", "partial"]),
                DocumentIndex.source_attempt_id == DocumentIngestion.attempt_id,
                DocumentIndex.embedding_model == self.model,
                DocumentIndex.embedding_version == self.version,
                DocumentChunk.embedding_model == self.model,
                DocumentChunk.embedding_version == self.version,
                DocumentChunk.embedding.is_not(None),
                DocumentIndex.chunking_version == CHUNKING_VERSION,
                DocumentChunk.chunking_version == CHUNKING_VERSION,
                DocumentChunk.source_hash == Document.file_hash,
                DocumentSection.document_id == Document.id,
                DocumentPage.state == "completed",
                DocumentPage.source_hash == Document.file_hash,
                DocumentChunk.page_start == DocumentChunk.page_end,
                DocumentPage.extraction_version
                == DocumentChunk.source_span[0]["extraction_version"].as_string(),
            )
        )
        if not include_reference_editions:
            statement = statement.where(
                Document.status == "active",
                or_(Document.is_primary, Document.document_type == "supporting_document"),
            )
        return statement

    @staticmethod
    def _passage(row):
        return Passage(**{field.name: row[field.name] for field in fields(Passage)})

    def has_sources(self, user_id, bike_id, include_reference_editions):
        query = self._eligible(user_id, bike_id, include_reference_editions).limit(1)
        return self.session.execute(query).first() is not None

    def vector(self, user_id, bike_id, query_vector, include_reference_editions, limit=50):
        distance = DocumentChunk.embedding.cosine_distance(query_vector)
        statement = (
            self._eligible(user_id, bike_id, include_reference_editions)
            .add_columns((1 - distance).label("score"))
            .order_by(distance, DocumentChunk.id)
            .limit(limit)
        )
        return [
            Candidate(self._passage(row), float(row["score"]))
            for row in self.session.execute(statement).mappings()
        ]

    def keyword(self, user_id, bike_id, query, include_reference_editions, limit=50):
        vector = func.to_tsvector(TEXT_CONFIG, DocumentChunk.cleaned_text)
        parsed = func.websearch_to_tsquery(TEXT_CONFIG, query)
        score = func.ts_rank_cd(vector, parsed)
        statement = (
            self._eligible(user_id, bike_id, include_reference_editions)
            .add_columns(score.label("score"))
            .where(vector.op("@@")(parsed))
            .order_by(score.desc(), DocumentChunk.id)
            .limit(limit)
        )
        return [
            Candidate(self._passage(row), float(row["score"]))
            for row in self.session.execute(statement).mappings()
        ]

    def neighbors(self, user_id, bike_id, passage, include_reference_editions):
        query = (
            self._eligible(user_id, bike_id, include_reference_editions)
            .where(
                DocumentChunk.document_id == passage.document_id,
                DocumentChunk.section_id == passage.section_id,
                DocumentChunk.section_chunk_index.in_(
                    [passage.section_chunk_index - 1, passage.section_chunk_index + 1]
                ),
            )
            .order_by(DocumentChunk.section_chunk_index)
        )
        return [self._passage(row) for row in self.session.execute(query).mappings()]

    def revalidate(self, user_id, bike_id, passages, include_reference_editions):
        if not passages:
            return []
        expected = {passage.id: passage for passage in passages}
        query = self._eligible(user_id, bike_id, include_reference_editions).where(
            DocumentChunk.id.in_(expected)
        )
        result = []
        for row in self.session.execute(query).mappings():
            current = self._passage(row)
            if current == expected[current.id]:
                result.append(current)
        return result
