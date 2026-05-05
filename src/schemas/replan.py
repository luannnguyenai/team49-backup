"""
schemas/replan.py
-----------------
Pydantic v2 request/response models for the Replan Production E2E endpoints.

POST /api/replan/analyze — Analyze a knowledge claim against the real current path.
POST /api/replan/assessment/start — Start an assessment with exact unit+difficulty filters.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.assessment import QuestionForAssessment


# ===========================================================================
# Shared types
# ===========================================================================

Difficulty = Literal["easy", "medium", "hard", "application"]
DifficultyFilter = Literal["easy", "easy_medium", "easy_medium_hard", "all"]
ReplanAnalyzeStatus = Literal[
    "ready",
    "guardrail_blocked",
    "no_active_path",
    "no_matching_units",
    "all_already_mastered",
    "internal_error",
]
ReplanPopupKind = Literal[
    "guardrail_blocked",
    "no_active_path",
    "no_matching_units",
    "all_already_mastered",
    "internal_error",
]


# ===========================================================================
# POST /api/replan/analyze — Request / Response
# ===========================================================================


class ReplanAnalyzeRequest(BaseModel):
    """User's knowledge claim sent for analysis against the current learning path."""

    claim: str = Field(
        min_length=3,
        description="Natural-language knowledge claim, e.g. 'Tôi biết Faster RCNN'.",
    )


class ReplanAnalyzeUnit(BaseModel):
    """A single unit matched from the current learning path."""

    canonical_unit_id: str = Field(alias="canonicalUnitId")
    title: str
    source: Literal["matched_from_description", "suggested_prerequisite"]
    suggested_for_title: str | None = Field(default=None, alias="suggestedForTitle")
    knowledge_points: list[str] = Field(default_factory=list, alias="knowledgePoints")
    question_counts: dict[Difficulty, int] = Field(alias="questionCounts")

    model_config = ConfigDict(populate_by_name=True)


class ReplanPrerequisiteSuggestionResponse(BaseModel):
    """A prerequisite unit suggestion returned by the analyze endpoint."""

    canonical_unit_id: str = Field(alias="canonicalUnitId")
    title: str
    reason: str
    depth: int
    review_unit: ReplanAnalyzeUnit = Field(alias="reviewUnit")

    model_config = ConfigDict(populate_by_name=True)


class ReplanPopup(BaseModel):
    """Popup metadata for frontend status-specific dialogs."""

    kind: ReplanPopupKind
    title: str
    message: str


class ReplanAnalyzeResponse(BaseModel):
    """Full analyze response with matched units, prerequisites, and metadata."""

    units: list[ReplanAnalyzeUnit]
    prerequisites: list[ReplanPrerequisiteSuggestionResponse]
    keyword_plan_specificity: str = Field(alias="keywordPlanSpecificity")
    guardrail_flags: list[str] = Field(default_factory=list, alias="guardrailFlags")
    status: ReplanAnalyzeStatus = "ready"
    popup: ReplanPopup | None = None

    model_config = ConfigDict(populate_by_name=True)


# ===========================================================================
# POST /api/replan/assessment/start — Request / Response
# ===========================================================================


class ReplanAssessmentUnitRequest(BaseModel):
    """One unit selected by the user for the replan assessment."""

    canonical_unit_id: str = Field(alias="canonicalUnitId")
    difficulty_filter: DifficultyFilter = Field(
        default="all",
        alias="difficultyFilter",
        description="Difficulty ceiling: only questions at or below this level.",
    )

    model_config = ConfigDict(populate_by_name=True)


class ReplanAssessmentStartRequest(BaseModel):
    """Request body for starting a replan assessment."""

    selected_units: list[ReplanAssessmentUnitRequest] = Field(
        min_length=1,
        alias="selectedUnits",
    )

    model_config = ConfigDict(populate_by_name=True)


class ReplanAssessmentStartResponse(BaseModel):
    """Response after creating a replan assessment session."""

    session_id: str = Field(alias="sessionId")
    total_questions: int = Field(alias="totalQuestions")
    canonical_unit_ids: list[str] = Field(alias="canonicalUnitIds")
    unit_name_map: dict[str, str] = Field(alias="unitNameMap")
    assessment_href: str = Field(alias="assessmentHref")
    questions: list[QuestionForAssessment]

    model_config = ConfigDict(populate_by_name=True)
