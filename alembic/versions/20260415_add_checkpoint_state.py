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

    # Check if table exists
    table_exists = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = 'learning_progress'"
    )).fetchone()

    if not table_exists:
        # Create the full table (was never included in initial migration)
        op.create_table(
            'learning_progress',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('session_id', sa.String(), nullable=False),
            sa.Column('lecture_id', sa.String(), nullable=False),
            sa.Column('last_timestamp', sa.Float(), nullable=True, server_default='0.0'),
            sa.Column('checkpoint_state', sa.String(), nullable=False, server_default='unwatched'),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['lecture_id'], ['lectures.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('session_id', 'lecture_id', name='uq_session_lecture'),
        )
        op.create_index(op.f('ix_learning_progress_id'), 'learning_progress', ['id'], unique=False)
        op.create_index(op.f('ix_learning_progress_session_id'), 'learning_progress', ['session_id'], unique=False)
    else:
        # Table exists — add column if missing
        col_exists = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'learning_progress' AND column_name = 'checkpoint_state'"
        )).fetchone()
        if not col_exists:
            op.add_column(
                'learning_progress',
                sa.Column('checkpoint_state', sa.String(), nullable=False, server_default='unwatched')
            )


def downgrade() -> None:
    conn = op.get_bind()
    table_exists = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = 'learning_progress'"
    )).fetchone()
    if table_exists:
        op.drop_column('learning_progress', 'checkpoint_state')
