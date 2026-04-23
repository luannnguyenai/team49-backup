"""Drop legacy curriculum and mastery tables after canonical cutover.

Revision ID: 20260423_drop_legacy
Revises: 20260423_item_cal_prior
Create Date: 2026-04-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260423_drop_legacy"
down_revision: str | None = "20260423_item_cal_prior"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


LEGACY_TABLES_DROP_ORDER: tuple[str, ...] = (
    "mastery_history",
    "learning_paths",
    "mastery_scores",
    "questions",
    "knowledge_components",
    "topics",
    "modules",
)


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    return bool(sa.inspect(bind).has_table(table_name))


def _drop_fk_if_exists(table_name: str, constrained_columns: tuple[str, ...]) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return
    for foreign_key in inspector.get_foreign_keys(table_name):
        columns = tuple(foreign_key.get("constrained_columns") or [])
        name = foreign_key.get("name")
        if columns == constrained_columns and name:
            with op.batch_alter_table(table_name) as batch_op:
                batch_op.drop_constraint(name, type_="foreignkey")
            return


def upgrade() -> None:
    _drop_fk_if_exists("sessions", ("topic_id",))
    _drop_fk_if_exists("sessions", ("module_id",))
    _drop_fk_if_exists("interactions", ("question_id",))

    for table_name in LEGACY_TABLES_DROP_ORDER:
        if _table_exists(table_name):
            op.drop_table(table_name)


def downgrade() -> None:
    raise RuntimeError(
        "Irreversible migration: legacy runtime tables were dropped after canonical cutover."
    )
