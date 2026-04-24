"""Store item calibration difficulty prior as numeric float.

Revision ID: 20260423_item_cal_prior
Revises: 20260423_canonical_numeric
Create Date: 2026-04-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260423_item_cal_prior"
down_revision: str | None = "20260423_canonical_numeric"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "item_calibration",
        "difficulty_prior",
        existing_type=sa.String(length=80),
        type_=sa.Float(),
        postgresql_using="NULLIF(difficulty_prior::text, '')::double precision",
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "item_calibration",
        "difficulty_prior",
        existing_type=sa.Float(),
        type_=sa.String(length=80),
        postgresql_using="difficulty_prior::text",
        existing_nullable=True,
    )
