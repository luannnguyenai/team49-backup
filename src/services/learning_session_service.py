from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError
from src.models.course import LearningProgressStatus
from src.repositories.canonical_content_repo import CanonicalContentRepository
from src.repositories.learning_progress_repo import LearningProgressRepository
from src.repositories.planner_audit_repo import PlannerAuditRepository
from src.schemas.learning_session import LearningUnitProgressResponse, ResumeStateResponse
from src.services.resume_state_service import classify_resume_route

CANONICAL_SESSION_ID = "canonical-learning-path"


async def get_resume_state(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> ResumeStateResponse:
    now = now or datetime.now(UTC)
    state = await PlannerAuditRepository(db).get_session_state(user_id, CANONICAL_SESSION_ID)
    if state is None or state.last_activity is None:
        return ResumeStateResponse(resume_route="no_active_session")

    return ResumeStateResponse(
        resume_route=classify_resume_route(last_activity=state.last_activity, now=now),
        current_unit_id=state.current_unit_id,
        current_stage=state.current_stage,
        current_progress=state.current_progress,
        last_activity=state.last_activity,
    )


async def update_learning_unit_progress(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    learning_unit_id: uuid.UUID,
    video_progress_s: float | None,
    video_finished: bool,
) -> LearningUnitProgressResponse:
    unit_by_id = await CanonicalContentRepository(db).get_learning_units_by_ids([learning_unit_id])
    unit = unit_by_id.get(learning_unit_id)
    if unit is None:
        raise NotFoundError("Learning unit not found.")

    now = datetime.now(UTC)
    current_stage = "post_quiz" if video_finished else "watching"
    progress = {
        "learning_unit_id": str(learning_unit_id),
        "video_progress_s": video_progress_s,
        "video_finished": video_finished,
    }
    await LearningProgressRepository(db).upsert(
        user_id=user_id,
        course_id=unit.course_id,
        learning_unit_id=unit.id,
        status=LearningProgressStatus.in_progress,
        last_position_seconds=video_progress_s,
        last_opened_at=now,
        completed_at=None,
    )
    await PlannerAuditRepository(db).upsert_session_state(
        user_id=user_id,
        session_id=CANONICAL_SESSION_ID,
        current_unit_id=unit.id,
        current_stage=current_stage,
        current_progress=progress,
        last_activity=now,
        state_json={"canonical_runtime": True, "source": "learning_unit_progress"},
    )
    return LearningUnitProgressResponse(
        learning_unit_id=unit.id,
        current_stage=current_stage,
        current_progress=progress,
        last_activity=now,
    )
