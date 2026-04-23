"""
schemas/assessment.py
---------------------
Pydantic v2 schemas for the Assessment Engine API.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.models.content import BloomLevel, DifficultyBucket
from src.models.learning import MasteryLevel, SelectedAnswer

# ===========================================================================
# POST /api/assessment/start
# ===========================================================================


class AssessmentStartRequest(BaseModel):
    topic_ids: list[uuid.UUID] = Field(
        default_factory=list,
        max_length=50,
        description="Legacy topics to include in this assessment.",
    )
    canonical_unit_ids: list[str] | None = Field(
        default=None,
        max_length=50,
        description="Canonical unit IDs to use when canonical question selection is enabled.",
    )
    phase: str = Field(
        default="placement",
        description="Canonical assessment phase used with item_phase_map.",
    )


class QuestionForAssessment(BaseModel):
    """Question payload sent to the client — correct_answer is intentionally omitted."""

    model_config = {"from_attributes": True}

    id: uuid.UUID | None = None
    item_id: str
    canonical_item_id: str | None = None
    canonical_unit_id: str | None = None
    topic_id: uuid.UUID | None = None
    bloom_level: BloomLevel | None = None
    difficulty_bucket: DifficultyBucket | None = None
    stem_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    time_expected_seconds: int | None


class AssessmentStartResponse(BaseModel):
    session_id: uuid.UUID
    total_questions: int
    questions: list[QuestionForAssessment]


# ===========================================================================
# POST /api/assessment/{session_id}/submit
# ===========================================================================


class AnswerInput(BaseModel):
    question_id: uuid.UUID | None = None
    canonical_item_id: str | None = None
    selected_answer: SelectedAnswer
    response_time_ms: int | None = Field(default=None, ge=0)


class AssessmentSubmitRequest(BaseModel):
    answers: list[AnswerInput] = Field(min_length=1)


# ===========================================================================
# Shared result schemas
# ===========================================================================


class TopicResult(BaseModel):
    topic_id: uuid.UUID
    topic_name: str
    score_percent: float
    mastery_level: MasteryLevel
    bloom_breakdown: dict[str, str]  # e.g. {"remember": "1/1", "analyze": "1/2"}
    weak_kcs: list[str]  # KC names where the user made errors
    misconceptions_detected: list[str]  # misconception IDs from wrong-answer mapping
    theta_estimate: float = Field(
        default=0.0,
        description=(
            "2PL IRT ability estimate (θ̂) for this topic on a logit scale. "
            "−3 = very low ability, 0 = average, +3 = very high ability."
        ),
    )


class AssessmentResultResponse(BaseModel):
    session_id: uuid.UUID
    completed_at: datetime
    overall_score_percent: float
    topic_results: list[TopicResult]
