from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    literal_column,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DocumentIndex(Base):
    __tablename__ = "document_indexes"
    __table_args__ = (
        CheckConstraint(
            "state IN ('queued','running','completed','partial','failed','awaiting_configuration')",
            name="ck_document_index_state",
        ),
    )
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    attempt_id: Mapped[UUID] = mapped_column()
    source_attempt_id: Mapped[UUID] = mapped_column()
    state: Mapped[str] = mapped_column(String(32))
    chunking_version: Mapped[str] = mapped_column(String(64))
    embedding_model: Mapped[str] = mapped_column(String(100))
    embedding_version: Mapped[str] = mapped_column(String(100))
    error_code: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    retry_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentSection(Base):
    __tablename__ = "document_sections"
    __table_args__ = (
        UniqueConstraint("document_id", "section_order"),
        UniqueConstraint("id", "document_id"),
        ForeignKeyConstraint(
            ["parent_section_id", "document_id"],
            ["document_sections.id", "document_sections.document_id"],
        ),
        CheckConstraint("start_page >= 0 AND end_page >= start_page"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    parent_section_id: Mapped[UUID | None] = mapped_column()
    section_title: Mapped[str] = mapped_column(Text)
    section_order: Mapped[int] = mapped_column()
    start_page: Mapped[int] = mapped_column()
    end_page: Mapped[int] = mapped_column()
    source_method: Mapped[str] = mapped_column(String(32))


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index"),
        UniqueConstraint("section_id", "section_chunk_index"),
        ForeignKeyConstraint(
            ["section_id", "document_id"],
            ["document_sections.id", "document_sections.document_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("page_start >= 0 AND page_end >= page_start"),
        CheckConstraint("chunk_index >= 0 AND section_chunk_index >= 0"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[UUID] = mapped_column()
    page_start: Mapped[int] = mapped_column()
    page_end: Mapped[int] = mapped_column()
    chunk_index: Mapped[int] = mapped_column()
    section_chunk_index: Mapped[int] = mapped_column()
    cleaned_text: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(32))
    source_span: Mapped[list[dict]] = mapped_column(JSON)
    source_hash: Mapped[str] = mapped_column(String(64))
    content_hash: Mapped[str] = mapped_column(String(64))
    chunking_version: Mapped[str] = mapped_column(String(64))
    embedding: Mapped[list[float] | None] = mapped_column(VECTOR(1536))
    embedding_model: Mapped[str | None] = mapped_column(String(100))
    embedding_version: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


Index(
    "ix_document_chunks_fts",
    func.to_tsvector(literal_column("'english'::regconfig"), DocumentChunk.cleaned_text),
    postgresql_using="gin",
)
