from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("bike_id", "attachment_id", name="uq_documents_bike_attachment"),
        UniqueConstraint("version_group_id", "revision", name="uq_documents_version_revision"),
        CheckConstraint(
            "document_type IN ('manufacturer_manual', 'supporting_document')",
            name="ck_documents_type",
        ),
        CheckConstraint(
            "status IN ('awaiting_confirmation', 'active', 'archived')", name="ck_documents_status"
        ),
        CheckConstraint("revision > 0", name="ck_documents_revision"),
        CheckConstraint("year BETWEEN 1885 AND 2100", name="ck_documents_year"),
        CheckConstraint(
            "NOT is_primary OR (document_type = 'manufacturer_manual' "
            "AND status = 'active' AND confirmed_at IS NOT NULL)",
            name="ck_documents_primary",
        ),
        Index(
            "ix_documents_primary_bike", "bike_id", unique=True, postgresql_where=text("is_primary")
        ),
        Index("ix_documents_file_hash", "file_hash"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    bike_id: Mapped[UUID] = mapped_column(ForeignKey("bikes.id", ondelete="CASCADE"), index=True)
    attachment_id: Mapped[UUID] = mapped_column(
        ForeignKey("attachments.id", ondelete="CASCADE"), index=True
    )
    document_type: Mapped[str] = mapped_column(String(32))
    make: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(100))
    year: Mapped[int] = mapped_column()
    file_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="awaiting_confirmation")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    version_group_id: Mapped[UUID] = mapped_column(default=uuid4)
    revision: Mapped[int] = mapped_column(default=1)
    supersedes_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL")
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
