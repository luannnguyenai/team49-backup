"""merge final two heads into single chain

Revision ID: 20260419_merge_final
Revises: 20260419_merge_schema_v1, 20260418_merge_schema_qa_heads
Create Date: 2026-04-19

"""

from collections.abc import Sequence

revision: str = "20260419_merge_final"
down_revision: tuple[str, str] = (
    "20260419_merge_schema_v1",
    "20260418_merge_schema_qa_heads",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
