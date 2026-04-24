"""Legacy archive placeholder kept for revision graph continuity.

Revision ID: 20260423_archive_legacy
Revises: 20260423_nullable_iq
Create Date: 2026-04-23

This revision used to rename legacy runtime tables. The project now performs a
hard canonical cutover and drops those tables in a later migration, so this
step is intentionally a no-op but must remain in the graph because subsequent
revisions depend on it.
"""

from collections.abc import Sequence

revision: str = "20260423_archive_legacy"
down_revision: str | None = "20260423_nullable_iq"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    return None


def downgrade() -> None:
    return None
