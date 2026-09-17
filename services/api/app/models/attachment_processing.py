from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AttachmentProcessing(Base):
    __tablename__ = "attachment_processing"
    __table_args__ = (
        CheckConstraint(
            "state IN ('queued', 'running', 'completed', 'failed')",
            name="ck_attachment_processing_state",
        ),
        CheckConstraint(
            "scan_status IN ('not_scanned', 'clean', 'infected', 'error')",
            name="ck_attachment_processing_scan_status",
        ),
    )

    attachment_id: Mapped[UUID] = mapped_column(
        ForeignKey("attachments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    attempt_id: Mapped[UUID] = mapped_column()
    state: Mapped[str] = mapped_column(String(32))
    scan_status: Mapped[str] = mapped_column(String(32), default="not_scanned")
    pipeline_version: Mapped[str] = mapped_column(String(64))
    scanner_version: Mapped[str | None] = mapped_column(String(128))
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    retry_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
