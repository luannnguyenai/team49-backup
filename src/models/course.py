"""
models/course.py
----------------
Canonical course-platform ORM models used by the course-first experience.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.store import Lecture
    from src.models.user import User


class CourseStatus(enum.StrEnum):
    ready = "ready"
    coming_soon = "coming_soon"
    metadata_partial = "metadata_partial"


class CourseVisibility(enum.StrEnum):
    public = "public"
    hidden = "hidden"


class CourseSectionKind(enum.StrEnum):
    module = "module"
    unit = "unit"
    lesson_group = "lesson_group"
    lecture_group = "lecture_group"


class LearningUnitType(enum.StrEnum):
    lesson = "lesson"
    lecture = "lecture"
    reading = "reading"
    practice = "practice"


class LearningUnitStatus(enum.StrEnum):
    ready = "ready"
    coming_soon = "coming_soon"
    metadata_partial = "metadata_partial"


class LearningUnitEntryMode(enum.StrEnum):
    text = "text"
    video = "video"
    hybrid = "hybrid"


class CourseAssetType(enum.StrEnum):
    video = "video"
    transcript = "transcript"
    slides = "slides"
    thumbnail = "thumbnail"
    supplement = "supplement"


class CourseAssetAvailabilityStatus(enum.StrEnum):
    available = "available"
    processing = "processing"
    missing = "missing"


class LearningProgressStatus(enum.StrEnum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"
    blocked = "blocked"


class LegacyLectureMigrationState(enum.StrEnum):
    pending = "pending"
    mapped = "mapped"
    deprecated = "deprecated"


class Course(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "courses"

    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    short_description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CourseStatus] = mapped_column(
        Enum(CourseStatus, name="course_status_enum"),
        nullable=False,
        default=CourseStatus.metadata_partial,
        server_default=CourseStatus.metadata_partial.value,
    )
    visibility: Mapped[CourseVisibility] = mapped_column(
        Enum(CourseVisibility, name="course_visibility_enum"),
        nullable=False,
        default=CourseVisibility.public,
        server_default=CourseVisibility.public.value,
    )
    cover_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hero_badge: Mapped[str | None] = mapped_column(String(255), nullable=True)
    primary_subject: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    overview: Mapped["CourseOverview | None"] = relationship(
        "CourseOverview",
        back_populates="course",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select",
    )
    sections: Mapped[list["CourseSection"]] = relationship(
        "CourseSection",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="select",
    )
    learning_units: Mapped[list["LearningUnit"]] = relationship(
        "LearningUnit",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="select",
    )
    assets: Mapped[list["CourseAsset"]] = relationship(
        "CourseAsset",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="select",
    )
    recommendations: Mapped[list["CourseRecommendation"]] = relationship(
        "CourseRecommendation",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="select",
    )
    progress_records: Mapped[list["LearningProgressRecord"]] = relationship(
        "LearningProgressRecord",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="select",
    )
    legacy_lecture_mappings: Mapped[list["LegacyLectureMapping"]] = relationship(
        "LegacyLectureMapping",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        Index("ix_courses_visibility_sort", "visibility", "sort_order"),
        Index("ix_courses_status", "status"),
    )


class CourseOverview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "course_overviews"

    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    headline: Mapped[str] = mapped_column(String(255), nullable=False)
    subheadline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    learning_outcomes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    prerequisites_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_duration_text: Mapped[str | None] = mapped_column(String(120), nullable=True)
    structure_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cta_label: Mapped[str | None] = mapped_column(String(120), nullable=True)

    course: Mapped["Course"] = relationship("Course", back_populates="overview", lazy="select")


class CourseSection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "course_sections"

    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("course_sections.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[CourseSectionKind] = mapped_column(
        Enum(CourseSectionKind, name="course_section_kind_enum"),
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_entry_section: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    course: Mapped["Course"] = relationship("Course", back_populates="sections", lazy="select")
    parent_section: Mapped["CourseSection | None"] = relationship(
        "CourseSection",
        remote_side="CourseSection.id",
        back_populates="child_sections",
        lazy="select",
    )
    child_sections: Mapped[list["CourseSection"]] = relationship(
        "CourseSection",
        back_populates="parent_section",
        lazy="select",
    )
    learning_units: Mapped[list["LearningUnit"]] = relationship(
        "LearningUnit",
        back_populates="section",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        Index("ix_course_sections_course_sort", "course_id", "sort_order"),
        Index("ix_course_sections_parent", "parent_section_id"),
    )


class LearningUnit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_units"

    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("course_sections.id", ondelete="CASCADE"),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_type: Mapped[LearningUnitType] = mapped_column(
        Enum(LearningUnitType, name="learning_unit_type_enum"),
        nullable=False,
    )
    status: Mapped[LearningUnitStatus] = mapped_column(
        Enum(LearningUnitStatus, name="learning_unit_status_enum"),
        nullable=False,
        default=LearningUnitStatus.metadata_partial,
        server_default=LearningUnitStatus.metadata_partial.value,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    content_source_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    content_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entry_mode: Mapped[LearningUnitEntryMode] = mapped_column(
        Enum(LearningUnitEntryMode, name="learning_unit_entry_mode_enum"),
        nullable=False,
        default=LearningUnitEntryMode.hybrid,
        server_default=LearningUnitEntryMode.hybrid.value,
    )

    course: Mapped["Course"] = relationship("Course", back_populates="learning_units", lazy="select")
    section: Mapped["CourseSection"] = relationship(
        "CourseSection",
        back_populates="learning_units",
        lazy="select",
    )
    assets: Mapped[list["CourseAsset"]] = relationship(
        "CourseAsset",
        back_populates="learning_unit",
        cascade="all, delete-orphan",
        lazy="select",
    )
    tutor_context_bindings: Mapped[list["TutorContextBinding"]] = relationship(
        "TutorContextBinding",
        back_populates="learning_unit",
        cascade="all, delete-orphan",
        lazy="select",
    )
    progress_records: Mapped[list["LearningProgressRecord"]] = relationship(
        "LearningProgressRecord",
        back_populates="learning_unit",
        cascade="all, delete-orphan",
        lazy="select",
    )
    legacy_lecture_mappings: Mapped[list["LegacyLectureMapping"]] = relationship(
        "LegacyLectureMapping",
        back_populates="learning_unit",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        UniqueConstraint("course_id", "slug", name="uq_learning_units_course_slug"),
        Index("ix_learning_units_course_section_sort", "course_id", "section_id", "sort_order"),
        Index("ix_learning_units_status", "status"),
    )


class CourseAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "course_assets"

    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    learning_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_units.id", ondelete="SET NULL"),
        nullable=True,
    )
    asset_type: Mapped[CourseAssetType] = mapped_column(
        Enum(CourseAssetType, name="course_asset_type_enum"),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    delivery_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    availability_status: Mapped[CourseAssetAvailabilityStatus] = mapped_column(
        Enum(CourseAssetAvailabilityStatus, name="course_asset_availability_status_enum"),
        nullable=False,
        default=CourseAssetAvailabilityStatus.processing,
        server_default=CourseAssetAvailabilityStatus.processing.value,
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    course: Mapped["Course"] = relationship("Course", back_populates="assets", lazy="select")
    learning_unit: Mapped["LearningUnit | None"] = relationship(
        "LearningUnit",
        back_populates="assets",
        lazy="select",
    )

    __table_args__ = (
        Index("ix_course_assets_course_asset_type", "course_id", "asset_type"),
        Index("ix_course_assets_learning_unit", "learning_unit_id"),
    )


class LearnerAssessmentProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learner_assessment_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    is_onboarded: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    skill_test_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assessment_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    recommendation_ready: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    user: Mapped["User"] = relationship("User", lazy="select")  # type: ignore[name-defined]


class CourseRecommendation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "course_recommendations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship("User", lazy="select")  # type: ignore[name-defined]
    course: Mapped["Course"] = relationship("Course", back_populates="recommendations", lazy="select")

    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_course_recommendations_user_course"),
        UniqueConstraint("user_id", "rank", name="uq_course_recommendations_user_rank"),
        Index("ix_course_recommendations_user_rank", "user_id", "rank"),
    )


class LearningProgressRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "learning_progress_records"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    learning_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_units.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[LearningProgressStatus] = mapped_column(
        Enum(LearningProgressStatus, name="learning_progress_status_enum"),
        nullable=False,
        default=LearningProgressStatus.not_started,
        server_default=LearningProgressStatus.not_started.value,
    )
    last_position_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", lazy="select")  # type: ignore[name-defined]
    course: Mapped["Course"] = relationship("Course", back_populates="progress_records", lazy="select")
    learning_unit: Mapped["LearningUnit"] = relationship(
        "LearningUnit",
        back_populates="progress_records",
        lazy="select",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "learning_unit_id",
            name="uq_learning_progress_records_user_unit",
        ),
        Index("ix_learning_progress_records_user_course", "user_id", "course_id"),
    )


class TutorContextBinding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tutor_context_bindings"

    learning_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_units.id", ondelete="CASCADE"),
        nullable=False,
    )
    context_type: Mapped[str] = mapped_column(String(120), nullable=False)
    source_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    context_window_rule: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    learning_unit: Mapped["LearningUnit"] = relationship(
        "LearningUnit",
        back_populates="tutor_context_bindings",
        lazy="select",
    )

    __table_args__ = (Index("ix_tutor_context_bindings_unit_active", "learning_unit_id", "is_active"),)


class LegacyLectureMapping(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "legacy_lecture_mappings"

    legacy_lecture_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("lectures.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    learning_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_units.id", ondelete="CASCADE"),
        nullable=False,
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    migration_state: Mapped[LegacyLectureMigrationState] = mapped_column(
        Enum(LegacyLectureMigrationState, name="legacy_lecture_migration_state_enum"),
        nullable=False,
        default=LegacyLectureMigrationState.pending,
        server_default=LegacyLectureMigrationState.pending.value,
    )

    learning_unit: Mapped["LearningUnit"] = relationship(
        "LearningUnit",
        back_populates="legacy_lecture_mappings",
        lazy="select",
    )
    course: Mapped["Course"] = relationship(
        "Course",
        back_populates="legacy_lecture_mappings",
        lazy="select",
    )
    lecture: Mapped["Lecture"] = relationship("Lecture", lazy="select")  # type: ignore[name-defined]

    __table_args__ = (
        UniqueConstraint("learning_unit_id", name="uq_legacy_lecture_mappings_learning_unit"),
        Index("ix_legacy_lecture_mappings_course_state", "course_id", "migration_state"),
    )
