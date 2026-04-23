"""Add learner and planner stub persistence tables.

Revision ID: 20260423_planner_stubs
Revises: 20260420_kg_schema_drift_fix
Create Date: 2026-04-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260423_planner_stubs"
down_revision: str | None = "20260420_kg_schema_drift_fix"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learner_mastery_kp",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("kp_id", sa.String(length=160), nullable=False),
        sa.Column("theta_mu", sa.Float(), nullable=False, server_default="0"),
        sa.Column("theta_sigma", sa.Float(), nullable=False, server_default="1"),
        sa.Column("mastery_mean_cached", sa.Float(), nullable=False, server_default="0"),
        sa.Column("n_items_observed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_by", sa.String(length=80), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("theta_sigma >= 0", name="ck_learner_mastery_kp_sigma_nonnegative"),
        sa.CheckConstraint(
            "mastery_mean_cached >= 0 AND mastery_mean_cached <= 1",
            name="ck_learner_mastery_kp_mastery_range",
        ),
        sa.CheckConstraint(
            "n_items_observed >= 0",
            name="ck_learner_mastery_kp_items_nonnegative",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "kp_id", name="uq_learner_mastery_kp_user_kp"),
    )
    op.create_index("ix_learner_mastery_kp_user", "learner_mastery_kp", ["user_id"], unique=False)
    op.create_index("ix_learner_mastery_kp_kp", "learner_mastery_kp", ["kp_id"], unique=False)

    op.create_table(
        "goal_preferences",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("goal_weights_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("selected_course_ids", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("goal_embedding", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("goal_embedding_version", sa.String(length=80), nullable=True),
        sa.Column("derived_from_course_set_hash", sa.String(length=128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_goal_preferences_user", "goal_preferences", ["user_id"], unique=False)
    op.create_index(
        "ix_goal_preferences_hash",
        "goal_preferences",
        ["derived_from_course_set_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_goal_preferences_hash", table_name="goal_preferences")
    op.drop_index("ix_goal_preferences_user", table_name="goal_preferences")
    op.drop_table("goal_preferences")

    op.drop_index("ix_learner_mastery_kp_kp", table_name="learner_mastery_kp")
    op.drop_index("ix_learner_mastery_kp_user", table_name="learner_mastery_kp")
    op.drop_table("learner_mastery_kp")
