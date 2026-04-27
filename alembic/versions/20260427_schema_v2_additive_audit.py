"""Add Schema v2 audit, calibration, and incremental ingest fields.

Revision ID: 20260427_schema_v2
Revises: 20260424_resume_state
Create Date: 2026-04-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260427_schema_v2"
down_revision: str | None = "20260424_resume_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    jsonb = postgresql.JSONB(astext_type=sa.Text())

    op.add_column("courses", sa.Column("course_config", jsonb, nullable=True))

    op.add_column(
        "learning_units",
        sa.Column("has_quiz_items", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("learning_units", sa.Column("salience_decision", sa.String(length=40), nullable=True))

    op.add_column("units", sa.Column("content_hash", sa.String(length=128), nullable=True))
    op.add_column("units", sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("units", sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("units", sa.Column("deprecated_reason", sa.Text(), nullable=True))
    op.add_column("units", sa.Column("content_type", sa.String(length=80), nullable=True))
    op.add_column("units", sa.Column("content_type_confidence", sa.String(length=40), nullable=True))
    op.add_column("units", sa.Column("is_worth_learning", sa.Boolean(), nullable=True))
    op.add_column("units", sa.Column("salience_score", sa.String(length=40), nullable=True))
    op.add_column("units", sa.Column("salience_confidence", sa.String(length=40), nullable=True))
    op.add_column(
        "units",
        sa.Column("override_critical_kp", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("units", sa.Column("has_quiz_items", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.add_column("concepts_kp", sa.Column("content_hash", sa.String(length=128), nullable=True))
    op.add_column("concepts_kp", sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("concepts_kp", sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("concepts_kp", sa.Column("deprecated_reason", sa.Text(), nullable=True))
    op.add_column(
        "concepts_kp",
        sa.Column("description_embedding_version", sa.String(length=120), nullable=True),
    )

    op.add_column("prerequisite_edges", sa.Column("evidence_ledger", jsonb, nullable=True))
    op.add_column(
        "prerequisite_edges",
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("prerequisite_edges", sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("prerequisite_edges", sa.Column("deprecated_reason", sa.Text(), nullable=True))
    op.add_column("prerequisite_edges", sa.Column("edge_kind", sa.String(length=40), nullable=True))
    op.add_column("prerequisite_edges", sa.Column("adjudication_trace", jsonb, nullable=True))

    op.add_column("pruned_edges", sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("pruned_edges", sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("pruned_edges", sa.Column("deprecated_reason", sa.Text(), nullable=True))
    op.add_column("pruned_edges", sa.Column("adjudication_trace", jsonb, nullable=True))

    op.add_column("sessions", sa.Column("selection_strategy", sa.String(length=80), nullable=True))
    op.add_column("sessions", sa.Column("calibration_mode", sa.String(length=80), nullable=True))
    op.add_column("sessions", sa.Column("theta_initial", sa.Float(), nullable=True))
    op.add_column("sessions", sa.Column("theta_final", sa.Float(), nullable=True))
    op.add_column("sessions", sa.Column("theta_sigma_initial", sa.Float(), nullable=True))
    op.add_column("sessions", sa.Column("theta_sigma_final", sa.Float(), nullable=True))
    op.add_column("sessions", sa.Column("target_se", sa.Float(), nullable=True))
    op.add_column("sessions", sa.Column("stop_reason", sa.String(length=120), nullable=True))

    op.add_column("interactions", sa.Column("selection_strategy", sa.String(length=80), nullable=True))
    op.add_column("interactions", sa.Column("theta_before", sa.Float(), nullable=True))
    op.add_column("interactions", sa.Column("theta_after", sa.Float(), nullable=True))
    op.add_column("interactions", sa.Column("theta_sigma_before", sa.Float(), nullable=True))
    op.add_column("interactions", sa.Column("theta_sigma_after", sa.Float(), nullable=True))
    op.add_column("interactions", sa.Column("predicted_probability", sa.Float(), nullable=True))
    op.add_column("interactions", sa.Column("item_information", sa.Float(), nullable=True))
    op.add_column("interactions", sa.Column("item_difficulty_at_time", sa.Float(), nullable=True))
    op.add_column("interactions", sa.Column("item_discrimination_at_time", sa.Float(), nullable=True))
    op.add_column("interactions", sa.Column("item_guessing_at_time", sa.Float(), nullable=True))

    op.add_column("item_calibration", sa.Column("standard_error_a", sa.Float(), nullable=True))
    op.add_column("item_calibration", sa.Column("standard_error_c", sa.Float(), nullable=True))
    op.add_column("item_calibration", sa.Column("calibration_run_id", sa.String(length=160), nullable=True))
    op.add_column(
        "item_calibration",
        sa.Column("calibration_dataset_version", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "item_calibration",
        sa.Column("real_response_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "item_calibration",
        sa.Column("synthetic_response_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "ingest_runs",
        sa.Column("run_id", sa.String(length=160), primary_key=True),
        sa.Column("course_id", sa.String(length=80), nullable=True),
        sa.Column("run_type", sa.String(length=80), nullable=False),
        sa.Column("input_hashes", jsonb, nullable=True),
        sa.Column("artifact_version", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("metrics_json", jsonb, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "kp_migration",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(length=160), nullable=True),
        sa.Column("migration_type", sa.String(length=80), nullable=False),
        sa.Column("source_kp_id", sa.String(length=160), nullable=False),
        sa.Column("target_kp_id", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "calibration_runs",
        sa.Column("run_id", sa.String(length=160), primary_key=True),
        sa.Column("method", sa.String(length=80), nullable=False),
        sa.Column("dataset_version", sa.String(length=120), nullable=True),
        sa.Column("real_response_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("synthetic_response_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metrics_json", jsonb, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "item_calibration_history",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "item_id",
            sa.String(length=180),
            sa.ForeignKey("question_bank.item_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("calibration_run_id", sa.String(length=160), nullable=True),
        sa.Column("difficulty_b", sa.Float(), nullable=True),
        sa.Column("discrimination_a", sa.Float(), nullable=True),
        sa.Column("guessing_c", sa.Float(), nullable=True),
        sa.Column("standard_error_b", sa.Float(), nullable=True),
        sa.Column("standard_error_a", sa.Float(), nullable=True),
        sa.Column("standard_error_c", sa.Float(), nullable=True),
        sa.Column("real_response_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("synthetic_response_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "item_exposure_stats",
        sa.Column(
            "item_id",
            sa.String(length=180),
            sa.ForeignKey("question_bank.item_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("phase", sa.String(length=80), primary_key=True),
        sa.Column("shown_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("answered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_shown_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exposure_rate", sa.Float(), nullable=True),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "human_review_queue",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=220), nullable=False),
        sa.Column("reason", sa.String(length=160), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("suggested_action", sa.Text(), nullable=True),
        sa.Column("context_json", jsonb, nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="open"),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalation_target", sa.String(length=160), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_units_content_hash", "units", ["content_hash"])
    op.create_index("ix_units_active", "units", ["active"])
    op.create_index("ix_concepts_kp_content_hash", "concepts_kp", ["content_hash"])
    op.create_index("ix_concepts_kp_active", "concepts_kp", ["active"])
    op.create_index("ix_prerequisite_edges_active", "prerequisite_edges", ["active"])
    op.create_index("ix_interactions_selection_strategy", "interactions", ["selection_strategy"])
    op.create_index("ix_item_calibration_run", "item_calibration", ["calibration_run_id"])
    op.create_index("ix_kp_migration_source", "kp_migration", ["source_kp_id"])
    op.create_index("ix_human_review_queue_status", "human_review_queue", ["status", "severity"])


def downgrade() -> None:
    op.drop_index("ix_human_review_queue_status", table_name="human_review_queue")
    op.drop_index("ix_kp_migration_source", table_name="kp_migration")
    op.drop_index("ix_item_calibration_run", table_name="item_calibration")
    op.drop_index("ix_interactions_selection_strategy", table_name="interactions")
    op.drop_index("ix_prerequisite_edges_active", table_name="prerequisite_edges")
    op.drop_index("ix_concepts_kp_active", table_name="concepts_kp")
    op.drop_index("ix_concepts_kp_content_hash", table_name="concepts_kp")
    op.drop_index("ix_units_active", table_name="units")
    op.drop_index("ix_units_content_hash", table_name="units")

    op.drop_table("human_review_queue")
    op.drop_table("item_exposure_stats")
    op.drop_table("item_calibration_history")
    op.drop_table("calibration_runs")
    op.drop_table("kp_migration")
    op.drop_table("ingest_runs")

    for column in [
        "standard_error_a",
        "standard_error_c",
        "calibration_run_id",
        "calibration_dataset_version",
        "real_response_count",
        "synthetic_response_count",
    ]:
        op.drop_column("item_calibration", column)

    for column in [
        "selection_strategy",
        "theta_before",
        "theta_after",
        "theta_sigma_before",
        "theta_sigma_after",
        "predicted_probability",
        "item_information",
        "item_difficulty_at_time",
        "item_discrimination_at_time",
        "item_guessing_at_time",
    ]:
        op.drop_column("interactions", column)

    for column in [
        "selection_strategy",
        "calibration_mode",
        "theta_initial",
        "theta_final",
        "theta_sigma_initial",
        "theta_sigma_final",
        "target_se",
        "stop_reason",
    ]:
        op.drop_column("sessions", column)

    for column in ["active", "deprecated_at", "deprecated_reason", "adjudication_trace"]:
        op.drop_column("pruned_edges", column)

    for column in [
        "evidence_ledger",
        "active",
        "deprecated_at",
        "deprecated_reason",
        "edge_kind",
        "adjudication_trace",
    ]:
        op.drop_column("prerequisite_edges", column)

    for column in [
        "content_hash",
        "active",
        "deprecated_at",
        "deprecated_reason",
        "description_embedding_version",
    ]:
        op.drop_column("concepts_kp", column)

    for column in [
        "content_hash",
        "active",
        "deprecated_at",
        "deprecated_reason",
        "content_type",
        "content_type_confidence",
        "is_worth_learning",
        "salience_score",
        "salience_confidence",
        "override_critical_kp",
        "has_quiz_items",
    ]:
        op.drop_column("units", column)

    op.drop_column("learning_units", "salience_decision")
    op.drop_column("learning_units", "has_quiz_items")
    op.drop_column("courses", "course_config")
