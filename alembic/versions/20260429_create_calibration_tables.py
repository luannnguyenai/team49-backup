"""Create calibration_runs and item_calibration_history tables + scaffold item_calibration.

Revision ID: 20260429_create_calibration_tables
Revises: 20260428_add_audit_fields
Create Date: 2026-04-29

Schema v2 Commit E: Calibration job infrastructure.
- CREATE TABLE calibration_runs: track calibration runs (status, metrics, active flag)
- CREATE TABLE item_calibration_history: audit trail of fitted parameters
- ALTER TABLE item_calibration ADD: SE_a, SE_c, calibration_run_id, dataset_version, response counts

All ADD-only; no drop/rename. Indexes for performance.
"""
from alembic import op
from sqlalchemy import text


revision = "20260429_calibration_tables"
down_revision = "20260428_add_audit_fields"
branch_labels = None
depends_on = None


def _exec(sql: str) -> None:
    op.get_bind().execute(text(sql))


def _add_col_if_not_exists(table: str, col: str, col_def: str) -> None:
    _exec(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_def}")


def _create_index_if_not_exists(name: str, table: str, col: str) -> None:
    _exec(f"CREATE INDEX IF NOT EXISTS {name} ON {table}({col})")


def upgrade() -> None:
    # Create calibration_runs table
    _exec(
        """
        CREATE TABLE IF NOT EXISTS calibration_runs (
            run_id VARCHAR(160) PRIMARY KEY,
            method VARCHAR(80) NOT NULL,
            dataset_version VARCHAR(255),
            real_response_count INTEGER NOT NULL DEFAULT 0,
            synthetic_response_count INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(80) NOT NULL,
            metrics_json JSONB,
            started_at TIMESTAMPTZ DEFAULT now(),
            finished_at TIMESTAMPTZ,
            active BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    _add_col_if_not_exists(
        "calibration_runs",
        "created_at",
        "TIMESTAMPTZ NOT NULL DEFAULT now()",
    )
    _add_col_if_not_exists(
        "calibration_runs",
        "updated_at",
        "TIMESTAMPTZ NOT NULL DEFAULT now()",
    )
    _create_index_if_not_exists("ix_calibration_runs_active", "calibration_runs", "active")
    _create_index_if_not_exists("ix_calibration_runs_status", "calibration_runs", "status")

    # Create item_calibration_history table
    _exec(
        """
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
        """
    )
    _create_index_if_not_exists("ix_item_calibration_history_item", "item_calibration_history", "item_id")
    _create_index_if_not_exists("ix_item_calibration_history_run", "item_calibration_history", "calibration_run_id")

    # Add columns to item_calibration (Commit E scaffold)
    _add_col_if_not_exists("item_calibration", "standard_error_a", "FLOAT")
    _add_col_if_not_exists("item_calibration", "standard_error_c", "FLOAT")
    _add_col_if_not_exists("item_calibration", "calibration_run_id", "VARCHAR(160)")
    _add_col_if_not_exists("item_calibration", "calibration_dataset_version", "VARCHAR(255)")
    _add_col_if_not_exists("item_calibration", "real_response_count", "INTEGER")
    _add_col_if_not_exists("item_calibration", "synthetic_response_count", "INTEGER DEFAULT 0")

    # Foreign key from item_calibration to calibration_runs
    _exec(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_item_calibration_calibration_run_id'
            ) THEN
                ALTER TABLE item_calibration
                ADD CONSTRAINT fk_item_calibration_calibration_run_id
                FOREIGN KEY (calibration_run_id)
                REFERENCES calibration_runs(run_id)
                ON DELETE SET NULL;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Downgrade: preserve data; do not drop in production.
    # For local dev only:
    # op.drop_constraint("fk_item_calibration_calibration_run_id", "item_calibration", type_="foreignkey")
    # op.drop_column("item_calibration", "synthetic_response_count")
    # ... (drop all 6 new item_calibration columns)
    # op.drop_index("ix_item_calibration_history_run")
    # op.drop_index("ix_item_calibration_history_item")
    # op.drop_table("item_calibration_history")
    # op.drop_index("ix_calibration_runs_status")
    # op.drop_index("ix_calibration_runs_active")
    # op.drop_table("calibration_runs")
    pass
