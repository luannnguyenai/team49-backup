"""merge schema_v1 and pgvector_ext heads

Revision ID: 20260419_merge_schema_v1
Revises: 20260418_pgvector_ext, 20260418_schema_v1
Create Date: 2026-04-19

"""

from collections.abc import Sequence

revision: str = "20260419_merge_schema_v1"
down_revision: tuple[str, str] = ("20260418_pgvector_ext", "20260418_schema_v1")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
