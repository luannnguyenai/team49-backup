"""Add fine-grained planner session resume state.

Revision ID: 20260424_resume_state
Revises: 20260424_lp_skipped
Create Date: 2026-04-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260424_resume_state"
down_revision: str | None = "20260424_lp_skipped"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("planner_session_state", sa.Column("current_unit_id", sa.UUID(), nullable=True))
    op.add_column("planner_session_state", sa.Column("current_stage", sa.String(length=40), nullable=True))
    op.add_column(
        "planner_session_state",
        sa.Column("current_progress", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "planner_session_state",
        sa.Column("last_activity", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_planner_session_state_current_unit",
        "planner_session_state",
        "learning_units",
        ["current_unit_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_planner_session_state_current_unit",
        "planner_session_state",
        ["current_unit_id"],
        unique=False,
    )
    op.create_index(
        "ix_planner_session_state_last_activity",
        "planner_session_state",
        ["last_activity"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_planner_session_state_current_stage",
        "planner_session_state",
        "current_stage IS NULL OR current_stage IN ('watching', 'quiz_in_progress', 'post_quiz', 'between_units')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_planner_session_state_current_stage",
        "planner_session_state",
        type_="check",
    )
    op.drop_index("ix_planner_session_state_last_activity", table_name="planner_session_state")
    op.drop_index("ix_planner_session_state_current_unit", table_name="planner_session_state")
    op.drop_constraint(
        "fk_planner_session_state_current_unit",
        "planner_session_state",
        type_="foreignkey",
    )
    op.drop_column("planner_session_state", "last_activity")
    op.drop_column("planner_session_state", "current_progress")
    op.drop_column("planner_session_state", "current_stage")
    op.drop_column("planner_session_state", "current_unit_id")
