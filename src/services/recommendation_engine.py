"""
services/recommendation_engine.py
-----------------------------------
Rule-based personalised learning path generator.

Algorithm (step-by-step)
------------------------
1. Resolve selected courses from goal_preferences.
2. Load linked canonical learning units and unit-KP mappings.
3. Read KP mastery from learner_mastery_kp.
4. Classify each unit action and persist planner audit rows.
5. Return a GeneratePathResponse.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from src.config import settings
from src.exceptions import ForbiddenError, NotFoundError, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.course import LearningProgressStatus
from src.models.learning import (
    PathAction,
    PathStatus,
    Session,
    SessionType,
)
from src.models.user import User
from src.repositories.canonical_content_repo import CanonicalContentRepository
from src.repositories.goal_preference_repo import GoalPreferenceRepository
from src.repositories.learner_mastery_kp_repo import LearnerMasteryKPRepository
from src.repositories.learning_progress_repo import LearningProgressRepository
from src.repositories.planner_audit_repo import PlannerAuditRepository
from src.repositories.waived_unit_repo import WaivedUnitRepository
from src.schemas.learning_path import (
    GeneratePathRequest,
    GeneratePathResponse,
    PathItemResponse,
)
from src.services.canonical_mastery_service import estimate_mastery_lcb_on_read
from src.services.canonical_planner_service import classify_unit_action
from src.services.skip_policy_service import can_skip_unit

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def generate_learning_path(
    db: AsyncSession,
    user: User,
    request: GeneratePathRequest,
) -> GeneratePathResponse:
    """Generate the canonical learning-unit path for `user`."""
    return await _generate_canonical_learning_path(db, user, request)


async def _generate_canonical_learning_path(
    db: AsyncSession,
    user: User,
    request: GeneratePathRequest,
) -> GeneratePathResponse:
    content_repo = CanonicalContentRepository(db)
    audit_repo = PlannerAuditRepository(db)
    goal_repo = GoalPreferenceRepository(db)
    goal = await goal_repo.get_by_user_id(user.id)
    if goal is None or not goal.selected_course_ids:
        raise ValidationError("Canonical planner requires goal_preferences.selected_course_ids.")

    units = await content_repo.get_linked_learning_units(goal.selected_course_ids)
    if not units:
        raise NotFoundError("No linked canonical learning units found for selected courses.")

    section_by_id = await content_repo.get_sections_by_ids([unit.section_id for unit in units])
    status_by_unit = await _get_canonical_path_status_map(
        db,
        user_id=user.id,
        learning_unit_ids=[unit.id for unit in units],
    )
    canonical_unit_ids = [unit.canonical_unit_id for unit in units if unit.canonical_unit_id]
    unit_kp_rows = await content_repo.get_unit_kp_rows(canonical_unit_ids)
    kp_ids = sorted({row.kp_id for row in unit_kp_rows})

    mastery_repo = LearnerMasteryKPRepository(db)
    mastery_by_kp = await mastery_repo.bulk_get_for_user(user.id, kp_ids)

    generated_at = datetime.now(UTC)
    items: list[PathItemResponse] = []
    recommended_path_json = []

    for order_index, unit in enumerate(units):
        unit_kps = [row.kp_id for row in unit_kp_rows if row.unit_id == unit.canonical_unit_id]
        mastery_values = [
            estimate_mastery_lcb_on_read(mastery_by_kp[kp_id], now=generated_at)
            for kp_id in unit_kps
            if kp_id in mastery_by_kp
        ]
        mastery_lcb = min(mastery_values) if mastery_values else 0.0
        action_value = classify_unit_action(mastery_lcb)
        action = PathAction(action_value)
        estimated_hours = 0.0 if action == PathAction.skip else ((unit.estimated_minutes or 30) / 60.0)

        item = PathItemResponse(
            id=unit.id,
            learning_unit_id=unit.id,
            learning_unit_title=unit.title,
            section_title=(
                section_by_id[unit.section_id].title if unit.section_id in section_by_id else None
            ),
            action=action,
            estimated_hours=estimated_hours if estimated_hours > 0 else None,
            order_index=order_index,
            week_number=None,
            status=status_by_unit.get(unit.id, PathStatus.pending),
            canonical_unit_id=unit.canonical_unit_id,
        )
        items.append(item)
        recommended_path_json.append(
            {
                "learning_unit_id": str(unit.id),
                "canonical_unit_id": unit.canonical_unit_id,
                "action": action.value,
                "estimated_hours": estimated_hours,
                "order_index": order_index,
                "kp_ids": unit_kps,
                "mastery_lcb": mastery_lcb,
            }
        )

    total_hours = sum(item.estimated_hours or 0.0 for item in items)
    plan = await audit_repo.create_plan(
        user_id=user.id,
        trigger="generate_canonical_learning_path",
        recommended_path_json=recommended_path_json,
        goal_snapshot_json={
            "selected_course_ids": goal.selected_course_ids,
            "derived_from_course_set_hash": goal.derived_from_course_set_hash,
        },
        weights_used_json={"planner": "canonical_unit_bootstrap"},
    )

    for rank, item in enumerate(items, start=1):
        await audit_repo.add_rationale(
            plan_history_id=plan.id,
            learning_unit_id=item.learning_unit_id,
            rank=rank,
            reason_code=f"canonical_unit_{item.action.value}",
            term_breakdown_json={
                "canonical_unit_id": item.canonical_unit_id,
                "estimated_hours": item.estimated_hours,
            },
            rationale_text=f"Canonical planner selected unit `{item.learning_unit_title}` as `{item.action.value}`.",
        )

    await audit_repo.upsert_session_state(
        user_id=user.id,
        session_id="canonical-learning-path",
        last_plan_history_id=plan.id,
        bridge_chain_depth=0,
        consecutive_bridge_count=0,
        current_stage="between_units",
        current_progress={"last_generated_plan_id": str(plan.id)},
        last_activity=generated_at,
        state_json={
            "canonical_runtime": True,
            "generated_at": generated_at.isoformat(),
            "unit_count": len(items),
        },
    )

    return GeneratePathResponse(
        generated_at=generated_at,
        total_units=len(items),
        total_hours=total_hours,
        required_hours_per_week=None,
        warnings=[],
        items=items,
    )


# ---------------------------------------------------------------------------
# GET /api/learning-path — current path
# ---------------------------------------------------------------------------


async def get_learning_path(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[tuple[SimpleNamespace, str, str]]:
    """Return the latest canonical planner path rows for the user."""
    return await _get_canonical_learning_path_rows(db, user_id)


# ---------------------------------------------------------------------------
# GET /api/learning-path/timeline
# ---------------------------------------------------------------------------


async def get_learning_path_timeline(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> dict[int, list[tuple[SimpleNamespace, str, str]]]:
    """Return canonical planner rows grouped by week number."""
    rows = await _get_canonical_learning_path_rows(db, user_id)
    grouped: dict[int, list] = {}
    for row in rows:
        lp = row[0]
        if lp.action == PathAction.skip:
            continue
        week = lp.week_number or 1
        grouped.setdefault(week, []).append(row)
    return grouped


async def _get_canonical_learning_path_rows(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[tuple[SimpleNamespace, str, str]]:
    audit_repo = PlannerAuditRepository(db)
    plan = await audit_repo.get_latest_plan_for_user(
        user_id,
        trigger="generate_canonical_learning_path",
    )
    if plan is None or not plan.recommended_path_json:
        return []

    learning_unit_ids: list[uuid.UUID] = []
    for item in plan.recommended_path_json:
        if not isinstance(item, dict):
            continue
        raw_unit_id = item.get("learning_unit_id")
        try:
            learning_unit_ids.append(uuid.UUID(str(raw_unit_id)))
        except (TypeError, ValueError):
            continue

    unit_by_id = await CanonicalContentRepository(db).get_learning_units_by_ids(learning_unit_ids)
    section_by_id = await CanonicalContentRepository(db).get_sections_by_ids(
        [unit.section_id for unit in unit_by_id.values()]
    )
    status_by_unit = await _get_canonical_path_status_map(
        db,
        user_id=user_id,
        learning_unit_ids=learning_unit_ids,
    )
    rows: list[tuple[SimpleNamespace, str, str]] = []
    for fallback_order, item in enumerate(plan.recommended_path_json):
        if not isinstance(item, dict):
            continue
        try:
            unit_id = uuid.UUID(str(item.get("learning_unit_id")))
        except (TypeError, ValueError):
            continue
        unit = unit_by_id.get(unit_id)
        action_value = str(item.get("action") or PathAction.deep_practice.value)
        try:
            action = PathAction(action_value)
        except ValueError:
            action = PathAction.deep_practice

        row = SimpleNamespace(
            id=unit_id,
            action=action,
            estimated_hours=item.get("estimated_hours"),
            order_index=int(item.get("order_index", fallback_order)),
            week_number=item.get("week_number"),
            status=status_by_unit.get(unit_id, PathStatus.pending),
            learning_unit_id=unit_id,
            canonical_unit_id=item.get("canonical_unit_id"),
        )
        section_title = None
        if unit is not None:
            section = section_by_id.get(unit.section_id)
            section_title = section.title if section is not None else None
        rows.append((row, unit.title if unit is not None else str(unit_id), section_title or "canonical_unit"))

    return sorted(rows, key=lambda row: row[0].order_index)


# ---------------------------------------------------------------------------
# PUT /api/learning-path/{path_id}/status
# ---------------------------------------------------------------------------


async def update_path_status(
    db: AsyncSession,
    user_id: uuid.UUID,
    path_id: uuid.UUID,
    new_status: PathStatus,
) -> SimpleNamespace:
    plan = await PlannerAuditRepository(db).get_latest_plan_for_user(
        user_id,
        trigger="generate_canonical_learning_path",
    )
    if plan is None or not plan.recommended_path_json:
        raise NotFoundError("Canonical learning path not found for current user.")

    if not any(
        isinstance(item, dict) and str(item.get("learning_unit_id")) == str(path_id)
        for item in plan.recommended_path_json
    ):
        raise NotFoundError("Learning unit is not part of the current canonical path.")

    content_repo = CanonicalContentRepository(db)
    unit_by_id = await content_repo.get_learning_units_by_ids([path_id])
    unit = unit_by_id.get(path_id)
    if unit is None:
        raise NotFoundError("Canonical learning unit not found.")

    now = datetime.now(UTC)
    progress_repo = LearningProgressRepository(db)
    waived_repo = WaivedUnitRepository(db)
    progress_status = _path_status_to_progress_status(new_status)

    mastery_lcb = None
    evidence_items: list[dict[str, object]] = []
    skip_quiz = None
    if new_status == PathStatus.skipped and settings.write_waived_units_enabled:
        mastery_lcb, evidence_items = await _build_waive_evidence(
            db,
            user_id=user_id,
            canonical_unit_id=unit.canonical_unit_id,
        )
        skip_quiz = await _latest_quiz_score_percent(db, user_id=user_id, learning_unit_id=unit.id)
        if not can_skip_unit(mastery_lcb=mastery_lcb, skip_quiz_score=skip_quiz):
            raise ForbiddenError(
                "Learning unit cannot be skipped without sufficient mastery LCB or skip-verification score."
            )

    progress_row = await progress_repo.upsert(
        user_id=user_id,
        course_id=unit.course_id,
        learning_unit_id=unit.id,
        status=progress_status,
        last_opened_at=now,
        completed_at=now if new_status == PathStatus.completed else None,
    )

    if new_status == PathStatus.skipped and settings.write_waived_units_enabled:
        await waived_repo.upsert(
            user_id=user_id,
            learning_unit_id=unit.id,
            evidence_items=evidence_items,
            mastery_lcb_at_waive=mastery_lcb,
            skip_quiz_score=skip_quiz,
        )
    else:
        await waived_repo.delete_for_user_unit(user_id, unit.id)

    await PlannerAuditRepository(db).upsert_session_state(
        user_id=user_id,
        session_id="canonical-learning-path",
        last_plan_history_id=plan.id,
        bridge_chain_depth=0,
        consecutive_bridge_count=0,
        current_unit_id=unit.id,
        current_stage=_path_status_to_current_stage(new_status),
        current_progress={
            "learning_unit_id": str(unit.id),
            "status": new_status.value,
            "video_finished": new_status in {PathStatus.completed, PathStatus.skipped},
        },
        last_activity=now,
        state_json={
            "canonical_runtime": True,
            "last_status_update": {
                "learning_unit_id": str(unit.id),
                "status": new_status.value,
                "updated_at": now.isoformat(),
            },
        },
    )

    return SimpleNamespace(
        id=unit.id,
        learning_unit_id=unit.id,
        status=new_status,
        updated_at=progress_row.completed_at or progress_row.last_opened_at,
    )


def _path_status_to_progress_status(status: PathStatus) -> LearningProgressStatus:
    return {
        PathStatus.pending: LearningProgressStatus.not_started,
        PathStatus.in_progress: LearningProgressStatus.in_progress,
        PathStatus.completed: LearningProgressStatus.completed,
        PathStatus.skipped: LearningProgressStatus.skipped,
    }[status]


def _path_status_to_current_stage(status: PathStatus) -> str:
    return {
        PathStatus.pending: "between_units",
        PathStatus.in_progress: "watching",
        PathStatus.completed: "post_quiz",
        PathStatus.skipped: "between_units",
    }[status]


def _progress_status_to_path_status(status: LearningProgressStatus) -> PathStatus:
    return {
        LearningProgressStatus.not_started: PathStatus.pending,
        LearningProgressStatus.in_progress: PathStatus.in_progress,
        LearningProgressStatus.completed: PathStatus.completed,
        LearningProgressStatus.blocked: PathStatus.pending,
        LearningProgressStatus.skipped: PathStatus.skipped,
    }[status]


async def _get_canonical_path_status_map(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    learning_unit_ids: list[uuid.UUID],
) -> dict[uuid.UUID, PathStatus]:
    progress_repo = LearningProgressRepository(db)
    waived_repo = WaivedUnitRepository(db)
    progress_by_unit = await progress_repo.list_for_user_units(user_id, learning_unit_ids)
    waived_by_unit = await waived_repo.list_for_user_units(user_id, learning_unit_ids)

    status_by_unit: dict[uuid.UUID, PathStatus] = {}
    for learning_unit_id in learning_unit_ids:
        if learning_unit_id in waived_by_unit:
            status_by_unit[learning_unit_id] = PathStatus.skipped
            continue
        progress = progress_by_unit.get(learning_unit_id)
        if progress is not None:
            status_by_unit[learning_unit_id] = _progress_status_to_path_status(progress.status)

    return status_by_unit


async def _build_waive_evidence(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    canonical_unit_id: str | None,
) -> tuple[float | None, list[dict[str, object]]]:
    if not canonical_unit_id:
        return None, []

    content_repo = CanonicalContentRepository(db)
    unit_kp_rows = await content_repo.get_unit_kp_rows([canonical_unit_id])
    kp_ids = sorted({row.kp_id for row in unit_kp_rows})
    if not kp_ids:
        return None, []

    mastery_by_kp = await LearnerMasteryKPRepository(db).bulk_get_for_user(user_id, kp_ids)
    generated_at = datetime.now(UTC)
    evidence_items: list[dict[str, object]] = []
    mastery_values: list[float] = []
    for kp_id in kp_ids:
        mastery = mastery_by_kp.get(kp_id)
        if mastery is None:
            continue
        mastery_lcb = estimate_mastery_lcb_on_read(mastery, now=generated_at)
        mastery_values.append(mastery_lcb)
        evidence_items.append(
            {
                "type": "kp_mastery_snapshot",
                "kp_id": kp_id,
                "mastery_mean_cached": mastery.mastery_mean_cached,
                "mastery_lcb_on_read": mastery_lcb,
                "theta_mu": mastery.theta_mu,
                "theta_sigma": mastery.theta_sigma,
                "n_items_observed": mastery.n_items_observed,
            }
        )

    mastery_lcb = min(mastery_values) if mastery_values else None
    return mastery_lcb, evidence_items


async def _latest_quiz_score_percent(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    learning_unit_id: uuid.UUID,
) -> float | None:
    from sqlalchemy import select

    result = await db.execute(
        select(Session.score_percent)
        .where(
            Session.user_id == user_id,
            Session.session_type == SessionType.quiz,
            Session.canonical_unit_id == learning_unit_id,
            Session.completed_at.isnot(None),
        )
        .order_by(Session.completed_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
