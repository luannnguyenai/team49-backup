"""Allow canonical-only interactions.

Revision ID: 20260423_nullable_iq
Revises: 20260423_runtime_bridge
Create Date: 2026-04-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260423_nullable_iq"
down_revision: str | None = "20260423_runtime_bridge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "interactions",
        "question_id",
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "interactions",
        "question_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
