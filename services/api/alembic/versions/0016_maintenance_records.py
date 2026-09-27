"""Add maintenance records and taxonomy gap events.

Revision ID: 0016_maintenance_records
Revises: 0015_message_citations
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_maintenance_records"
down_revision: str | None = "0015_message_citations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "maintenance_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bike_id", sa.Uuid(), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("engine_hours", sa.Numeric(8, 1)),
        sa.Column("engine_hours_is_estimated", sa.Boolean(), nullable=False),
        sa.Column("system", sa.String(length=64), nullable=False),
        sa.Column("component", sa.String(length=64), nullable=False),
        sa.Column("component_detail", sa.Text()),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("service_type", sa.String(length=64)),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("reason_details", sa.Text()),
        sa.Column("performer_type", sa.String(length=32), nullable=False),
        sa.Column("performer_name", sa.String(length=120)),
        sa.Column("parts", sa.Text()),
        sa.Column("fluids", sa.Text()),
        sa.Column("cost", sa.Numeric(12, 2)),
        sa.Column("evidence_type", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=120)),
        sa.Column("linked_conversation_id", sa.Uuid()),
        sa.Column("details", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["bike_id"], ["bikes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "engine_hours IS NULL OR engine_hours >= 0",
            name="ck_maint_hours",
        ),
        sa.CheckConstraint("cost IS NULL OR cost >= 0", name="ck_maint_cost"),
    )
    op.create_index("ix_maintenance_records_bike_id", "maintenance_records", ["bike_id"])
    op.create_index(
        "ix_maintenance_records_bike_service_date",
        "maintenance_records",
        ["bike_id", "service_date"],
    )

    op.create_table(
        "taxonomy_gap_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("taxonomy_type", sa.String(length=32), nullable=False),
        sa.Column("submitted_term", sa.String(length=200), nullable=False),
        sa.Column("bike_id", sa.Uuid()),
        sa.Column("mapped_system", sa.String(length=64)),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("review_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["bike_id"], ["bikes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "review_status IN ('open', 'reviewed', 'dismissed')",
            name="ck_taxonomy_gap_review_status",
        ),
    )
    op.create_index(
        "ix_taxonomy_gap_lookup",
        "taxonomy_gap_events",
        ["taxonomy_type", "submitted_term", "mapped_system"],
    )


def downgrade() -> None:
    op.drop_index("ix_taxonomy_gap_lookup", table_name="taxonomy_gap_events")
    op.drop_table("taxonomy_gap_events")
    op.drop_index(
        "ix_maintenance_records_bike_service_date", table_name="maintenance_records"
    )
    op.drop_index("ix_maintenance_records_bike_id", table_name="maintenance_records")
    op.drop_table("maintenance_records")
