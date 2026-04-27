"""Add Schema v2 audit, calibration, and incremental ingest fields.

Revision ID: 20260427_schema_v2
Revises: 20260424_resume_state
Create Date: 2026-04-27
"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

revision: str = "20260427_schema_v2"
down_revision: str | None = "20260424_resume_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_col_if_not_exists(conn, table: str, col: str, col_def: str) -> None:
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_def}"))


def _create_index_if_not_exists(conn, name: str, table: str, col: str) -> None:
    conn.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON {table}({col})"))


def upgrade() -> None:
    conn = op.get_bind()

    # --- courses ---
    _add_col_if_not_exists(conn, "courses", "course_config", "JSONB")

    # --- learning_units ---
    _add_col_if_not_exists(conn, "learning_units", "has_quiz_items", "BOOLEAN NOT NULL DEFAULT FALSE")
    _add_col_if_not_exists(conn, "learning_units", "salience_decision", "VARCHAR(40)")

    # --- units (may already exist from 20260430_units_cat_fields) ---
    _add_col_if_not_exists(conn, "units", "content_hash", "VARCHAR(128)")
    _add_col_if_not_exists(conn, "units", "active", "BOOLEAN NOT NULL DEFAULT TRUE")
    _add_col_if_not_exists(conn, "units", "deprecated_at", "TIMESTAMPTZ")
    _add_col_if_not_exists(conn, "units", "deprecated_reason", "TEXT")
    _add_col_if_not_exists(conn, "units", "content_type", "VARCHAR(80)")
    _add_col_if_not_exists(conn, "units", "content_type_confidence", "VARCHAR(40)")
    _add_col_if_not_exists(conn, "units", "is_worth_learning", "BOOLEAN")
    _add_col_if_not_exists(conn, "units", "salience_score", "VARCHAR(40)")
    _add_col_if_not_exists(conn, "units", "salience_confidence", "VARCHAR(40)")
    _add_col_if_not_exists(conn, "units", "override_critical_kp", "BOOLEAN NOT NULL DEFAULT FALSE")
    _add_col_if_not_exists(conn, "units", "has_quiz_items", "BOOLEAN NOT NULL DEFAULT FALSE")

    # --- concepts_kp ---
    _add_col_if_not_exists(conn, "concepts_kp", "content_hash", "VARCHAR(128)")
    _add_col_if_not_exists(conn, "concepts_kp", "active", "BOOLEAN NOT NULL DEFAULT TRUE")
    _add_col_if_not_exists(conn, "concepts_kp", "deprecated_at", "TIMESTAMPTZ")
    _add_col_if_not_exists(conn, "concepts_kp", "deprecated_reason", "TEXT")
    _add_col_if_not_exists(conn, "concepts_kp", "description_embedding_version", "VARCHAR(120)")

    # --- prerequisite_edges ---
    _add_col_if_not_exists(conn, "prerequisite_edges", "evidence_ledger", "JSONB")
    _add_col_if_not_exists(conn, "prerequisite_edges", "active", "BOOLEAN NOT NULL DEFAULT TRUE")
    _add_col_if_not_exists(conn, "prerequisite_edges", "deprecated_at", "TIMESTAMPTZ")
    _add_col_if_not_exists(conn, "prerequisite_edges", "deprecated_reason", "TEXT")
    _add_col_if_not_exists(conn, "prerequisite_edges", "edge_kind", "VARCHAR(40)")
    _add_col_if_not_exists(conn, "prerequisite_edges", "adjudication_trace", "JSONB")

    # --- pruned_edges ---
    _add_col_if_not_exists(conn, "pruned_edges", "active", "BOOLEAN NOT NULL DEFAULT FALSE")
    _add_col_if_not_exists(conn, "pruned_edges", "deprecated_at", "TIMESTAMPTZ")
    _add_col_if_not_exists(conn, "pruned_edges", "deprecated_reason", "TEXT")
    _add_col_if_not_exists(conn, "pruned_edges", "adjudication_trace", "JSONB")

    # --- sessions ---
    _add_col_if_not_exists(conn, "sessions", "selection_strategy", "VARCHAR(80)")
    _add_col_if_not_exists(conn, "sessions", "calibration_mode", "VARCHAR(80)")
    _add_col_if_not_exists(conn, "sessions", "theta_initial", "FLOAT")
    _add_col_if_not_exists(conn, "sessions", "theta_final", "FLOAT")
    _add_col_if_not_exists(conn, "sessions", "theta_sigma_initial", "FLOAT")
    _add_col_if_not_exists(conn, "sessions", "theta_sigma_final", "FLOAT")
    _add_col_if_not_exists(conn, "sessions", "target_se", "FLOAT")
    _add_col_if_not_exists(conn, "sessions", "stop_reason", "VARCHAR(120)")

    # --- interactions ---
    _add_col_if_not_exists(conn, "interactions", "selection_strategy", "VARCHAR(80)")
    _add_col_if_not_exists(conn, "interactions", "theta_before", "FLOAT")
    _add_col_if_not_exists(conn, "interactions", "theta_after", "FLOAT")
    _add_col_if_not_exists(conn, "interactions", "theta_sigma_before", "FLOAT")
    _add_col_if_not_exists(conn, "interactions", "theta_sigma_after", "FLOAT")
    _add_col_if_not_exists(conn, "interactions", "predicted_probability", "FLOAT")
    _add_col_if_not_exists(conn, "interactions", "item_information", "FLOAT")
    _add_col_if_not_exists(conn, "interactions", "item_difficulty_at_time", "FLOAT")
    _add_col_if_not_exists(conn, "interactions", "item_discrimination_at_time", "FLOAT")
    _add_col_if_not_exists(conn, "interactions", "item_guessing_at_time", "FLOAT")

    # --- item_calibration (may already exist from 20260429_calibration_tables) ---
    _add_col_if_not_exists(conn, "item_calibration", "standard_error_a", "FLOAT")
    _add_col_if_not_exists(conn, "item_calibration", "standard_error_c", "FLOAT")
    _add_col_if_not_exists(conn, "item_calibration", "calibration_run_id", "VARCHAR(160)")
    _add_col_if_not_exists(conn, "item_calibration", "calibration_dataset_version", "VARCHAR(120)")
    _add_col_if_not_exists(conn, "item_calibration", "real_response_count", "INTEGER NOT NULL DEFAULT 0")
    _add_col_if_not_exists(conn, "item_calibration", "synthetic_response_count", "INTEGER NOT NULL DEFAULT 0")

    # --- standalone tables (IF NOT EXISTS to handle prior migration) ---
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ingest_runs (
            run_id VARCHAR(160) PRIMARY KEY,
            course_id VARCHAR(80),
            run_type VARCHAR(80) NOT NULL,
            input_hashes JSONB,
            artifact_version VARCHAR(120),
            status VARCHAR(40) NOT NULL,
            metrics_json JSONB,
            started_at TIMESTAMPTZ,
            finished_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS kp_migration (
            id BIGSERIAL PRIMARY KEY,
            run_id VARCHAR(160),
            migration_type VARCHAR(80) NOT NULL,
            source_kp_id VARCHAR(160) NOT NULL,
            target_kp_id VARCHAR(160),
            status VARCHAR(80) NOT NULL,
            rationale TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS calibration_runs (
            run_id VARCHAR(160) PRIMARY KEY,
            method VARCHAR(80) NOT NULL,
            dataset_version VARCHAR(120),
            real_response_count INTEGER NOT NULL DEFAULT 0,
            synthetic_response_count INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(40) NOT NULL,
            active BOOLEAN NOT NULL DEFAULT FALSE,
            metrics_json JSONB,
            started_at TIMESTAMPTZ,
            finished_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS item_calibration_history (
            id BIGSERIAL PRIMARY KEY,
            item_id VARCHAR(180) NOT NULL REFERENCES question_bank(item_id) ON DELETE CASCADE,
            calibration_run_id VARCHAR(160),
            difficulty_b FLOAT,
            discrimination_a FLOAT,
            guessing_c FLOAT,
            standard_error_b FLOAT,
            standard_error_a FLOAT,
            standard_error_c FLOAT,
            real_response_count INTEGER NOT NULL DEFAULT 0,
            synthetic_response_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS item_exposure_stats (
            item_id VARCHAR(180) NOT NULL REFERENCES question_bank(item_id) ON DELETE CASCADE,
            phase VARCHAR(80) NOT NULL,
            shown_count INTEGER NOT NULL DEFAULT 0,
            answered_count INTEGER NOT NULL DEFAULT 0,
            correct_count INTEGER NOT NULL DEFAULT 0,
            last_shown_at TIMESTAMPTZ,
            exposure_rate FLOAT,
            refreshed_at TIMESTAMPTZ,
            PRIMARY KEY (item_id, phase)
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS human_review_queue (
            id BIGSERIAL PRIMARY KEY,
            entity_type VARCHAR(80) NOT NULL,
            entity_id VARCHAR(220) NOT NULL,
            reason VARCHAR(160) NOT NULL,
            severity VARCHAR(40) NOT NULL,
            suggested_action TEXT,
            context_json JSONB,
            status VARCHAR(40) NOT NULL DEFAULT 'open',
            assigned_to UUID,
            due_at TIMESTAMPTZ,
            escalated_at TIMESTAMPTZ,
            escalation_target VARCHAR(160),
            reviewed_by UUID,
            reviewed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))

    # --- indexes (IF NOT EXISTS) ---
    _create_index_if_not_exists(conn, "ix_units_content_hash", "units", "content_hash")
    _create_index_if_not_exists(conn, "ix_units_active", "units", "active")
    _create_index_if_not_exists(conn, "ix_units_content_type", "units", "content_type")
    _create_index_if_not_exists(conn, "ix_concepts_kp_content_hash", "concepts_kp", "content_hash")
    _create_index_if_not_exists(conn, "ix_concepts_kp_active", "concepts_kp", "active")
    _create_index_if_not_exists(conn, "ix_prerequisite_edges_active", "prerequisite_edges", "active")
    _create_index_if_not_exists(conn, "ix_interactions_selection_strategy", "interactions", "selection_strategy")
    _create_index_if_not_exists(conn, "ix_item_calibration_run", "item_calibration", "calibration_run_id")
    _create_index_if_not_exists(conn, "ix_kp_migration_source", "kp_migration", "source_kp_id")
    _create_index_if_not_exists(conn, "ix_human_review_queue_status", "human_review_queue", "status, severity")


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
