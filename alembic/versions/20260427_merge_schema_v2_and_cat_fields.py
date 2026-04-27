"""merge schema_v2 and units_cat_fields heads

Revision ID: 20260427_merge_schema_v2_cat
Revises: 20260427_schema_v2, 20260430_units_cat_fields
Create Date: 2026-04-27

"""

from alembic import op

revision: str = "20260427_merge_schema_v2_cat"
down_revision: tuple[str, str] = ("20260427_schema_v2", "20260430_units_cat_fields")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
