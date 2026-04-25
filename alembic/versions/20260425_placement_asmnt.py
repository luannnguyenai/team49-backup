"""Add placement_assessment_results table.

Revision ID: 20260425_placement_asmnt
Revises: 20260424_resume_state
Create Date: 2026-04-25
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260425_placement_asmnt"
down_revision: str | None = "20260424_resume_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "placement_assessment_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_unit_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("learning_units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score_pct", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("user_choice", sa.Text(), nullable=True),
        sa.Column("raw_answers", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default="[]"),
        sa.Column("theta_estimate", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "decision IN ('skip', 'review', 'relearn')",
            name="ck_placement_results_decision",
        ),
        sa.CheckConstraint(
            "user_choice IS NULL OR user_choice IN ('skip', 'review')",
            name="ck_placement_results_user_choice",
        ),
        sa.CheckConstraint(
            "score_pct >= 0 AND score_pct <= 100",
            name="ck_placement_results_score_range",
        ),
    )
    op.create_index(
        "ix_placement_results_user_unit",
        "placement_assessment_results",
        ["user_id", "topic_unit_id"],
    )
    op.create_index(
        "ix_placement_results_user",
        "placement_assessment_results",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_placement_results_user", table_name="placement_assessment_results")
    op.drop_index("ix_placement_results_user_unit", table_name="placement_assessment_results")
    op.drop_table("placement_assessment_results")
