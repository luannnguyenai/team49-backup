"""
schemas/history.py
------------------
Pydantic v2 schemas for the unified Learning History API.

Endpoints
---------
GET  /api/history                       Paginated session list with summary stats
GET  /api/history/{session_id}/detail   Per-question breakdown for one session
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from src.models.learning import SessionType

# ---------------------------------------------------------------------------
# GET /api/history
# ---------------------------------------------------------------------------


class HistoryItem(BaseModel):
    """One row in the history list."""

    session_id: uuid.UUID
    session_type: SessionType
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: int | None  # None if session never completed

    # Subject: learning unit title for quiz/assessment rows, section title for module_test
    subject: str
    learning_unit_id: uuid.UUID | None
    section_id: uuid.UUID | None

    score_percent: float | None
    correct_count: int
    total_questions: int


class ScoreTrendPoint(BaseModel):
    """One point on the score trend mini-chart (ordered oldest → newest)."""

    started_at: datetime
    score_percent: float


class HistorySummary(BaseModel):
    """Aggregate stats shown above the table."""

    total_sessions: int
    completed_sessions: int
    avg_score: float | None  # None if no completed sessions
    total_study_seconds: int  # sum of durations for completed sessions
    score_trend: list[ScoreTrendPoint]  # last ≤ 20 completed sessions


class HistoryResponse(BaseModel):
    summary: HistorySummary
    total: int  # total rows matching filters
    page: int
    page_size: int
    items: list[HistoryItem]


# ---------------------------------------------------------------------------
# GET /api/history/{session_id}/detail
# ---------------------------------------------------------------------------


class QuestionInteractionDetail(BaseModel):
    """One question + user's answer within a session."""

    question_id: uuid.UUID | None = None
    canonical_item_id: str | None = None
    sequence_position: int
    topic_name: str
    stem_text: str
    bloom_level: str
    difficulty_bucket: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    selected_answer: str | None  # None if skipped
    correct_answer: str
    is_correct: bool
    response_time_ms: int | None
    explanation_text: str | None


class SessionDetailResponse(BaseModel):
    """Full detail for one completed session."""

    session_id: uuid.UUID
    session_type: SessionType
    bloom_breakdown: dict[str, str]  # {"remember": "2/3", …}
    weak_kcs: list[str]  # KC names for wrong answers
    misconceptions: list[str]  # misconception IDs detected
    questions: list[QuestionInteractionDetail]
