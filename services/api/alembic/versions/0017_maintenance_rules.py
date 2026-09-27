"""Add bike-scoped maintenance rules for derived due state.

Revision ID: 0017_maintenance_rules
Revises: 0016_maintenance_records
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_maintenance_rules"
down_revision: str | None = "0016_maintenance_records"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "maintenance_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bike_id", sa.Uuid(), nullable=False),
        sa.Column("system", sa.String(64), nullable=False),
        sa.Column("component", sa.String(64), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("initial_interval_hours", sa.Numeric(8, 1)),
        sa.Column("recurring_interval_hours", sa.Numeric(8, 1)),
        sa.Column("calendar_interval_days", sa.Integer()),
        sa.Column("whichever_comes_first", sa.Boolean(), nullable=False),
        sa.Column("usage_condition_variant", sa.String(64), nullable=False),
        sa.Column("validation_status", sa.String(32), nullable=False),
        sa.Column("rule_version", sa.Integer(), nullable=False),
        sa.Column("pipeline_version", sa.String(64)),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("supersedes_rule_id", sa.Uuid()),
        sa.Column("source_document_id", sa.Uuid()),
        sa.Column("source_page", sa.Integer()),
        sa.Column("source_span", sa.Text()),
        sa.Column("extraction_confidence", sa.Numeric(4, 3)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["bike_id"], ["bikes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "validation_status IN ('draft', 'validated', 'active', 'superseded')",
            name="ck_maint_rules_validation",
        ),
        sa.CheckConstraint(
            "initial_interval_hours IS NULL OR initial_interval_hours >= 0",
            name="ck_maint_rules_initial_hours",
        ),
        sa.CheckConstraint(
            "recurring_interval_hours IS NULL OR recurring_interval_hours >= 0",
            name="ck_maint_rules_recurring_hours",
        ),
        sa.CheckConstraint(
            "calendar_interval_days IS NULL OR calendar_interval_days >= 0",
            name="ck_maint_rules_calendar_days",
        ),
    )
    op.create_index("ix_maintenance_rules_bike_id", "maintenance_rules", ["bike_id"])
    op.create_index(
        "ix_maintenance_rules_bike_active", "maintenance_rules", ["bike_id", "active"]
    )


def downgrade() -> None:
    op.drop_index("ix_maintenance_rules_bike_active", table_name="maintenance_rules")
    op.drop_index("ix_maintenance_rules_bike_id", table_name="maintenance_rules")
    op.drop_table("maintenance_rules")
