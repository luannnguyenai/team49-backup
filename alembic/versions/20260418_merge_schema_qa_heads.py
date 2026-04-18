"""merge schema v1 and qa context binding heads

Revision ID: 20260418_merge_schema_qa_heads
Revises: 20260418_schema_v1, 20260418_qa_context_binding
Create Date: 2026-04-18 23:28:00.000000
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "20260418_merge_schema_qa_heads"
down_revision: tuple[str, str] = (
    "20260418_schema_v1",
    "20260418_qa_context_binding",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
