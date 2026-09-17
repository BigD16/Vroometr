"""GIN index for owner-filtered document keyword retrieval.

Revision ID: 0013_retrieval_fts
Revises: 0012_document_chunks
"""

from alembic import op

revision = "0013_retrieval_fts"
down_revision = "0012_document_chunks"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE INDEX ix_document_chunks_fts ON document_chunks "
        "USING gin (to_tsvector('english'::regconfig, cleaned_text))"
    )


def downgrade():
    op.drop_index("ix_document_chunks_fts", table_name="document_chunks")
