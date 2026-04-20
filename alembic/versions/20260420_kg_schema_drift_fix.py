"""Patch KG schema drift for existing demo databases.

Revision ID: 20260420_kg_schema_drift_fix
Revises: 20260419_kg_init
Create Date: 2026-04-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260420_kg_schema_drift_fix"
down_revision: str = "20260419_kg_init"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Bring pre-existing KG tables into alignment with current ORM models."""
    op.execute(
        sa.text(
            "ALTER TABLE kg_concepts "
            "ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE kg_edges "
            "ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE kg_sync_state "
            "ADD COLUMN IF NOT EXISTS source VARCHAR(50) NOT NULL DEFAULT 'manual'"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE kg_sync_state "
            "ALTER COLUMN status SET DEFAULT 'ok'"
        )
    )


def downgrade() -> None:
    """Keep downgrade conservative for demo databases."""
    op.execute(sa.text("ALTER TABLE kg_sync_state ALTER COLUMN status DROP DEFAULT"))
    op.execute(sa.text("ALTER TABLE kg_sync_state DROP COLUMN IF EXISTS source"))
    op.execute(sa.text("ALTER TABLE kg_edges DROP COLUMN IF EXISTS deleted_at"))
    op.execute(sa.text("ALTER TABLE kg_concepts DROP COLUMN IF EXISTS deleted_at"))
