"""Create the bikes table.

Revision ID: 0004_bikes
Revises: 0003_parental_consents
Create Date: 2026-09-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_bikes"
down_revision: str | None = "0003_parental_consents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bikes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("nickname", sa.String(length=255), nullable=False),
        sa.Column("make", sa.String(length=255), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("displacement", sa.Integer(), nullable=False),
        sa.Column("bike_type", sa.String(length=32), nullable=False),
        sa.Column("stroke_type", sa.String(length=8), nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("engine_hours_at_purchase", sa.Numeric(8, 1), nullable=True),
        sa.Column("current_engine_hours", sa.Numeric(8, 1), nullable=True),
        sa.Column("current_engine_hours_is_estimated", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("unit_preference", sa.String(length=32), nullable=False),
        sa.Column("selected_garage_scene_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "bike_type IN ('motorcycle', 'dirt_bike')",
            name="ck_bikes_bike_type",
        ),
        sa.CheckConstraint("stroke_type IN ('2T', '4T')", name="ck_bikes_stroke_type"),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'archive')",
            name="ck_bikes_status",
        ),
        sa.CheckConstraint(
            "unit_preference IN ('imperial', 'metric')",
            name="ck_bikes_unit_preference",
        ),
        sa.CheckConstraint("year >= 1900", name="ck_bikes_year"),
        sa.CheckConstraint("displacement > 0", name="ck_bikes_displacement"),
        sa.CheckConstraint(
            "engine_hours_at_purchase IS NULL OR engine_hours_at_purchase >= 0",
            name="ck_bikes_purchase_hours",
        ),
        sa.CheckConstraint(
            "current_engine_hours IS NULL OR current_engine_hours >= 0",
            name="ck_bikes_current_hours",
        ),
    )
    op.create_index("ix_bikes_user_id", "bikes", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_bikes_user_id", table_name="bikes")
    op.drop_table("bikes")
