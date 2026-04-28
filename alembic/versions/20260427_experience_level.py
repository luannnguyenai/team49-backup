"""Add experience_level to goal_preferences.

Revision ID: 20260427_experience_level
Revises: 20260426_goal_placement_status
Create Date: 2026-04-27
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260427_experience_level"
down_revision: str | None = "20260426_goal_placement_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ADD ONLY — never drop existing columns.
    # Allowed values: 'beginner' | 'experienced'. NULL = not yet set.
    op.add_column(
        "goal_preferences",
        sa.Column(
            "experience_level",
            sa.Text(),
            nullable=True,
            server_default=None,
        ),
    )
    op.create_check_constraint(
        "ck_goal_preferences_experience_level",
        "goal_preferences",
        "experience_level IN ('beginner', 'experienced') OR experience_level IS NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_goal_preferences_experience_level", "goal_preferences")
    op.drop_column("goal_preferences", "experience_level")
