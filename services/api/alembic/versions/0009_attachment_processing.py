"""Persist attachment processing attempts and scan outcomes.

Revision ID: 0009_attachment_processing
Revises: 0008_attachment_links
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_attachment_processing"
down_revision: str | None = "0008_attachment_links"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "attachment_processing",
        sa.Column("attachment_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("scan_status", sa.String(32), nullable=False),
        sa.Column("pipeline_version", sa.String(64), nullable=False),
        sa.Column("scanner_version", sa.String(128)),
        sa.Column("error_code", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("retry_after", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("attachment_id"),
        sa.ForeignKeyConstraint(["attachment_id"], ["attachments.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "state IN ('queued', 'running', 'completed', 'failed')",
            name="ck_attachment_processing_state",
        ),
        sa.CheckConstraint(
            "scan_status IN ('not_scanned', 'clean', 'infected', 'error')",
            name="ck_attachment_processing_scan_status",
        ),
    )
    # Existing attachments have no attempt: API reports not_started / not_scanned.


def downgrade() -> None:
    op.drop_table("attachment_processing")
