"""add checkpoint_state to learning_progress

Revision ID: 20260415_checkpoint_state
Revises: 20260414_add_rating
Create Date: 2026-04-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '20260415_checkpoint_state'
down_revision = '20260414_add_rating'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Add checkpoint_state column if not exists
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'learning_progress' AND column_name = 'checkpoint_state'"
    ))
    if not result.fetchone():
        op.add_column(
            'learning_progress',
            sa.Column('checkpoint_state', sa.String(), nullable=False, server_default='unwatched')
        )
    # Ensure learning_progress table exists (created by init_db, not alembic)
    # This migration only adds the column — table creation handled by SQLAlchemy


def downgrade() -> None:
    op.drop_column('learning_progress', 'checkpoint_state')
