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
from sqlalchemy import text


revision = "20260430_units_cat_fields"
down_revision = "20260429_calibration_tables"
branch_labels = None
depends_on = None


def _exec(sql: str) -> None:
    op.get_bind().execute(text(sql))


def _add_col_if_not_exists(table: str, col: str, col_def: str) -> None:
    _exec(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_def}")


def _create_index_if_not_exists(name: str, table: str, col: str) -> None:
    _exec(f"CREATE INDEX IF NOT EXISTS {name} ON {table}({col})")


def upgrade() -> None:
    _add_col_if_not_exists("units", "active", "BOOLEAN DEFAULT TRUE")
    _add_col_if_not_exists("units", "content_hash", "VARCHAR(128)")
    _add_col_if_not_exists("units", "content_type", "VARCHAR(80)")
    _add_col_if_not_exists("units", "content_type_confidence", "VARCHAR(40)")
    _add_col_if_not_exists("units", "deprecated_at", "VARCHAR(80)")
    _add_col_if_not_exists("units", "deprecated_reason", "TEXT")
    _add_col_if_not_exists("units", "has_quiz_items", "BOOLEAN")
    _add_col_if_not_exists("units", "is_worth_learning", "BOOLEAN")
    _add_col_if_not_exists("units", "override_critical_kp", "BOOLEAN DEFAULT FALSE")
    _add_col_if_not_exists("units", "salience_confidence", "VARCHAR(40)")
    _add_col_if_not_exists("units", "salience_score", "VARCHAR(80)")

    _create_index_if_not_exists("ix_units_active", "units", "active")
    _create_index_if_not_exists("ix_units_content_type", "units", "content_type")


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
