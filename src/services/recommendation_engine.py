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
from src.repositories.placement_assessment_repo import PlacementAssessmentRepository
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


def _unit_active(unit: object | None) -> bool:
    active_value = getattr(unit, "active", True)
    return True if active_value is None else bool(active_value)


def _section_flags(unit: object | None) -> set[str]:
    flags = getattr(unit, "section_flags", None)
    if not isinstance(flags, list):
        return set()
    return {str(flag).strip().lower() for flag in flags if str(flag).strip()}


def _segment_policy(unit: object | None) -> str:
    if not _unit_active(unit):
        return "hidden"
    flags = _section_flags(unit)
    content_type = str(getattr(unit, "content_type", "") or "").strip().lower()
    if flags.intersection({"logistics", "admin", "administrative"}) or content_type in {
        "logistics",
        "admin",
        "administrative",
    }:
        return "hidden"
    if "reference" in flags or content_type == "reference":
        return "reference"
    if getattr(unit, "is_worth_learning", None) is False:
        return "reference"
    return "core"


def _high_salience(unit: object | None) -> bool:
    raw = getattr(unit, "salience_score", None)
    if raw is None:
        return False
    if isinstance(raw, (int, float)):
        return float(raw) >= 0.75
    value = str(raw).strip().lower()
    if value in {"critical", "high"}:
        return True
    try:
        return float(value) >= 0.75
    except ValueError:
        return False


def _planner_reason_codes(
    *,
    action: PathAction,
    canonical_unit: object | None,
    has_quiz_items: bool,
    segment_policy: str,
) -> list[str]:
    reason_codes: list[str] = []
    content_type = str(getattr(canonical_unit, "content_type", "") or "").strip().lower()

    if getattr(canonical_unit, "override_critical_kp", False):
        reason_codes.append("critical_kp")
    if _high_salience(canonical_unit):
        reason_codes.append("high_salience")
    if has_quiz_items:
        reason_codes.append("quiz_available")
    if content_type in {"prerequisite", "foundation"}:
        reason_codes.append("required_prerequisite")
    if action == PathAction.skip:
        reason_codes.append("skip_by_mastery")
    if action == PathAction.quick_review:
        reason_codes.append("quick_review")
    if segment_policy == "hidden":
        reason_codes.append("hidden_logistics")
    if segment_policy == "reference":
        reason_codes.append("reference_only")

    return reason_codes


def _derive_salience_from_kp_rows(unit_kp_rows: list[object]) -> str | None:
    weights: list[float] = []
    for row in unit_kp_rows:
        planner_role = str(getattr(row, "planner_role", "") or "").strip().lower()
        coverage_level = str(getattr(row, "coverage_level", "") or "").strip().lower()
        if planner_role not in {"", "main", "prereq", "prerequisite"}:
            continue
        if coverage_level == "mention":
            continue
        weight = getattr(row, "coverage_weight", None)
        if isinstance(weight, (int, float)):
            weights.append(float(weight))

    if not weights:
        return None
    return f"{max(weights):g}"


def _has_critical_gateway_kp(
    unit_kp_rows: list[object],
    kp_by_id: dict[str, object],
) -> bool:
    for row in unit_kp_rows:
        planner_role = str(getattr(row, "planner_role", "") or "").strip().lower()
        if planner_role not in {"", "main", "prereq", "prerequisite"}:
            continue
        kp = kp_by_id.get(str(getattr(row, "kp_id", "") or ""))
        if kp is None:
            continue
        importance = str(getattr(kp, "importance_level", "") or "").strip().lower()
        structural_role = str(getattr(kp, "structural_role", "") or "").strip().lower()
        if importance == "critical" and structural_role == "gateway":
            return True
    return False


def classify_schema_v2_unit_priority(
    unit: object,
    *,
    unit_kp_rows: list[object],
    kp_by_id: dict[str, object],
    quiz_item_count: int,
    action: PathAction,
) -> SimpleNamespace:
    """Classify a canonical unit using denormalized fields first, graph fallback second."""

    segment_policy = _segment_policy(unit)
    derived_salience = _derive_salience_from_kp_rows(unit_kp_rows)
    salience_score = getattr(unit, "salience_score", None) or derived_salience
    has_quiz_items = bool(getattr(unit, "has_quiz_items", False) or quiz_item_count > 0)
    override_critical = bool(getattr(unit, "override_critical_kp", False)) or _has_critical_gateway_kp(
        unit_kp_rows,
        kp_by_id,
    )

    canonical_unit = SimpleNamespace(
        content_type=getattr(unit, "content_type", None),
        salience_score=salience_score,
        has_quiz_items=has_quiz_items,
        is_worth_learning=getattr(unit, "is_worth_learning", None),
        override_critical_kp=override_critical,
        active=getattr(unit, "active", True),
        section_flags=getattr(unit, "section_flags", []),
    )
    reason_codes = _planner_reason_codes(
        action=action,
        canonical_unit=canonical_unit,
        has_quiz_items=has_quiz_items,
        segment_policy=segment_policy,
    )

    return SimpleNamespace(
        segment_policy=segment_policy,
        reason_codes=reason_codes,
        has_quiz_items=has_quiz_items,
        salience_score=str(salience_score) if salience_score is not None else None,
        override_critical_kp=override_critical,
    )


def find_prerequisite_gaps(
    *,
    target_kp_ids: list[str],
    prerequisite_edges: list[object],
    mastered_kp_ids: set[str],
    max_depth: int = 2,
) -> list[str]:
    """Walk prerequisite edges backwards and return unmastered KP gaps up to `max_depth`."""

    parents_by_target: dict[str, list[str]] = {}
    for edge in prerequisite_edges:
        if getattr(edge, "active", True) is False:
            continue
        source = str(getattr(edge, "source_kp_id", "") or "")
        target = str(getattr(edge, "target_kp_id", "") or "")
        if source and target:
            parents_by_target.setdefault(target, []).append(source)

    gaps: list[str] = []
    seen = set(target_kp_ids)
    frontier = [(kp_id, 0) for kp_id in target_kp_ids]
    while frontier:
        current, depth = frontier.pop(0)
        if depth >= max_depth:
            continue
        for parent in parents_by_target.get(current, []):
            if parent in seen:
                continue
            seen.add(parent)
            if parent not in mastered_kp_ids:
                gaps.append(parent)
                frontier.append((parent, depth + 1))

    return gaps


def is_mastery_evidence_backed(mastery: object | None) -> bool:
    if mastery is None:
        return False
    updated_by = str(getattr(mastery, "updated_by", "") or "").strip().lower()
    observed = int(getattr(mastery, "n_items_observed", 0) or 0)
    if observed <= 0:
        return False
    return updated_by not in {"self_report", "self-report", "manual_prior"}


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
    selected_course_ids = list(goal.selected_course_ids) if goal and goal.selected_course_ids else []
    if not selected_course_ids:
        selected_course_ids = [
            str(course_id).strip()
            for course_id in request.selected_course_ids
            if str(course_id).strip()
        ]
    if not selected_course_ids:
        raise ValidationError(
            "Canonical planner requires selected_course_ids or goal_preferences.selected_course_ids."
        )

    units = await content_repo.get_linked_learning_units(selected_course_ids)
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
    canonical_unit_by_id = await content_repo.get_canonical_units_by_ids(canonical_unit_ids)
    quiz_counts_by_unit_id = await content_repo.get_quiz_item_counts_by_unit_ids(canonical_unit_ids)
    kp_ids = sorted({row.kp_id for row in unit_kp_rows})
    kp_by_id = await content_repo.get_concepts_by_ids(kp_ids)
    unit_kp_rows_by_unit_id: dict[str, list[object]] = {}
    for row in unit_kp_rows:
        unit_kp_rows_by_unit_id.setdefault(row.unit_id, []).append(row)

    mastery_repo = LearnerMasteryKPRepository(db)
    mastery_by_kp = await mastery_repo.bulk_get_for_user(user.id, kp_ids)

    # Load placement results for Phase A/B split
    placement_results = await PlacementAssessmentRepository(db).get_by_user_id(user.id)
    placement_by_unit: dict[uuid.UUID, str] = {
        row.topic_unit_id: row.decision for row in placement_results
    }
    placement_score_by_unit: dict[uuid.UUID, float] = {
        row.topic_unit_id: float(row.score_pct) for row in placement_results
    }
    has_placement = len(placement_by_unit) > 0
    placement_skipped = getattr(goal, "placement_status", None) == "skipped"

    generated_at = datetime.now(UTC)
    items: list[PathItemResponse] = []
    recommended_path_json = []
    course_id_by_unit: dict[uuid.UUID, uuid.UUID] = {}

    for order_index, unit in enumerate(units):
        canonical_unit = (
            canonical_unit_by_id.get(unit.canonical_unit_id)
            if unit.canonical_unit_id
            else None
        )
        current_unit_kp_rows = unit_kp_rows_by_unit_id.get(unit.canonical_unit_id or "", [])
        unit_kps = [row.kp_id for row in current_unit_kp_rows]
        mastery_values = [
            estimate_mastery_lcb_on_read(mastery_by_kp[kp_id], now=generated_at)
            for kp_id in unit_kps
            if kp_id in mastery_by_kp
        ]
        mastery_lcb = min(mastery_values) if mastery_values else 0.0
        action_value = classify_unit_action(mastery_lcb)
        action = PathAction(action_value)
        priority = classify_schema_v2_unit_priority(
            canonical_unit or SimpleNamespace(active=True),
            unit_kp_rows=current_unit_kp_rows,
            kp_by_id=kp_by_id,
            quiz_item_count=quiz_counts_by_unit_id.get(unit.canonical_unit_id or "", 0),
            action=action,
        )
        segment_policy = priority.segment_policy
        has_quiz_items = priority.has_quiz_items
        reason_codes = priority.reason_codes
        if segment_policy == "hidden":
            estimated_hours = 0.0
        else:
            estimated_hours = 0.0 if action == PathAction.skip else ((unit.estimated_minutes or 30) / 60.0)

        # Determine Phase A/B tag and rationale
        if placement_skipped:
            phase_tag = None
            is_locked = False
            rationale_log = "placement_skipped_by_user"
        elif not has_placement:
            phase_tag = None
            is_locked = False
            rationale_log = None
        else:
            decision = placement_by_unit.get(unit.id)
            if decision is None:
                # Not assessed — include in Phase A as prereq
                phase_tag = "phase_a"
                is_locked = False
                rationale_log = "placement_prereq_unassessed"
            elif decision == "skip":
                # Already mastered — Phase B, locked
                phase_tag = "phase_b"
                is_locked = True
                rationale_log = None
            else:
                # "review" or "relearn" — Phase A
                phase_tag = "phase_a"
                is_locked = False
                score_pct = placement_score_by_unit.get(unit.id, 0.0)
                if decision == "review":
                    rationale_log = f"placement_review_score={round(score_pct)}"
                else:
                    rationale_log = f"placement_relearn_score={round(score_pct)}"

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
            reason_codes=reason_codes,
            prerequisite_gap_kp_ids=[],
            segment_policy=segment_policy,
            content_type=getattr(canonical_unit, "content_type", None),
            salience_score=priority.salience_score,
            has_quiz_items=has_quiz_items,
            is_worth_learning=getattr(canonical_unit, "is_worth_learning", None),
            override_critical_kp=bool(priority.override_critical_kp),
            phase_tag=phase_tag,
            is_locked=is_locked,
            rationale_log=rationale_log,
        )
        items.append(item)
        course_id_by_unit[unit.id] = unit.course_id
        recommended_path_json.append(
            {
                "learning_unit_id": str(unit.id),
                "canonical_unit_id": unit.canonical_unit_id,
                "action": action.value,
                "estimated_hours": estimated_hours,
                "order_index": order_index,
                "kp_ids": unit_kps,
                "mastery_lcb": mastery_lcb,
                "reason_codes": reason_codes,
                "prerequisite_gap_kp_ids": [],
                "segment_policy": segment_policy,
                "content_type": getattr(canonical_unit, "content_type", None),
                "salience_score": priority.salience_score,
                "has_quiz_items": has_quiz_items,
                "is_worth_learning": getattr(canonical_unit, "is_worth_learning", None),
                "override_critical_kp": bool(priority.override_critical_kp),
                "phase_tag": phase_tag,
                "is_locked": is_locked,
                "rationale_log": rationale_log,
            }
        )

    # Sort: Phase A interleaved round-robin by course, then Phase B
    if has_placement and not placement_skipped:
        phase_a = [i for i in items if i.phase_tag == "phase_a"]
        phase_b = [i for i in items if i.phase_tag == "phase_b"]

        # Group Phase A items by course_id, preserving original order within each group
        phase_a_by_course: dict[uuid.UUID, list[PathItemResponse]] = {}
        for item in phase_a:
            cid = course_id_by_unit[item.learning_unit_id]
            phase_a_by_course.setdefault(cid, []).append(item)

        # Round-robin across courses
        course_groups = list(phase_a_by_course.values())
        interleaved: list[PathItemResponse] = []
        max_len = max((len(g) for g in course_groups), default=0)
        for idx in range(max_len):
            for group in course_groups:
                if idx < len(group):
                    interleaved.append(group[idx])

        items = interleaved + phase_b
        # Re-assign order_index to reflect new ordering
        for new_order, item in enumerate(items):
            item.order_index = new_order

    total_hours = sum(item.estimated_hours or 0.0 for item in items)
    plan = await audit_repo.create_plan(
        user_id=user.id,
        trigger="generate_canonical_learning_path",
        recommended_path_json=recommended_path_json,
        goal_snapshot_json={
            "selected_course_ids": selected_course_ids,
            "derived_from_course_set_hash": getattr(goal, "derived_from_course_set_hash", None),
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
        if getattr(lp, "segment_policy", None) == "hidden":
            continue
        week = lp.week_number or 1
        grouped.setdefault(week, []).append(row)
    return grouped


async def _phase_b_unlocked(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    phase_a_unit_ids: list[uuid.UUID],
    unit_by_id: dict[uuid.UUID, object],
    content_repo: CanonicalContentRepository,
) -> bool:
    """Return True if all Phase A units have min mastery_lcb >= 0.7, else False.

    A unit with no mastery records is treated as LCB=0 (not cleared).
    If there are no Phase A units, Phase B is unlocked.
    """
    if not phase_a_unit_ids:
        return True

    canonical_unit_ids = [
        unit.canonical_unit_id
        for uid in phase_a_unit_ids
        if (unit := unit_by_id.get(uid)) is not None and unit.canonical_unit_id
    ]
    if not canonical_unit_ids:
        return False

    unit_kp_rows = await content_repo.get_unit_kp_rows(canonical_unit_ids)
    kp_ids = sorted({row.kp_id for row in unit_kp_rows})
    mastery_by_kp = await LearnerMasteryKPRepository(db).bulk_get_for_user(user_id, kp_ids)

    now = datetime.now(UTC)

    # Build kp_ids per canonical_unit_id
    kps_by_canonical: dict[str, list[str]] = {}
    for row in unit_kp_rows:
        kps_by_canonical.setdefault(row.unit_id, []).append(row.kp_id)

    # For each Phase A unit, compute min LCB across its KPs
    for uid in phase_a_unit_ids:
        unit = unit_by_id.get(uid)
        canonical_id = unit.canonical_unit_id if unit is not None else None
        kps = kps_by_canonical.get(canonical_id, []) if canonical_id else []
        mastery_values = [
            estimate_mastery_lcb_on_read(mastery_by_kp[kp_id], now=now)
            for kp_id in kps
            if kp_id in mastery_by_kp
        ]
        min_lcb = min(mastery_values) if mastery_values else 0.0
        if min_lcb < 0.7:
            return False

    return True


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

    content_repo = CanonicalContentRepository(db)
    unit_by_id = await content_repo.get_learning_units_by_ids(learning_unit_ids)
    section_by_id = await content_repo.get_sections_by_ids(
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
            reason_codes=list(item.get("reason_codes") or []),
            prerequisite_gap_kp_ids=list(item.get("prerequisite_gap_kp_ids") or []),
            segment_policy=item.get("segment_policy"),
            content_type=item.get("content_type"),
            salience_score=item.get("salience_score"),
            has_quiz_items=item.get("has_quiz_items"),
            is_worth_learning=item.get("is_worth_learning"),
            override_critical_kp=bool(item.get("override_critical_kp", False)),
            phase_tag=item.get("phase_tag"),
            is_locked=bool(item.get("is_locked", False)),
            rationale_log=item.get("rationale_log"),
        )
        section_title = None
        if unit is not None:
            section = section_by_id.get(unit.section_id)
            section_title = section.title if section is not None else None
        rows.append((row, unit.title if unit is not None else str(unit_id), section_title or "canonical_unit"))

    # Fix 3: Dynamic gate — recompute is_locked for Phase B based on current Phase A mastery
    phase_a_unit_ids = [
        row[0].learning_unit_id for row in rows if row[0].phase_tag == "phase_a"
    ]
    phase_b_unlocked = await _phase_b_unlocked(
        db,
        user_id=user_id,
        phase_a_unit_ids=phase_a_unit_ids,
        unit_by_id=unit_by_id,
        content_repo=content_repo,
    )
    if phase_b_unlocked:
        for row_tuple in rows:
            if row_tuple[0].phase_tag == "phase_b":
                row_tuple[0].is_locked = False

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
