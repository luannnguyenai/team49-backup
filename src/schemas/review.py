from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from src.schemas.assessment import AssessmentStartResponse


class ReviewStartRequest(BaseModel):
    learning_unit_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    count: int = Field(default=5, ge=1, le=20)


class ReviewStartResponse(AssessmentStartResponse):
    review_kp_ids: list[str] = Field(default_factory=list)
