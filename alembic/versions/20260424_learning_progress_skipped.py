"""Add skipped status to canonical learning progress enum.

Revision ID: 20260424_lp_skipped
Revises: 20260423_drop_legacy
Create Date: 2026-04-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260424_lp_skipped"
down_revision: str | None = "20260423_drop_legacy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE learning_progress_status_enum ADD VALUE IF NOT EXISTS 'skipped'")
        return

    with op.batch_alter_table("learning_progress_records") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.Enum(
                "not_started",
                "in_progress",
                "completed",
                "blocked",
                name="learning_progress_status_enum",
            ),
            type_=sa.Enum(
                "not_started",
                "in_progress",
                "completed",
                "blocked",
                "skipped",
                name="learning_progress_status_enum",
            ),
            existing_nullable=False,
            existing_server_default="not_started",
        )


def downgrade() -> None:
    raise RuntimeError(
        "Irreversible migration: learning_progress_status_enum gained canonical 'skipped'."
    )
