"""
services/onboarding_service.py
-------------------------------
Business logic for the onboarding flow.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from uuid import UUID

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import DEFAULT_MODEL, settings
from src.config.goal_course_map import GOAL_COURSE_MAP
from src.repositories.canonical_content_repo import CanonicalContentRepository
from src.repositories.goal_preference_repo import GoalPreferenceRepository
from src.schemas.onboarding import (
    CourseSummary,
    ExperienceLevelResponse,
    GoalsResponse,
    KnownTopicsResponse,
    PriorAnalysisRequest,
    PriorAnalysisResponse,
    SectionSummary,
    TopicsResponse,
    UnitSummary,
)
from src.services.chat_model_factory import build_chat_model_kwargs
from src.services.llm_rate_limiter import enforce_llm_rate_limit

logger = logging.getLogger(__name__)

# Average minutes per hour — used to convert estimated_minutes → hours
_MINUTES_PER_HOUR = 60.0
# Fallback when estimated_minutes is None
_DEFAULT_HOURS = 1.0
_PRIOR_ANALYSIS_LIMIT = 8


_PRIOR_ANALYSIS_SYSTEM = """\
You are an onboarding planner for an AI learning platform.
Given a learner's self-reported background and a list of candidate course topics,
choose only the common topics that should be confirmed with the learner before placement.

Rules:
- Return JSON only: {"shortlisted_topic_ids": ["topic-id", ...]}.
- Select at most 8 topic IDs.
- Prefer topics explicitly mentioned by the learner or strongly implied by coding/tools.
- Keep common topics such as CNNs, transformers, agents, Python, PyTorch, HuggingFace when relevant.
- Do not select niche/admin topics unless clearly requested.
- Self-report is not mastery; this shortlist only decides what to ask next.
"""


def _derive_course_ids(goal_ids: list[str]) -> list[str]:
    """Deduplicated course_ids for the given goal_ids, preserving insertion order."""
    seen: set[str] = set()
    result: list[str] = []
    for goal_id in goal_ids:
        for course_id in GOAL_COURSE_MAP.get(goal_id, []):
            if course_id not in seen:
                seen.add(course_id)
                result.append(course_id)
    return result


def _all_course_ids() -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for course_ids in GOAL_COURSE_MAP.values():
        for cid in course_ids:
            if cid not in seen:
                seen.add(cid)
                result.append(cid)
    return result


def _candidate_match_score(candidate, text: str) -> int:
    haystack = " ".join(
        [
            candidate.display_label,
            candidate.raw_title,
            " ".join(candidate.unit_titles or []),
        ]
    ).lower()
    tokens = [token for token in text.lower().replace("/", " ").split() if len(token) >= 3]
    return sum(1 for token in tokens if token in haystack)


def _fallback_prior_shortlist(body: PriorAnalysisRequest) -> list[str]:
    text = f"{body.prior_knowledge_text} {body.coding_experience_text}".strip()
    scored = [
        (_candidate_match_score(candidate, text), idx, candidate.id)
        for idx, candidate in enumerate(body.candidates)
    ]
    matched = [item for item in scored if item[0] > 0]
    source = matched if matched else scored
    return [
        item[2]
        for item in sorted(source, key=lambda item: (-item[0], item[1]))[:_PRIOR_ANALYSIS_LIMIT]
    ]


def _parse_prior_analysis_response(raw: str, valid_ids: set[str]) -> list[str]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    payload = json.loads(text)
    ids = payload.get("shortlisted_topic_ids", [])
    if not isinstance(ids, list):
        return []

    result: list[str] = []
    for value in ids:
        if isinstance(value, str) and value in valid_ids and value not in result:
            result.append(value)
    return result[:_PRIOR_ANALYSIS_LIMIT]


async def analyze_prior_profile(body: PriorAnalysisRequest) -> PriorAnalysisResponse:
    """Use the configured reasoning model to shortlist prior-knowledge topics.

    The endpoint is intentionally stateless: the frontend sends already-filtered
    candidate topics, and this service returns topic IDs to confirm with the user.
    """
    if not body.candidates:
        return PriorAnalysisResponse(
            shortlisted_topic_ids=[],
            model_used=DEFAULT_MODEL,
            provider=settings.model_provider,
            fallback=True,
        )

    valid_ids = {candidate.id for candidate in body.candidates}
    candidates_json = json.dumps(
        [
            {
                "id": candidate.id,
                "display_label": candidate.display_label,
                "raw_title": candidate.raw_title,
                "unit_titles": candidate.unit_titles[:8],
            }
            for candidate in body.candidates[:40]
        ],
        ensure_ascii=False,
    )

    user_text = (
        f"Goal: {body.goal_id}\n"
        f"Prior knowledge: {body.prior_knowledge_text or '(empty)'}\n"
        f"Coding/tools: {body.coding_experience_text or '(empty)'}\n"
        f"Candidate topics JSON:\n{candidates_json}"
    )

    try:
        enforce_llm_rate_limit(model=DEFAULT_MODEL, model_provider=settings.model_provider)
        llm = init_chat_model(
            **build_chat_model_kwargs(
                model=DEFAULT_MODEL,
                temperature=0,
                max_tokens=700,
            )
        )
        response = llm.invoke(
            [
                SystemMessage(content=_PRIOR_ANALYSIS_SYSTEM),
                HumanMessage(content=user_text),
            ]
        )
        shortlisted = _parse_prior_analysis_response(str(response.content), valid_ids)
        if not shortlisted:
            shortlisted = _fallback_prior_shortlist(body)
            fallback = True
        else:
            fallback = False
    except Exception as exc:
        logger.warning("prior analysis LLM failed; using fallback: %s", exc)
        shortlisted = _fallback_prior_shortlist(body)
        fallback = True

    return PriorAnalysisResponse(
        shortlisted_topic_ids=shortlisted,
        model_used=DEFAULT_MODEL,
        provider=settings.model_provider,
        fallback=fallback,
    )


# Reverse map: canonical_course_id → goal_id (first match wins)
_COURSE_TO_GOAL: dict[str, str] = {}
for _goal, _courses in GOAL_COURSE_MAP.items():
    for _cid in _courses:
        _COURSE_TO_GOAL.setdefault(_cid, _goal)


async def save_user_goals(
    db: AsyncSession,
    user_id: UUID,
    goal_ids: list[str],
) -> GoalsResponse:
    course_ids = _derive_course_ids(goal_ids)

    repo = GoalPreferenceRepository(db)
    await repo.upsert_for_user(
        user_id,
        goal_weights_json={g: 1.0 for g in goal_ids},
        selected_course_ids=course_ids,
    )
    await db.commit()

    return GoalsResponse(goal_ids=goal_ids, course_ids=course_ids)


async def get_topics_tree(
    db: AsyncSession,
    goal_ids: list[str],
) -> TopicsResponse:
    if goal_ids:
        course_ids = _derive_course_ids(goal_ids)
    else:
        course_ids = _all_course_ids()

    content_repo = CanonicalContentRepository(db)
    units = await content_repo.get_linked_learning_units(course_ids)

    if not units:
        return TopicsResponse(courses=[])

    # Collect unique section IDs
    section_ids: list[UUID] = list({u.section_id for u in units})
    sections_map = await content_repo.get_sections_by_ids(section_ids)

    # Build tree: canonical_course_id → section_id → [units]
    # We also need canonical_course_id per unit; we get it from the Course relationship.
    # Instead, derive it: unit.course_id is a UUID; we match via canonical_content_repo's
    # Course join logic. Use a separate grouping by course_id UUID, then look up
    # canonical_course_id from the section's course.

    # Group units by (course_id UUID, section_id)
    course_section_units: dict[UUID, dict[UUID, list]] = defaultdict(lambda: defaultdict(list))
    for unit in units:
        course_section_units[unit.course_id][unit.section_id].append(unit)

    # We need canonical_course_id for each course UUID.
    # The LearningUnit has a .course relationship but it's lazy-loaded.
    # Build canonical_course_id by inspecting unit.canonical_unit_id prefix (e.g. "cs231n::...")
    # or by fetching the Course records. Use canonical_unit_id prefix as a reliable approach.
    course_uuid_to_canonical: dict[UUID, str] = {}
    for unit in units:
        if unit.canonical_unit_id and "::" in unit.canonical_unit_id:
            prefix = unit.canonical_unit_id.split("::")[0]
            course_uuid_to_canonical.setdefault(unit.course_id, prefix)

    courses_out: list[CourseSummary] = []
    for course_uuid, sec_map in course_section_units.items():
        canonical_cid = course_uuid_to_canonical.get(course_uuid, str(course_uuid))
        goal_id = _COURSE_TO_GOAL.get(canonical_cid, "unknown")

        sections_out: list[SectionSummary] = []
        for section_uuid, sec_units in sec_map.items():
            section = sections_map.get(section_uuid)
            section_title = section.title if section else str(section_uuid)

            units_out = [
                UnitSummary(
                    unit_id=u.id,
                    title=u.title,
                    estimated_hours_beginner=(
                        round(u.estimated_minutes / _MINUTES_PER_HOUR, 2)
                        if u.estimated_minutes
                        else _DEFAULT_HOURS
                    ),
                )
                for u in sorted(sec_units, key=lambda u: u.sort_order)
            ]
            sections_out.append(
                SectionSummary(section_id=section_uuid, title=section_title, units=units_out)
            )

        # Sort sections by their sort_order if available
        sections_out.sort(
            key=lambda s: (
                sections_map[s.section_id].sort_order
                if s.section_id in sections_map
                else 0
            )
        )
        courses_out.append(
            CourseSummary(
                course_id=canonical_cid,
                goal_id=goal_id,
                sections=sections_out,
            )
        )

    return TopicsResponse(courses=courses_out)


async def save_known_topics(
    db: AsyncSession,
    user_id: UUID,
    topic_unit_ids: list[UUID],
) -> KnownTopicsResponse:
    """Store known unit IDs in goal_preferences.notes as JSON.

    Empty topic_unit_ids signals a newcomer skip: sets placement_status='skipped'.
    """
    repo = GoalPreferenceRepository(db)

    # Load existing record to merge, if present
    existing = await repo.get_by_user_id(user_id)
    existing_notes: dict = {}
    if existing and existing.notes:
        try:
            existing_notes = json.loads(existing.notes)
        except (json.JSONDecodeError, TypeError):
            existing_notes = {}

    known_ids = list({str(uid) for uid in topic_unit_ids} | set(existing_notes.get("known_unit_ids", [])))
    new_notes = {**existing_notes, "known_unit_ids": known_ids}

    await repo.upsert_for_user(user_id, notes=json.dumps(new_notes))
    await db.commit()

    return KnownTopicsResponse(saved=True, count=len(known_ids))


async def save_experience_level(
    db: AsyncSession,
    user_id: UUID,
    level: str,
) -> ExperienceLevelResponse:
    """Persist the user's experience level.

    When level='beginner', also sets placement_status='skipped' so the
    recommendation engine bypasses Phase A entirely — double-write to ensure
    correctness regardless of whether the frontend also calls known-topics.
    """
    repo = GoalPreferenceRepository(db)
    kwargs: dict = {"experience_level": level}
    if level == "beginner":
        kwargs["placement_status"] = "skipped"

    await repo.upsert_for_user(user_id, **kwargs)
    await db.commit()

    placement_status = kwargs.get("placement_status")
    return ExperienceLevelResponse(level=level, placement_status=placement_status)
