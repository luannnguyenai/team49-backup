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
        min_length=1,
        max_length=50,
        description="Topics to include in this assessment (1-50)",
    )


class QuestionForAssessment(BaseModel):
    """Question payload sent to the client — correct_answer is intentionally omitted."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    item_id: str
    topic_id: uuid.UUID
    bloom_level: BloomLevel
    difficulty_bucket: DifficultyBucket
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
    question_id: uuid.UUID
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


class AssessmentResultResponse(BaseModel):
    session_id: uuid.UUID
    completed_at: datetime
    overall_score_percent: float
    topic_results: list[TopicResult]
