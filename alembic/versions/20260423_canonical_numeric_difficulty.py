"""Store canonical difficulty fields as numeric floats.

Revision ID: 20260423_canonical_numeric
Revises: 20260423_session_refs
Create Date: 2026-04-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260423_canonical_numeric"
down_revision: str | None = "20260423_session_refs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "concepts_kp",
        "difficulty_level",
        existing_type=sa.String(length=80),
        type_=sa.Float(),
        postgresql_using="NULLIF(difficulty_level::text, '')::double precision",
        existing_nullable=True,
    )
    op.alter_column(
        "units",
        "difficulty",
        existing_type=sa.String(length=80),
        type_=sa.Float(),
        postgresql_using="NULLIF(difficulty::text, '')::double precision",
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "units",
        "difficulty",
        existing_type=sa.Float(),
        type_=sa.String(length=80),
        postgresql_using="difficulty::text",
        existing_nullable=True,
    )
    op.alter_column(
        "concepts_kp",
        "difficulty_level",
        existing_type=sa.Float(),
        type_=sa.String(length=80),
        postgresql_using="difficulty_level::text",
        existing_nullable=True,
    )
