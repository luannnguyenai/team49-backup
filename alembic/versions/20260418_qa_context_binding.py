"""add context binding id to qa_history

Revision ID: 20260418_qa_context_binding
Revises: 20260418_pgvector_ext
Create Date: 2026-04-18 23:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260418_qa_context_binding"
down_revision: str | None = "20260418_pgvector_ext"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'qa_history' AND column_name = 'context_binding_id'"
    ))
    if not result.fetchone():
        op.add_column(
            "qa_history",
            sa.Column("context_binding_id", sa.String(length=255), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("qa_history", "context_binding_id")
