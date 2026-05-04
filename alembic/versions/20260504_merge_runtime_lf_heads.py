"""merge runtime/admin and langfuse trace heads

Revision ID: 20260504_merge_runtime_lf_heads
Revises: 20260503_merge_agent_admin_heads, 20260503_lf_trace_fields
Create Date: 2026-05-04
"""

from collections.abc import Sequence


revision: str = "20260504_merge_runtime_lf_heads"
down_revision: tuple[str, str] = (
    "20260503_merge_agent_admin_heads",
    "20260503_lf_trace_fields",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
