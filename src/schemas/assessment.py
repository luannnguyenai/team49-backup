"""
schemas/assessment.py
---------------------
Pydantic v2 schemas for the Assessment Engine API.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field

from src.models.content import BloomLevel, DifficultyBucket
from src.models.learning import MasteryLevel, SelectedAnswer

# ===========================================================================
# POST /api/assessment/start
# ===========================================================================


class AssessmentStartRequest(BaseModel):
    learning_unit_ids: list[uuid.UUID] = Field(
        default_factory=list,
        validation_alias=AliasChoices("learning_unit_ids", "topic_ids"),
        description="Product learning units to include in this assessment.",
    )
    canonical_unit_ids: list[str] | None = Field(
        default=None,
        description="Canonical unit IDs to use when canonical question selection is enabled.",
    )
    phase: str = Field(
        default="placement",
        description="Canonical assessment phase used with item_phase_map.",
    )
    assessment_depth: Literal["quick", "standard", "deep"] = Field(
        default="standard",
        description="Placement length/depth: quick<=15, standard<=30, deep<=50.",
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
    # Commit B: audit fields (ADD-only, backwards compatible)
    selection_strategy: str | None = Field(
        default=None,
        description="Strategy used for item selection (legacy | random_uniform | spread_by_prior | irt_adaptive)",
    )
    calibration_mode: str | None = Field(
        default=None,
        description="Calibration mode (prior_only | calibrated_2pl | calibrated_3pl)",
    )


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


class LearningUnitResult(BaseModel):
    learning_unit_id: uuid.UUID
    learning_unit_title: str
    score_percent: float
    mastery_level: MasteryLevel
    bloom_breakdown: dict[str, str]  # e.g. {"remember": "1/1", "analyze": "1/2"}
    weak_kcs: list[str]  # KC names where the user made errors
    misconceptions_detected: list[str]  # misconception IDs from wrong-answer mapping
    theta_estimate: float = Field(
        default=0.0,
        description=(
            "2PL IRT ability estimate (θ̂) for this learning unit on a logit scale. "
            "−3 = very low ability, 0 = average, +3 = very high ability."
        ),
    )


class TopicDecisionResult(BaseModel):
    """Per-unit placement decision exposed in AssessmentResultResponse."""

    topic_unit_id: str  # learning_unit.id (UUID as string)
    topic_unit_name: str  # learning_unit.title
    score_pct: float  # 0–100
    decision: str  # "skip" | "review" | "relearn"
    mastery_level: str  # derived label
    questions_total: int
    questions_correct: int


class TopicDecisionUpdateRequest(BaseModel):
    session_id: uuid.UUID
    topic_unit_id: uuid.UUID
    user_choice: str = Field(
        description="User-chosen override: 'skip', 'review', or 'relearn'",
        pattern="^(skip|review|relearn)$",
    )


class AssessmentResultResponse(BaseModel):
    session_id: uuid.UUID
    completed_at: datetime
    overall_score_percent: float
    learning_unit_results: list[LearningUnitResult]
    topic_decisions: list[TopicDecisionResult] | None = None


class AssessmentAISummaryResponse(BaseModel):
    """Optional LLM-written result summary.

    If generation fails or returns invalid content, available=false and the
    frontend should simply omit the AI summary block.
    """

    available: bool = False
    summary: str | None = None
    highlights: list[str] = Field(default_factory=list)
    next_step: str | None = None
    model_used: str | None = None
    provider: str | None = None
