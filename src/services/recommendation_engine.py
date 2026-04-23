"""
services/recommendation_engine.py
-----------------------------------
Rule-based personalised learning path generator.

Algorithm (step-by-step)
------------------------
1.  Load all Topics belonging to the user's desired_module_ids.
2.  Build prerequisite_graph from Topic.prerequisite_topic_ids.
3.  Topological-sort topics within the working set.
4.  For each topic (in topo order) determine the action + estimated_hours:

        mastery_score ≥ 76  → skip          (0 hours)
        mastery_score 51–75 → quick_review   (topic.estimated_hours_review)
        mastery_score 26–50 → standard_learn (topic.estimated_hours_intermediate)
        mastery_score  0–25 → deep_practice  (topic.estimated_hours_beginner)

    Override to "remediate" if the user has an unresolved misconception linked
    to this topic AND mastery < 76.  The estimated_hours is the topic's
    beginner estimate (most thorough).

5.  Run timeline_builder.build_timeline() to assign week numbers.
6.  Delete old LearningPath rows for this user (full replace).
7.  Insert new LearningPath rows (one per topic).
8.  Return a GeneratePathResponse.

Fallback hours
--------------
If a topic doesn't have the specific estimate for the chosen action, we fall
back through the chain:  review → intermediate → beginner → 1.0 h.

Misconception detection
-----------------------
Misconceptions are recorded as string IDs (not UUIDs) in
Interaction.question.misconception_{a,b,c,d}_id.
We load all interactions where:
  - user answered INCORRECTLY
  - question belongs to a topic in the working set
  - the question carries a misconception ID for the chosen distractor

A misconception is "unresolved" unless the user later answered the same
topic correctly in a *newer* interaction (crude recency check).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from src.exceptions import NotFoundError, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.content import Module, Topic
from src.models.learning import (
    Interaction,
    LearningPath,
    MasteryScore,
    PathAction,
    PathStatus,
    SelectedAnswer,
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
from src.services.timeline_builder import TopicSlot, build_timeline
from src.utils.topological_sort import CycleDetectedError, topological_sort

# ---------------------------------------------------------------------------
# Mastery → action mapping
# ---------------------------------------------------------------------------


def _mastery_to_action(score_percent: float) -> PathAction:
    if score_percent >= 76:
        return PathAction.skip
    if score_percent >= 51:
        return PathAction.quick_review
    if score_percent >= 26:
        return PathAction.standard_learn
    return PathAction.deep_practice


def _pick_hours(topic: Topic, action: PathAction) -> float:
    """
    Return estimated_hours for a topic given the chosen action.
    Falls back gracefully when a field is NULL.
    """
    candidates: list[float | None]
    if action == PathAction.quick_review:
        candidates = [
            topic.estimated_hours_review,
            topic.estimated_hours_intermediate,
            topic.estimated_hours_beginner,
        ]
    elif action == PathAction.standard_learn:
        candidates = [
            topic.estimated_hours_intermediate,
            topic.estimated_hours_beginner,
            topic.estimated_hours_review,
        ]
    elif action in (PathAction.deep_practice, PathAction.remediate):
        candidates = [
            topic.estimated_hours_beginner,
            topic.estimated_hours_intermediate,
            topic.estimated_hours_review,
        ]
    else:  # skip
        return 0.0

    for h in candidates:
        if h is not None and h > 0:
            return h
    return 1.0  # absolute fallback


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def generate_learning_path(
    db: AsyncSession,
    user: User,
    request: GeneratePathRequest,
) -> GeneratePathResponse:
    """
    Generate (or regenerate) the personalised learning path for `user`.

    1. Resolve topics for the requested modules.
    2. Build prerequisite graph & topological sort.
    3. Classify each topic (action + hours) using mastery scores.
    4. Detect unresolved misconceptions.
    5. Run timeline builder.
    6. Persist (full replace) LearningPath rows.
    7. Return GeneratePathResponse.
    """
    if settings.read_canonical_planner_enabled:
        return await _generate_canonical_learning_path(db, user, request)

    if not settings.allow_legacy_planner_writes:
        raise ValidationError(
            "Legacy planner writes are disabled. Enable READ_CANONICAL_PLANNER_ENABLED and use canonical planner."
        )

    # ── 1. Load topics for desired modules ──────────────────────────────────
    module_ids = request.desired_module_ids
    topics_result = await db.execute(
        select(Topic, Module.name.label("module_name"))
        .join(Module, Topic.module_id == Module.id)
        .where(Topic.module_id.in_(module_ids))
        .order_by(Topic.module_id, Topic.order_index)
    )
    rows = topics_result.all()

    if not rows:
        raise NotFoundError("No topics found for the specified modules.")

    topics: list[Topic] = [r[0] for r in rows]
    topic_module_name: dict[uuid.UUID, str] = {r[0].id: r[1] for r in rows}
    topic_by_id: dict[uuid.UUID, Topic] = {t.id: t for t in topics}
    topic_ids: list[uuid.UUID] = [t.id for t in topics]

    # ── 2. Build prerequisite graph ──────────────────────────────────────────
    prereq_graph: dict[uuid.UUID, list[uuid.UUID]] = {}
    for topic in topics:
        prereqs: list[uuid.UUID] = []
        if topic.prerequisite_topic_ids:
            for raw in topic.prerequisite_topic_ids:
                try:
                    prereqs.append(uuid.UUID(str(raw)))
                except (ValueError, AttributeError):
                    pass  # ignore malformed IDs
        prereq_graph[topic.id] = prereqs

    # ── 3. Topological sort ───────────────────────────────────────────────────
    try:
        sorted_ids = topological_sort(topic_ids, prereq_graph)
    except CycleDetectedError as exc:
        raise ValidationError(f"Prerequisite cycle detected: {exc}") from exc

    # ── 4. Load mastery scores ────────────────────────────────────────────────
    mastery_result = await db.execute(
        select(MasteryScore).where(
            MasteryScore.user_id == user.id,
            MasteryScore.topic_id.in_(topic_ids),
            MasteryScore.kc_id.is_(None),  # topic-grain only
        )
    )
    mastery_by_topic: dict[uuid.UUID, float] = {}
    for ms in mastery_result.scalars().all():
        mastery_by_topic[ms.topic_id] = ms.mastery_probability * 100  # → percent

    # Apply any caller-supplied overrides (used for re-generation after practice)
    if request.mastery_overrides:
        for tid_str, pct in request.mastery_overrides.items():
            try:
                mastery_by_topic[uuid.UUID(tid_str)] = float(pct)
            except (ValueError, AttributeError):
                pass

    # ── 5. Detect unresolved misconceptions per topic ─────────────────────────
    misconception_topics = await _find_misconception_topics(db, user.id, topic_ids)

    # ── 6. Build action + hours for each topic ────────────────────────────────
    @dataclass_like
    class _ClassifiedTopic:
        topic: Topic
        action: PathAction
        estimated_hours: float
        order_index: int
        module_name: str

    classified: list[_ClassifiedTopic] = []
    for order_idx, tid in enumerate(sorted_ids):
        topic = topic_by_id[tid]
        score = mastery_by_topic.get(tid, 0.0)
        action = _mastery_to_action(score)

        # Remediation override: only when not already skipped
        if tid in misconception_topics and action != PathAction.skip:
            action = PathAction.remediate

        hours = _pick_hours(topic, action)
        classified.append(
            _ClassifiedTopic(
                topic=topic,
                action=action,
                estimated_hours=hours,
                order_index=order_idx,
                module_name=topic_module_name.get(tid, ""),
            )
        )

    # ── 7. Build timeline ──────────────────────────────────────────────────────
    slots = [
        TopicSlot(
            topic_id=c.topic.id,
            estimated_hours=c.estimated_hours,
        )
        for c in classified
    ]
    timeline = build_timeline(
        items=slots,
        available_hours_per_week=user.available_hours_per_week or 5.0,
        deadline=user.target_deadline,
    )

    # ── 8. Persist: full replace ──────────────────────────────────────────────
    await db.execute(delete(LearningPath).where(LearningPath.user_id == user.id))
    await db.flush()

    now = datetime.now(UTC)
    lp_records: list[LearningPath] = []
    for c in classified:
        week_num = timeline.topic_week_map.get(c.topic.id)
        lp = LearningPath(
            user_id=user.id,
            topic_id=c.topic.id,
            action=c.action,
            estimated_hours=c.estimated_hours if c.estimated_hours > 0 else None,
            order_index=c.order_index,
            week_number=week_num,
            status=PathStatus.pending,
        )
        db.add(lp)
        lp_records.append(lp)

    await db.flush()

    # Refresh all records to get auto-generated IDs and timestamps
    for lp in lp_records:
        await db.refresh(lp)

    await _write_planner_audit_if_enabled(
        db=db,
        user_id=user.id,
        now=now,
        classified=classified,
        timeline=timeline,
        mastery_by_topic=mastery_by_topic,
        misconception_topics=misconception_topics,
    )

    # ── 9. Build response ─────────────────────────────────────────────────────
    items: list[PathItemResponse] = []
    for c, lp in zip(classified, lp_records):
        items.append(
            PathItemResponse(
                id=lp.id,
                topic_id=c.topic.id,
                topic_name=c.topic.name,
                module_name=c.module_name,
                action=c.action,
                estimated_hours=lp.estimated_hours,
                order_index=lp.order_index,
                week_number=lp.week_number,
                status=lp.status,
            )
        )

    return GeneratePathResponse(
        generated_at=now,
        total_topics=len(classified),
        total_hours=timeline.total_hours,
        required_hours_per_week=timeline.required_hours_per_week,
        warnings=timeline.warnings,
        items=items,
    )


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


async def _write_planner_audit_if_enabled(
    db: AsyncSession,
    user_id: uuid.UUID,
    now: datetime,
    classified: list,
    timeline,
    mastery_by_topic: dict[uuid.UUID, float],
    misconception_topics: set[uuid.UUID],
) -> None:
    """
    Persist planner audit rows using legacy topic-grain payloads.

    This is intentionally compatibility-oriented: `learning_unit_id` remains null
    because the current runtime planner still ranks topics, not canonical units.
    The sidecar rows give the next integration phase an audit trail without
    forcing a premature topic->unit mapping.
    """
    if not settings.write_planner_audit_enabled:
        return

    repo = PlannerAuditRepository(db)
    recommended_path_json = []
    for item in classified:
        week_number = timeline.topic_week_map.get(item.topic.id)
        recommended_path_json.append(
            {
                "topic_id": str(item.topic.id),
                "module_name": item.module_name,
                "action": item.action.value,
                "estimated_hours": item.estimated_hours,
                "order_index": item.order_index,
                "week_number": week_number,
            }
        )

    plan = await repo.create_plan(
        user_id=user_id,
        trigger="generate_learning_path",
        recommended_path_json=recommended_path_json,
        goal_snapshot_json={
            "legacy_runtime": True,
            "generated_at": now.isoformat(),
        },
        weights_used_json={
            "legacy_planner": True,
            "kg_phase": settings.kg_phase,
        },
    )

    for rank, item in enumerate(classified, start=1):
        week_number = timeline.topic_week_map.get(item.topic.id)
        await repo.add_rationale(
            plan_history_id=plan.id,
            learning_unit_id=None,
            rank=rank,
            reason_code=f"legacy_topic_{item.action.value}",
            term_breakdown_json={
                "topic_id": str(item.topic.id),
                "module_name": item.module_name,
                "legacy_mastery_percent": mastery_by_topic.get(item.topic.id, 0.0),
                "has_unresolved_misconception": item.topic.id in misconception_topics,
                "week_number": week_number,
                "estimated_hours": item.estimated_hours,
            },
            rationale_text=(
                f"Legacy topic planner chose `{item.action.value}` for topic `{item.topic.name}` "
                f"at order {item.order_index}."
            ),
        )

    skipped_topic_ids = [
        str(item.topic.id)
        for item in classified
        if item.action == PathAction.skip
    ]
    await repo.upsert_session_state(
        user_id=user_id,
        session_id="learning-path",
        last_plan_history_id=plan.id,
        bridge_chain_depth=0,
        consecutive_bridge_count=0,
        state_json={
            "legacy_runtime": True,
            "generated_at": now.isoformat(),
            "topic_count": len(classified),
            "skipped_topic_ids": skipped_topic_ids,
        },
    )


# ---------------------------------------------------------------------------
# GET /api/learning-path — current path
# ---------------------------------------------------------------------------


async def get_learning_path(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[tuple[LearningPath, str, str]]:
    """
    Return all LearningPath rows for the user with topic_name + module_name.
    Returns list of (LearningPath, topic_name, module_name).
    """
    result = await db.execute(
        select(
            LearningPath,
            Topic.name.label("topic_name"),
            Module.name.label("module_name"),
        )
        .join(Topic, LearningPath.topic_id == Topic.id)
        .join(Module, Topic.module_id == Module.id)
        .where(LearningPath.user_id == user_id)
        .order_by(LearningPath.order_index)
    )
    return result.all()


# ---------------------------------------------------------------------------
# GET /api/learning-path/timeline
# ---------------------------------------------------------------------------


async def get_learning_path_timeline(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> dict[int, list[tuple[LearningPath, str, str]]]:
    """
    Return LearningPath rows grouped by week_number.
    Returns dict {week_number: [(LearningPath, topic_name, module_name)]}.
    Items with week_number IS NULL are placed in week 0 (skipped).
    """
    result = await db.execute(
        select(
            LearningPath,
            Topic.name.label("topic_name"),
            Module.name.label("module_name"),
        )
        .join(Topic, LearningPath.topic_id == Topic.id)
        .join(Module, Topic.module_id == Module.id)
        .where(
            LearningPath.user_id == user_id,
            LearningPath.week_number.isnot(None),  # exclude skipped
        )
        .order_by(LearningPath.week_number, LearningPath.order_index)
    )
    rows = result.all()

    grouped: dict[int, list] = {}
    for row in rows:
        week = row[0].week_number or 0
        grouped.setdefault(week, []).append(row)

    return grouped


# ---------------------------------------------------------------------------
# PUT /api/learning-path/{path_id}/status
# ---------------------------------------------------------------------------


async def update_path_status(
    db: AsyncSession,
    user_id: uuid.UUID,
    path_id: uuid.UUID,
    new_status: PathStatus,
) -> LearningPath:
    result = await db.execute(
        select(LearningPath).where(
            LearningPath.id == path_id,
            LearningPath.user_id == user_id,
        )
    )
    lp = result.scalar_one_or_none()
    if lp is None:
        raise NotFoundError("Learning path item not found.")

    lp.status = new_status
    db.add(lp)
    await db.flush()
    await db.refresh(lp)
    return lp


# ---------------------------------------------------------------------------
# Internal: detect topics with unresolved misconceptions
# ---------------------------------------------------------------------------


async def _find_misconception_topics(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic_ids: list[uuid.UUID],
) -> set[uuid.UUID]:
    """
    Return the set of topic IDs where the user has at least one unresolved
    misconception.

    Strategy (simple recency heuristic):
    1. Load all interactions for the user where question.topic_id ∈ topic_ids.
    2. Sort by global_sequence_position (ascending = oldest first).
    3. For each topic, scan in order:
       - Wrong answer with misconception ID → add topic to "flagged".
       - Correct answer → remove topic from "flagged" (resolved via correct answer).
    """
    from src.models.content import Question  # local import to avoid circular

    result = await db.execute(
        select(Interaction, Question)
        .join(Question, Interaction.question_id == Question.id)
        .where(
            Interaction.user_id == user_id,
            Question.topic_id.in_(topic_ids),
        )
        .order_by(Interaction.global_sequence_position)
    )
    rows = result.all()

    flagged: set[uuid.UUID] = set()

    for interaction, question in rows:
        tid: uuid.UUID = question.topic_id

        if interaction.is_correct:
            # Correct answer → tentatively clear the flag for this topic
            flagged.discard(tid)
        else:
            # Wrong answer — check if the chosen distractor has a misconception ID
            answer = interaction.selected_answer
            misc_id: str | None = None
            if answer == SelectedAnswer.A:
                misc_id = question.misconception_a_id
            elif answer == SelectedAnswer.B:
                misc_id = question.misconception_b_id
            elif answer == SelectedAnswer.C:
                misc_id = question.misconception_c_id
            elif answer == SelectedAnswer.D:
                misc_id = question.misconception_d_id

            if misc_id:
                flagged.add(tid)

    return flagged


# ---------------------------------------------------------------------------
# Simple dataclass-like helper (avoids importing dataclasses at top level)
# ---------------------------------------------------------------------------


def dataclass_like(cls):
    """Ultra-minimal dataclass decorator — just attaches __init__ from annotations."""
    import dataclasses

    return dataclasses.dataclass(cls)
