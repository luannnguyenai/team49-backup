from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.schemas.learning_session import (
    LearningUnitProgressRequest,
    LearningUnitProgressResponse,
    ResumeStateResponse,
)
from src.services.learning_session_service import get_resume_state, update_learning_unit_progress

learning_session_router = APIRouter(prefix="/api/learning-session", tags=["Learning Session"])


@learning_session_router.get("/resume", response_model=ResumeStateResponse)
async def api_get_resume_state(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> ResumeStateResponse:
    return await get_resume_state(db, user.id)


@learning_session_router.put(
    "/learning-units/{learning_unit_id}/progress",
    response_model=LearningUnitProgressResponse,
)
async def api_update_learning_unit_progress(
    learning_unit_id: uuid.UUID,
    body: LearningUnitProgressRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> LearningUnitProgressResponse:
    return await update_learning_unit_progress(
        db,
        user_id=user.id,
        learning_unit_id=learning_unit_id,
        video_progress_s=body.video_progress_s,
        video_finished=body.video_finished,
    )
