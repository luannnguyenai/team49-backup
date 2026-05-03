"""Add role column to users table for admin RBAC.

Revision ID: 20260502_add_user_role
Revises: 20260427_merge_schema_v2_cat
Create Date: 2026-05-02

Adds a single `role` column to users with default 'user'. Used by the new
admin dashboard to gate /api/admin/* endpoints via require_admin dependency.

Backwards compatible: existing rows get default 'user'. To promote an admin,
run: python admin-dashboard/scripts/seed_admin.py --email <e>
"""
from alembic import op
import sqlalchemy as sa


revision = "20260502_add_user_role"
down_revision = "20260427_merge_schema_v2_cat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
            server_default="user",
        ),
    )
    op.create_index("ix_users_role", "users", ["role"])


def downgrade() -> None:
    op.drop_index("ix_users_role", table_name="users")
    op.drop_column("users", "role")
