"""enable pgvector extension on hybrid head

Revision ID: 20260418_enable_pgvector_extension
Revises: 20260418_merge_heads
Create Date: 2026-04-18 21:25:00.000000
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260418_enable_pgvector_extension"
down_revision: str | None = "20260418_merge_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector;")
