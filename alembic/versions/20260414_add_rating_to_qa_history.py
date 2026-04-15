"""add rating to qa_history

Revision ID: 20260414_add_rating
Revises: e56e139d2676
Create Date: 2026-04-14 07:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260414_add_rating'
down_revision = 'e56e139d2676'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'qa_history' AND column_name = 'rating'"
    ))
    if not result.fetchone():
        op.add_column('qa_history', sa.Column('rating', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('qa_history', 'rating')
