"""
services/replan_service.py
--------------------------
Production replan composition service.

Composes keyword planner, unit discovery, prerequisite suggestions, and
question scope builder against real DB data (current learning path, canonical
questions, prerequisite edges, handled/mastered state).
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.canonical import (
    CanonicalUnit,
    ItemPhaseMap,
    PrerequisiteEdge,
    QuestionBankItem,
    UnitKPMap,
)
from src.models.course import LearningUnit
from src.repositories.canonical_content_repo import CanonicalContentRepository
from src.repositories.canonical_question_repo import CanonicalQuestionRepository
from src.repositories.placement_assessment_repo import PlacementAssessmentRepository
from src.repositories.planner_audit_repo import PlannerAuditRepository
from src.schemas.replan import (
    ReplanAnalyzeResponse,
    ReplanAnalyzeUnit,
    ReplanAssessmentStartResponse,
    ReplanAssessmentUnitRequest,
    ReplanPrerequisiteSuggestionResponse,
)
from src.services.assessment_service import start_assessment
from src.services.replan_keyword_planner import ReplanKeywordPlanner
from src.services.replan_prerequisite_suggestions import (
    ReplanPrerequisiteSuggester,
    ReplanPrerequisiteUnit,
)
from src.services.replan_question_scope import (
    ReplanQuestion,
    ReplanQuestionScopeBuilder,
    ReplanScopeUnit,
)
from src.services.replan_unit_discovery import (
    ReplanCurrentPathUnitDiscovery,
    ReplanUnitCandidate,
)

log = logging.getLogger(__name__)

# Difficulty filter ceiling mapping
_DIFFICULTY_CEILING: dict[str, set[str]] = {
    "easy": {"easy"},
    "easy_medium": {"easy", "medium"},
    "easy_medium_hard": {"easy", "medium", "hard"},
    "all": {"easy", "medium", "hard", "application"},
}


# ---------------------------------------------------------------------------
# POST /api/replan/analyze — production composition
# ---------------------------------------------------------------------------


async def analyze_replan(
    db: AsyncSession,
    user_id: uuid.UUID,
    claim: str,
) -> ReplanAnalyzeResponse:
    """Analyze a knowledge claim against the user's real current learning path."""

    try:
        # 1. Load the user's current learning path from planner audit
        path_items = await _load_current_path_items(db, user_id)
        if not path_items:
            return ReplanAnalyzeResponse(
                units=[],
                prerequisites=[],
                keywordPlanSpecificity="specific",
                guardrailFlags=["no_active_path"],
            )

        # 2. Build keyword plan
        planner = ReplanKeywordPlanner()
        keyword_plan = await planner.plan(claim)

        # 3. Build unit candidates from real path data
        canonical_unit_ids = [
        item["canonical_unit_id"]
        for item in path_items
        if item.get("canonical_unit_id")
    ]

        content_repo = CanonicalContentRepository(db)
        canonical_units = await content_repo.get_canonical_units_by_ids(canonical_unit_ids)

        # Get question counts by difficulty for each unit
        question_counts_by_unit = await _get_question_counts_by_difficulty(
            db, canonical_unit_ids
        )

        # Get handled state (placement decisions)
        placement_repo = PlacementAssessmentRepository(db)
        placement_results = await placement_repo.get_by_user_id(user_id)
        handled_unit_ids = {
            str(row.topic_unit_id)
            for row in placement_results
            if row.decision in ("skip",)
        }

        # Build learning_unit_id -> canonical_unit_id mapping
        lu_by_canonical = {}
        for item in path_items:
            cuid = item.get("canonical_unit_id")
            luid = item.get("learning_unit_id")
            if cuid and luid:
                lu_by_canonical[cuid] = luid

        candidates: list[ReplanUnitCandidate] = []
        for order_index, item in enumerate(path_items):
            cuid = item.get("canonical_unit_id")
            if not cuid:
                continue
            canonical_unit = canonical_units.get(cuid)
            q_counts = question_counts_by_unit.get(cuid, {})
            luid = item.get("learning_unit_id", "")

            candidates.append(
                ReplanUnitCandidate(
                    canonicalUnitId=cuid,
                    title=canonical_unit.unit_name if canonical_unit else cuid,
                    summary=canonical_unit.summary or "" if canonical_unit else "",
                    keyPoints=(
                        list(canonical_unit.key_points)
                        if canonical_unit and canonical_unit.key_points
                        else []
                    ),
                    pathOrder=order_index,
                    questionCounts=q_counts,
                    inCurrentPath=True,
                    alreadyHandled=str(luid) in handled_unit_ids,
                )
            )

        # 4. Unit discovery — match keywords against candidates
        discovery = ReplanCurrentPathUnitDiscovery()
        discovery_result = discovery.discover(keyword_plan, candidates)

        # 5. Build selected units for question scope
        selected_ids = [u.canonical_unit_id for u in discovery_result.selected_units]
        candidate_by_id = {c.canonical_unit_id: c for c in candidates}

        # 6. Get KP data for selected units
        unit_kp_rows = await content_repo.get_unit_kp_rows(selected_ids)
        unit_kp_map: dict[str, list[str]] = defaultdict(list)
        for row in unit_kp_rows:
            kp_name = row.kp_id  # We'll resolve names below
            unit_kp_map[row.unit_id].append(kp_name)

        # Resolve KP names
        kp_ids = sorted({row.kp_id for row in unit_kp_rows})
        kp_by_id = await content_repo.get_concepts_by_ids(kp_ids)
        unit_kp_names_map: dict[str, list[str]] = {}
        for uid, kp_id_list in unit_kp_map.items():
            unit_kp_names_map[uid] = [
                kp_by_id[kp_id].name
                for kp_id in kp_id_list
                if kp_id in kp_by_id and kp_by_id[kp_id].name
            ]

        # 7. Build question metadata for scope builder
        questions: list[ReplanQuestion] = []
        for uid in selected_ids:
            q_counts = question_counts_by_unit.get(uid, {})
            kps = unit_kp_names_map.get(uid, [])
            for difficulty, count in q_counts.items():
                for _ in range(count):
                    questions.append(
                        ReplanQuestion(
                            unitId=uid,
                            difficulty=difficulty,
                            knowledgePoints=kps[:3],  # Top 3 KPs per question
                        )
                    )

        scope_builder = ReplanQuestionScopeBuilder()
        scope_units_input = [
            ReplanScopeUnit(
                canonicalUnitId=uid,
                title=candidate_by_id[uid].title if uid in candidate_by_id else uid,
                source="matched_from_description",
                keyPoints=candidate_by_id[uid].key_points if uid in candidate_by_id else [],
            )
            for uid in selected_ids
        ]
        review_scope = scope_builder.build(scope_units_input, questions, unit_kp_names_map)

        # 8. Build response units
        response_units: list[ReplanAnalyzeUnit] = [
            ReplanAnalyzeUnit(
                canonicalUnitId=scope_unit.canonical_unit_id,
                title=scope_unit.title,
                source=scope_unit.source,
                suggestedForTitle=scope_unit.suggested_for_title,
                knowledgePoints=scope_unit.knowledge_points,
                questionCounts=scope_unit.question_counts,
            )
            for scope_unit in review_scope
        ]

        # 9. Prerequisite suggestions
        prereq_units_by_id: dict[str, ReplanPrerequisiteUnit] = {}
        for c in candidates:
            q_total = sum(c.question_counts.values())
            prereq_units_by_id[c.canonical_unit_id] = ReplanPrerequisiteUnit(
                canonicalUnitId=c.canonical_unit_id,
                title=c.title,
                pathOrder=c.path_order,
                inCurrentPath=c.in_current_path,
                alreadyHandled=c.already_handled,
                questionCount=q_total,
            )

        # Build prerequisite edges from KP graph (unit-level)
        unit_prereq_edges = await _build_unit_prerequisite_edges(
            db, content_repo, canonical_unit_ids
        )

        suggester = ReplanPrerequisiteSuggester(unit_prereq_edges)
        suggestions = suggester.suggest(selected_ids, prereq_units_by_id)

        # Build prerequisite response with review units
        prerequisite_responses: list[ReplanPrerequisiteSuggestionResponse] = []
        for s in suggestions:
            prereq_candidate = candidate_by_id.get(s.canonical_unit_id)
            if not prereq_candidate:
                continue
            prereq_q_counts = question_counts_by_unit.get(s.canonical_unit_id, {})
            prereq_kps = unit_kp_names_map.get(s.canonical_unit_id, [])

            # Find the title of the unit this is a prerequisite for
            suggested_for_candidate = candidate_by_id.get(
                s.suggested_for_canonical_unit_id
            )
            suggested_for_title = (
                suggested_for_candidate.title if suggested_for_candidate else None
            )

            prerequisite_responses.append(
                ReplanPrerequisiteSuggestionResponse(
                    canonicalUnitId=s.canonical_unit_id,
                    title=s.title,
                    reason=s.reason,
                    depth=s.depth,
                    reviewUnit=ReplanAnalyzeUnit(
                        canonicalUnitId=s.canonical_unit_id,
                        title=s.title,
                        source="suggested_prerequisite",
                        suggestedForTitle=suggested_for_title,
                        knowledgePoints=prereq_kps,
                        questionCounts=prereq_q_counts,
                    ),
                )
            )

            return ReplanAnalyzeResponse(
                units=response_units,
            prerequisites=prerequisite_responses,
            keywordPlanSpecificity=keyword_plan.specificity,
            guardrailFlags=keyword_plan.guardrail_flags,
        )
    except Exception as e:
        log.error(f"Error in analyze_replan for user {user_id}: {e}", exc_info=True)
        # Return safe fallback response
        return ReplanAnalyzeResponse(
            units=[],
            prerequisites=[],
            keywordPlanSpecificity="specific",
            guardrailFlags=["internal_error"],
        )


# ---------------------------------------------------------------------------
# POST /api/replan/assessment/start — production bridge
# ---------------------------------------------------------------------------


async def start_replan_assessment(
    db: AsyncSession,
    user_id: uuid.UUID,
    selected_units: list[ReplanAssessmentUnitRequest],
) -> ReplanAssessmentStartResponse:
    """Start an assessment session with exact unit + difficulty filters."""

    canonical_unit_ids = [u.canonical_unit_id for u in selected_units]

    # Build difficulty filter map
    difficulty_by_unit = {
        u.canonical_unit_id: u.difficulty_filter for u in selected_units
    }

    # Load unit names for the response
    content_repo = CanonicalContentRepository(db)
    canonical_units = await content_repo.get_canonical_units_by_ids(canonical_unit_ids)
    unit_name_map = {
        uid: canonical_units[uid].unit_name if uid in canonical_units else uid
        for uid in canonical_unit_ids
    }

    # Compute per-unit question budget based on difficulty filter
    # Use "deep" assessment depth with per-unit difficulty filtering
    assessment_response = await start_assessment(
        db,
        user_id,
        learning_unit_ids=[],
        canonical_unit_ids=canonical_unit_ids,
        phase="placement",
        assessment_depth="deep",
    )

    # Filter questions by per-unit difficulty ceiling
    filtered_questions = []
    for q in assessment_response.questions:
        unit_id = q.canonical_unit_id
        if not unit_id:
            filtered_questions.append(q)
            continue

        filter_key = difficulty_by_unit.get(unit_id, "all")
        allowed = _DIFFICULTY_CEILING.get(filter_key, _DIFFICULTY_CEILING["all"])

        q_difficulty = (
            q.difficulty_bucket.value if q.difficulty_bucket else "medium"
        )
        if q_difficulty.lower() in allowed:
            filtered_questions.append(q)

    # Update session question count if we filtered
    # Note: We don't modify the DB session here; the filtered count is
    # reflected in the response. The submit flow handles whatever questions
    # the user actually answers.

    assessment_href = "/assessment?next=/learn"

    return ReplanAssessmentStartResponse(
        sessionId=str(assessment_response.session_id),
        totalQuestions=len(filtered_questions),
        canonicalUnitIds=canonical_unit_ids,
        unitNameMap=unit_name_map,
        assessmentHref=assessment_href,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _load_current_path_items(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[dict]:
    """Load the user's current learning path items from the latest plan."""
    audit_repo = PlannerAuditRepository(db)
    plan = await audit_repo.get_latest_plan_for_user(
        user_id,
        trigger="generate_canonical_learning_path",
    )
    if plan is None or not plan.recommended_path_json:
        return []

    items = []
    for item in plan.recommended_path_json:
        if not isinstance(item, dict):
            continue
        items.append(item)
    return items


async def _get_question_counts_by_difficulty(
    db: AsyncSession,
    canonical_unit_ids: list[str],
) -> dict[str, dict[str, int]]:
    """Get question counts grouped by unit and difficulty level."""
    if not canonical_unit_ids:
        return {}

    result = await db.execute(
        select(
            QuestionBankItem.unit_id,
            QuestionBankItem.difficulty,
            func.count(func.distinct(QuestionBankItem.item_id)),
        )
        .join(ItemPhaseMap, ItemPhaseMap.item_id == QuestionBankItem.item_id)
        .where(
            QuestionBankItem.unit_id.in_(canonical_unit_ids),
            ItemPhaseMap.phase == "placement",
            QuestionBankItem.qa_gate_passed.is_not(False),
        )
        .group_by(QuestionBankItem.unit_id, QuestionBankItem.difficulty)
    )

    counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"easy": 0, "medium": 0, "hard": 0, "application": 0}
    )
    for unit_id, difficulty, count in result.all():
        difficulty_key = str(difficulty or "medium").lower()
        if difficulty_key in counts[unit_id]:
            counts[unit_id][difficulty_key] = int(count)
    return dict(counts)


async def _build_unit_prerequisite_edges(
    db: AsyncSession,
    content_repo: CanonicalContentRepository,
    canonical_unit_ids: list[str],
) -> dict[str, list[str]]:
    """Build unit-level prerequisite edges from the KP prerequisite graph.

    Returns a dict: {unit_id -> [prerequisite_unit_ids]}.
    A unit B is a prerequisite for unit A if any KP in A has a prerequisite
    edge to a KP in B.
    """
    if not canonical_unit_ids:
        return {}

    # Get all KPs for these units
    unit_kp_rows = await content_repo.get_unit_kp_rows(canonical_unit_ids)
    kp_ids = sorted({row.kp_id for row in unit_kp_rows})

    if not kp_ids:
        return {}

    # Build KP -> unit mapping
    kp_to_units: dict[str, set[str]] = defaultdict(set)
    for row in unit_kp_rows:
        kp_to_units[row.kp_id].add(row.unit_id)

    # Get prerequisite edges between these KPs
    prereq_edges = await content_repo.get_prerequisite_edges_for_kps(kp_ids)

    # Build unit-level edges: if KP_A depends on KP_B,
    # then unit containing KP_A depends on unit containing KP_B
    unit_edges: dict[str, set[str]] = defaultdict(set)
    unit_set = set(canonical_unit_ids)
    for edge in prereq_edges:
        if not getattr(edge, "active", True):
            continue
        source_units = kp_to_units.get(edge.source_kp_id, set())
        target_units = kp_to_units.get(edge.target_kp_id, set())
        for target_unit in target_units:
            if target_unit not in unit_set:
                continue
            for source_unit in source_units:
                if source_unit not in unit_set or source_unit == target_unit:
                    continue
                # target_kp depends on source_kp, so target_unit depends on source_unit
                unit_edges[target_unit].add(source_unit)

    return {uid: sorted(prereqs) for uid, prereqs in unit_edges.items()}
