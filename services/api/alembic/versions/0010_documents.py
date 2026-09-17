"""Add bike document records and version groups.

Revision ID: 0010_documents
Revises: 0009_attachment_processing
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_documents"
down_revision: str | None = "0009_attachment_processing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bike_id", sa.Uuid(), nullable=False),
        sa.Column("attachment_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(32), nullable=False),
        sa.Column("make", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("version_group_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("supersedes_document_id", sa.Uuid()),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["bike_id"], ["bikes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["attachment_id"], ["attachments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supersedes_document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("bike_id", "attachment_id", name="uq_documents_bike_attachment"),
        sa.UniqueConstraint("version_group_id", "revision", name="uq_documents_version_revision"),
        sa.CheckConstraint(
            "document_type IN ('manufacturer_manual', 'supporting_document')",
            name="ck_documents_type",
        ),
        sa.CheckConstraint(
            "status IN ('awaiting_confirmation', 'active', 'archived')", name="ck_documents_status"
        ),
        sa.CheckConstraint("revision > 0", name="ck_documents_revision"),
        sa.CheckConstraint("year BETWEEN 1885 AND 2100", name="ck_documents_year"),
        sa.CheckConstraint(
            "NOT is_primary OR (document_type = 'manufacturer_manual' "
            "AND status = 'active' AND confirmed_at IS NOT NULL)",
            name="ck_documents_primary",
        ),
    )
    op.create_index("ix_documents_bike_id", "documents", ["bike_id"])
    op.create_index("ix_documents_attachment_id", "documents", ["attachment_id"])
    op.create_index("ix_documents_file_hash", "documents", ["file_hash"])
    op.create_index(
        "ix_documents_primary_bike",
        "documents",
        ["bike_id"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )


def downgrade() -> None:
    op.drop_table("documents")
