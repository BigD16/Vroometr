"""Durable document ingestion and page provenance.

Revision ID: 0011_document_ingestion
Revises: 0010_documents
"""

import sqlalchemy as sa
from alembic import op

revision = "0011_document_ingestion"
down_revision = "0010_documents"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "document_ingestion",
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("pipeline_version", sa.String(64), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(64)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retry_after", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "state IN ('queued','running','completed','partial','failed')",
            name="ck_document_ingestion_state",
        ),
        sa.CheckConstraint("page_count >= 0", name="ck_document_ingestion_pages"),
    )
    op.create_table(
        "document_pages",
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("page_index", sa.Integer(), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("visual_score", sa.Float(), nullable=False),
        sa.Column("visual_score_reasons", sa.JSON(), nullable=False),
        sa.Column("processing_class", sa.String(24), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("error_code", sa.String(64)),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("extraction_version", sa.String(64), nullable=False),
        sa.Column("ocr_version", sa.String(64)),
        sa.Column("vision_version", sa.String(64)),
        sa.CheckConstraint("page_index >= 0", name="ck_document_pages_index"),
        sa.CheckConstraint("visual_score BETWEEN 0 AND 1", name="ck_document_pages_score"),
        sa.CheckConstraint(
            "processing_class IN ('text_only','ocr_enhanced','ocr_vision')",
            name="ck_document_pages_class",
        ),
        sa.CheckConstraint(
            "state IN ('completed','pending_provider','failed')", name="ck_document_pages_state"
        ),
    )


def downgrade():
    op.drop_table("document_pages")
    op.drop_table("document_ingestion")
