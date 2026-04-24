from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ResumeStateResponse(BaseModel):
    resume_route: str
    current_unit_id: uuid.UUID | None = None
    current_stage: str | None = None
    current_progress: dict | None = None
    last_activity: datetime | None = None


class LearningUnitProgressRequest(BaseModel):
    video_progress_s: float | None = Field(default=None, ge=0)
    video_finished: bool = False


class LearningUnitProgressResponse(BaseModel):
    learning_unit_id: uuid.UUID
    current_stage: str
    current_progress: dict
    last_activity: datetime
