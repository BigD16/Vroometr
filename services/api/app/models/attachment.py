from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.attachment_processing import AttachmentProcessing


class AttachmentStatus(StrEnum):
    PENDING = "pending"
    UPLOADED = "uploaded"


class RetentionClass(StrEnum):
    PERSISTENT = "persistent"
    TEMPORARY = "temporary"


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (
        CheckConstraint("file_size > 0", name="ck_attachments_file_size"),
        CheckConstraint(
            "status IN ('pending', 'uploaded')",
            name="ck_attachments_status",
        ),
        CheckConstraint(
            "retention_class IN ('persistent', 'temporary')",
            name="ck_attachments_retention_class",
        ),
        Index("ix_attachments_user_id_status", "user_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    s3_key: Mapped[str] = mapped_column(String(1024), unique=True)
    file_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(127))
    file_size: Mapped[int] = mapped_column(BigInteger)
    purpose: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default=AttachmentStatus.PENDING.value)
    retention_class: Mapped[str] = mapped_column(
        String(32),
        default=RetentionClass.PERSISTENT.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    processing: Mapped["AttachmentProcessing | None"] = relationship(
        lazy="selectin", passive_deletes="all", uselist=False,
    )
