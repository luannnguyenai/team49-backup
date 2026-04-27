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
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


revision = "20260429_calibration_tables"
down_revision = "20260428_add_audit_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create calibration_runs table
    op.create_table(
        "calibration_runs",
        sa.Column("run_id", sa.String(80), primary_key=True),
        sa.Column("method", sa.String(80), nullable=False),  # 1pl, 2pl, 3pl, mirt
        sa.Column("dataset_version", sa.String(255), nullable=False),
        sa.Column("real_response_count", sa.Integer, nullable=False),
        sa.Column("synthetic_response_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(80), nullable=False),  # started, passed, failed
        sa.Column("metrics_json", JSON, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("ix_calibration_runs_active", "calibration_runs", ["active"])
    op.create_index("ix_calibration_runs_status", "calibration_runs", ["status"])

    # Create item_calibration_history table
    op.create_table(
        "item_calibration_history",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("item_id", sa.String(180), nullable=False),
        sa.Column("calibration_run_id", sa.String(80), nullable=False),
        sa.Column("difficulty_b", sa.Float, nullable=True),
        sa.Column("discrimination_a", sa.Float, nullable=True),
        sa.Column("guessing_c", sa.Float, nullable=True),
        sa.Column("standard_error_b", sa.Float, nullable=True),
        sa.Column("standard_error_a", sa.Float, nullable=True),
        sa.Column("standard_error_c", sa.Float, nullable=True),
        sa.Column("real_response_count", sa.Integer, nullable=False),
        sa.Column("synthetic_response_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["item_id"], ["question_bank.item_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["calibration_run_id"], ["calibration_runs.run_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_item_calibration_history_item", "item_calibration_history", ["item_id"])
    op.create_index("ix_item_calibration_history_run", "item_calibration_history", ["calibration_run_id"])

    # Add columns to item_calibration (Commit E scaffold)
    op.add_column("item_calibration", sa.Column("standard_error_a", sa.Float, nullable=True))
    op.add_column("item_calibration", sa.Column("standard_error_c", sa.Float, nullable=True))
    op.add_column("item_calibration", sa.Column("calibration_run_id", sa.String(80), nullable=True))
    op.add_column("item_calibration", sa.Column("calibration_dataset_version", sa.String(255), nullable=True))
    op.add_column("item_calibration", sa.Column("real_response_count", sa.Integer, nullable=True))
    op.add_column("item_calibration", sa.Column("synthetic_response_count", sa.Integer, nullable=True, server_default="0"))

    # Foreign key from item_calibration to calibration_runs
    op.create_foreign_key(
        "fk_item_calibration_calibration_run_id",
        "item_calibration",
        "calibration_runs",
        ["calibration_run_id"],
        ["run_id"],
        ondelete="SET NULL",
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
