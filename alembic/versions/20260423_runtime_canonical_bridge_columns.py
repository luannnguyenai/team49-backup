"""Add runtime canonical bridge columns.

Revision ID: 20260423_runtime_bridge
Revises: 20260423_canonical_content
Create Date: 2026-04-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260423_runtime_bridge"
down_revision: str | None = "20260423_canonical_content"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("canonical_course_id", sa.String(length=80), nullable=True))
    op.create_index("ix_courses_canonical_course_id", "courses", ["canonical_course_id"])

    op.add_column("learning_units", sa.Column("canonical_unit_id", sa.String(length=220), nullable=True))
    op.create_index("ix_learning_units_canonical_unit_id", "learning_units", ["canonical_unit_id"])

    op.add_column("sessions", sa.Column("canonical_phase", sa.String(length=80), nullable=True))

    op.add_column("interactions", sa.Column("canonical_item_id", sa.String(length=180), nullable=True))
    op.create_foreign_key(
        "fk_interactions_canonical_item_id_question_bank",
        "interactions",
        "question_bank",
        ["canonical_item_id"],
        ["item_id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_interactions_canonical_item_id", "interactions", ["canonical_item_id"])


def downgrade() -> None:
    op.drop_index("ix_interactions_canonical_item_id", table_name="interactions")
    op.drop_constraint("fk_interactions_canonical_item_id_question_bank", "interactions", type_="foreignkey")
    op.drop_column("interactions", "canonical_item_id")

    op.drop_column("sessions", "canonical_phase")

    op.drop_index("ix_learning_units_canonical_unit_id", table_name="learning_units")
    op.drop_column("learning_units", "canonical_unit_id")

    op.drop_index("ix_courses_canonical_course_id", table_name="courses")
    op.drop_column("courses", "canonical_course_id")
