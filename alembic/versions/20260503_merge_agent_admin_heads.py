"""Merge agent runtime and admin role migration heads.

Revision ID: 20260503_merge_agent_admin_heads
Revises: 20260502_thread_memory_scope, 20260502_add_user_role
Create Date: 2026-05-03
"""

from collections.abc import Sequence


revision: str = "20260503_merge_agent_admin_heads"
down_revision: tuple[str, str] = (
    "20260502_thread_memory_scope",
    "20260502_add_user_role",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
