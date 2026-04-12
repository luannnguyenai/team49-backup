"""
schemas/learning.py
-------------------
Pydantic v2 schemas for Session, Interaction, MasteryScore, LearningPath.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from src.models.learning import (
    MasteryLevel,
    PathAction,
    PathStatus,
    RecentTrend,
    SelectedAnswer,
    SessionType,
)

# ===========================================================================
# Session
# ===========================================================================


class SessionCreate(BaseModel):
    session_type: SessionType
    topic_id: uuid.UUID | None = None
    module_id: uuid.UUID | None = None


class SessionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    session_type: SessionType
    topic_id: uuid.UUID | None
    module_id: uuid.UUID | None
    started_at: datetime
    completed_at: datetime | None
    total_questions: int
    correct_count: int
    score_percent: float | None


class SessionComplete(BaseModel):
    """PATCH /sessions/{id}/complete — finalise a session."""

    completed_at: datetime
    total_questions: int = Field(ge=0)
    correct_count: int = Field(ge=0)
    score_percent: float | None = Field(default=None, ge=0, le=100)

    @field_validator("correct_count")
    @classmethod
    def correct_le_total(cls, v: int, info) -> int:
        total = info.data.get("total_questions")
        if total is not None and v > total:
            raise ValueError("correct_count cannot exceed total_questions")
        return v


# ===========================================================================
# Interaction
# ===========================================================================


class InteractionCreate(BaseModel):
    question_id: uuid.UUID
    sequence_position: int = Field(ge=1)
    global_sequence_position: int = Field(ge=1)
    selected_answer: SelectedAnswer | None = None
    is_correct: bool
    response_time_ms: int | None = Field(default=None, ge=0)
    changed_answer: bool = False
    hint_used: bool = False
    explanation_viewed: bool = False


class InteractionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    session_id: uuid.UUID
    question_id: uuid.UUID
    sequence_position: int
    global_sequence_position: int
    selected_answer: SelectedAnswer | None
    is_correct: bool
    response_time_ms: int | None
    changed_answer: bool
    hint_used: bool
    explanation_viewed: bool
    timestamp: datetime


# ===========================================================================
# MasteryScore
# ===========================================================================


class MasteryScoreResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    topic_id: uuid.UUID
    kc_id: uuid.UUID | None
    mastery_probability: float
    mastery_level: MasteryLevel
    bloom_max_achieved: str | None
    evidence_count: int
    recent_trend: RecentTrend | None
    last_practiced: datetime | None
    updated_at: datetime


class MasteryScoreUpdate(BaseModel):
    """Used internally by the scoring pipeline."""

    mastery_probability: float = Field(ge=0, le=1)
    mastery_level: MasteryLevel
    bloom_max_achieved: str | None = None
    evidence_count: int = Field(ge=0)
    recent_trend: RecentTrend | None = None


# ===========================================================================
# LearningPath
# ===========================================================================


class LearningPathCreate(BaseModel):
    topic_id: uuid.UUID
    action: PathAction
    estimated_hours: float | None = Field(default=None, gt=0)
    order_index: int = Field(ge=0)
    week_number: int | None = Field(default=None, ge=1)


class LearningPathUpdate(BaseModel):
    action: PathAction | None = None
    estimated_hours: float | None = None
    order_index: int | None = Field(default=None, ge=0)
    week_number: int | None = None
    status: PathStatus | None = None


class LearningPathResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    topic_id: uuid.UUID
    action: PathAction
    estimated_hours: float | None
    order_index: int
    week_number: int | None
    status: PathStatus
    created_at: datetime
    updated_at: datetime


class LearningPathBatchCreate(BaseModel):
    """POST /users/{id}/learning-path — replace the entire path."""

    items: list[LearningPathCreate] = Field(min_length=1)
