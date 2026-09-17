from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DocumentIngestion(Base):
    __tablename__ = "document_ingestion"
    __table_args__ = (
        CheckConstraint(
            "state IN ('queued','running','completed','partial','failed')",
            name="ck_document_ingestion_state",
        ),
        CheckConstraint("page_count >= 0", name="ck_document_ingestion_pages"),
    )
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    attempt_id: Mapped[UUID] = mapped_column()
    state: Mapped[str] = mapped_column(String(16))
    pipeline_version: Mapped[str] = mapped_column(String(64))
    page_count: Mapped[int] = mapped_column(default=0)
    error_code: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    retry_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentPage(Base):
    __tablename__ = "document_pages"
    __table_args__ = (
        CheckConstraint("page_index >= 0", name="ck_document_pages_index"),
        CheckConstraint("visual_score BETWEEN 0 AND 1", name="ck_document_pages_score"),
        CheckConstraint(
            "processing_class IN ('text_only','ocr_enhanced','ocr_vision')",
            name="ck_document_pages_class",
        ),
        CheckConstraint(
            "state IN ('completed','pending_provider','failed')", name="ck_document_pages_state"
        ),
    )
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    page_index: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    visual_score: Mapped[float] = mapped_column()
    visual_score_reasons: Mapped[list[str]] = mapped_column(JSON)
    processing_class: Mapped[str] = mapped_column(String(24))
    state: Mapped[str] = mapped_column(String(24))
    error_code: Mapped[str | None] = mapped_column(String(64))
    source_hash: Mapped[str] = mapped_column(String(64))
    extraction_version: Mapped[str] = mapped_column(String(64))
    ocr_version: Mapped[str | None] = mapped_column(String(64))
    vision_version: Mapped[str | None] = mapped_column(String(64))
