"""
schemas/module_test.py
----------------------
Pydantic v2 schemas for the Module Test System.

Endpoints
---------
POST  /api/module-test/start                  Begin a new module test session
POST  /api/module-test/{session_id}/submit    Submit all answers and get results
GET   /api/module-test/{session_id}/results   Retrieve previously-submitted results
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from src.models.content import BloomLevel, DifficultyBucket
from src.models.learning import SelectedAnswer


# ---------------------------------------------------------------------------
# POST /api/module-test/start
# ---------------------------------------------------------------------------

class ModuleTestStartRequest(BaseModel):
    module_id: uuid.UUID


class QuestionForModuleTest(BaseModel):
    """Question sent to the client — correct_answer intentionally omitted."""
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


class TopicQuestionsGroup(BaseModel):
    """Questions for one topic within the module test."""

    topic_id: uuid.UUID
    topic_name: str
    questions: list[QuestionForModuleTest]


class ModuleTestStartResponse(BaseModel):
    session_id: uuid.UUID
    module_id: uuid.UUID
    module_name: str
    total_topics: int
    total_questions: int          # sum across all topics (≤ topics × 5)
    topics: list[TopicQuestionsGroup]


# ---------------------------------------------------------------------------
# POST /api/module-test/{session_id}/submit
# ---------------------------------------------------------------------------

class ModuleTestAnswerInput(BaseModel):
    question_id: uuid.UUID
    selected_answer: SelectedAnswer
    response_time_ms: int | None = Field(default=None, ge=0)


class ModuleTestSubmitRequest(BaseModel):
    answers: list[ModuleTestAnswerInput] = Field(min_length=1)


class TopicTestResult(BaseModel):
    """Per-topic grading detail."""

    topic_id: uuid.UUID
    topic_name: str
    score: str                          # e.g. "4/5"
    score_percent: float                # 0.0 – 100.0
    bloom_max: str | None               # highest Bloom level answered correctly
    verdict: Literal["pass", "fail"]    # pass ≥ 60 %
    weak_kcs: list[str]                 # KC names linked to wrong answers


class ReviewTopicSuggestion(BaseModel):
    """One topic recommended for remediation (only present when verdict == fail)."""

    topic_id: uuid.UUID
    topic_name: str
    weak_kcs: list[str]
    misconceptions: list[str]           # misconception IDs triggered
    estimated_review_hours: float


class NextModuleInfo(BaseModel):
    module_id: uuid.UUID
    module_name: str


class ModuleTestResultResponse(BaseModel):
    """
    Returned by both POST /submit and GET /results.
    The shape is identical; only the timing of DB mutations differs.
    """

    session_id: uuid.UUID
    module_id: uuid.UUID
    module_name: str

    # Overall
    total_score_percent: float
    passed: bool                        # True if total ≥ 70 %

    # Per-topic breakdown
    per_topic: list[TopicTestResult]

    # Remediation (non-empty only when passed == False)
    recommended_review_topics: list[ReviewTopicSuggestion]
    estimated_review_hours: float       # sum of review hours for weak topics

    # Progression (non-None only when passed == True)
    next_module: NextModuleInfo | None
