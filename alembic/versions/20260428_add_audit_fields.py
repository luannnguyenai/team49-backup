"""Add audit fields to sessions and interactions for placement strategy tracking.

Revision ID: 20260428_add_audit_fields
Revises: 20260427_experience_level
Create Date: 2026-04-28

Schema v2 Commit C: ADD-only migration (no drop, no rename).
- sessions: add selection_strategy, calibration_mode, theta_*, target_se, stop_reason
- interactions: add selection_strategy, theta_before/after, predicted_probability, item_information, etc.
"""
from alembic import op
import sqlalchemy as sa


revision = "20260428_add_audit_fields"
down_revision = "20260427_experience_level"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add audit fields to sessions table
    op.add_column("sessions", sa.Column("selection_strategy", sa.String(80), nullable=True))
    op.add_column("sessions", sa.Column("calibration_mode", sa.String(80), nullable=True))
    op.add_column("sessions", sa.Column("theta_initial", sa.Float, nullable=True))
    op.add_column("sessions", sa.Column("theta_final", sa.Float, nullable=True))
    op.add_column("sessions", sa.Column("theta_sigma_initial", sa.Float, nullable=True))
    op.add_column("sessions", sa.Column("theta_sigma_final", sa.Float, nullable=True))
    op.add_column("sessions", sa.Column("target_se", sa.Float, nullable=True))
    op.add_column("sessions", sa.Column("stop_reason", sa.String(80), nullable=True))

    # Add audit fields to interactions table
    op.add_column("interactions", sa.Column("selection_strategy", sa.String(80), nullable=True))
    op.add_column("interactions", sa.Column("theta_before", sa.Float, nullable=True))
    op.add_column("interactions", sa.Column("theta_after", sa.Float, nullable=True))
    op.add_column("interactions", sa.Column("theta_sigma_before", sa.Float, nullable=True))
    op.add_column("interactions", sa.Column("theta_sigma_after", sa.Float, nullable=True))
    op.add_column("interactions", sa.Column("predicted_probability", sa.Float, nullable=True))
    op.add_column("interactions", sa.Column("item_information", sa.Float, nullable=True))
    op.add_column("interactions", sa.Column("item_difficulty_at_time", sa.Float, nullable=True))
    op.add_column("interactions", sa.Column("item_discrimination_at_time", sa.Float, nullable=True))
    op.add_column("interactions", sa.Column("item_guessing_at_time", sa.Float, nullable=True))


def downgrade() -> None:
    # Downgrade: NEVER DROP in production. But for local dev:
    # op.drop_column("interactions", "item_guessing_at_time")
    # op.drop_column("interactions", "item_discrimination_at_time")
    # ... (all 10 interaction fields)
    # op.drop_column("sessions", "stop_reason")
    # ... (all 8 session fields)
    # For now, downgrade is a no-op (data preservation).
    pass
