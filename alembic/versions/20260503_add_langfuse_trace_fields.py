"""Add LangFuse trace linkage fields to qa_history.

Revision ID: 20260503_lf_trace_fields
Revises: 20260502_add_user_role
Create Date: 2026-05-03
"""
from alembic import op
import sqlalchemy as sa


revision = "20260503_lf_trace_fields"
down_revision = "20260502_add_user_role"
branch_labels = None
depends_on = None


def _has_column(column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'qa_history' AND column_name = :column_name"
        ),
        {"column_name": column_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    if not _has_column("langfuse_trace_id"):
        op.add_column("qa_history", sa.Column("langfuse_trace_id", sa.String(length=64), nullable=True))
    if not _has_column("langfuse_observation_id"):
        op.add_column(
            "qa_history",
            sa.Column("langfuse_observation_id", sa.String(length=64), nullable=True),
        )


def downgrade() -> None:
    if _has_column("langfuse_observation_id"):
        op.drop_column("qa_history", "langfuse_observation_id")
    if _has_column("langfuse_trace_id"):
        op.drop_column("qa_history", "langfuse_trace_id")
