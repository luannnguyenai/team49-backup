"""Add localized user-facing content sidecar table.

Revision ID: 20260512_localized_content
Revises: 20260505_password_reset_tokens
Create Date: 2026-05-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260512_localized_content"
down_revision = "20260505_password_reset_tokens"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    locale_code_enum = postgresql.ENUM("en", "vi", name="locale_code_enum", create_type=False)
    localization_status_enum = postgresql.ENUM(
        "translated",
        "reviewed",
        name="localization_status_enum",
        create_type=False,
    )
    locale_code_enum.create(op.get_bind(), checkfirst=True)
    localization_status_enum.create(op.get_bind(), checkfirst=True)

    if not _has_table("localized_content"):
        op.create_table(
            "localized_content",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("entity_type", sa.String(length=80), nullable=False),
            sa.Column("entity_id", sa.String(length=255), nullable=False),
            sa.Column("field_name", sa.String(length=160), nullable=False),
            sa.Column("source_language", locale_code_enum, nullable=False),
            sa.Column("target_language", locale_code_enum, nullable=False),
            sa.Column("source_text_hash", sa.String(length=64), nullable=False),
            sa.Column("translated_text", sa.Text(), nullable=False),
            sa.Column(
                "status",
                localization_status_enum,
                server_default="translated",
                nullable=False,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "source_language <> target_language",
                name="ck_localized_content_language_pair",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "entity_type",
                "entity_id",
                "field_name",
                "source_language",
                "target_language",
                name="uq_localized_content_entity_field_locale",
            ),
        )

    if not _has_index("localized_content", "ix_localized_content_lookup"):
        op.create_index(
            "ix_localized_content_lookup",
            "localized_content",
            ["entity_type", "entity_id", "target_language"],
        )
    if not _has_index("localized_content", "ix_localized_content_hash"):
        op.create_index(
            "ix_localized_content_hash",
            "localized_content",
            ["source_text_hash"],
        )


def downgrade() -> None:
    if _has_table("localized_content"):
        if _has_index("localized_content", "ix_localized_content_hash"):
            op.drop_index("ix_localized_content_hash", table_name="localized_content")
        if _has_index("localized_content", "ix_localized_content_lookup"):
            op.drop_index("ix_localized_content_lookup", table_name="localized_content")
        op.drop_table("localized_content")

    localization_status_enum = postgresql.ENUM(name="localization_status_enum")
    locale_code_enum = postgresql.ENUM(name="locale_code_enum")
    localization_status_enum.drop(op.get_bind(), checkfirst=True)
    locale_code_enum.drop(op.get_bind(), checkfirst=True)
