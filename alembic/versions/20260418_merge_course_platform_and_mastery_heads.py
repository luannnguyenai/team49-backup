"""merge course platform and mastery history heads

Revision ID: 20260418_merge_heads
Revises: 20260417_mastery_history, 20260418_course_platform
Create Date: 2026-04-18 18:05:00.000000

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "20260418_merge_heads"
down_revision: tuple[str, str] = (
    "20260417_mastery_history",
    "20260418_course_platform",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
