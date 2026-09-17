"""Add bike-scoped conversations, messages, and context boundaries.

Revision ID: 0014_conversations
Revises: 0013_retrieval_fts
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_conversations"
down_revision: str | None = "0013_retrieval_fts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("initial_bike_id", sa.Uuid(), nullable=False),
        sa.Column("current_bike_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rolling_summary", sa.Text()),
        sa.Column("summary_model_version", sa.String(length=64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["initial_bike_id"], ["bikes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["current_bike_id"], ["bikes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_conversations_status",
        ),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index("ix_conversations_initial_bike_id", "conversations", ["initial_bike_id"])
    op.create_index("ix_conversations_current_bike_id", "conversations", ["current_bike_id"])

    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("bike_context_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bike_context_id"], ["bikes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "role IN ('user', 'assistant', 'system')",
            name="ck_conversation_messages_role",
        ),
    )
    op.create_index(
        "ix_conversation_messages_conversation_id",
        "conversation_messages",
        ["conversation_id"],
    )
    op.create_index(
        "ix_conversation_messages_bike_context_id",
        "conversation_messages",
        ["bike_context_id"],
    )

    op.create_table(
        "conversation_context_boundaries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("from_bike_id", sa.Uuid(), nullable=False),
        sa.Column("to_bike_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_bike_id"], ["bikes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_bike_id"], ["bikes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["message_id"], ["conversation_messages.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversation_context_boundaries_conversation_id",
        "conversation_context_boundaries",
        ["conversation_id"],
    )


def downgrade() -> None:
    op.drop_table("conversation_context_boundaries")
    op.drop_table("conversation_messages")
    op.drop_table("conversations")
