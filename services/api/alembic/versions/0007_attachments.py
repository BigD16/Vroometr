"""Create owner-scoped attachment upload records.

Revision ID: 0007_attachments
Revises: 0006_electric_bikes
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_attachments"
down_revision: str | None = "0006_electric_bikes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("s3_key", sa.String(length=1024), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=127), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("retention_class", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("file_size > 0", name="ck_attachments_file_size"),
        sa.CheckConstraint(
            "status IN ('pending', 'uploaded')",
            name="ck_attachments_status",
        ),
        sa.CheckConstraint(
            "retention_class IN ('persistent', 'temporary')",
            name="ck_attachments_retention_class",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("s3_key"),
    )
    op.create_index("ix_attachments_user_id", "attachments", ["user_id"])
    op.create_index(
        "ix_attachments_user_id_status",
        "attachments",
        ["user_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_attachments_user_id_status", table_name="attachments")
    op.drop_index("ix_attachments_user_id", table_name="attachments")
    op.drop_table("attachments")
