"""Archive legacy runtime/content tables after canonical cutover.

Revision ID: 20260423_archive_legacy
Revises: 20260423_nullable_iq
Create Date: 2026-04-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260423_archive_legacy"
down_revision: str | None = "20260423_nullable_iq"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


LEGACY_TABLE_RENAMES: tuple[tuple[str, str], ...] = (
    ("questions", "questions_legacy_archived"),
    ("mastery_scores", "mastery_scores_legacy_archived"),
    ("mastery_history", "mastery_history_legacy_archived"),
    ("learning_paths", "learning_paths_legacy_archived"),
    ("modules", "modules_legacy_archived"),
    ("topics", "topics_legacy_archived"),
    ("knowledge_components", "knowledge_components_legacy_archived"),
)


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    return bool(bind.dialect.has_table(bind, table_name))


def _rename_if_present(source: str, target: str) -> None:
    source_exists = _table_exists(source)
    target_exists = _table_exists(target)
    if source_exists and target_exists:
        raise RuntimeError(f"Both {source!r} and {target!r} exist; refusing ambiguous legacy archive.")
    if source_exists:
        op.rename_table(source, target)


def upgrade() -> None:
    for source, target in LEGACY_TABLE_RENAMES:
        _rename_if_present(source, target)


def downgrade() -> None:
    for source, target in reversed(LEGACY_TABLE_RENAMES):
        _rename_if_present(target, source)
