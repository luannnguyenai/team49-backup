"""
schemas/content.py
------------------
Pydantic v2 schemas for Module, Topic, KnowledgeComponent, and Question.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.models.content import (
    BloomLevel,
    CorrectAnswer,
    DifficultyBucket,
    QuestionStatus,
)

# ===========================================================================
# Module
# ===========================================================================


class ModuleBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    order_index: int = Field(ge=0)
    prerequisite_module_ids: list[uuid.UUID] | None = None


class ModuleCreate(ModuleBase):
    pass


class ModuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    order_index: int | None = Field(default=None, ge=0)
    prerequisite_module_ids: list[uuid.UUID] | None = None


class ModuleResponse(ModuleBase):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ===========================================================================
# Topic
# ===========================================================================


class TopicBase(BaseModel):
    module_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    order_index: int = Field(ge=0)
    prerequisite_topic_ids: list[uuid.UUID] | None = None
    estimated_hours_beginner: float | None = Field(default=None, gt=0)
    estimated_hours_intermediate: float | None = Field(default=None, gt=0)
    estimated_hours_review: float | None = Field(default=None, gt=0)


class TopicCreate(TopicBase):
    pass


class TopicUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    order_index: int | None = Field(default=None, ge=0)
    prerequisite_topic_ids: list[uuid.UUID] | None = None
    estimated_hours_beginner: float | None = None
    estimated_hours_intermediate: float | None = None
    estimated_hours_review: float | None = None


class TopicResponse(TopicBase):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ===========================================================================
# KnowledgeComponent
# ===========================================================================


class KCBase(BaseModel):
    topic_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class KCCreate(KCBase):
    pass


class KCUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class KCResponse(KCBase):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ===========================================================================
# Question
# ===========================================================================


class StemMedia(BaseModel):
    """Optional media attached to a question stem."""

    url: str
    media_type: str = Field(description="e.g. image/png, video/mp4")
    alt_text: str | None = None


class QuestionBase(BaseModel):
    item_id: str = Field(
        pattern=r"^ITEM-[A-Z0-9]{2,8}-\d{5}$",
        description="Format: ITEM-{MODULE_CODE}-{5_DIGITS}, e.g. ITEM-PYB-00001",
    )
    version: int = Field(default=1, ge=1)
    status: QuestionStatus = QuestionStatus.draft

    topic_id: uuid.UUID
    module_id: uuid.UUID

    bloom_level: BloomLevel
    difficulty_bucket: DifficultyBucket

    stem_text: str
    stem_media: StemMedia | None = None

    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: CorrectAnswer

    distractor_a_rationale: str | None = None
    distractor_b_rationale: str | None = None
    distractor_c_rationale: str | None = None
    distractor_d_rationale: str | None = None

    misconception_a_id: str | None = None
    misconception_b_id: str | None = None
    misconception_c_id: str | None = None
    misconception_d_id: str | None = None

    explanation_text: str | None = None
    time_expected_seconds: int | None = Field(default=None, gt=0)

    usage_context: list[str] | None = None
    kc_ids: list[uuid.UUID] | None = None

    irt_difficulty: float | None = None
    irt_discrimination: float | None = None
    irt_guessing: float | None = Field(default=None, ge=0, le=1)


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    """All fields optional for PATCH."""

    version: int | None = Field(default=None, ge=1)
    status: QuestionStatus | None = None
    bloom_level: BloomLevel | None = None
    difficulty_bucket: DifficultyBucket | None = None
    stem_text: str | None = None
    stem_media: StemMedia | None = None
    option_a: str | None = None
    option_b: str | None = None
    option_c: str | None = None
    option_d: str | None = None
    correct_answer: CorrectAnswer | None = None
    distractor_a_rationale: str | None = None
    distractor_b_rationale: str | None = None
    distractor_c_rationale: str | None = None
    distractor_d_rationale: str | None = None
    misconception_a_id: str | None = None
    misconception_b_id: str | None = None
    misconception_c_id: str | None = None
    misconception_d_id: str | None = None
    explanation_text: str | None = None
    time_expected_seconds: int | None = None
    usage_context: list[str] | None = None
    kc_ids: list[uuid.UUID] | None = None
    irt_difficulty: float | None = None
    irt_discrimination: float | None = None
    irt_guessing: float | None = None


class QuestionResponse(QuestionBase):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    total_responses: int
    created_at: datetime
    updated_at: datetime


class QuestionSummary(BaseModel):
    """Lightweight view used in session/interaction responses."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    item_id: str
    bloom_level: BloomLevel
    difficulty_bucket: DifficultyBucket
    status: QuestionStatus


# ===========================================================================
# Canonical content route response schemas
# ===========================================================================


class LearningUnitSelectionItem(BaseModel):
    """Learning-unit row used by canonical section detail and selection UIs."""

    id: uuid.UUID
    canonical_unit_id: str | None = None
    title: str
    description: str | None
    order_index: int
    estimated_hours_beginner: float | None
    estimated_hours_intermediate: float | None


class CourseSectionListItem(BaseModel):
    """One row in GET /api/course-sections."""

    id: uuid.UUID
    title: str
    description: str | None
    order_index: int
    prerequisite_section_ids: list[uuid.UUID] | None
    learning_units_count: int


class CourseSectionDetailResponse(CourseSectionListItem):
    """GET /api/course-sections/{id} — section with ordered learning units."""

    learning_units: list[LearningUnitSelectionItem]
    created_at: datetime
    updated_at: datetime


class LearningUnitContentResponse(BaseModel):
    """GET /api/learning-units/{id}/content — canonical learning material."""

    learning_unit_id: uuid.UUID
    title: str
    section_id: uuid.UUID
    section_title: str
    content_markdown: str | None
    video_url: str | None
