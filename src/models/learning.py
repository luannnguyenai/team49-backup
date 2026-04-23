"""
models/learning.py
------------------
Learning activity models: Session, Interaction, MasteryScore, LearningPath.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
    from src.models.content import KnowledgeComponent, Module, Question, Topic
    from src.models.user import User

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SessionType(enum.StrEnum):
    assessment = "assessment"
    quiz = "quiz"
    module_test = "module_test"
    practice = "practice"


class MasteryLevel(enum.StrEnum):
    not_started = "not_started"
    novice = "novice"
    developing = "developing"
    proficient = "proficient"
    mastered = "mastered"


class RecentTrend(enum.StrEnum):
    improving = "improving"
    stable = "stable"
    declining = "declining"


class PathAction(enum.StrEnum):
    skip = "skip"
    quick_review = "quick_review"
    standard_learn = "standard_learn"
    deep_practice = "deep_practice"
    remediate = "remediate"


class PathStatus(enum.StrEnum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    skipped = "skipped"


class SelectedAnswer(enum.StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


class Session(UUIDPrimaryKeyMixin, Base):
    """A single learning or assessment session."""

    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_type: Mapped[SessionType] = mapped_column(
        Enum(SessionType, name="session_type_enum"), nullable=False
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="SET NULL"),
        nullable=True,
    )
    module_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("modules.id", ondelete="SET NULL"),
        nullable=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")  # type: ignore[name-defined]
    topic: Mapped["Topic | None"] = relationship("Topic", lazy="select")  # type: ignore[name-defined]
    module: Mapped["Module | None"] = relationship("Module", lazy="select")  # type: ignore[name-defined]
    interactions: Mapped[list["Interaction"]] = relationship(
        "Interaction", back_populates="session", lazy="select"
    )

    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_user_type", "user_id", "session_type"),
        Index("ix_sessions_started_at", "started_at"),
        CheckConstraint("score_percent >= 0 AND score_percent <= 100", name="ck_score_range"),
    )


# ---------------------------------------------------------------------------
# Interaction
# ---------------------------------------------------------------------------


class Interaction(UUIDPrimaryKeyMixin, Base):
    """Single question-response event within a session."""

    __tablename__ = "interactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="RESTRICT"),
        nullable=False,
    )

    sequence_position: Mapped[int] = mapped_column(Integer, nullable=False)
    global_sequence_position: Mapped[int] = mapped_column(Integer, nullable=False)

    selected_answer: Mapped["SelectedAnswer | None"] = mapped_column(
        Enum(SelectedAnswer, name="selected_answer_enum"), nullable=True
    )
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    changed_answer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hint_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    explanation_viewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="interactions")  # type: ignore[name-defined]
    session: Mapped["Session"] = relationship("Session", back_populates="interactions")
    question: Mapped["Question"] = relationship("Question", back_populates="interactions")  # type: ignore[name-defined]

    __table_args__ = (
        Index("ix_interactions_user_id", "user_id"),
        Index("ix_interactions_session_id", "session_id"),
        Index("ix_interactions_question_id", "question_id"),
        Index("ix_interactions_user_timestamp", "user_id", "timestamp"),
        Index("ix_interactions_global_seq", "user_id", "global_sequence_position"),
    )


# ---------------------------------------------------------------------------
# MasteryScore
# ---------------------------------------------------------------------------


class MasteryScore(UUIDPrimaryKeyMixin, Base):
    """Tracks the estimated mastery probability for a user × topic (× optional KC) pair."""

    __tablename__ = "mastery_scores"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
    )
    kc_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_components.id", ondelete="SET NULL"),
        nullable=True,
        comment="NULL means score is at topic grain, not KC grain",
    )

    mastery_probability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    mastery_level: Mapped[MasteryLevel] = mapped_column(
        Enum(MasteryLevel, name="mastery_level_enum"),
        nullable=False,
        default=MasteryLevel.not_started,
    )
    bloom_max_achieved: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Highest Bloom level demonstrated (remember → analyze)"
    )
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recent_trend: Mapped[RecentTrend | None] = mapped_column(
        Enum(RecentTrend, name="recent_trend_enum"), nullable=True
    )
    last_practiced: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="mastery_scores")  # type: ignore[name-defined]
    topic: Mapped["Topic"] = relationship("Topic", lazy="select")  # type: ignore[name-defined]
    knowledge_component: Mapped["KnowledgeComponent | None"] = relationship(  # type: ignore[name-defined]
        "KnowledgeComponent", lazy="select"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", "kc_id", name="uq_mastery_user_topic_kc"),
        Index("ix_mastery_user_id", "user_id"),
        Index("ix_mastery_user_topic", "user_id", "topic_id"),
        CheckConstraint(
            "mastery_probability >= 0 AND mastery_probability <= 1",
            name="ck_mastery_probability_range",
        ),
    )


# ---------------------------------------------------------------------------
# MasteryHistory (audit trail for every mastery change)
# ---------------------------------------------------------------------------


class MasteryHistory(UUIDPrimaryKeyMixin, Base):
    """Append-only audit log of mastery changes — one row per upsert."""

    __tablename__ = "mastery_history"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    kc_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_components.id", ondelete="SET NULL"), nullable=True
    )
    old_mastery_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    new_mastery_probability: Mapped[float] = mapped_column(Float, nullable=False)
    old_mastery_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_mastery_level: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    trigger_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_mh_user_topic", "user_id", "topic_id"),
        Index("ix_mh_changed_at", "changed_at"),
    )


# ---------------------------------------------------------------------------
# LearningPath
# ---------------------------------------------------------------------------


class LearningPath(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """AI-generated personalised learning plan entry for a user."""

    __tablename__ = "learning_paths"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[PathAction] = mapped_column(
        Enum(PathAction, name="path_action_enum"), nullable=False
    )
    estimated_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    order_index: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Step order within the full path"
    )
    week_number: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Suggested calendar week (1-based)"
    )
    status: Mapped[PathStatus] = mapped_column(
        Enum(PathStatus, name="path_status_enum"),
        nullable=False,
        default=PathStatus.pending,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="learning_paths")  # type: ignore[name-defined]
    topic: Mapped["Topic"] = relationship("Topic", lazy="select")  # type: ignore[name-defined]

    __table_args__ = (
        Index("ix_lp_user_id", "user_id"),
        Index("ix_lp_user_status", "user_id", "status"),
        Index("ix_lp_user_order", "user_id", "order_index"),
    )


class LearnerMasteryKP(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Posterior-like mastery state for a user × canonical KP pair."""

    __tablename__ = "learner_mastery_kp"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    kp_id: Mapped[str] = mapped_column(String(160), nullable=False)
    theta_mu: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    theta_sigma: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    mastery_mean_cached: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    n_items_observed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_by: Mapped[str | None] = mapped_column(String(80), nullable=True)

    user: Mapped["User"] = relationship("User", lazy="select")  # type: ignore[name-defined]

    __table_args__ = (
        UniqueConstraint("user_id", "kp_id", name="uq_learner_mastery_kp_user_kp"),
        Index("ix_learner_mastery_kp_user", "user_id"),
        Index("ix_learner_mastery_kp_kp", "kp_id"),
        CheckConstraint("theta_sigma >= 0", name="ck_learner_mastery_kp_sigma_nonnegative"),
        CheckConstraint(
            "mastery_mean_cached >= 0 AND mastery_mean_cached <= 1",
            name="ck_learner_mastery_kp_mastery_range",
        ),
        CheckConstraint(
            "n_items_observed >= 0",
            name="ck_learner_mastery_kp_items_nonnegative",
        ),
    )


class GoalPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persistent learner goal profile for planner-scoped decisions."""

    __tablename__ = "goal_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    goal_weights_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    selected_course_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    goal_embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    goal_embedding_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    derived_from_course_set_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", lazy="select")  # type: ignore[name-defined]

    __table_args__ = (
        Index("ix_goal_preferences_user", "user_id"),
        Index("ix_goal_preferences_hash", "derived_from_course_set_hash"),
    )


class WaivedUnit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Audit record for units explicitly waived/skipped by planner logic."""

    __tablename__ = "waived_units"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    learning_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_units.id", ondelete="CASCADE"),
        nullable=False,
    )
    evidence_items: Mapped[list | None] = mapped_column(JSON, nullable=True)
    mastery_lcb_at_waive: Mapped[float | None] = mapped_column(Float, nullable=True)
    skip_quiz_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped["User"] = relationship("User", lazy="select")  # type: ignore[name-defined]

    __table_args__ = (
        UniqueConstraint("user_id", "learning_unit_id", name="uq_waived_units_user_unit"),
        Index("ix_waived_units_user", "user_id"),
        Index("ix_waived_units_learning_unit", "learning_unit_id"),
        CheckConstraint(
            "mastery_lcb_at_waive IS NULL OR (mastery_lcb_at_waive >= 0 AND mastery_lcb_at_waive <= 1)",
            name="ck_waived_units_mastery_lcb_range",
        ),
        CheckConstraint(
            "skip_quiz_score IS NULL OR (skip_quiz_score >= 0 AND skip_quiz_score <= 100)",
            name="ck_waived_units_skip_quiz_score_range",
        ),
    )
