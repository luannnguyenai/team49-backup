"""
services/assessment_service.py
--------------------------------
Business logic for the Assessment Engine.

Flow
----
1. start_assessment   — validate topics, select questions, create Session
2. submit_assessment  — grade answers, create Interactions, compute + persist mastery
3. get_assessment_results — recompute results from stored Interactions

Question selection per topic (5 questions):
  Slot A  — 1 question  bloom=remember
  Slot B  — 2 questions bloom∈{understand, apply}
  Slot C  — 2 questions bloom=analyze
  Filter: status=active AND usage_context @> '["assessment"]'
  Exclude: questions the user has ever answered before
"""

import math
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.content import (
    BloomLevel,
    KnowledgeComponent,
    Question,
    Topic,
)
from src.models.learning import (
    Interaction,
    MasteryScore,
    SelectedAnswer,
    Session,
    SessionType,
)
from src.schemas.assessment import (
    AnswerInput,
    AssessmentResultResponse,
    AssessmentStartResponse,
    QuestionForAssessment,
    TopicResult,
)
from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.repositories.assessment_repo import AssessmentRepository
from src.repositories.question_repo import QuestionRepository
from src.services.mastery_evaluator import (
    QuestionResult,
    TopicMasteryResult,
    evaluate_topic,
)
from src.services.question_selector import QuestionSelector

# ---------------------------------------------------------------------------
# 2PL IRT model
# ---------------------------------------------------------------------------
#
# P(θ | a, b) = 1 / (1 + exp(−a · (θ − b)))
#
#   a  — discrimination: steepness of the ICC curve  (default 1.0 when uncalibrated)
#   b  — difficulty: θ value at which P = 0.50       (default from difficulty_bucket)
#   θ  — ability estimate on a logit scale  [−3, +3]
#
# No guessing parameter (c = 0), unlike 3PL.
# ---------------------------------------------------------------------------

# Default parameter values used when a question has not been IRT-calibrated yet.
_IRT_DEFAULT_DISCRIMINATION: float = 1.0
_IRT_BUCKET_DIFFICULTY: dict[str, float] = {
    "easy": -1.0,    # b ≈ −1 SD  → answered correctly by most users
    "medium": 0.0,   # b =  0     → average difficulty
    "hard": 1.0,     # b ≈ +1 SD  → challenging for most users
}


def _resolve_2pl_params(q: "Question") -> tuple[float, float]:
    """Return (a, b) for a question.

    Uses stored IRT params when available; falls back to bucket defaults so
    that the 2PL model works even before formal calibration.
    """
    a = q.irt_discrimination if q.irt_discrimination is not None else _IRT_DEFAULT_DISCRIMINATION
    if q.irt_difficulty is not None:
        b = q.irt_difficulty
    else:
        bucket_key = q.difficulty_bucket.value if q.difficulty_bucket else "medium"
        b = _IRT_BUCKET_DIFFICULTY.get(bucket_key, 0.0)
    return max(a, 0.1), b  # a must be strictly positive


def _irt_2pl_prob(theta: float, a: float, b: float) -> float:
    """Probability of a correct response under the 2PL model."""
    exponent = -a * (theta - b)
    exponent = max(-500.0, min(500.0, exponent))  # guard against overflow
    return 1.0 / (1.0 + math.exp(exponent))


def _irt_2pl_information(theta: float, a: float, b: float) -> float:
    """Item information function: I(θ) = a² · P(θ) · (1 − P(θ)).

    Maximum information is achieved when θ ≈ b (item difficulty), so
    selecting items whose b is closest to the current θ maximises measurement
    precision — equivalent to, but more principled than, simple |b − θ|.
    """
    p = _irt_2pl_prob(theta, a, b)
    return a * a * p * (1.0 - p)


def _estimate_theta_2pl(
    responses: list[tuple[float, float, bool]],
    theta_init: float = 0.0,
) -> float:
    """Newton-Raphson MLE for ability θ under the 2PL IRT model.

    Parameters
    ----------
    responses  : list of (a, b, is_correct) triples
    theta_init : starting value; use prior mastery estimate when available

    Returns
    -------
    float — θ̂ clamped to [−3.0, 3.0].  Returns theta_init when the response
            vector is empty or the likelihood is flat (all correct / all wrong).
    """
    if not responses:
        return theta_init

    theta = theta_init
    for _ in range(50):
        L1 = 0.0   # ∂ log L / ∂θ   (score function)
        L2 = 0.0   # ∂² log L / ∂θ² (observed information, negative)
        for a, b, correct in responses:
            p = _irt_2pl_prob(theta, a, b)
            q_val = 1.0 - p
            L1 += a * (int(correct) - p)
            L2 -= a * a * p * q_val
        if abs(L2) < 1e-9:
            break  # flat likelihood — can't improve (e.g. all correct / all wrong)
        delta = L1 / L2
        theta -= delta
        if abs(delta) < 1e-4:
            break  # converged

    return max(-3.0, min(3.0, theta))


# ---------------------------------------------------------------------------
# Question selection: bloom slot definition
# ---------------------------------------------------------------------------

_BLOOM_SLOTS: list[tuple[list[BloomLevel], int]] = [
    ([BloomLevel.remember], 1),
    ([BloomLevel.understand, BloomLevel.apply], 2),
    ([BloomLevel.analyze], 2),
]


# ===========================================================================
# POST /api/assessment/start
# ===========================================================================


async def start_assessment(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic_ids: list[uuid.UUID],
) -> AssessmentStartResponse:
    repo = AssessmentRepository(db)
    # 1. Validate all requested topics exist
    found_ids = {t.id for t in await repo.get_topics_by_ids(topic_ids)}
    missing = [tid for tid in topic_ids if tid not in found_ids]
    if missing:
        raise NotFoundError(f"Topics not found: {[str(m) for m in missing]}")

    # 2. Collect answered question IDs + estimate ability (θ) from user history
    rows = await repo.get_answered_question_rows(user_id)
    excluded_ids: set[uuid.UUID] = {row[0] for row in rows}

    # ── 2PL MLE ability estimate ──────────────────────────────────────────────
    # Build (a, b, is_correct) triples for every previously answered question.
    # Questions without calibrated IRT params use bucket-derived defaults so
    # the 2PL estimator works even before formal item calibration.
    ability = 0.0  # θ = 0 for brand-new users (average ability prior)
    if rows:
        hist_ids = [row[0] for row in rows]
        hist_q_map = {q.id: q for q in await repo.get_questions_by_ids(hist_ids)}
        correct_map: dict[uuid.UUID, bool] = {row[0]: row[1] for row in rows}

        irt_responses: list[tuple[float, float, bool]] = [
            (*_resolve_2pl_params(hist_q_map[qid]), is_correct)
            for qid, is_correct in correct_map.items()
            if qid in hist_q_map
        ]
        ability = _estimate_theta_2pl(irt_responses)

    # 3. Select questions for each topic
    all_questions: list[Question] = []
    skipped_topics: list[str] = []
    for topic_id in topic_ids:
        topic_qs = await _select_questions_for_topic(db, user_id, topic_id, excluded_ids, ability)
        if topic_qs:
            all_questions.extend(topic_qs)
        else:
            skipped_topics.append(str(topic_id))

    if not all_questions:
        raise ValidationError((
                "No eligible assessment questions found for any of the requested topics. "
                "The question bank may not include active assessment questions for these topics."
            ))

    # 4. Create the Session (no topic_id/module_id — spans multiple topics)
    session = Session(
        user_id=user_id,
        session_type=SessionType.assessment,
        topic_id=None,
        module_id=None,
        total_questions=len(all_questions),
        correct_count=0,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    return AssessmentStartResponse(
        session_id=session.id,
        total_questions=len(all_questions),
        questions=[QuestionForAssessment.model_validate(q) for q in all_questions],
    )


async def _select_questions_for_topic(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic_id: uuid.UUID,
    excluded_ids: set[uuid.UUID],
    ability: float = 0.0,
) -> list[Question]:
    """Select assessment questions through the shared QuestionSelector strategy."""
    selector = QuestionSelector(QuestionRepository(db))
    return await selector.select_by_bloom_irt(
        user_id=user_id,
        topic_id=topic_id,
        slots=_BLOOM_SLOTS,
        ability=ability,
        excluded_ids=excluded_ids,
    )


# ===========================================================================
# POST /api/assessment/{session_id}/submit
# ===========================================================================


async def submit_assessment(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    answers: list[AnswerInput],
) -> AssessmentResultResponse:
    repo = AssessmentRepository(db)
    # 1. Load + validate session ownership
    session = await _get_session(db, user_id, session_id)
    if session.completed_at is not None:
        raise ConflictError("This assessment has already been submitted.")

    # 2. Reject duplicate question_ids in the submission
    question_ids = [a.question_id for a in answers]
    if len(question_ids) != len(set(question_ids)):
        raise ValidationError("Duplicate question_id entries in answers.")

    # 3. Batch-load all referenced questions
    questions = {q.id: q for q in await repo.get_questions_by_ids(question_ids)}
    missing = [qid for qid in question_ids if qid not in questions]
    if missing:
        raise ValidationError(f"Unknown question IDs: {[str(m) for m in missing]}")

    # 4. Determine next global_sequence_position for this user
    base_global = await repo.get_max_global_sequence(user_id)

    # 5. Grade answers, create Interactions, build QuestionResult list
    now = datetime.now(UTC)
    correct_count = 0
    question_results: list[QuestionResult] = []

    for seq, answer in enumerate(answers, start=1):
        q = questions[answer.question_id]
        is_correct = q.correct_answer.value == answer.selected_answer.value

        if is_correct:
            correct_count += 1

        db.add(
            Interaction(
                user_id=user_id,
                session_id=session_id,
                question_id=answer.question_id,
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

        question_results.append(
            QuestionResult(
                question_id=q.id,
                topic_id=q.topic_id,
                bloom_level=q.bloom_level,
                correct_answer=q.correct_answer,
                selected_answer=answer.selected_answer,
                is_correct=is_correct,
                kc_ids=q.kc_ids or [],
                misconception_a_id=q.misconception_a_id,
                misconception_b_id=q.misconception_b_id,
                misconception_c_id=q.misconception_c_id,
                misconception_d_id=q.misconception_d_id,
            )
        )

    # 6. Complete the session (raw correct rate for session-level score)
    total = len(answers)
    session.completed_at = now
    session.total_questions = total
    session.correct_count = correct_count
    session.score_percent = round(correct_count / total * 100, 1) if total else 0.0
    db.add(session)

    # 7. Evaluate mastery per topic + compute 2PL theta per topic
    grouped: dict[uuid.UUID, list[QuestionResult]] = {}
    for qr in question_results:
        grouped.setdefault(qr.topic_id, []).append(qr)

    topic_results_map: dict[uuid.UUID, TopicMasteryResult] = {
        topic_id: evaluate_topic(qrs) for topic_id, qrs in grouped.items()
    }

    # Build per-topic IRT response vectors and estimate final θ̂ per topic.
    # The seed θ_init per topic is the overall session ability (all answers).
    all_irt: list[tuple[float, float, bool]] = [
        (*_resolve_2pl_params(questions[qr.question_id]), qr.is_correct)
        for qr in question_results
        if qr.question_id in questions
    ]
    session_theta = _estimate_theta_2pl(all_irt)

    topic_theta: dict[uuid.UUID, float] = {}
    for topic_id, qrs in grouped.items():
        irt_vec: list[tuple[float, float, bool]] = [
            (*_resolve_2pl_params(questions[qr.question_id]), qr.is_correct)
            for qr in qrs
            if qr.question_id in questions
        ]
        topic_theta[topic_id] = _estimate_theta_2pl(irt_vec, theta_init=session_theta)

    # 8. Upsert topic-grain MasteryScore records
    await _upsert_mastery_scores(db, user_id, topic_results_map, now)
    await db.flush()

    return await _build_result_response(db, session_id, topic_results_map, now, topic_theta)


# ===========================================================================
# GET /api/assessment/{session_id}/results
# ===========================================================================


async def get_assessment_results(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> AssessmentResultResponse:
    repo = AssessmentRepository(db)
    session = await _get_session(db, user_id, session_id)
    if session.completed_at is None:
        raise NotFoundError("Assessment not yet submitted.")

    # Load all interactions joined with their questions
    rows = await repo.get_session_question_rows(session_id)

    if not rows:
        raise NotFoundError("No interaction data found for this session.")

    # Rebuild QuestionResult list from stored interactions
    question_results: list[QuestionResult] = [
        QuestionResult(
            question_id=q.id,
            topic_id=q.topic_id,
            bloom_level=q.bloom_level,
            correct_answer=q.correct_answer,
            selected_answer=interaction.selected_answer,
            is_correct=interaction.is_correct,
            kc_ids=q.kc_ids or [],
            misconception_a_id=q.misconception_a_id,
            misconception_b_id=q.misconception_b_id,
            misconception_c_id=q.misconception_c_id,
            misconception_d_id=q.misconception_d_id,
        )
        for interaction, q in rows
    ]

    # Group by topic and evaluate
    grouped: dict[uuid.UUID, list[QuestionResult]] = {}
    for qr in question_results:
        grouped.setdefault(qr.topic_id, []).append(qr)

    topic_results_map: dict[uuid.UUID, TopicMasteryResult] = {
        topic_id: evaluate_topic(qrs) for topic_id, qrs in grouped.items()
    }

    return await _build_result_response(db, session_id, topic_results_map, session.completed_at)


# ===========================================================================
# Helpers
# ===========================================================================


async def _get_session(db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID) -> Session:
    repo = AssessmentRepository(db)
    session = await repo.get_assessment_session(user_id=user_id, session_id=session_id)
    if session is None:
        raise NotFoundError("Assessment session not found.")
    return session


async def _upsert_mastery_scores(
    db: AsyncSession,
    user_id: uuid.UUID,
    results: dict[uuid.UUID, TopicMasteryResult],
    now: datetime,
) -> None:
    """Insert or update topic-grain MasteryScore for every evaluated topic."""
    for topic_id, r in results.items():
        repo = AssessmentRepository(db)
        score = await repo.get_mastery_score(user_id=user_id, topic_id=topic_id)

        if score is None:
            score = MasteryScore(
                user_id=user_id,
                topic_id=topic_id,
                kc_id=None,
                evidence_count=0,
            )
            db.add(score)

        score.mastery_probability = r.mastery_probability
        score.mastery_level = r.mastery_level
        score.bloom_max_achieved = r.bloom_max_achieved
        score.evidence_count = score.evidence_count + r.max_points
        score.recent_trend = None  # trend requires history; set by a dedicated job
        score.last_practiced = now


async def _build_result_response(
    db: AsyncSession,
    session_id: uuid.UUID,
    topic_results_map: dict[uuid.UUID, TopicMasteryResult],
    completed_at: datetime,
    topic_theta: dict[uuid.UUID, float] | None = None,
) -> AssessmentResultResponse:
    """Construct the API response, resolving topic names and KC names."""

    topic_ids = list(topic_results_map.keys())

    # Batch-fetch topic names
    repo = AssessmentRepository(db)
    topics = await repo.get_topic_map(topic_ids)

    # Batch-fetch KC names for all weak KC UUIDs
    all_weak_kc_uuids: list[uuid.UUID] = []
    for r in topic_results_map.values():
        for kc_id_str in r.weak_kc_ids:
            try:
                all_weak_kc_uuids.append(uuid.UUID(kc_id_str))
            except ValueError:
                pass  # non-UUID slug; will fall back to raw string

    kc_name_by_id: dict[str, str] = {}
    if all_weak_kc_uuids:
        kc_name_by_id = await repo.get_kc_name_map(all_weak_kc_uuids)

    # Compute overall weighted score across all topics
    total_earned = sum(r.earned_points for r in topic_results_map.values())
    total_max = sum(r.max_points for r in topic_results_map.values())
    overall_score = round(total_earned / total_max * 100, 1) if total_max > 0 else 0.0

    # Build per-topic result list
    theta_map = topic_theta or {}
    topic_results: list[TopicResult] = []
    for topic_id, r in topic_results_map.items():
        topic = topics.get(topic_id)
        topic_results.append(
            TopicResult(
                topic_id=topic_id,
                topic_name=topic.name if topic else str(topic_id),
                score_percent=r.score_percent,
                mastery_level=r.mastery_level,
                bloom_breakdown=r.bloom_breakdown,
                weak_kcs=[kc_name_by_id.get(kc_id, kc_id) for kc_id in r.weak_kc_ids],
                misconceptions_detected=r.misconceptions_detected,
                theta_estimate=round(theta_map.get(topic_id, 0.0), 4),
            )
        )

    return AssessmentResultResponse(
        session_id=session_id,
        completed_at=completed_at,
        overall_score_percent=overall_score,
        topic_results=topic_results,
    )
