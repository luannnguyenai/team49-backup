"""Add unique constraint on placement_assessment_results(user_id, topic_unit_id).

Revision ID: 20260425_placement_unique
Revises: 20260425_placement_asmnt
Create Date: 2026-04-25
"""
from collections.abc import Sequence
from alembic import op

revision: str = "20260425_placement_unique"
down_revision: str | None = "20260425_placement_asmnt"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_placement_results_user_unit",
        "placement_assessment_results",
        ["user_id", "topic_unit_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_placement_results_user_unit",
        "placement_assessment_results",
        type_="unique",
    )
