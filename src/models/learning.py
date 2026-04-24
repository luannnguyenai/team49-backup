"""
models/learning.py
------------------
Canonical learning runtime tables plus compatibility session/interaction IDs.
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
    from src.models.user import User


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
        nullable=True,
        comment="Archived legacy compatibility field; no active FK/runtime reads.",
    )
    module_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Archived legacy compatibility field; no active FK/runtime reads.",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    canonical_phase: Mapped[str | None] = mapped_column(String(80), nullable=True)
    canonical_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_units.id", ondelete="SET NULL"),
        nullable=True,
    )
    canonical_section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("course_sections.id", ondelete="SET NULL"),
        nullable=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="sessions")  # type: ignore[name-defined]
    interactions: Mapped[list["Interaction"]] = relationship(
        "Interaction", back_populates="session", lazy="select"
    )

    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_user_type", "user_id", "session_type"),
        Index("ix_sessions_canonical_unit", "canonical_unit_id"),
        Index("ix_sessions_canonical_section", "canonical_section_id"),
        Index("ix_sessions_started_at", "started_at"),
        CheckConstraint("score_percent >= 0 AND score_percent <= 100", name="ck_score_range"),
    )


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
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Archived legacy compatibility field; canonical_item_id is authoritative.",
    )
    canonical_item_id: Mapped[str | None] = mapped_column(
        String(180),
        ForeignKey("question_bank.item_id", ondelete="RESTRICT"),
        nullable=True,
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

    user: Mapped["User"] = relationship("User", back_populates="interactions")  # type: ignore[name-defined]
    session: Mapped["Session"] = relationship("Session", back_populates="interactions")

    __table_args__ = (
        Index("ix_interactions_user_id", "user_id"),
        Index("ix_interactions_session_id", "session_id"),
        Index("ix_interactions_question_id", "question_id"),
        Index("ix_interactions_canonical_item_id", "canonical_item_id"),
        Index("ix_interactions_user_timestamp", "user_id", "timestamp"),
        Index("ix_interactions_global_seq", "user_id", "global_sequence_position"),
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

    user: Mapped["User"] = relationship("User", back_populates="learner_mastery_kp", lazy="select")  # type: ignore[name-defined]

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

    user: Mapped["User"] = relationship("User", back_populates="goal_preferences", lazy="select")  # type: ignore[name-defined]

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

    user: Mapped["User"] = relationship("User", back_populates="waived_units", lazy="select")  # type: ignore[name-defined]

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


class PlanHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Planner run snapshot for audit, replay, and diffing."""

    __tablename__ = "plan_history"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plan_history.id", ondelete="SET NULL"),
        nullable=True,
    )
    trigger: Mapped[str] = mapped_column(String(80), nullable=False)
    recommended_path_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    goal_snapshot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    weights_used_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="plan_histories", lazy="select")  # type: ignore[name-defined]
    parent_plan: Mapped["PlanHistory | None"] = relationship(
        "PlanHistory",
        remote_side="PlanHistory.id",
        lazy="select",
    )

    __table_args__ = (
        Index("ix_plan_history_user", "user_id"),
        Index("ix_plan_history_parent", "parent_plan_id"),
        Index("ix_plan_history_trigger", "trigger"),
    )


class RationaleLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-unit rationale emitted by planner ranking logic."""

    __tablename__ = "rationale_log"

    plan_history_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plan_history.id", ondelete="CASCADE"),
        nullable=False,
    )
    learning_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_units.id", ondelete="SET NULL"),
        nullable=True,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(80), nullable=False)
    term_breakdown_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rationale_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_rationale_log_plan", "plan_history_id"),
        Index("ix_rationale_log_unit", "learning_unit_id"),
        Index("ix_rationale_log_plan_rank", "plan_history_id", "rank"),
    )


class PlannerSessionState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Planner-local session counters and sticky state across replans."""

    __tablename__ = "planner_session_state"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[str] = mapped_column(String(120), nullable=False)
    last_plan_history_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plan_history.id", ondelete="SET NULL"),
        nullable=True,
    )
    bridge_chain_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consecutive_bridge_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_units.id", ondelete="SET NULL"),
        nullable=True,
    )
    current_stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    current_progress: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_activity: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    state_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="planner_session_states", lazy="select")  # type: ignore[name-defined]

    __table_args__ = (
        UniqueConstraint("user_id", "session_id", name="uq_planner_session_state_user_session"),
        Index("ix_planner_session_state_user", "user_id"),
        Index("ix_planner_session_state_last_plan", "last_plan_history_id"),
        Index("ix_planner_session_state_current_unit", "current_unit_id"),
        Index("ix_planner_session_state_last_activity", "last_activity"),
        CheckConstraint(
            "bridge_chain_depth >= 0",
            name="ck_planner_session_state_bridge_depth_nonnegative",
        ),
        CheckConstraint(
            "consecutive_bridge_count >= 0",
            name="ck_planner_session_state_consecutive_bridge_nonnegative",
        ),
        CheckConstraint(
            "current_stage IS NULL OR current_stage IN ('watching', 'quiz_in_progress', 'post_quiz', 'between_units')",
            name="ck_planner_session_state_current_stage",
        ),
    )
