"""
schemas/learning_path.py
-------------------------
Pydantic v2 schemas for the Learning Path / Recommendation Engine API.

Endpoints covered
-----------------
POST  /api/learning-path/generate
GET   /api/learning-path
GET   /api/learning-path/timeline
PUT   /api/learning-path/{path_id}/status
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.models.learning import PathAction, PathStatus

# ---------------------------------------------------------------------------
# POST /api/learning-path/generate  — request
# ---------------------------------------------------------------------------


class GeneratePathRequest(BaseModel):
    """
    Body for the generate endpoint.

    desired_module_ids: UUIDs of the modules the user wants to learn.
    mastery_overrides:  Optional per-topic score overrides (used in tests /
                        re-generation after additional practice). When absent
                        the engine reads live MasteryScore rows from the DB.
    """

    desired_module_ids: list[uuid.UUID] = Field(
        min_length=1,
        description="Modules chosen during onboarding",
    )
    mastery_overrides: dict[str, float] | None = Field(
        default=None,
        description="Optional {topic_id_str: score_percent} overrides",
    )


# ---------------------------------------------------------------------------
# Shared path item shape (used in multiple responses)
# ---------------------------------------------------------------------------


class PathItemResponse(BaseModel):
    """One row in the learning path — maps to a LearningPath ORM record."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    learning_unit_id: uuid.UUID
    learning_unit_title: str
    section_title: str | None = None
    action: PathAction
    estimated_hours: float | None
    order_index: int
    week_number: int | None
    status: PathStatus
    canonical_unit_id: str | None = None


# ---------------------------------------------------------------------------
# POST /api/learning-path/generate  — response
# ---------------------------------------------------------------------------


class GeneratePathResponse(BaseModel):
    """Full generated path with metadata and optional warnings."""

    generated_at: datetime
    total_topics: int
    total_hours: float
    required_hours_per_week: float | None = Field(
        description="Hours/week needed to meet the deadline"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal warnings (e.g. deadline too tight)",
    )
    items: list[PathItemResponse]


# ---------------------------------------------------------------------------
# GET /api/learning-path  — response
# ---------------------------------------------------------------------------


class LearningPathResponse(BaseModel):
    """Current user's full learning path."""

    total_topics: int
    completed_topics: int
    in_progress_topics: int
    items: list[PathItemResponse]


# ---------------------------------------------------------------------------
# GET /api/learning-path/timeline  — response
# ---------------------------------------------------------------------------


class WeekEntry(BaseModel):
    """Topics allocated to a single calendar week."""

    week: int
    topics: list[PathItemResponse]
    total_hours: float


class TimelineResponse(BaseModel):
    """Weekly timeline breakdown."""

    total_weeks: int
    items: list[WeekEntry]


# ---------------------------------------------------------------------------
# PUT /api/learning-path/{path_id}/status  — request / response
# ---------------------------------------------------------------------------


class UpdateStatusRequest(BaseModel):
    status: PathStatus = Field(description="New status: in_progress | completed | skipped")


class UpdateStatusResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    learning_unit_id: uuid.UUID
    status: PathStatus
    updated_at: datetime
