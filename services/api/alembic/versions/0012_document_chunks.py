"""Sections, provenance chunks, and durable embedding attempts.

Revision ID: 0012_document_chunks
Revises: 0011_document_ingestion
"""

from alembic import op

revision = "0012_document_chunks"
down_revision = "0011_document_ingestion"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("""
CREATE TABLE document_indexes (
	document_id UUID NOT NULL,
	attempt_id UUID NOT NULL,
	source_attempt_id UUID NOT NULL,
	state VARCHAR(32) NOT NULL,
	chunking_version VARCHAR(64) NOT NULL,
	embedding_model VARCHAR(100) NOT NULL,
	embedding_version VARCHAR(100) NOT NULL,
	error_code VARCHAR(64),
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	retry_after TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (document_id),
	CONSTRAINT ck_document_index_state CHECK (state IN
        ('queued','running','completed','partial','failed','awaiting_configuration')),
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE
)
    """)
    op.execute("""
CREATE TABLE document_sections (
	id UUID NOT NULL,
	document_id UUID NOT NULL,
	parent_section_id UUID,
	section_title TEXT NOT NULL,
	section_order INTEGER NOT NULL,
	start_page INTEGER NOT NULL,
	end_page INTEGER NOT NULL,
	source_method VARCHAR(32) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (document_id, section_order),
	UNIQUE (id, document_id),
	FOREIGN KEY(parent_section_id, document_id) REFERENCES document_sections (id, document_id),
	CHECK (start_page >= 0 AND end_page >= start_page),
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE
)
    """)
    op.execute("CREATE INDEX ix_document_sections_document_id ON document_sections (document_id)")
    op.execute("""
CREATE TABLE document_chunks (
	id UUID NOT NULL,
	document_id UUID NOT NULL,
	section_id UUID NOT NULL,
	page_start INTEGER NOT NULL,
	page_end INTEGER NOT NULL,
	chunk_index INTEGER NOT NULL,
	section_chunk_index INTEGER NOT NULL,
	cleaned_text TEXT NOT NULL,
	content_type VARCHAR(32) NOT NULL,
	source_span JSON NOT NULL,
	source_hash VARCHAR(64) NOT NULL,
	content_hash VARCHAR(64) NOT NULL,
	chunking_version VARCHAR(64) NOT NULL,
	embedding VECTOR(1536),
	embedding_model VARCHAR(100),
	embedding_version VARCHAR(100),
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (document_id, chunk_index),
	UNIQUE (section_id, section_chunk_index),
	FOREIGN KEY(section_id, document_id) REFERENCES document_sections (id, document_id)
        ON DELETE CASCADE,
	CHECK (page_start >= 0 AND page_end >= page_start),
	CHECK (chunk_index >= 0 AND section_chunk_index >= 0),
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE
)
    """)
    op.execute("CREATE INDEX ix_document_chunks_document_id ON document_chunks (document_id)")


def downgrade():
    op.drop_table("document_chunks")
    op.drop_table("document_sections")
    op.drop_table("document_indexes")
