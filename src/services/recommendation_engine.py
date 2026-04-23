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

from src.exceptions import NotFoundError, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.learning import (
    PathAction,
    PathStatus,
)
from src.models.user import User
from src.repositories.canonical_content_repo import CanonicalContentRepository
from src.repositories.goal_preference_repo import GoalPreferenceRepository
from src.repositories.learner_mastery_kp_repo import LearnerMasteryKPRepository
from src.repositories.planner_audit_repo import PlannerAuditRepository
from src.schemas.learning_path import (
    GeneratePathRequest,
    GeneratePathResponse,
    PathItemResponse,
)
from src.services.canonical_planner_service import classify_unit_action

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
            mastery_by_kp[kp_id].mastery_mean_cached
            for kp_id in unit_kps
            if kp_id in mastery_by_kp
        ]
        mastery_lcb = min(mastery_values) if mastery_values else 0.0
        action_value = classify_unit_action(mastery_lcb)
        action = PathAction(action_value)
        estimated_hours = 0.0 if action == PathAction.skip else ((unit.estimated_minutes or 30) / 60.0)

        item = PathItemResponse(
            id=unit.id,
            topic_id=None,
            topic_name=unit.title,
            module_name="canonical_unit",
            action=action,
            estimated_hours=estimated_hours if estimated_hours > 0 else None,
            order_index=order_index,
            week_number=None,
            status=PathStatus.pending,
            learning_unit_id=unit.id,
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
            rationale_text=f"Canonical planner selected unit `{item.topic_name}` as `{item.action.value}`.",
        )

    await audit_repo.upsert_session_state(
        user_id=user.id,
        session_id="canonical-learning-path",
        last_plan_history_id=plan.id,
        bridge_chain_depth=0,
        consecutive_bridge_count=0,
        state_json={
            "canonical_runtime": True,
            "generated_at": generated_at.isoformat(),
            "unit_count": len(items),
        },
    )

    return GeneratePathResponse(
        generated_at=generated_at,
        total_topics=len(items),
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
            topic_id=None,
            action=action,
            estimated_hours=item.get("estimated_hours"),
            order_index=int(item.get("order_index", fallback_order)),
            week_number=item.get("week_number"),
            status=PathStatus.pending,
            learning_unit_id=unit_id,
            canonical_unit_id=item.get("canonical_unit_id"),
        )
        rows.append((row, unit.title if unit is not None else str(unit_id), "canonical_unit"))

    return sorted(rows, key=lambda row: row[0].order_index)


# ---------------------------------------------------------------------------
# PUT /api/learning-path/{path_id}/status
# ---------------------------------------------------------------------------


async def update_path_status(
    db: AsyncSession,
    user_id: uuid.UUID,
    path_id: uuid.UUID,
    new_status: PathStatus,
) -> None:
    raise ValidationError(
        "Canonical planner status updates must write a canonical progress/audit table; "
        "legacy learning_paths writes are removed."
    )
