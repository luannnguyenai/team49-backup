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

from pydantic import AliasChoices, BaseModel, Field

from src.models.content import BloomLevel, DifficultyBucket
from src.models.learning import SelectedAnswer

# ---------------------------------------------------------------------------
# POST /api/module-test/start
# ---------------------------------------------------------------------------


class ModuleTestStartRequest(BaseModel):
    section_id: uuid.UUID = Field(
        validation_alias=AliasChoices("section_id", "module_id")
    )


class QuestionForModuleTest(BaseModel):
    """Question sent to the client — correct_answer intentionally omitted."""

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


class TopicQuestionsGroup(BaseModel):
    """Questions for one topic within the module test."""

    learning_unit_id: uuid.UUID
    learning_unit_title: str
    questions: list[QuestionForModuleTest]


class ModuleTestStartResponse(BaseModel):
    session_id: uuid.UUID
    section_id: uuid.UUID
    section_title: str
    total_learning_units: int
    total_questions: int  # sum across all topics (≤ topics × 5)
    learning_units: list[TopicQuestionsGroup]


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

    learning_unit_id: uuid.UUID
    learning_unit_title: str
    score: str  # e.g. "4/5"
    score_percent: float  # 0.0 – 100.0
    bloom_max: str | None  # highest Bloom level answered correctly
    verdict: Literal["pass", "fail"]  # pass ≥ 60 %
    weak_kcs: list[str]  # KC names linked to wrong answers


class ReviewTopicSuggestion(BaseModel):
    """One topic recommended for remediation (only present when verdict == fail)."""

    learning_unit_id: uuid.UUID
    learning_unit_title: str
    weak_kcs: list[str]
    misconceptions: list[str]  # misconception IDs triggered
    estimated_review_hours: float


class NextSectionInfo(BaseModel):
    section_id: uuid.UUID
    section_title: str


class WrongAnswerDetail(BaseModel):
    """Full detail for one incorrectly-answered question — shown in results UI."""

    question_id: uuid.UUID
    learning_unit_id: uuid.UUID
    learning_unit_title: str
    stem_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    selected_answer: SelectedAnswer
    correct_answer: str  # CorrectAnswer.value  e.g. "B"
    explanation_text: str | None


class ModuleTestResultResponse(BaseModel):
    """
    Returned by both POST /submit and GET /results.
    The shape is identical; only the timing of DB mutations differs.
    """

    session_id: uuid.UUID
    section_id: uuid.UUID
    section_title: str

    # Overall
    total_score_percent: float
    passed: bool  # True if total ≥ 70 %

    # Per-topic breakdown
    per_learning_unit: list[TopicTestResult]

    # Remediation (non-empty only when passed == False)
    recommended_review_topics: list[ReviewTopicSuggestion]
    estimated_review_hours: float  # sum of review hours for weak topics

    # Progression (non-None only when passed == True)
    next_section: NextSectionInfo | None

    # Per-question wrong-answer details (for review section)
    wrong_answers: list[WrongAnswerDetail]
