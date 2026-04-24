"""
schemas/quiz.py
---------------
Pydantic v2 schemas for the Quiz System API.

Endpoints
---------
POST  /api/quiz/start
POST  /api/quiz/{session_id}/answer
POST  /api/quiz/{session_id}/complete
GET   /api/quiz/history
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import AliasChoices, BaseModel, Field

from src.models.content import BloomLevel, CorrectAnswer, DifficultyBucket
from src.models.learning import MasteryLevel, SelectedAnswer

# ---------------------------------------------------------------------------
# POST /api/quiz/start
# ---------------------------------------------------------------------------


class QuizStartRequest(BaseModel):
    learning_unit_id: uuid.UUID = Field(
        validation_alias=AliasChoices("learning_unit_id", "topic_id")
    )


class QuestionForQuiz(BaseModel):
    """Question payload sent to client — correct_answer intentionally omitted."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    item_id: str
    learning_unit_id: uuid.UUID
    bloom_level: BloomLevel
    difficulty_bucket: DifficultyBucket
    stem_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    time_expected_seconds: int | None


class QuizStartResponse(BaseModel):
    session_id: uuid.UUID
    learning_unit_id: uuid.UUID
    total_questions: int
    questions: list[QuestionForQuiz]


# ---------------------------------------------------------------------------
# POST /api/quiz/{session_id}/answer  (real-time, one at a time)
# ---------------------------------------------------------------------------


class QuizAnswerRequest(BaseModel):
    question_id: uuid.UUID
    selected_answer: SelectedAnswer
    response_time_ms: int | None = Field(default=None, ge=0)


class QuizAnswerResponse(BaseModel):
    """Immediate feedback returned after each answered question."""

    is_correct: bool
    correct_answer: CorrectAnswer
    explanation_text: str | None
    # Running tally so the client can show live progress
    questions_answered: int
    questions_correct: int


# ---------------------------------------------------------------------------
# POST /api/quiz/{session_id}/complete
# ---------------------------------------------------------------------------


class QuizCompleteResponse(BaseModel):
    session_id: uuid.UUID
    learning_unit_id: uuid.UUID
    learning_unit_title: str

    # Raw score
    score: str  # e.g. "7/10"
    percent: float  # 0.0 – 100.0

    # Mastery delta
    mastery_before: float  # score_percent before this quiz
    mastery_after: float  # score_percent after EMA update
    mastery_level: MasteryLevel  # resulting level bucket

    # Bloom + KCs
    bloom_breakdown: dict[str, str]  # {"remember": "2/3", "analyze": "1/2"}
    weak_kcs: list[str]  # KC names (not UUIDs) for wrong answers
    misconceptions: list[str]  # misconception IDs detected in this quiz

    # Timing
    time_total_seconds: float
    avg_time_per_question: float

    # Was the learning-path item auto-completed?
    learning_path_updated: bool


# ---------------------------------------------------------------------------
# GET /api/quiz/history
# ---------------------------------------------------------------------------


class QuizHistorySummary(BaseModel):
    session_id: uuid.UUID
    learning_unit_id: uuid.UUID
    learning_unit_title: str
    score_percent: float | None
    correct_count: int
    total_questions: int
    completed_at: datetime | None
    started_at: datetime


class QuizHistoryResponse(BaseModel):
    total: int
    items: list[QuizHistorySummary]
