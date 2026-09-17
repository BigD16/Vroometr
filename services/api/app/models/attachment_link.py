from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AttachmentLink(Base):
    """One file can support several records without copying the stored object."""

    __tablename__ = "attachment_links"
    __table_args__ = (
        UniqueConstraint(
            "attachment_id",
            "entity_type",
            "entity_id",
            "relationship_type",
            name="uq_attachment_links_relationship",
        ),
        CheckConstraint("length(trim(entity_type)) > 0", name="ck_attachment_links_entity_type"),
        CheckConstraint(
            "length(trim(relationship_type)) > 0",
            name="ck_attachment_links_relationship_type",
        ),
        Index("ix_attachment_links_entity", "entity_type", "entity_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    attachment_id: Mapped[UUID] = mapped_column(
        ForeignKey("attachments.id", ondelete="CASCADE"),
        index=True,
    )
    # Polymorphic targets are validated by the domain service, not a database FK.
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[UUID] = mapped_column()
    relationship_type: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
