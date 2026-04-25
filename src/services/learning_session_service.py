from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel
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
    watch_percent: float | None = None,
    inline_quiz: dict | None = None,
) -> LearningUnitProgressResponse:
    unit_by_id = await CanonicalContentRepository(db).get_learning_units_by_ids([learning_unit_id])
    unit = unit_by_id.get(learning_unit_id)
    if unit is None:
        raise NotFoundError("Learning unit not found.")

    now = datetime.now(UTC)
    planner_repo = PlannerAuditRepository(db)
    existing_state = await planner_repo.get_session_state(user_id, CANONICAL_SESSION_ID)
    existing_progress = (
        dict(existing_state.current_progress)
        if existing_state is not None and isinstance(existing_state.current_progress, dict)
        else {}
    )
    merged_inline_quiz = _merge_inline_quiz_progress(existing_progress.get("inline_quiz"), inline_quiz)
    current_stage = "watching"
    if video_finished and _has_completed_end_inline_quiz(merged_inline_quiz):
        current_stage = "post_quiz"
    elif _has_active_inline_quiz(merged_inline_quiz):
        current_stage = "quiz_in_progress"
    progress = {
        **existing_progress,
        "learning_unit_id": str(learning_unit_id),
        "video_progress_s": video_progress_s,
        "video_finished": video_finished,
    }
    if watch_percent is not None:
        progress["watch_percent"] = watch_percent
    if merged_inline_quiz:
        progress["inline_quiz"] = merged_inline_quiz
    await LearningProgressRepository(db).upsert(
        user_id=user_id,
        course_id=unit.course_id,
        learning_unit_id=unit.id,
        status=LearningProgressStatus.in_progress,
        last_position_seconds=video_progress_s,
        last_opened_at=now,
        completed_at=None,
    )
    await planner_repo.upsert_session_state(
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


def _merge_inline_quiz_progress(existing_inline_quiz: dict | None, incoming_inline_quiz: dict | None) -> dict:
    merged = _sanitize_inline_quiz_progress(existing_inline_quiz)
    sanitized_incoming = _sanitize_inline_quiz_progress(incoming_inline_quiz)
    if not sanitized_incoming:
        return merged
    for checkpoint, checkpoint_state in sanitized_incoming.items():
        existing_checkpoint_state = merged.get(checkpoint)
        merged[checkpoint] = {
            **(existing_checkpoint_state if isinstance(existing_checkpoint_state, dict) else {}),
            **checkpoint_state,
        }
    return merged


def _has_active_inline_quiz(inline_quiz: dict | None) -> bool:
    if not isinstance(inline_quiz, dict):
        return False
    for checkpoint_state in inline_quiz.values():
        if isinstance(checkpoint_state, dict) and checkpoint_state.get("active_session_id"):
            return True
    return False


def _has_completed_end_inline_quiz(inline_quiz: dict | None) -> bool:
    if not isinstance(inline_quiz, dict):
        return False
    end_state = inline_quiz.get("end")
    return isinstance(end_state, dict) and bool(end_state.get("completed_session_id"))


def _sanitize_inline_quiz_progress(inline_quiz: dict | BaseModel | None) -> dict:
    if isinstance(inline_quiz, BaseModel):
        inline_quiz = inline_quiz.model_dump(exclude_none=True)
    if not isinstance(inline_quiz, dict):
        return {}

    sanitized: dict = {}
    for checkpoint in ("midpoint", "end"):
        checkpoint_state = inline_quiz.get(checkpoint)
        if isinstance(checkpoint_state, BaseModel):
            checkpoint_state = checkpoint_state.model_dump(exclude_none=True)
        if not isinstance(checkpoint_state, dict):
            continue

        normalized_state = {}
        if "shown" in checkpoint_state and isinstance(checkpoint_state["shown"], bool):
            normalized_state["shown"] = checkpoint_state["shown"]
        for field_name in ("active_session_id", "completed_session_id", "quiz_phase"):
            value = checkpoint_state.get(field_name)
            if value is None or isinstance(value, str):
                normalized_state[field_name] = value
        for field_name in ("excluded_item_ids", "item_ids", "answered_item_ids"):
            value = checkpoint_state.get(field_name)
            if isinstance(value, list):
                normalized_state[field_name] = [str(item_id) for item_id in value]
        if normalized_state:
            sanitized[checkpoint] = normalized_state
    return sanitized
