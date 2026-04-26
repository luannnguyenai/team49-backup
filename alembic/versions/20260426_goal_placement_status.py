"""Add placement_status to goal_preferences.

Revision ID: 20260426_goal_placement_status
Revises: 20260425_placement_unique
Create Date: 2026-04-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260426_goal_placement_status"
down_revision: str | None = "20260425_placement_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ADD ONLY — never drop existing columns.
    # Allowed values: 'pending' | 'completed' | 'skipped'. NULL = not yet set (legacy rows).
    op.add_column(
        "goal_preferences",
        sa.Column(
            "placement_status",
            sa.Text(),
            nullable=True,
            server_default=None,
        ),
    )
    op.create_check_constraint(
        "ck_goal_preferences_placement_status",
        "goal_preferences",
        "placement_status IN ('pending', 'completed', 'skipped') OR placement_status IS NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_goal_preferences_placement_status", "goal_preferences")
    op.drop_column("goal_preferences", "placement_status")
