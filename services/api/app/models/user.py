from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Role(StrEnum):
    USER = "user"
    ADMIN = "admin"


class Entitlement(StrEnum):
    NONE = "none"
    PRO = "pro"
    TESTER = "tester"
    INTERNAL = "internal"


class User(Base):
    """Vroometr user. Clerk proves identity; this row is source of truth for access."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("clerk_user_id", name="uq_users_clerk_user_id"),
        CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
        CheckConstraint(
            "entitlement IN ('none', 'pro', 'tester', 'internal')",
            name="ck_users_entitlement",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    clerk_user_id: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default=Role.USER.value)
    entitlement: Mapped[str] = mapped_column(String(32), default=Entitlement.NONE.value)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
