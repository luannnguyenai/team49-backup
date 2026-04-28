"""Add audit fields to sessions and interactions for placement strategy tracking.

Revision ID: 20260428_add_audit_fields
Revises: 20260427_experience_level
Create Date: 2026-04-28

Schema v2 Commit C: ADD-only migration (no drop, no rename).
- sessions: add selection_strategy, calibration_mode, theta_*, target_se, stop_reason
- interactions: add selection_strategy, theta_before/after, predicted_probability, item_information, etc.
"""
from alembic import op
from sqlalchemy import text


revision = "20260428_add_audit_fields"
down_revision = "20260427_experience_level"
branch_labels = None
depends_on = None


def _add_col_if_not_exists(table: str, col: str, col_def: str) -> None:
    op.get_bind().execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_def}"))


def upgrade() -> None:
    # Add audit fields to sessions table
    _add_col_if_not_exists("sessions", "selection_strategy", "VARCHAR(80)")
    _add_col_if_not_exists("sessions", "calibration_mode", "VARCHAR(80)")
    _add_col_if_not_exists("sessions", "theta_initial", "FLOAT")
    _add_col_if_not_exists("sessions", "theta_final", "FLOAT")
    _add_col_if_not_exists("sessions", "theta_sigma_initial", "FLOAT")
    _add_col_if_not_exists("sessions", "theta_sigma_final", "FLOAT")
    _add_col_if_not_exists("sessions", "target_se", "FLOAT")
    _add_col_if_not_exists("sessions", "stop_reason", "VARCHAR(80)")

    # Add audit fields to interactions table
    _add_col_if_not_exists("interactions", "selection_strategy", "VARCHAR(80)")
    _add_col_if_not_exists("interactions", "theta_before", "FLOAT")
    _add_col_if_not_exists("interactions", "theta_after", "FLOAT")
    _add_col_if_not_exists("interactions", "theta_sigma_before", "FLOAT")
    _add_col_if_not_exists("interactions", "theta_sigma_after", "FLOAT")
    _add_col_if_not_exists("interactions", "predicted_probability", "FLOAT")
    _add_col_if_not_exists("interactions", "item_information", "FLOAT")
    _add_col_if_not_exists("interactions", "item_difficulty_at_time", "FLOAT")
    _add_col_if_not_exists("interactions", "item_discrimination_at_time", "FLOAT")
    _add_col_if_not_exists("interactions", "item_guessing_at_time", "FLOAT")


def downgrade() -> None:
    # Downgrade: NEVER DROP in production. But for local dev:
    # op.drop_column("interactions", "item_guessing_at_time")
    # op.drop_column("interactions", "item_discrimination_at_time")
    # ... (all 10 interaction fields)
    # op.drop_column("sessions", "stop_reason")
    # ... (all 8 session fields)
    # For now, downgrade is a no-op (data preservation).
    pass
