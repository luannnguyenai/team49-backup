"""
models/content.py
-----------------
Curriculum content models: Module, Topic, KnowledgeComponent, Question.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
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

from src.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BloomLevel(str, enum.Enum):
    remember = "remember"
    understand = "understand"
    apply = "apply"
    analyze = "analyze"


class DifficultyBucket(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class QuestionStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    calibrated = "calibrated"
    retired = "retired"


class CorrectAnswer(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

class Module(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Top-level curriculum module (e.g. 'Deep Learning Foundations')."""

    __tablename__ = "modules"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Display / learning order"
    )
    prerequisite_module_ids: Mapped[list | None] = mapped_column(
        JSON, nullable=True, comment="JSON array of Module UUIDs"
    )

    # Relationships
    topics: Mapped[list["Topic"]] = relationship(
        "Topic", back_populates="module", lazy="select"
    )
    questions: Mapped[list["Question"]] = relationship(
        "Question", back_populates="module", lazy="select"
    )

    __table_args__ = (
        Index("ix_modules_order_index", "order_index"),
    )


# ---------------------------------------------------------------------------
# Topic
# ---------------------------------------------------------------------------

class Topic(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Sub-topic within a Module."""

    __tablename__ = "topics"

    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    prerequisite_topic_ids: Mapped[list | None] = mapped_column(
        JSON, nullable=True, comment="JSON array of Topic UUIDs"
    )
    estimated_hours_beginner: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_hours_intermediate: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_hours_review: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    module: Mapped["Module"] = relationship("Module", back_populates="topics")
    knowledge_components: Mapped[list["KnowledgeComponent"]] = relationship(
        "KnowledgeComponent", back_populates="topic", lazy="select"
    )
    questions: Mapped[list["Question"]] = relationship(
        "Question", back_populates="topic", lazy="select"
    )

    __table_args__ = (
        Index("ix_topics_module_id", "module_id"),
        Index("ix_topics_module_order", "module_id", "order_index"),
    )


# ---------------------------------------------------------------------------
# KnowledgeComponent
# ---------------------------------------------------------------------------

class KnowledgeComponent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Atomic knowledge component (KC) within a Topic."""

    __tablename__ = "knowledge_components"

    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    topic: Mapped["Topic"] = relationship(
        "Topic", back_populates="knowledge_components"
    )

    __table_args__ = (
        Index("ix_kc_topic_id", "topic_id"),
    )


# ---------------------------------------------------------------------------
# Question
# ---------------------------------------------------------------------------

class Question(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single multiple-choice question item."""

    __tablename__ = "questions"

    # Business key
    item_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True,
        comment="Human-readable unique identifier, e.g. ITEM-001-00001"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[QuestionStatus] = mapped_column(
        Enum(QuestionStatus, name="question_status_enum"),
        nullable=False,
        default=QuestionStatus.draft,
    )

    # Content FK
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False
    )
    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("modules.id", ondelete="RESTRICT"), nullable=False
    )

    # Taxonomy
    bloom_level: Mapped[BloomLevel] = mapped_column(
        Enum(BloomLevel, name="bloom_level_enum"), nullable=False
    )
    difficulty_bucket: Mapped[DifficultyBucket] = mapped_column(
        Enum(DifficultyBucket, name="difficulty_bucket_enum"), nullable=False
    )

    # Stem
    stem_text: Mapped[str] = mapped_column(Text, nullable=False)
    stem_media: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Optional media metadata (url, type, alt)"
    )

    # Options
    option_a: Mapped[str] = mapped_column(Text, nullable=False)
    option_b: Mapped[str] = mapped_column(Text, nullable=False)
    option_c: Mapped[str] = mapped_column(Text, nullable=False)
    option_d: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[CorrectAnswer] = mapped_column(
        Enum(CorrectAnswer, name="correct_answer_enum"), nullable=False
    )

    # Distractors
    distractor_a_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    distractor_b_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    distractor_c_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    distractor_d_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    misconception_a_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    misconception_b_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    misconception_c_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    misconception_d_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Explanation
    explanation_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_expected_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    usage_context: Mapped[list | None] = mapped_column(
        JSON, nullable=True, comment="JSON array: assessment | quiz | module_test"
    )
    kc_ids: Mapped[list | None] = mapped_column(
        JSON, nullable=True, comment="JSON array of KnowledgeComponent UUIDs"
    )

    # IRT parameters
    irt_difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    irt_discrimination: Mapped[float | None] = mapped_column(Float, nullable=True)
    irt_guessing: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_responses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    topic: Mapped["Topic"] = relationship("Topic", back_populates="questions")
    module: Mapped["Module"] = relationship("Module", back_populates="questions")
    interactions: Mapped[list["Interaction"]] = relationship(  # type: ignore[name-defined]
        "Interaction", back_populates="question", lazy="select"
    )

    __table_args__ = (
        Index("ix_questions_topic_id", "topic_id"),
        Index("ix_questions_module_id", "module_id"),
        Index("ix_questions_status", "status"),
        Index("ix_questions_bloom_difficulty", "bloom_level", "difficulty_bucket"),
        Index("ix_questions_item_id", "item_id"),
    )
