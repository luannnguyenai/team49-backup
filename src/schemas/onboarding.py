"""
schemas/onboarding.py
---------------------
Pydantic v2 request/response models for the onboarding flow.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, field_validator

from src.config.goal_course_map import VALID_GOAL_IDS


class GoalsRequest(BaseModel):
    goal_ids: list[str]

    @field_validator("goal_ids")
    @classmethod
    def validate_goal_ids(cls, v: list[str]) -> list[str]:
        invalid = [g for g in v if g not in VALID_GOAL_IDS]
        if invalid:
            raise ValueError(f"Invalid goal_ids: {invalid}. Valid: {sorted(VALID_GOAL_IDS)}")
        if not v:
            raise ValueError("goal_ids must not be empty")
        if len(v) != 1:
            raise ValueError("Planner V1 requires exactly one goal_id")
        return v


class GoalsResponse(BaseModel):
    goal_ids: list[str]
    course_ids: list[str]


class UnitSummary(BaseModel):
    unit_id: UUID
    title: str
    estimated_hours_beginner: float


class SectionSummary(BaseModel):
    section_id: UUID
    title: str
    units: list[UnitSummary]


class CourseSummary(BaseModel):
    course_id: str
    goal_id: str
    sections: list[SectionSummary]


class TopicsResponse(BaseModel):
    courses: list[CourseSummary]


class KnownTopicsRequest(BaseModel):
    topic_unit_ids: list[UUID]


class KnownTopicsResponse(BaseModel):
    saved: bool
    count: int
    skip_placement: bool = False


class ExperienceLevelRequest(BaseModel):
    level: str

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        if v not in ("beginner", "experienced"):
            raise ValueError("level must be 'beginner' or 'experienced'")
        return v


class ExperienceLevelResponse(BaseModel):
    level: str
    placement_status: str | None


class PriorAnalysisCandidate(BaseModel):
    id: str
    display_label: str
    raw_title: str
    unit_titles: list[str] = []


class PriorAnalysisRequest(BaseModel):
    goal_id: str
    prior_knowledge_text: str = ""
    coding_experience_text: str = ""
    candidates: list[PriorAnalysisCandidate]

    @field_validator("goal_id")
    @classmethod
    def validate_goal_id(cls, v: str) -> str:
        if v not in VALID_GOAL_IDS:
            raise ValueError(f"Invalid goal_id: {v}. Valid: {sorted(VALID_GOAL_IDS)}")
        return v


class PriorAnalysisResponse(BaseModel):
    shortlisted_topic_ids: list[str]
    model_used: str
    provider: str
    fallback: bool = False
