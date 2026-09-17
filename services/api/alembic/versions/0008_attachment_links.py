"""Add reusable attachment relationships.

Revision ID: 0008_attachment_links
Revises: 0007_attachments
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_attachment_links"
down_revision: str | None = "0007_attachments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "attachment_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("attachment_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["attachment_id"], ["attachments.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "attachment_id",
            "entity_type",
            "entity_id",
            "relationship_type",
            name="uq_attachment_links_relationship",
        ),
        sa.CheckConstraint(
            "length(trim(entity_type)) > 0",
            name="ck_attachment_links_entity_type",
        ),
        sa.CheckConstraint(
            "length(trim(relationship_type)) > 0",
            name="ck_attachment_links_relationship_type",
        ),
    )
    op.create_index("ix_attachment_links_attachment_id", "attachment_links", ["attachment_id"])
    op.create_index("ix_attachment_links_entity", "attachment_links", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_table("attachment_links")
