from __future__ import annotations

from pydantic import BaseModel, Field

from src.schemas.assessment import AssessmentStartResponse


class PlacementLiteStartRequest(BaseModel):
    selected_course_ids: list[str] = Field(default_factory=list, max_length=10)
    count: int = Field(default=10, ge=1, le=30)
    max_units: int = Field(default=10, ge=1, le=30)


class PlacementLiteStartResponse(AssessmentStartResponse):
    selected_course_ids: list[str] = Field(default_factory=list)
    sampled_canonical_unit_ids: list[str] = Field(default_factory=list)
