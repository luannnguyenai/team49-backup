"""add mastery_history audit table

Revision ID: 20260417_mastery_history
Revises: 20260415_checkpoint_state
Create Date: 2026-04-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '20260417_mastery_history'
down_revision = '20260415_checkpoint_state'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'mastery_history',
        sa.Column('id', UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('topic_id', UUID(as_uuid=True),
                  sa.ForeignKey('topics.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kc_id', UUID(as_uuid=True),
                  sa.ForeignKey('knowledge_components.id', ondelete='SET NULL'), nullable=True),
        sa.Column('old_mastery_probability', sa.Float(), nullable=True),
        sa.Column('new_mastery_probability', sa.Float(), nullable=False),
        sa.Column('old_mastery_level', sa.String(50), nullable=True),
        sa.Column('new_mastery_level', sa.String(50), nullable=False),
        sa.Column('evidence_count', sa.Integer(), nullable=False),
        sa.Column('trigger_session_id', UUID(as_uuid=True),
                  sa.ForeignKey('sessions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('changed_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_mh_user_topic', 'mastery_history', ['user_id', 'topic_id'])
    op.create_index('ix_mh_changed_at', 'mastery_history', ['changed_at'])


def downgrade() -> None:
    op.drop_index('ix_mh_changed_at', table_name='mastery_history')
    op.drop_index('ix_mh_user_topic', table_name='mastery_history')
    op.drop_table('mastery_history')
