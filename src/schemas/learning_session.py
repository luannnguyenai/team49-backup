from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

InlineQuizCheckpoint = Literal["midpoint", "end"]


class InlineQuizCheckpointUpdate(BaseModel):
    shown: bool | None = None
    active_session_id: str | None = None
    completed_session_id: str | None = None
    excluded_item_ids: list[str] | None = None
    item_ids: list[str] | None = None
    answered_item_ids: list[str] | None = None
    quiz_phase: str | None = None


class InlineQuizUpdate(BaseModel):
    midpoint: InlineQuizCheckpointUpdate | None = None
    end: InlineQuizCheckpointUpdate | None = None


class ResumeStateResponse(BaseModel):
    resume_route: str
    current_unit_id: uuid.UUID | None = None
    current_stage: str | None = None
    current_progress: dict | None = None
    last_activity: datetime | None = None


class LearningUnitProgressRequest(BaseModel):
    video_progress_s: float | None = Field(default=None, ge=0)
    video_finished: bool = False
    watch_percent: float | None = Field(default=None, ge=0, le=1)
    inline_quiz: InlineQuizUpdate | None = None


class LearningUnitProgressResponse(BaseModel):
    learning_unit_id: uuid.UUID
    current_stage: str
    current_progress: dict
    last_activity: datetime
