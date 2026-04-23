"""Add canonical unit and section refs to sessions.

Revision ID: 20260423_session_refs
Revises: 20260423_archive_legacy
Create Date: 2026-04-23
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260423_session_refs"
down_revision: str | None = "20260423_archive_legacy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("canonical_unit_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column("canonical_section_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_sessions_canonical_unit_id_learning_units",
        "sessions",
        "learning_units",
        ["canonical_unit_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_sessions_canonical_section_id_course_sections",
        "sessions",
        "course_sections",
        ["canonical_section_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_sessions_canonical_unit", "sessions", ["canonical_unit_id"])
    op.create_index("ix_sessions_canonical_section", "sessions", ["canonical_section_id"])


def downgrade() -> None:
    op.drop_index("ix_sessions_canonical_section", table_name="sessions")
    op.drop_index("ix_sessions_canonical_unit", table_name="sessions")
    op.drop_constraint(
        "fk_sessions_canonical_section_id_course_sections",
        "sessions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_sessions_canonical_unit_id_learning_units",
        "sessions",
        type_="foreignkey",
    )
    op.drop_column("sessions", "canonical_section_id")
    op.drop_column("sessions", "canonical_unit_id")
