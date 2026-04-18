"""course platform schema

Revision ID: 20260418_course_platform
Revises: 20260415_checkpoint_state
Create Date: 2026-04-18 11:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260418_course_platform"
down_revision: str | None = "20260415_checkpoint_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    course_status_enum = sa.Enum(
        "ready",
        "coming_soon",
        "metadata_partial",
        name="course_status_enum",
    )
    course_visibility_enum = sa.Enum("public", "hidden", name="course_visibility_enum")
    course_section_kind_enum = sa.Enum(
        "module",
        "unit",
        "lesson_group",
        "lecture_group",
        name="course_section_kind_enum",
    )
    learning_unit_type_enum = sa.Enum(
        "lesson",
        "lecture",
        "reading",
        "practice",
        name="learning_unit_type_enum",
    )
    learning_unit_status_enum = sa.Enum(
        "ready",
        "coming_soon",
        "metadata_partial",
        name="learning_unit_status_enum",
    )
    learning_unit_entry_mode_enum = sa.Enum(
        "text",
        "video",
        "hybrid",
        name="learning_unit_entry_mode_enum",
    )
    course_asset_type_enum = sa.Enum(
        "video",
        "transcript",
        "slides",
        "thumbnail",
        "supplement",
        name="course_asset_type_enum",
    )
    course_asset_availability_status_enum = sa.Enum(
        "available",
        "processing",
        "missing",
        name="course_asset_availability_status_enum",
    )
    learning_progress_status_enum = sa.Enum(
        "not_started",
        "in_progress",
        "completed",
        "blocked",
        name="learning_progress_status_enum",
    )
    legacy_lecture_migration_state_enum = sa.Enum(
        "pending",
        "mapped",
        "deprecated",
        name="legacy_lecture_migration_state_enum",
    )

    bind = op.get_bind()
    enums = [
        course_status_enum,
        course_visibility_enum,
        course_section_kind_enum,
        learning_unit_type_enum,
        learning_unit_status_enum,
        learning_unit_entry_mode_enum,
        course_asset_type_enum,
        course_asset_availability_status_enum,
        learning_progress_status_enum,
        legacy_lecture_migration_state_enum,
    ]
    for enum_type in enums:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "courses",
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("short_description", sa.Text(), nullable=False),
        sa.Column(
            "status",
            course_status_enum,
            nullable=False,
            server_default="metadata_partial",
        ),
        sa.Column(
            "visibility",
            course_visibility_enum,
            nullable=False,
            server_default="public",
        ),
        sa.Column("cover_image_url", sa.String(length=500), nullable=True),
        sa.Column("hero_badge", sa.String(length=255), nullable=True),
        sa.Column("primary_subject", sa.String(length=120), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_courses_status", "courses", ["status"], unique=False)
    op.create_index("ix_courses_visibility_sort", "courses", ["visibility", "sort_order"], unique=False)

    op.create_table(
        "course_overviews",
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("headline", sa.String(length=255), nullable=False),
        sa.Column("subheadline", sa.String(length=255), nullable=True),
        sa.Column("summary_markdown", sa.Text(), nullable=False),
        sa.Column("learning_outcomes", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("target_audience", sa.Text(), nullable=True),
        sa.Column("prerequisites_summary", sa.Text(), nullable=True),
        sa.Column("estimated_duration_text", sa.String(length=120), nullable=True),
        sa.Column("structure_snapshot", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("cta_label", sa.String(length=120), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id"),
    )

    op.create_table(
        "course_sections",
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("parent_section_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("kind", course_section_kind_enum, nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_entry_section", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_section_id"], ["course_sections.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_course_sections_course_sort", "course_sections", ["course_id", "sort_order"], unique=False)
    op.create_index("ix_course_sections_parent", "course_sections", ["parent_section_id"], unique=False)

    op.create_table(
        "learning_units",
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("unit_type", learning_unit_type_enum, nullable=False),
        sa.Column(
            "status",
            learning_unit_status_enum,
            nullable=False,
            server_default="metadata_partial",
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_source_type", sa.String(length=120), nullable=True),
        sa.Column("content_body", sa.Text(), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "entry_mode",
            learning_unit_entry_mode_enum,
            nullable=False,
            server_default="hybrid",
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_id"], ["course_sections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "slug", name="uq_learning_units_course_slug"),
    )
    op.create_index(
        "ix_learning_units_course_section_sort",
        "learning_units",
        ["course_id", "section_id", "sort_order"],
        unique=False,
    )
    op.create_index("ix_learning_units_status", "learning_units", ["status"], unique=False)

    op.create_table(
        "course_assets",
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("learning_unit_id", sa.UUID(), nullable=True),
        sa.Column("asset_type", course_asset_type_enum, nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("delivery_url", sa.String(length=500), nullable=True),
        sa.Column(
            "availability_status",
            course_asset_availability_status_enum,
            nullable=False,
            server_default="processing",
        ),
        sa.Column("metadata_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learning_unit_id"], ["learning_units.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_course_assets_course_asset_type", "course_assets", ["course_id", "asset_type"], unique=False)
    op.create_index("ix_course_assets_learning_unit", "course_assets", ["learning_unit_id"], unique=False)

    op.create_table(
        "learner_assessment_profiles",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("is_onboarded", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("skill_test_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assessment_session_id", sa.UUID(), nullable=True),
        sa.Column("recommendation_ready", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assessment_session_id"], ["sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "course_recommendations",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("reason_summary", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "course_id", name="uq_course_recommendations_user_course"),
        sa.UniqueConstraint("user_id", "rank", name="uq_course_recommendations_user_rank"),
    )
    op.create_index(
        "ix_course_recommendations_user_rank",
        "course_recommendations",
        ["user_id", "rank"],
        unique=False,
    )

    op.create_table(
        "learning_progress_records",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("learning_unit_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            learning_progress_status_enum,
            nullable=False,
            server_default="not_started",
        ),
        sa.Column("last_position_seconds", sa.Float(), nullable=True),
        sa.Column("last_opened_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learning_unit_id"], ["learning_units.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "learning_unit_id", name="uq_learning_progress_records_user_unit"),
    )
    op.create_index(
        "ix_learning_progress_records_user_course",
        "learning_progress_records",
        ["user_id", "course_id"],
        unique=False,
    )

    op.create_table(
        "tutor_context_bindings",
        sa.Column("learning_unit_id", sa.UUID(), nullable=False),
        sa.Column("context_type", sa.String(length=120), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=False),
        sa.Column("context_window_rule", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["learning_unit_id"], ["learning_units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tutor_context_bindings_unit_active",
        "tutor_context_bindings",
        ["learning_unit_id", "is_active"],
        unique=False,
    )

    op.create_table(
        "legacy_lecture_mappings",
        sa.Column("legacy_lecture_id", sa.String(), nullable=False),
        sa.Column("learning_unit_id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column(
            "migration_state",
            legacy_lecture_migration_state_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learning_unit_id"], ["learning_units.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["legacy_lecture_id"], ["lectures.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("learning_unit_id", name="uq_legacy_lecture_mappings_learning_unit"),
        sa.UniqueConstraint("legacy_lecture_id"),
    )
    op.create_index(
        "ix_legacy_lecture_mappings_course_state",
        "legacy_lecture_mappings",
        ["course_id", "migration_state"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_legacy_lecture_mappings_course_state", table_name="legacy_lecture_mappings")
    op.drop_table("legacy_lecture_mappings")
    op.drop_index("ix_tutor_context_bindings_unit_active", table_name="tutor_context_bindings")
    op.drop_table("tutor_context_bindings")
    op.drop_index("ix_learning_progress_records_user_course", table_name="learning_progress_records")
    op.drop_table("learning_progress_records")
    op.drop_index("ix_course_recommendations_user_rank", table_name="course_recommendations")
    op.drop_table("course_recommendations")
    op.drop_table("learner_assessment_profiles")
    op.drop_index("ix_course_assets_learning_unit", table_name="course_assets")
    op.drop_index("ix_course_assets_course_asset_type", table_name="course_assets")
    op.drop_table("course_assets")
    op.drop_index("ix_learning_units_status", table_name="learning_units")
    op.drop_index("ix_learning_units_course_section_sort", table_name="learning_units")
    op.drop_table("learning_units")
    op.drop_index("ix_course_sections_parent", table_name="course_sections")
    op.drop_index("ix_course_sections_course_sort", table_name="course_sections")
    op.drop_table("course_sections")
    op.drop_table("course_overviews")
    op.drop_index("ix_courses_visibility_sort", table_name="courses")
    op.drop_index("ix_courses_status", table_name="courses")
    op.drop_table("courses")

    bind = op.get_bind()
    for enum_name in [
        "legacy_lecture_migration_state_enum",
        "learning_progress_status_enum",
        "course_asset_availability_status_enum",
        "course_asset_type_enum",
        "learning_unit_entry_mode_enum",
        "learning_unit_status_enum",
        "learning_unit_type_enum",
        "course_section_kind_enum",
        "course_visibility_enum",
        "course_status_enum",
    ]:
        sa.Enum(name=enum_name).drop(bind, checkfirst=True)
