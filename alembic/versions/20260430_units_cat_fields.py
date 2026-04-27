"""Add CAT academic fields to units table.

Revision ID: 20260430_units_cat_fields
Revises: 20260429_calibration_tables
Create Date: 2026-04-30

The canonical JSONL bundle (cs224n_cs231n_cs230_v1) now ships 11 additional
fields per learning unit that were not present in the original schema:

    active, content_hash, content_type, content_type_confidence,
    deprecated_at, deprecated_reason, has_quiz_items, is_worth_learning,
    override_critical_kp, salience_confidence, salience_score

All columns are ADD-only and nullable (or with a safe default). No existing
data is dropped or renamed. Two covering indexes are added for the most common
query patterns (filtering by active flag, filtering by content_type).
"""
from alembic import op
import sqlalchemy as sa


revision = "20260430_units_cat_fields"
down_revision = "20260429_calibration_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("units", sa.Column("active", sa.Boolean, nullable=True, server_default="true"))
    op.add_column("units", sa.Column("content_hash", sa.String(64), nullable=True))
    op.add_column("units", sa.Column("content_type", sa.String(80), nullable=True))
    op.add_column("units", sa.Column("content_type_confidence", sa.String(40), nullable=True))
    op.add_column("units", sa.Column("deprecated_at", sa.String(80), nullable=True))
    op.add_column("units", sa.Column("deprecated_reason", sa.Text, nullable=True))
    op.add_column("units", sa.Column("has_quiz_items", sa.Boolean, nullable=True))
    op.add_column("units", sa.Column("is_worth_learning", sa.Boolean, nullable=True))
    op.add_column("units", sa.Column("override_critical_kp", sa.Boolean, nullable=True))
    op.add_column("units", sa.Column("salience_confidence", sa.String(40), nullable=True))
    op.add_column("units", sa.Column("salience_score", sa.String(80), nullable=True))

    op.create_index("ix_units_active", "units", ["active"])
    op.create_index("ix_units_content_type", "units", ["content_type"])


def downgrade() -> None:
    # Preserve data in production; local dev only.
    op.drop_index("ix_units_content_type", table_name="units")
    op.drop_index("ix_units_active", table_name="units")
    op.drop_column("units", "salience_score")
    op.drop_column("units", "salience_confidence")
    op.drop_column("units", "override_critical_kp")
    op.drop_column("units", "is_worth_learning")
    op.drop_column("units", "has_quiz_items")
    op.drop_column("units", "deprecated_reason")
    op.drop_column("units", "deprecated_at")
    op.drop_column("units", "content_type_confidence")
    op.drop_column("units", "content_type")
    op.drop_column("units", "content_hash")
    op.drop_column("units", "active")
