from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ConsentStatus(StrEnum):
    PENDING = "pending"
    GRANTED = "granted"
    REVOKED = "revoked"


class ParentalConsent(Base):
    """Versioned guardian approval for a 13–17 user. Under-13 accounts are not allowed."""

    __tablename__ = "parental_consents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'granted', 'revoked')",
            name="ck_parental_consents_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    minor_user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    guardian_contact: Mapped[str] = mapped_column(String(255))
    consent_version: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default=ConsentStatus.PENDING.value)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
