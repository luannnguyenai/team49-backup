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
from src.schemas.assessment import QuestionForAssessment
from src.schemas.replan import (
    ReplanAnalyzeResponse,
    ReplanAnalyzeUnit,
    ReplanAssessmentStartResponse,
    ReplanAssessmentUnitRequest,
    ReplanPopup,
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
from src.services.replan_unit_recommender import get_unit_recommender

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
        # 1. Build keyword plan first so guardrail classification is independent
        # of whether the learner already has an active path.
        planner = ReplanKeywordPlanner()
        keyword_plan = await planner.plan(claim)

        blocking_flags = {
            flag
            for flag in keyword_plan.guardrail_flags
            if flag in {"skip_all", "too_short", "all_already_mastered"}
        }
        if blocking_flags:
            flag = sorted(blocking_flags)[0]
            popup = _popup_for_guardrail(flag)
            return ReplanAnalyzeResponse(
                units=[],
                prerequisites=[],
                keywordPlanSpecificity=keyword_plan.specificity,
                guardrailFlags=keyword_plan.guardrail_flags,
                status="guardrail_blocked",
                popup=popup,
            )

        # 2. Load the user's current learning path from planner audit
        path_items = await _load_current_path_items(db, user_id)
        if not path_items:
            return ReplanAnalyzeResponse(
                units=[],
                prerequisites=[],
                keywordPlanSpecificity=keyword_plan.specificity,
                guardrailFlags=[*keyword_plan.guardrail_flags, "no_active_path"],
                status="no_active_path",
                popup=ReplanPopup(
                    kind="no_active_path",
                    title="No active learning path",
                    message="Create a learning path before optimizing it.",
                ),
            )

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

            # Extract key point text strings from dict objects
            raw_key_points = canonical_unit.key_points if canonical_unit else []
            key_points_strs: list[str] = []
            if raw_key_points:
                for kp in raw_key_points:
                    if isinstance(kp, dict):
                        # Extract text from dict (try common keys)
                        key_points_strs.append(kp.get("text") or kp.get("name") or kp.get("kp_name") or str(kp))
                    elif isinstance(kp, str):
                        key_points_strs.append(kp)

            candidates.append(
                ReplanUnitCandidate(
                    canonicalUnitId=cuid,
                    title=canonical_unit.unit_name if canonical_unit else cuid,
                    summary=canonical_unit.summary or "" if canonical_unit else "",
                    keyPoints=key_points_strs,
                    pathOrder=order_index,
                    questionCounts=q_counts,
                    inCurrentPath=True,
                    alreadyHandled=str(luid) in handled_unit_ids,
                )
            )

        # 4. Unit discovery — match keywords against candidates (locked to path)
        discovery = ReplanCurrentPathUnitDiscovery()
        discovery_result = discovery.discover(keyword_plan, candidates)

        # If no units matched, return early with helpful message
        if not discovery_result.selected_units:
            mastered_matches = [
                unit for unit in discovery_result.dropped_units
                if unit.reason == "Unit is already mastered or skipped."
            ]
            if mastered_matches:
                return ReplanAnalyzeResponse(
                    units=[],
                    prerequisites=[],
                    keywordPlanSpecificity=keyword_plan.specificity,
                    guardrailFlags=[*keyword_plan.guardrail_flags, "all_already_mastered"],
                    status="all_already_mastered",
                    popup=ReplanPopup(
                        kind="all_already_mastered",
                        title="Already mastered",
                        message=(
                            "The matching units are already marked as mastered in your learning path. "
                            "There is nothing new to verify for this claim."
                        ),
                    ),
                )
            log.info(f"[Replan] No units matched for claim: {claim}")
            return ReplanAnalyzeResponse(
                units=[],
                prerequisites=[],
                keywordPlanSpecificity=keyword_plan.specificity,
                guardrailFlags=[*keyword_plan.guardrail_flags, "no_matching_units"],
                status="no_matching_units",
                popup=ReplanPopup(
                    kind="no_matching_units",
                    title="No matching units",
                    message="No units in your learning path match this description.",
                ),
            )

        # 4.5 LLM recommender — analyze intent and recommend which units to test
        selected_unit_ids = [u.canonical_unit_id for u in discovery_result.selected_units]
        matched_candidates = [c for c in candidates if c.canonical_unit_id in selected_unit_ids]

        # Build context for LLM recommender
        available_units_context = [
            {
                "unit_id": c.canonical_unit_id,
                "title": c.title,
                "summary": c.summary,
                "key_points": c.key_points,
            }
            for c in matched_candidates
        ]

        recommender = get_unit_recommender()
        recommendation = await recommender.recommend(claim, available_units_context)

        # If LLM says skip (intent doesn't match path), return early
        if recommendation.should_skip_all:
            log.info(f"[Replan] LLM recommended skip: {recommendation.skip_reason}")
            return ReplanAnalyzeResponse(
                units=[],
                prerequisites=[],
                keywordPlanSpecificity=keyword_plan.specificity,
                guardrailFlags=[*keyword_plan.guardrail_flags, "no_matching_units", recommendation.skip_reason],
                status="no_matching_units",
                popup=ReplanPopup(
                    kind="no_matching_units",
                    title="No matching units",
                    message=recommendation.skip_reason or "No units in your learning path match this description.",
                ),
            )

        # Filter to only recommended units
        recommended_unit_ids = {r.unit_id for r in recommendation.recommendations}
        valid_recommended_unit_ids = recommended_unit_ids & set(selected_unit_ids)
        if valid_recommended_unit_ids:
            discovery_result.selected_units = [
                u for u in discovery_result.selected_units
                if u.canonical_unit_id in valid_recommended_unit_ids
            ]
        elif recommended_unit_ids:
            log.warning(
                "[Replan] LLM returned recommendation IDs outside discovered units; keeping discovered units"
            )
        else:
            log.warning(
                "[Replan] LLM returned no recommendations without should_skip_all; keeping discovered units"
            )
        if not discovery_result.selected_units:
            return ReplanAnalyzeResponse(
                units=[],
                prerequisites=[],
                keywordPlanSpecificity=keyword_plan.specificity,
                guardrailFlags=[*keyword_plan.guardrail_flags, "no_matching_units"],
                status="no_matching_units",
                popup=ReplanPopup(
                    kind="no_matching_units",
                    title="No matching units",
                    message="No units in your learning path match this description closely enough.",
                ),
            )

        # Log LLM reasoning
        for rec in recommendation.recommendations:
            log.info(f"[Replan] LLM recommended {rec.unit_id}: {rec.reason}")

        # 5. Build selected units for question scope
        selected_ids = [u.canonical_unit_id for u in discovery_result.selected_units]
        candidate_by_id = {c.canonical_unit_id: c for c in candidates}

        # 6. Get KP data for current-path units so selected and prerequisite units
        # can both display readable KP names.
        unit_kp_rows = await content_repo.get_unit_kp_rows(canonical_unit_ids)
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

        # Build prerequisite edges from KP graph - include KP names for detailed reasons
        unit_prereq_edges, unit_kp_edges = await _build_unit_prerequisite_edges_with_kp_names(
            db, content_repo, canonical_unit_ids, kp_by_id
        )

        suggester = ReplanPrerequisiteSuggester(unit_prereq_edges, unit_kp_edges)
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
            status="ready",
        )
    except Exception as e:
        log.error(f"Error in analyze_replan for user {user_id}: {type(e).__name__}: {e}", exc_info=True)
        # Return safe fallback response with error details in guardrail flag
        error_msg = f"{type(e).__name__}: {str(e)[:200]}"  # Truncate long errors
        return ReplanAnalyzeResponse(
            units=[],
            prerequisites=[],
            keywordPlanSpecificity="specific",
            guardrailFlags=["internal_error", error_msg],
            status="internal_error",
            popup=ReplanPopup(
                kind="internal_error",
                title="Analysis failed",
                message="An internal error occurred while analyzing this claim. Please try again.",
            ),
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

        q_difficulty = _difficulty_value(q.difficulty_bucket)
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
        questions=[_question_for_response(question) for question in filtered_questions],
    )


def _popup_for_guardrail(flag: str) -> ReplanPopup:
    if flag == "skip_all":
        return ReplanPopup(
            kind="guardrail_blocked",
            title="Scope too broad",
            message="Specify the concepts or units you already know instead of trying to skip the entire path.",
        )
    if flag == "too_short":
        return ReplanPopup(
            kind="guardrail_blocked",
            title="More detail needed",
            message="Describe specific concepts or units you already know.",
        )
    return ReplanPopup(
        kind="guardrail_blocked",
        title="Already mastered",
        message="This claim says the whole scope is already mastered. Please describe the specific units to verify.",
    )


def _difficulty_value(difficulty) -> str:
    if difficulty is None:
        return "medium"
    return str(getattr(difficulty, "value", difficulty))


def _question_for_response(question) -> QuestionForAssessment:
    return QuestionForAssessment(
        id=getattr(question, "id", None),
        item_id=getattr(question, "item_id"),
        canonical_item_id=getattr(question, "canonical_item_id", None),
        canonical_unit_id=getattr(question, "canonical_unit_id", None),
        topic_id=getattr(question, "topic_id", None),
        bloom_level=getattr(question, "bloom_level", None),
        difficulty_bucket=_difficulty_value(getattr(question, "difficulty_bucket", None)),
        stem_text=getattr(question, "stem_text"),
        option_a=getattr(question, "option_a"),
        option_b=getattr(question, "option_b"),
        option_c=getattr(question, "option_c"),
        option_d=getattr(question, "option_d"),
        time_expected_seconds=getattr(question, "time_expected_seconds", None),
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


async def _build_unit_prerequisite_edges_with_kp_names(
    db: AsyncSession,
    content_repo: CanonicalContentRepository,
    canonical_unit_ids: list[str],
    kp_by_id: dict[str, any],
) -> tuple[dict[str, list[str]], dict[tuple[str, str], list[tuple[str, str]]]]:
    """Build unit-level prerequisite edges with KP name mappings.

    Returns:
        - unit_edges: {unit_id -> [prerequisite_unit_ids]}
        - unit_kp_edges: {(source_unit, target_unit) -> [(source_kp_name, target_kp_name), ...]}
    """
    if not canonical_unit_ids:
        return {}, {}

    # Get all KPs for these units
    unit_kp_rows = await content_repo.get_unit_kp_rows(canonical_unit_ids)
    kp_ids = sorted({row.kp_id for row in unit_kp_rows})

    if not kp_ids:
        return {}, {}

    # Build KP -> unit mapping and KP -> name mapping
    kp_to_units: dict[str, set[str]] = defaultdict(set)
    for row in unit_kp_rows:
        kp_to_units[row.kp_id].add(row.unit_id)

    def get_kp_name(kp_id: str) -> str:
        """Get KP name from kp_by_id dict."""
        kp = kp_by_id.get(kp_id)
        if kp and hasattr(kp, 'name'):
            return kp.name
        return kp_id

    # Get prerequisite edges between these KPs
    prereq_edges = await content_repo.get_prerequisite_edges_for_kps(kp_ids)

    # Build unit-level edges and KP name mappings
    unit_edges: dict[str, set[str]] = defaultdict(set)
    unit_kp_edges: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    unit_set = set(canonical_unit_ids)

    for edge in prereq_edges:
        if not getattr(edge, "active", True):
            continue

        source_units = kp_to_units.get(edge.source_kp_id, set())
        target_units = kp_to_units.get(edge.target_kp_id, set())

        source_kp_name = get_kp_name(edge.source_kp_id)
        target_kp_name = get_kp_name(edge.target_kp_id)

        for target_unit in target_units:
            if target_unit not in unit_set:
                continue
            for source_unit in source_units:
                if source_unit not in unit_set or source_unit == target_unit:
                    continue

                # target_kp depends on source_kp, so target_unit depends on source_unit
                unit_edges[target_unit].add(source_unit)

                # Store KP name pair for this unit pair
                unit_kp_edges[(source_unit, target_unit)].append((source_kp_name, target_kp_name))

    # Deduplicate KP edges per unit pair
    for key in unit_kp_edges:
        # Remove duplicates while preserving order
        seen = set()
        unique_edges = []
        for pair in unit_kp_edges[key]:
            if pair not in seen:
                seen.add(pair)
                unique_edges.append(pair)
        unit_kp_edges[key] = unique_edges

    return (
        {uid: sorted(prereqs) for uid, prereqs in unit_edges.items()},
        dict(unit_kp_edges),
    )
