"""
services/assessment_service.py
--------------------------------
Canonical-only assessment runtime.

Merges placement_assessment_service logic: per-unit item selection (5/unit),
decision classification (skip/review/relearn), and persistence to
placement_assessment_results.
"""

from __future__ import annotations

import json
import logging
import uuid
from ast import literal_eval
from dataclasses import dataclass
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import DEFAULT_MODEL, settings
from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.models.canonical import ConceptKP, ItemKPMap, QuestionBankItem
from src.models.content import DifficultyBucket
from src.models.course import LearningUnit
from src.models.learning import Interaction, SelectedAnswer, Session, SessionType
from src.repositories.canonical_question_repo import CanonicalQuestionRepository
from src.repositories.placement_assessment_repo import PlacementAssessmentRepository
from src.schemas.assessment import (
    AnswerInput,
    AssessmentAISummaryResponse,
    AssessmentResultResponse,
    AssessmentStartResponse,
    LearningUnitResult,
    TopicDecisionResult,
)
from src.services.assessment_strategies import UnitPools
from src.services.canonical_mastery_service import update_kp_mastery_from_item
from src.services.mastery_evaluator import classify_mastery
from src.services.strategy_router import pick_strategy
from src.core.observability import (
    build_langfuse_metadata,
    llm_callbacks,
    propagate_langfuse_attributes,
    start_langfuse_root_span,
)

log = logging.getLogger(__name__)

_ASSESSMENT_SUMMARY_SYSTEM = """\
You write concise English feedback for an AI learning assessment result.

Return JSON only:
{
  "summary": "2 short sentences, natural and specific",
  "highlights": ["max 3 short bullets"],
  "next_step": "1 short next-step sentence"
}

Rules:
- Base the feedback only on the provided scores and decisions.
- Do not list every unit.
- Do not over-praise if there are relearn/review items.
- Mention skip/review/relearn in learner-friendly English.
- Keep the tone direct, calm, and useful.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AssessmentDepthPolicy:
    max_questions: int
    questions_per_unit: int
    allowed_difficulties: set[str]
    allow_application: bool


def _assessment_depth_policy(depth: str) -> AssessmentDepthPolicy:
    if depth == "quick":
        return AssessmentDepthPolicy(
            max_questions=15,
            questions_per_unit=2,
            allowed_difficulties={"easy", "medium"},
            allow_application=False,
        )
    if depth == "deep":
        return AssessmentDepthPolicy(
            max_questions=50,
            questions_per_unit=5,
            allowed_difficulties={"easy", "medium", "hard"},
            allow_application=True,
        )
    return AssessmentDepthPolicy(
        max_questions=30,
        questions_per_unit=3,
        allowed_difficulties={"easy", "medium", "hard"},
        allow_application=False,
    )


def _assessment_budget_policy(depth: str, question_budget: int | None) -> AssessmentDepthPolicy:
    policy = _assessment_depth_policy(depth)
    if question_budget is None:
        return policy

    budget = max(1, min(int(question_budget), 70))
    if budget <= 15:
        return AssessmentDepthPolicy(
            max_questions=budget,
            questions_per_unit=policy.questions_per_unit,
            allowed_difficulties={"easy", "medium"},
            allow_application=False,
        )
    if budget > 30:
        return AssessmentDepthPolicy(
            max_questions=budget,
            questions_per_unit=max(policy.questions_per_unit, 5),
            allowed_difficulties={"easy", "medium", "hard"},
            allow_application=True,
        )
    return AssessmentDepthPolicy(
        max_questions=budget,
        questions_per_unit=max(policy.questions_per_unit, 3),
        allowed_difficulties={"easy", "medium", "hard"},
        allow_application=False,
    )


def _filter_unit_pools_for_depth(
    unit_pools: UnitPools,
    policy: AssessmentDepthPolicy,
) -> UnitPools:
    filtered: UnitPools = {}
    for unit_id, pairs in unit_pools.items():
        depth_pairs = [
            (item, difficulty_prior)
            for item, difficulty_prior in pairs
            if str(getattr(item, "difficulty", "")).lower() in policy.allowed_difficulties
            and (
                policy.allow_application
                or str(getattr(item, "question_intent", "")).lower() != "application"
            )
        ]
        filtered[unit_id] = depth_pairs
    return filtered


def _selected_answer_to_index(answer: SelectedAnswer) -> int:
    return {"A": 0, "B": 1, "C": 2, "D": 3}[answer.value]


def _classify_decision(score_pct: float) -> str:
    """Raw threshold — no Laplace smoothing, no cap rule."""
    if score_pct >= 70.0:
        return "skip"
    if score_pct >= 50.0:
        return "review"
    return "relearn"


def _canonical_item_to_assessment_question(item: QuestionBankItem):
    from src.schemas.assessment import QuestionForAssessment
    choices = list(item.choices or [])
    padded_choices = (choices + ["", "", "", ""])[:4]
    difficulty_bucket = None
    if item.difficulty in {bucket.value for bucket in DifficultyBucket}:
        difficulty_bucket = DifficultyBucket(item.difficulty)

    return QuestionForAssessment(
        id=None,
        item_id=item.item_id,
        canonical_item_id=item.item_id,
        canonical_unit_id=item.unit_id,
        topic_id=None,
        bloom_level=None,
        difficulty_bucket=difficulty_bucket,
        stem_text=item.question,
        option_a=str(padded_choices[0]),
        option_b=str(padded_choices[1]),
        option_c=str(padded_choices[2]),
        option_d=str(padded_choices[3]),
        time_expected_seconds=None,
    )


# ---------------------------------------------------------------------------
# start_assessment — per-unit selection with strategy router
# ---------------------------------------------------------------------------


async def start_assessment(
    db: AsyncSession,
    user_id: uuid.UUID,
    learning_unit_ids: list[uuid.UUID],
    canonical_unit_ids: list[str] | None = None,
    phase: str = "placement",
    assessment_depth: str = "standard",
    question_budget: int | None = None,
) -> AssessmentStartResponse:
    selected_unit_ids = await _resolve_canonical_unit_ids(
        db,
        learning_unit_ids=learning_unit_ids,
        canonical_unit_ids=canonical_unit_ids,
    )

    # Fetch per-unit pools
    repo = CanonicalQuestionRepository(db)
    unit_pools: UnitPools = {}
    for unit_id in selected_unit_ids:
        pairs = await repo.get_items_for_placement_bucketed(
            canonical_unit_ids=[unit_id],
            phase=phase,
        )
        unit_pools[unit_id] = pairs
        log.info(
            "assessment_start: unit=%s candidates=%d", unit_id, len(pairs)
        )

    policy = _assessment_budget_policy(assessment_depth, question_budget)
    filtered_unit_pools = _filter_unit_pools_for_depth(unit_pools, policy)
    strategy = pick_strategy(filtered_unit_pools)
    items = strategy.select(
        filtered_unit_pools,
        k=policy.questions_per_unit,
    )[: policy.max_questions]

    if not items:
        raise ValidationError("No eligible canonical assessment questions found.")

    session = Session(
        user_id=user_id,
        session_type=SessionType.assessment,
        topic_id=None,
        module_id=None,
        canonical_phase=phase,
        total_questions=len(items),
        correct_count=0,
        selection_strategy=strategy.name,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    log.info(
        "assessment_start: session=%s strategy=%s total_questions=%d",
        session.id,
        strategy.name,
        len(items),
    )

    return AssessmentStartResponse(
        session_id=session.id,
        total_questions=len(items),
        questions=[_canonical_item_to_assessment_question(item) for item in items],
        selection_strategy=strategy.name,
    )


async def _resolve_canonical_unit_ids(
    db: AsyncSession,
    *,
    learning_unit_ids: list[uuid.UUID],
    canonical_unit_ids: list[str] | None,
) -> list[str]:
    if canonical_unit_ids:
        return list(dict.fromkeys(str(unit_id) for unit_id in canonical_unit_ids))

    if not learning_unit_ids:
        raise ValidationError(
            "Assessment requires canonical_unit_ids or learning_unit_ids."
        )

    result = await db.execute(
        select(LearningUnit).where(LearningUnit.id.in_(learning_unit_ids))
    )
    units = result.scalars().all()
    unit_by_id = {unit.id: unit for unit in units if unit.canonical_unit_id}
    missing = [str(unit_id) for unit_id in learning_unit_ids if unit_id not in unit_by_id]
    if missing:
        raise ValidationError(
            "Assessment requires canonical learning unit IDs. Missing canonical mapping for: "
            + ", ".join(missing)
        )
    return [str(unit_by_id[unit_id].canonical_unit_id) for unit_id in learning_unit_ids]


# ---------------------------------------------------------------------------
# submit_assessment
# ---------------------------------------------------------------------------


async def submit_assessment(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    answers: list[AnswerInput],
) -> AssessmentResultResponse:
    session = await _get_session(db, user_id, session_id)
    if session.completed_at is not None:
        raise ConflictError("This assessment has already been submitted.")
    if not _is_canonical_answer_batch(answers):
        raise ValidationError(
            "Assessment submissions must include canonical_item_id. Legacy question_id submissions are removed."
        )
    return await _submit_canonical_assessment(
        db=db,
        user_id=user_id,
        session=session,
        session_id=session_id,
        answers=answers,
    )


def _is_canonical_answer_batch(answers: list[AnswerInput]) -> bool:
    return bool(answers) and all(answer.canonical_item_id for answer in answers)


async def _submit_canonical_assessment(
    db: AsyncSession,
    user_id: uuid.UUID,
    session: Session,
    session_id: uuid.UUID,
    answers: list[AnswerInput],
) -> AssessmentResultResponse:
    if not settings.write_canonical_interactions_enabled:
        raise ValidationError("Canonical assessment submit is not enabled.")

    canonical_item_ids = [str(answer.canonical_item_id) for answer in answers if answer.canonical_item_id]
    if len(canonical_item_ids) != len(set(canonical_item_ids)):
        raise ValidationError("Duplicate canonical_item_id entries in answers.")

    result = await db.execute(
        select(QuestionBankItem).where(QuestionBankItem.item_id.in_(canonical_item_ids))
    )
    items = {item.item_id: item for item in result.scalars().all()}
    missing = [item_id for item_id in canonical_item_ids if item_id not in items]
    if missing:
        raise ValidationError(f"Unknown canonical item IDs: {missing}")

    from sqlalchemy import func
    base_global_result = await db.execute(
        select(func.max(Interaction.global_sequence_position)).where(Interaction.user_id == user_id)
    )
    base_global = base_global_result.scalar() or 0
    now = datetime.now(UTC)
    correct_count = 0

    # Track per-unit correctness for decision classification
    per_unit_correct: dict[str, int] = defaultdict(int)
    per_unit_total: dict[str, int] = defaultdict(int)

    for seq, answer in enumerate(answers, start=1):
        item_id = str(answer.canonical_item_id)
        item = items[item_id]
        is_correct = int(item.answer_index) == _selected_answer_to_index(answer.selected_answer)
        if is_correct:
            correct_count += 1
        per_unit_correct[item.unit_id] += int(is_correct)
        per_unit_total[item.unit_id] += 1

        db.add(
            Interaction(
                user_id=user_id,
                session_id=session_id,
                question_id=None,
                canonical_item_id=item_id,
                sequence_position=seq,
                global_sequence_position=base_global + seq,
                selected_answer=SelectedAnswer(answer.selected_answer.value),
                is_correct=is_correct,
                response_time_ms=answer.response_time_ms,
                changed_answer=False,
                hint_used=False,
                explanation_viewed=False,
                timestamp=now,
            )
        )

        if settings.write_learner_mastery_kp_enabled:
            await update_kp_mastery_from_item(
                db,
                user_id=user_id,
                canonical_item_id=item_id,
                is_correct=is_correct,
            )

    total = len(answers)
    session.completed_at = now
    session.total_questions = total
    session.correct_count = correct_count
    session.score_percent = round(correct_count / total * 100, 1) if total else 0.0
    db.add(session)
    await db.flush()

    # Persist per-unit decisions to placement_assessment_results
    canonical_unit_ids_list = list(per_unit_total.keys())
    unit_lookup_result = await db.execute(
        select(LearningUnit).where(LearningUnit.canonical_unit_id.in_(canonical_unit_ids_list))
    )
    unit_by_canonical_for_placement = {
        str(u.canonical_unit_id): u for u in unit_lookup_result.scalars().all()
    }

    placement_repo = PlacementAssessmentRepository(db)
    for c_unit_id, unit_total in per_unit_total.items():
        unit_correct = per_unit_correct[c_unit_id]
        score_pct = round(unit_correct / unit_total * 100, 1) if unit_total else 0.0
        decision = _classify_decision(score_pct)
        unit = unit_by_canonical_for_placement.get(c_unit_id)
        if unit:
            await placement_repo.upsert(
                user_id=user_id,
                topic_unit_id=unit.id,
                score_pct=score_pct,
                decision=decision,
                raw_answers=[],
            )
            log.info(
                "assessment_submit: unit=%s score=%.1f decision=%s",
                c_unit_id, score_pct, decision,
            )

    # Build rows for response (transient objects, not added to DB)
    rows = [
        (
            Interaction(
                user_id=user_id,
                session_id=session_id,
                question_id=None,
                canonical_item_id=item.item_id,
                sequence_position=index,
                global_sequence_position=base_global + index,
                selected_answer=SelectedAnswer(answer.selected_answer.value),
                is_correct=int(item.answer_index) == _selected_answer_to_index(answer.selected_answer),
                response_time_ms=answer.response_time_ms,
                changed_answer=False,
                hint_used=False,
                explanation_viewed=False,
                timestamp=now,
            ),
            item,
        )
        for index, answer in enumerate(answers, start=1)
        for item in [items[str(answer.canonical_item_id)]]
    ]

    return await _build_canonical_assessment_response(
        db=db,
        session_id=session_id,
        completed_at=now,
        rows=rows,
        placement_overrides=None,  # fresh submit — use computed decisions
    )


# ---------------------------------------------------------------------------
# get_assessment_results
# ---------------------------------------------------------------------------


async def get_assessment_results(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> AssessmentResultResponse:
    session = await _get_session(db, user_id, session_id)
    if session.completed_at is None:
        raise NotFoundError("Assessment not yet submitted.")

    result = await db.execute(
        select(Interaction, QuestionBankItem)
        .join(QuestionBankItem, Interaction.canonical_item_id == QuestionBankItem.item_id)
        .where(Interaction.session_id == session_id)
        .order_by(Interaction.sequence_position)
    )
    rows = result.all()
    if not rows:
        raise NotFoundError("No canonical interaction data found for this session.")

    # Load any user-override decisions from placement_assessment_results
    placement_rows = await PlacementAssessmentRepository(db).get_by_user_id(user_id)
    placement_overrides = {
        str(row.topic_unit_id): str(row.decision) for row in placement_rows
    }

    return await _build_canonical_assessment_response(
        db=db,
        session_id=session_id,
        completed_at=session.completed_at,
        rows=rows,
        placement_overrides=placement_overrides,
    )


def _parse_assessment_ai_summary(raw: str) -> AssessmentAISummaryResponse:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = literal_eval(text)
    if not isinstance(payload, dict):
        return AssessmentAISummaryResponse(
            available=False,
            model_used=DEFAULT_MODEL,
            provider=settings.model_provider,
        )
    summary = payload.get("summary")
    next_step = payload.get("next_step")
    highlights_payload = payload.get("highlights", [])
    highlights = [
        item.strip()
        for item in highlights_payload
        if isinstance(item, str) and item.strip()
    ][:3]

    if not isinstance(summary, str) or not summary.strip():
        return AssessmentAISummaryResponse(
            available=False,
            model_used=DEFAULT_MODEL,
            provider=settings.model_provider,
        )

    return AssessmentAISummaryResponse(
        available=True,
        summary=summary.strip(),
        highlights=highlights,
        next_step=next_step.strip() if isinstance(next_step, str) and next_step.strip() else None,
        model_used=DEFAULT_MODEL,
        provider=settings.model_provider,
    )


def _assessment_summary_input(result: AssessmentResultResponse) -> str:
    decisions = result.topic_decisions or []
    priority = [
        {
            "title": item.topic_unit_name,
            "score_pct": item.score_pct,
            "decision": item.decision,
            "questions": f"{item.questions_correct}/{item.questions_total}",
        }
        for item in sorted(
            decisions,
            key=lambda item: (
                {"relearn": 0, "review": 1, "skip": 2}.get(item.decision, 9),
                item.score_pct,
            ),
        )[:8]
    ]
    counts = {
        "relearn": sum(1 for item in decisions if item.decision == "relearn"),
        "review": sum(1 for item in decisions if item.decision == "review"),
        "skip": sum(1 for item in decisions if item.decision == "skip"),
        "total": len(decisions),
    }
    weak_units = [
        {
            "title": unit.learning_unit_title,
            "score_percent": unit.score_percent,
            "mastery_level": str(unit.mastery_level),
            "weak_kcs": unit.weak_kcs[:5],
            "misconceptions": unit.misconceptions_detected[:5],
        }
        for unit in sorted(result.learning_unit_results, key=lambda unit: unit.score_percent)[:8]
    ]
    return json.dumps(
        {
            "overall_score_percent": result.overall_score_percent,
            "decision_counts": counts,
            "priority_units": priority,
            "weak_units": weak_units,
        },
        ensure_ascii=False,
    )


async def generate_assessment_ai_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> AssessmentAISummaryResponse:
    """Generate optional LLM feedback for an assessment result.

    This intentionally has no deterministic copy fallback. If the LLM is
    unavailable or invalid, the frontend should omit the AI summary block.
    """
    try:
        from langchain.chat_models import init_chat_model
        from langchain_core.messages import HumanMessage, SystemMessage

        from src.services.chat_model_factory import build_chat_model_kwargs
        from src.services.llm_rate_limiter import enforce_llm_rate_limit

        result = await get_assessment_results(db, user_id, session_id)
        enforce_llm_rate_limit(model=DEFAULT_MODEL, model_provider=settings.model_provider)
        llm = init_chat_model(
            **build_chat_model_kwargs(
                model=DEFAULT_MODEL,
                temperature=0.4,
                max_tokens=500,
            )
        )
        trace_metadata = build_langfuse_metadata(
            user_id=str(user_id),
            session_id=str(session_id),
            tags=["assessment", "summary"],
            feature="assessment",
            route="summary",
            assessment_session_id=str(session_id),
            overall_score_percent=result.overall_score_percent,
        )
        with start_langfuse_root_span(
            name="assessment-summary",
            input={"session_id": str(session_id)},
            metadata=trace_metadata,
        ):
            with propagate_langfuse_attributes(
                user_id=str(user_id),
                session_id=str(session_id),
                tags=["assessment", "summary"],
                metadata={
                    "feature": "assessment",
                    "route": "summary",
                    "assessment_session_id": str(session_id),
                },
                trace_name="assessment-summary",
            ):
                response = llm.invoke(
                    [
                        SystemMessage(content=_ASSESSMENT_SUMMARY_SYSTEM),
                        HumanMessage(content=_assessment_summary_input(result)),
                    ],
                    config={
                        "callbacks": llm_callbacks(),
                        "metadata": trace_metadata,
                    },
                )
        parsed = _parse_assessment_ai_summary(str(response.content))
        return parsed
    except Exception as exc:
        log.warning("assessment AI summary unavailable: %s", exc)
        return AssessmentAISummaryResponse(
            available=False,
            model_used=DEFAULT_MODEL,
            provider=settings.model_provider,
        )


# ---------------------------------------------------------------------------
# update_topic_decision
# ---------------------------------------------------------------------------


async def update_topic_decision(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic_unit_id: uuid.UUID,
    user_choice: str,
) -> TopicDecisionResult:
    """Override the decision for one unit. Updates placement_assessment_results.decision."""
    repo = PlacementAssessmentRepository(db)
    row = await repo.get_by_user_and_unit(user_id, topic_unit_id)
    if row is None:
        raise NotFoundError("No placement result found for this topic unit.")

    # Update decision field (user_choice column constraint limits to skip/review;
    # to support relearn override without migration, we update decision directly)
    row.decision = user_choice
    await db.flush()

    # Load unit title for response
    unit_result = await db.execute(
        select(LearningUnit).where(LearningUnit.id == topic_unit_id)
    )
    unit = unit_result.scalar_one_or_none()
    score_pct = float(row.score_pct)

    return TopicDecisionResult(
        topic_unit_id=str(topic_unit_id),
        topic_unit_name=unit.title if unit else str(topic_unit_id),
        score_pct=score_pct,
        decision=user_choice,
        mastery_level=str(classify_mastery(score_pct)),
        questions_total=0,
        questions_correct=0,
    )


# ---------------------------------------------------------------------------
# Internal response builder
# ---------------------------------------------------------------------------


async def _build_canonical_assessment_response(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    completed_at: datetime,
    rows: list[tuple[Interaction, QuestionBankItem]],
    placement_overrides: dict[str, str] | None,
) -> AssessmentResultResponse:
    unit_ids = sorted({item.unit_id for _, item in rows})
    unit_result = await db.execute(
        select(LearningUnit).where(LearningUnit.canonical_unit_id.in_(unit_ids))
    )
    unit_by_canonical_id = {
        str(unit.canonical_unit_id): unit for unit in unit_result.scalars().all() if unit.canonical_unit_id
    }

    wrong_item_ids = [item.item_id for interaction, item in rows if not interaction.is_correct]
    weak_kps = await _canonical_kp_names_by_item(db, wrong_item_ids)
    per_unit_rows: dict[str, list[tuple[Interaction, QuestionBankItem]]] = defaultdict(list)
    for interaction, item in rows:
        per_unit_rows[item.unit_id].append((interaction, item))

    learning_unit_results: list[LearningUnitResult] = []
    topic_decisions: list[TopicDecisionResult] = []
    total_correct = 0
    total_questions = 0

    for unit_id, unit_rows in per_unit_rows.items():
        correct = sum(1 for interaction, _ in unit_rows if interaction.is_correct)
        total = len(unit_rows)
        total_correct += correct
        total_questions += total
        score_percent = round(correct / total * 100, 1) if total else 0.0
        unit = unit_by_canonical_id.get(unit_id)
        mastery = classify_mastery(score_percent)

        learning_unit_results.append(
            LearningUnitResult(
                learning_unit_id=unit.id if unit is not None else uuid.uuid5(uuid.NAMESPACE_URL, unit_id),
                learning_unit_title=unit.title if unit is not None else unit_id,
                score_percent=score_percent,
                mastery_level=mastery,
                bloom_breakdown={"canonical": f"{correct}/{total}"},
                weak_kcs=weak_kps.get(unit_id, []),
                misconceptions_detected=[],
                theta_estimate=0.0,
            )
        )

        # Build topic_decision for this unit
        topic_unit_id_str = str(unit.id) if unit else unit_id
        computed_decision = _classify_decision(score_percent)
        decision = (
            placement_overrides.get(topic_unit_id_str, computed_decision)
            if placement_overrides
            else computed_decision
        )
        topic_decisions.append(
            TopicDecisionResult(
                topic_unit_id=topic_unit_id_str,
                topic_unit_name=unit.title if unit else unit_id,
                score_pct=score_percent,
                decision=decision,
                mastery_level=str(mastery),
                questions_total=total,
                questions_correct=correct,
            )
        )

    learning_unit_results.sort(key=lambda item: item.learning_unit_title.lower())
    topic_decisions.sort(key=lambda d: d.topic_unit_name.lower())

    overall_score = round(total_correct / total_questions * 100, 1) if total_questions else 0.0
    return AssessmentResultResponse(
        session_id=session_id,
        completed_at=completed_at,
        overall_score_percent=overall_score,
        learning_unit_results=learning_unit_results,
        topic_decisions=topic_decisions if topic_decisions else None,
    )


async def _canonical_kp_names_by_item(
    db: AsyncSession,
    item_ids: list[str],
) -> dict[str, list[str]]:
    if not item_ids:
        return {}
    result = await db.execute(
        select(ItemKPMap.unit_id, ConceptKP.name)
        .join(ConceptKP, ItemKPMap.kp_id == ConceptKP.kp_id)
        .where(ItemKPMap.item_id.in_(item_ids))
    )
    per_unit: dict[str, set[str]] = defaultdict(set)
    for unit_id, kp_name in result.all():
        if kp_name:
            per_unit[str(unit_id)].add(str(kp_name))
    return {unit_id: sorted(names) for unit_id, names in per_unit.items()}


async def _get_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> Session:
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
            Session.session_type == SessionType.assessment,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise NotFoundError("Assessment session not found.")
    return session
