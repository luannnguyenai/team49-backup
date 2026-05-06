"""Add password reset tokens.

Revision ID: 20260505_password_reset_tokens
Revises: 20260504_merge_runtime_lf_heads
Create Date: 2026-05-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260505_password_reset_tokens"
down_revision = "20260504_merge_runtime_lf_heads"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    if not _has_column("users", "password_changed_at"):
        op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
    if not _has_table("password_reset_tokens"):
        op.create_table(
            "password_reset_tokens",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("requested_ip", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index("password_reset_tokens", "ix_password_reset_tokens_token_hash"):
        op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)
    if not _has_index("password_reset_tokens", "ix_password_reset_tokens_user_id"):
        op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])


def downgrade() -> None:
    if _has_table("password_reset_tokens"):
        if _has_index("password_reset_tokens", "ix_password_reset_tokens_user_id"):
            op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
        if _has_index("password_reset_tokens", "ix_password_reset_tokens_token_hash"):
            op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
        op.drop_table("password_reset_tokens")
    if _has_column("users", "password_changed_at"):
        op.drop_column("users", "password_changed_at")
