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

    op.create_table(
        "waived_units",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("learning_unit_id", sa.UUID(), nullable=False),
        sa.Column("evidence_items", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("mastery_lcb_at_waive", sa.Float(), nullable=True),
        sa.Column("skip_quiz_score", sa.Float(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "mastery_lcb_at_waive IS NULL OR (mastery_lcb_at_waive >= 0 AND mastery_lcb_at_waive <= 1)",
            name="ck_waived_units_mastery_lcb_range",
        ),
        sa.CheckConstraint(
            "skip_quiz_score IS NULL OR (skip_quiz_score >= 0 AND skip_quiz_score <= 100)",
            name="ck_waived_units_skip_quiz_score_range",
        ),
        sa.ForeignKeyConstraint(["learning_unit_id"], ["learning_units.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "learning_unit_id", name="uq_waived_units_user_unit"),
    )
    op.create_index("ix_waived_units_user", "waived_units", ["user_id"], unique=False)
    op.create_index("ix_waived_units_learning_unit", "waived_units", ["learning_unit_id"], unique=False)

    op.create_table(
        "plan_history",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("parent_plan_id", sa.UUID(), nullable=True),
        sa.Column("trigger", sa.String(length=80), nullable=False),
        sa.Column("recommended_path_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("goal_snapshot_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("weights_used_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parent_plan_id"], ["plan_history.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plan_history_user", "plan_history", ["user_id"], unique=False)
    op.create_index("ix_plan_history_parent", "plan_history", ["parent_plan_id"], unique=False)
    op.create_index("ix_plan_history_trigger", "plan_history", ["trigger"], unique=False)

    op.create_table(
        "rationale_log",
        sa.Column("plan_history_id", sa.UUID(), nullable=False),
        sa.Column("learning_unit_id", sa.UUID(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("reason_code", sa.String(length=80), nullable=False),
        sa.Column("term_breakdown_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("rationale_text", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["learning_unit_id"], ["learning_units.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plan_history_id"], ["plan_history.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rationale_log_plan", "rationale_log", ["plan_history_id"], unique=False)
    op.create_index("ix_rationale_log_unit", "rationale_log", ["learning_unit_id"], unique=False)
    op.create_index(
        "ix_rationale_log_plan_rank",
        "rationale_log",
        ["plan_history_id", "rank"],
        unique=False,
    )

    op.create_table(
        "planner_session_state",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.String(length=120), nullable=False),
        sa.Column("last_plan_history_id", sa.UUID(), nullable=True),
        sa.Column("bridge_chain_depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consecutive_bridge_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("state_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "bridge_chain_depth >= 0",
            name="ck_planner_session_state_bridge_depth_nonnegative",
        ),
        sa.CheckConstraint(
            "consecutive_bridge_count >= 0",
            name="ck_planner_session_state_consecutive_bridge_nonnegative",
        ),
        sa.ForeignKeyConstraint(["last_plan_history_id"], ["plan_history.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "session_id", name="uq_planner_session_state_user_session"),
    )
    op.create_index("ix_planner_session_state_user", "planner_session_state", ["user_id"], unique=False)
    op.create_index(
        "ix_planner_session_state_last_plan",
        "planner_session_state",
        ["last_plan_history_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_planner_session_state_last_plan", table_name="planner_session_state")
    op.drop_index("ix_planner_session_state_user", table_name="planner_session_state")
    op.drop_table("planner_session_state")

    op.drop_index("ix_rationale_log_plan_rank", table_name="rationale_log")
    op.drop_index("ix_rationale_log_unit", table_name="rationale_log")
    op.drop_index("ix_rationale_log_plan", table_name="rationale_log")
    op.drop_table("rationale_log")

    op.drop_index("ix_plan_history_trigger", table_name="plan_history")
    op.drop_index("ix_plan_history_parent", table_name="plan_history")
    op.drop_index("ix_plan_history_user", table_name="plan_history")
    op.drop_table("plan_history")

    op.drop_index("ix_waived_units_learning_unit", table_name="waived_units")
    op.drop_index("ix_waived_units_user", table_name="waived_units")
    op.drop_table("waived_units")

    op.drop_index("ix_goal_preferences_hash", table_name="goal_preferences")
    op.drop_index("ix_goal_preferences_user", table_name="goal_preferences")
    op.drop_table("goal_preferences")

    op.drop_index("ix_learner_mastery_kp_kp", table_name="learner_mastery_kp")
    op.drop_index("ix_learner_mastery_kp_user", table_name="learner_mastery_kp")
    op.drop_table("learner_mastery_kp")
