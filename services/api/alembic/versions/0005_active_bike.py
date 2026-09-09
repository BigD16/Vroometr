"""Persist each user's active bike.

Revision ID: 0005_active_bike
Revises: 0004_bikes
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_active_bike"
down_revision: str | None = "0004_bikes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("active_bike_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_users_active_bike_id_bikes",
        "users",
        "bikes",
        ["active_bike_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_active_bike_id_bikes", "users", type_="foreignkey")
    op.drop_column("users", "active_bike_id")
