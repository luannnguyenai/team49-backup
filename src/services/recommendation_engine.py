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
from src.schemas.learning_path import (
    GeneratePathRequest,
    GeneratePathResponse,
    PathItemResponse,
)
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
