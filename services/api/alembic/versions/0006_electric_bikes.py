"""Support explicit electric bike powertrains.

Revision ID: 0006_electric_bikes
Revises: 0005_active_bike
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_electric_bikes"
down_revision: str | None = "0005_active_bike"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "bikes",
        sa.Column("powertrain_type", sa.String(length=32), nullable=True),
    )
    op.execute("UPDATE bikes SET powertrain_type = 'combustion'")
    op.alter_column("bikes", "powertrain_type", nullable=False)
    op.alter_column("bikes", "displacement", existing_type=sa.Integer(), nullable=True)
    op.alter_column(
        "bikes",
        "stroke_type",
        existing_type=sa.String(length=8),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_bikes_powertrain_type",
        "bikes",
        "powertrain_type IN ('combustion', 'electric')",
    )
    op.create_check_constraint(
        "ck_bikes_powertrain_configuration",
        "bikes",
        """
        (
            powertrain_type = 'combustion'
            AND displacement IS NOT NULL
            AND stroke_type IS NOT NULL
        )
        OR
        (
            powertrain_type = 'electric'
            AND displacement IS NULL
            AND stroke_type IS NULL
        )
        """,
    )


def downgrade() -> None:
    electric_count = op.get_bind().execute(
        sa.text("SELECT count(*) FROM bikes WHERE powertrain_type = 'electric'")
    ).scalar_one()
    if electric_count:
        raise RuntimeError("Cannot downgrade while electric bike rows exist")

    op.drop_constraint(
        "ck_bikes_powertrain_configuration",
        "bikes",
        type_="check",
    )
    op.drop_constraint("ck_bikes_powertrain_type", "bikes", type_="check")
    op.alter_column(
        "bikes",
        "stroke_type",
        existing_type=sa.String(length=8),
        nullable=False,
    )
    op.alter_column("bikes", "displacement", existing_type=sa.Integer(), nullable=False)
    op.drop_column("bikes", "powertrain_type")
