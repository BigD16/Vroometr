"""Wire Alembic. Product tables are added in later migrations.

Revision ID: 0001_alembic_setup
Revises:
Create Date: 2026-09-02
"""

from collections.abc import Sequence

revision: str = "0001_alembic_setup"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Intentionally empty. Do not create product tables at API startup.
    pass


def downgrade() -> None:
    pass
