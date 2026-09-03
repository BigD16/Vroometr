"""Add parental_consents and users.date_of_birth.

Revision ID: 0003_parental_consents
Revises: 0002_users
Create Date: 2026-09-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_parental_consents"
down_revision: str | None = "0002_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.create_table(
        "parental_consents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("minor_user_id", sa.Uuid(), nullable=False),
        sa.Column("guardian_contact", sa.String(length=255), nullable=False),
        sa.Column("consent_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["minor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('pending', 'granted', 'revoked')",
            name="ck_parental_consents_status",
        ),
    )
    op.create_index(
        "ix_parental_consents_minor_user_id",
        "parental_consents",
        ["minor_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_parental_consents_minor_user_id", table_name="parental_consents")
    op.drop_table("parental_consents")
    op.drop_column("users", "date_of_birth")
