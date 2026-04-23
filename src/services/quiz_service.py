"""
services/quiz_service.py
------------------------
Business logic for the Quiz System.

Flow
----
1. start_quiz
   - Validate topic exists.
   - Select 10 questions: 3 Easy · 4 Medium · 3 Hard
     Filter: usage_context @> '["quiz"]'
     Priority per bucket:
       tier-1 → never answered by this user
       tier-2 → answered previously and got it WRONG at some point
       tier-3 → answered correctly in all prior attempts
     Exclude questions seen in the user's last 2 assessment sessions.
   - Create Session(type=quiz, topic_id=topic_id).
   - Return session_id + questions (no correct_answer).

2. answer_question  (real-time, one question at a time)
   - Validate session ownership + open + question belongs to session.
   - Guard duplicate answers (one answer per question per session).
   - Save Interaction.
   - Return is_correct + correct_answer + explanation + running tally.

3. complete_quiz
   - Validate session ownership + not already completed.
   - Load all interactions for the session.
   - Compute raw score.
   - EMA-update MasteryScore.
   - Update bloom_max_achieved.
   - Detect new misconceptions (wrong answer → misconception field).
   - Update LearningPath status → completed if mastery ≥ 76.
   - Mark session completed.
   - Return QuizCompleteResponse.

4. get_quiz_history
   - Return Sessions (type=quiz) for user, optionally filtered by topic.
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.models.canonical import ItemKPMap, QuestionBankItem
from src.models.content import (
    DifficultyBucket,
    KnowledgeComponent,
    Question,
    Topic,
)
from src.models.course import LearningUnit
from src.models.learning import (
    Interaction,
    LearningPath,
    MasteryScore,
    PathStatus,
    SelectedAnswer,
    Session,
    SessionType,
)
from src.schemas.quiz import (
    QuestionForQuiz,
    QuizAnswerRequest,
    QuizAnswerResponse,
    QuizCompleteResponse,
    QuizHistoryResponse,
    QuizHistorySummary,
    QuizStartResponse,
)
from src.services.mastery_evaluator import (
    QuestionResult,
    apply_ema_mastery,
    classify_mastery,
    evaluate_topic,
    update_bloom_max,
)
from src.services.canonical_assessor_compat import (
    answer_index_to_correct_answer,
    canonical_item_to_quiz_question,
    canonical_question_uuid,
    selected_answer_to_index,
)
from src.services.canonical_mastery_service import update_kp_mastery_from_item
from src.services.canonical_question_selector import CanonicalQuestionSelector
from src.repositories.canonical_question_repo import CanonicalQuestionRepository

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Target counts per difficulty bucket
_DIFFICULTY_SLOTS: list[tuple[DifficultyBucket, int]] = [
    (DifficultyBucket.easy, 3),
    (DifficultyBucket.medium, 4),
    (DifficultyBucket.hard, 3),
]

# How many recent assessment sessions to look back for exclusion
_RECENT_ASSESSMENT_LOOKBACK = 2


def _ensure_legacy_quiz_question_reads_allowed() -> None:
    if not settings.allow_legacy_question_reads:
        raise ValidationError(
            "Legacy quiz question reads are disabled. Use canonical question_bank quiz flow."
        )


def _ensure_legacy_quiz_mutations_allowed() -> None:
    if not settings.allow_legacy_mastery_writes:
        raise ValidationError(
            "Legacy quiz mastery writes are disabled. Use learner_mastery_kp canonical updates."
        )
    if not settings.allow_legacy_planner_writes:
        raise ValidationError(
            "Legacy quiz learning_path writes are disabled. Use canonical planner audit/output."
        )


# ===========================================================================
# POST /api/quiz/start
# ===========================================================================


async def start_quiz(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic_id: uuid.UUID,
) -> QuizStartResponse:
    if not settings.allow_legacy_question_reads:
        return await _start_canonical_quiz(db, user_id, topic_id)

    _ensure_legacy_quiz_question_reads_allowed()

    # 1. Validate topic
    await _get_topic_or_404(db, topic_id)

    # 2. Get question IDs seen in last N assessment sessions
    excluded_from_assessments = await _recent_assessment_question_ids(
        db, user_id, lookback=_RECENT_ASSESSMENT_LOOKBACK
    )

    # 3. Get the user's interaction history on this topic for prioritisation
    prior_results = await _prior_topic_interactions(db, user_id, topic_id)
    # prior_results: dict[question_id → True if ever wrong, False if always correct]
    ever_wrong: set[uuid.UUID] = {qid for qid, wrong in prior_results.items() if wrong}
    always_correct: set[uuid.UUID] = {qid for qid, wrong in prior_results.items() if not wrong}
    answered_ids: set[uuid.UUID] = set(prior_results.keys())

    # 4. Select questions per difficulty bucket with tier prioritisation
    selected: list[Question] = []
    selected_ids: set[uuid.UUID] = set()

    for difficulty, count in _DIFFICULTY_SLOTS:
        pool = await _get_quiz_questions_for_bucket(db, topic_id, difficulty)

        # Filter out recently-seen assessment questions
        pool = [q for q in pool if q.id not in excluded_from_assessments]
        # Filter already selected in this session (shouldn't overlap, safety guard)
        pool = [q for q in pool if q.id not in selected_ids]

        # Split into priority tiers
        tier1 = [q for q in pool if q.id not in answered_ids]  # never answered
        tier2 = [q for q in pool if q.id in ever_wrong]  # prev wrong
        tier3 = [q for q in pool if q.id in always_correct]  # prev all-correct

        chosen = _sample_with_priority([tier1, tier2, tier3], count)
        selected.extend(chosen)
        selected_ids.update(q.id for q in chosen)

    if not selected:
        raise ValidationError("Không tìm thấy câu hỏi quiz cho topic này. "
            "Hãy đảm bảo question bank đã được seeded.")

    # 5. Shuffle final list so difficulty doesn't cluster
    random.shuffle(selected)

    # 6. Create Session
    session = Session(
        user_id=user_id,
        session_type=SessionType.quiz,
        topic_id=topic_id,
        module_id=None,
        total_questions=len(selected),
        correct_count=0,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    return QuizStartResponse(
        session_id=session.id,
        topic_id=topic_id,
        total_questions=len(selected),
        questions=[QuestionForQuiz.model_validate(q) for q in selected],
    )


# ===========================================================================
# POST /api/quiz/{session_id}/answer
# ===========================================================================


async def answer_question(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    req: QuizAnswerRequest,
) -> QuizAnswerResponse:
    # 1. Load and validate session
    session = await _get_quiz_session(db, user_id, session_id)
    if session.canonical_unit_id is not None:
        return await _answer_canonical_quiz_question(db, user_id, session, req)

    _ensure_legacy_quiz_question_reads_allowed()
    if session.completed_at is not None:
        raise ConflictError("Quiz đã hoàn thành. Không thể ghi thêm câu trả lời.")

    # 2. Load question and verify it belongs to the session topic
    q_result = await db.execute(select(Question).where(Question.id == req.question_id))
    question = q_result.scalar_one_or_none()
    if question is None:
        raise NotFoundError("Question not found.")
    if question.topic_id != session.topic_id:
        raise ValidationError("Question does not belong to this quiz's topic.")

    # 3. Guard: already answered this question in this session?
    existing = await db.execute(
        select(Interaction).where(
            Interaction.session_id == session_id,
            Interaction.question_id == req.question_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("Câu hỏi này đã được trả lời trong phiên quiz này.")

    # 4. Determine correctness
    is_correct = question.correct_answer.value == req.selected_answer.value

    # 5. Determine sequence position within session
    count_result = await db.execute(
        select(func.count()).where(Interaction.session_id == session_id)
    )
    seq_pos: int = (count_result.scalar() or 0) + 1

    # 6. Global sequence position (across all user sessions)
    max_global_result = await db.execute(
        select(func.max(Interaction.global_sequence_position)).where(Interaction.user_id == user_id)
    )
    base_global: int = max_global_result.scalar() or 0

    # 7. Persist interaction
    db.add(
        Interaction(
            user_id=user_id,
            session_id=session_id,
            question_id=req.question_id,
            sequence_position=seq_pos,
            global_sequence_position=base_global + 1,
            selected_answer=SelectedAnswer(req.selected_answer.value),
            is_correct=is_correct,
            response_time_ms=req.response_time_ms,
            changed_answer=False,
            hint_used=False,
            explanation_viewed=bool(question.explanation_text),
            timestamp=datetime.now(UTC),
        )
    )
    await db.flush()

    # 8. Running tally for live progress display
    # Count all interactions in this session (including the one just saved)
    all_interactions_result = await db.execute(
        select(Interaction.is_correct).where(Interaction.session_id == session_id)
    )
    all_correct_flags = all_interactions_result.scalars().all()
    questions_answered = len(all_correct_flags)
    questions_correct = sum(1 for c in all_correct_flags if c)

    return QuizAnswerResponse(
        is_correct=is_correct,
        correct_answer=question.correct_answer,
        explanation_text=question.explanation_text,
        questions_answered=questions_answered,
        questions_correct=questions_correct,
    )


# ===========================================================================
# POST /api/quiz/{session_id}/complete
# ===========================================================================


async def complete_quiz(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> QuizCompleteResponse:
    # 1. Validate session
    session = await _get_quiz_session(db, user_id, session_id)
    if session.canonical_unit_id is not None:
        return await _complete_canonical_quiz(db, user_id, session)

    _ensure_legacy_quiz_question_reads_allowed()
    _ensure_legacy_quiz_mutations_allowed()
    if session.completed_at is not None:
        raise ConflictError("Quiz đã được hoàn thành trước đó.")

    # 2. Load all interactions + questions for this session
    rows_result = await db.execute(
        select(Interaction, Question)
        .join(Question, Interaction.question_id == Question.id)
        .where(Interaction.session_id == session_id)
        .order_by(Interaction.sequence_position)
    )
    rows = rows_result.all()

    if not rows:
        raise ValidationError("Không có câu trả lời nào trong phiên quiz. "
            "Hãy trả lời ít nhất 1 câu trước khi hoàn thành.")

    topic_id = session.topic_id
    topic = await _get_topic_or_404(db, topic_id)

    # 3. Build QuestionResult list for the evaluator
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

    eval_result = evaluate_topic(question_results)

    # 4. Raw score
    total_answered = len(rows)
    correct_count = sum(1 for r in question_results if r.is_correct)
    quiz_score_percent = round(correct_count / total_answered * 100, 1) if total_answered else 0.0

    # 5. Load existing MasteryScore (topic-grain)
    ms_result = await db.execute(
        select(MasteryScore).where(
            MasteryScore.user_id == user_id,
            MasteryScore.topic_id == topic_id,
            MasteryScore.kc_id.is_(None),
        )
    )
    mastery_score = ms_result.scalar_one_or_none()
    mastery_before = round((mastery_score.mastery_probability * 100), 1) if mastery_score else 0.0

    # 6. EMA update
    mastery_after = apply_ema_mastery(mastery_before, quiz_score_percent)
    new_level = classify_mastery(mastery_after)

    # 7. Update bloom_max_achieved
    current_bloom_max = mastery_score.bloom_max_achieved if mastery_score else None
    new_bloom_max = current_bloom_max
    for r in question_results:
        if r.is_correct:
            new_bloom_max = update_bloom_max(new_bloom_max, r.bloom_level)

    # 8. Upsert MasteryScore
    now = datetime.now(UTC)
    if mastery_score is None:
        mastery_score = MasteryScore(
            user_id=user_id,
            topic_id=topic_id,
            kc_id=None,
            evidence_count=0,
        )
        db.add(mastery_score)

    mastery_score.mastery_probability = round(mastery_after / 100, 4)
    mastery_score.mastery_level = new_level
    mastery_score.bloom_max_achieved = new_bloom_max
    mastery_score.evidence_count = mastery_score.evidence_count + total_answered
    mastery_score.last_practiced = now

    # 9. Resolve weak KC names
    weak_kc_names = await _resolve_kc_names(db, eval_result.weak_kc_ids)

    # 10. Update LearningPath status if mastery ≥ 76 → mark completed
    lp_updated = await _maybe_complete_learning_path(db, user_id, topic_id, mastery_after)

    # 11. Compute timing
    time_total_ms = sum((interaction.response_time_ms or 0) for interaction, _ in rows)
    time_total_sec = round(time_total_ms / 1000, 1)
    avg_time_sec = round(time_total_sec / total_answered, 1) if total_answered else 0.0

    # 12. Finalise session
    session.completed_at = now
    session.total_questions = total_answered
    session.correct_count = correct_count
    session.score_percent = quiz_score_percent
    db.add(session)

    await db.flush()

    return QuizCompleteResponse(
        session_id=session_id,
        topic_id=topic_id,
        topic_name=topic.name,
        score=f"{correct_count}/{total_answered}",
        percent=quiz_score_percent,
        mastery_before=mastery_before,
        mastery_after=mastery_after,
        mastery_level=new_level,
        bloom_breakdown=eval_result.bloom_breakdown,
        weak_kcs=weak_kc_names,
        misconceptions=eval_result.misconceptions_detected,
        time_total_seconds=time_total_sec,
        avg_time_per_question=avg_time_sec,
        learning_path_updated=lp_updated,
    )


# ===========================================================================
# GET /api/quiz/history
# ===========================================================================


async def get_quiz_history(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic_id: uuid.UUID | None = None,
) -> QuizHistoryResponse:
    _ensure_legacy_quiz_question_reads_allowed()

    stmt = (
        select(Session, Topic.name.label("topic_name"))
        .join(Topic, Session.topic_id == Topic.id)
        .where(
            Session.user_id == user_id,
            Session.session_type == SessionType.quiz,
        )
        .order_by(Session.started_at.desc())
    )
    if topic_id is not None:
        stmt = stmt.where(Session.topic_id == topic_id)

    result = await db.execute(stmt)
    rows = result.all()

    items: list[QuizHistorySummary] = [
        QuizHistorySummary(
            session_id=sess.id,
            topic_id=sess.topic_id,
            topic_name=topic_name,
            score_percent=sess.score_percent,
            correct_count=sess.correct_count,
            total_questions=sess.total_questions,
            completed_at=sess.completed_at,
            started_at=sess.started_at,
        )
        for sess, topic_name in rows
    ]

    return QuizHistoryResponse(total=len(items), items=items)


# ===========================================================================
# Internal helpers
# ===========================================================================


async def _get_topic_or_404(db: AsyncSession, topic_id: uuid.UUID) -> Topic:
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    if topic is None:
        raise NotFoundError(f"Topic {topic_id} not found.")
    return topic


async def _get_learning_unit_or_404(db: AsyncSession, learning_unit_id: uuid.UUID) -> LearningUnit:
    result = await db.execute(select(LearningUnit).where(LearningUnit.id == learning_unit_id))
    unit = result.scalar_one_or_none()
    if unit is None or not unit.canonical_unit_id:
        raise NotFoundError(f"Canonical learning unit {learning_unit_id} not found.")
    return unit


async def _start_canonical_quiz(
    db: AsyncSession,
    user_id: uuid.UUID,
    learning_unit_id: uuid.UUID,
) -> QuizStartResponse:
    unit = await _get_learning_unit_or_404(db, learning_unit_id)
    selector = CanonicalQuestionSelector(CanonicalQuestionRepository(db))
    items = await selector.select_for_phase(
        phase="mini_quiz",
        canonical_unit_ids=[unit.canonical_unit_id],
        count=10,
    )
    if not items:
        raise ValidationError("Không tìm thấy câu hỏi quiz canonical cho learning unit này.")

    session = Session(
        user_id=user_id,
        session_type=SessionType.quiz,
        topic_id=None,
        module_id=None,
        canonical_unit_id=unit.id,
        canonical_phase="mini_quiz",
        total_questions=len(items),
        correct_count=0,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    return QuizStartResponse(
        session_id=session.id,
        topic_id=unit.id,
        total_questions=len(items),
        questions=[canonical_item_to_quiz_question(item, topic_id=unit.id) for item in items],
    )


async def _answer_canonical_quiz_question(
    db: AsyncSession,
    user_id: uuid.UUID,
    session: Session,
    req: QuizAnswerRequest,
) -> QuizAnswerResponse:
    if session.completed_at is not None:
        raise ConflictError("Quiz đã hoàn thành. Không thể ghi thêm câu trả lời.")

    unit = await _get_learning_unit_or_404(db, session.canonical_unit_id)
    item = await _get_canonical_quiz_item_by_surrogate(db, unit, req.question_id)
    if item is None:
        raise ValidationError("Question does not belong to this canonical quiz unit.")

    existing = await db.execute(
        select(Interaction).where(
            Interaction.session_id == session.id,
            Interaction.canonical_item_id == item.item_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("Câu hỏi này đã được trả lời trong phiên quiz này.")

    is_correct = item.answer_index == selected_answer_to_index(req.selected_answer.value)
    count_result = await db.execute(select(func.count()).where(Interaction.session_id == session.id))
    seq_pos: int = (count_result.scalar() or 0) + 1
    max_global_result = await db.execute(
        select(func.max(Interaction.global_sequence_position)).where(Interaction.user_id == user_id)
    )
    base_global: int = max_global_result.scalar() or 0

    db.add(
        Interaction(
            user_id=user_id,
            session_id=session.id,
            question_id=None,
            canonical_item_id=item.item_id,
            sequence_position=seq_pos,
            global_sequence_position=base_global + 1,
            selected_answer=SelectedAnswer(req.selected_answer.value),
            is_correct=is_correct,
            response_time_ms=req.response_time_ms,
            changed_answer=False,
            hint_used=False,
            explanation_viewed=bool(item.explanation),
            timestamp=datetime.now(UTC),
        )
    )
    await db.flush()

    all_interactions_result = await db.execute(
        select(Interaction.is_correct).where(Interaction.session_id == session.id)
    )
    all_correct_flags = all_interactions_result.scalars().all()
    return QuizAnswerResponse(
        is_correct=is_correct,
        correct_answer=answer_index_to_correct_answer(item.answer_index),
        explanation_text=item.explanation,
        questions_answered=len(all_correct_flags),
        questions_correct=sum(1 for correct in all_correct_flags if correct),
    )


async def _complete_canonical_quiz(
    db: AsyncSession,
    user_id: uuid.UUID,
    session: Session,
) -> QuizCompleteResponse:
    if session.completed_at is not None:
        raise ConflictError("Quiz đã được hoàn thành trước đó.")

    unit = await _get_learning_unit_or_404(db, session.canonical_unit_id)
    rows_result = await db.execute(
        select(Interaction, QuestionBankItem)
        .join(QuestionBankItem, Interaction.canonical_item_id == QuestionBankItem.item_id)
        .where(Interaction.session_id == session.id)
        .order_by(Interaction.sequence_position)
    )
    rows = rows_result.all()
    if not rows:
        raise ValidationError("Không có câu trả lời nào trong phiên quiz. Hãy trả lời ít nhất 1 câu trước khi hoàn thành.")

    total_answered = len(rows)
    correct_count = sum(1 for interaction, _ in rows if interaction.is_correct)
    quiz_score_percent = round(correct_count / total_answered * 100, 1)
    wrong_item_ids = [item.item_id for interaction, item in rows if not interaction.is_correct]

    for interaction, item in rows:
        await update_kp_mastery_from_item(
            db,
            user_id=user_id,
            canonical_item_id=item.item_id,
            is_correct=interaction.is_correct,
        )

    now = datetime.now(UTC)
    session.completed_at = now
    session.total_questions = total_answered
    session.correct_count = correct_count
    session.score_percent = quiz_score_percent
    db.add(session)
    await db.flush()

    weak_kcs = await _canonical_weak_kp_ids(db, wrong_item_ids)
    time_total_ms = sum((interaction.response_time_ms or 0) for interaction, _ in rows)
    time_total_sec = round(time_total_ms / 1000, 1)
    avg_time_sec = round(time_total_sec / total_answered, 1) if total_answered else 0.0

    return QuizCompleteResponse(
        session_id=session.id,
        topic_id=unit.id,
        topic_name=unit.title,
        score=f"{correct_count}/{total_answered}",
        percent=quiz_score_percent,
        mastery_before=0.0,
        mastery_after=quiz_score_percent,
        mastery_level=classify_mastery(quiz_score_percent),
        bloom_breakdown=_canonical_bloom_breakdown(rows),
        weak_kcs=weak_kcs,
        misconceptions=[],
        time_total_seconds=time_total_sec,
        avg_time_per_question=avg_time_sec,
        learning_path_updated=False,
    )


async def _get_canonical_quiz_item_by_surrogate(
    db: AsyncSession,
    unit: LearningUnit,
    question_id: uuid.UUID,
) -> QuestionBankItem | None:
    if not unit.canonical_unit_id:
        return None
    result = await db.execute(
        select(QuestionBankItem).where(QuestionBankItem.unit_id == unit.canonical_unit_id)
    )
    for item in result.scalars().all():
        if canonical_question_uuid(item.item_id) == question_id:
            return item
    return None


async def _canonical_weak_kp_ids(db: AsyncSession, item_ids: list[str]) -> list[str]:
    if not item_ids:
        return []
    result = await db.execute(select(ItemKPMap.kp_id).where(ItemKPMap.item_id.in_(item_ids)))
    return sorted({str(kp_id) for kp_id in result.scalars().all()})


def _canonical_bloom_breakdown(rows) -> dict[str, str]:
    total = len(rows)
    correct = sum(1 for interaction, _ in rows if interaction.is_correct)
    return {"canonical": f"{correct}/{total}"}


async def _get_quiz_session(db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID) -> Session:
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
            Session.session_type == SessionType.quiz,
        )
    )
    sess = result.scalar_one_or_none()
    if sess is None:
        raise NotFoundError("Quiz session not found.")
    return sess


async def _recent_assessment_question_ids(
    db: AsyncSession,
    user_id: uuid.UUID,
    lookback: int,
) -> set[uuid.UUID]:
    """Return question IDs seen in the user's last `lookback` assessment sessions."""
    # Get the most recent N completed assessment session IDs
    sessions_result = await db.execute(
        select(Session.id)
        .where(
            Session.user_id == user_id,
            Session.session_type == SessionType.assessment,
            Session.completed_at.isnot(None),
        )
        .order_by(Session.completed_at.desc())
        .limit(lookback)
    )
    recent_session_ids = [r[0] for r in sessions_result]
    if not recent_session_ids:
        return set()

    qids_result = await db.execute(
        select(Interaction.question_id)
        .where(Interaction.session_id.in_(recent_session_ids))
        .distinct()
    )
    return {r[0] for r in qids_result}


async def _prior_topic_interactions(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic_id: uuid.UUID,
) -> dict[uuid.UUID, bool]:
    """
    For each question in this topic the user has answered,
    return {question_id: True} if they ever got it wrong, else False.
    """
    result = await db.execute(
        select(Interaction.question_id, Interaction.is_correct)
        .join(Question, Interaction.question_id == Question.id)
        .where(
            Interaction.user_id == user_id,
            Question.topic_id == topic_id,
        )
    )
    rows = result.all()

    # Aggregate: ever_wrong = any row where is_correct=False
    per_question: dict[uuid.UUID, bool] = {}  # True = ever wrong
    for qid, is_correct in rows:
        if qid not in per_question:
            per_question[qid] = False
        if not is_correct:
            per_question[qid] = True

    return per_question


async def _get_quiz_questions_for_bucket(
    db: AsyncSession,
    topic_id: uuid.UUID,
    difficulty: DifficultyBucket,
) -> list[Question]:
    """Fetch all active quiz questions for a topic + difficulty, in random order."""
    from src.models.content import QuestionStatus  # local to avoid circular at top

    result = await db.execute(
        select(Question)
        .where(
            Question.topic_id == topic_id,
            Question.status == QuestionStatus.active,
            Question.difficulty_bucket == difficulty,
            text("usage_context::jsonb @> '[\"quiz\"]'::jsonb"),
        )
        .order_by(func.random())
    )
    return result.scalars().all()


def _sample_with_priority(
    tiers: list[list[Question]],
    count: int,
) -> list[Question]:
    """
    Draw `count` questions from prioritised tiers.
    Fill from tier-1 first, then tier-2, then tier-3.
    Never exceed `count` total.
    """
    selected: list[Question] = []
    for tier in tiers:
        if len(selected) >= count:
            break
        needed = count - len(selected)
        # Shuffle within tier for variety (tier order already handles priority)
        pool = list(tier)
        random.shuffle(pool)
        selected.extend(pool[:needed])
    return selected


async def _resolve_kc_names(
    db: AsyncSession,
    kc_id_strs: list[str],
) -> list[str]:
    """Convert KC UUID strings to display names; fall back to raw string."""
    valid_uuids: list[uuid.UUID] = []
    for s in kc_id_strs:
        try:
            valid_uuids.append(uuid.UUID(s))
        except ValueError:
            pass

    if not valid_uuids:
        return kc_id_strs

    result = await db.execute(
        select(KnowledgeComponent).where(KnowledgeComponent.id.in_(valid_uuids))
    )
    name_map: dict[str, str] = {str(kc.id): kc.name for kc in result.scalars().all()}
    return [name_map.get(s, s) for s in kc_id_strs]


async def _maybe_complete_learning_path(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic_id: uuid.UUID,
    mastery_after: float,
) -> bool:
    """
    If mastery ≥ 76 (mastered), mark the corresponding LearningPath item as
    completed.  Returns True if an update was made.
    """
    if mastery_after < 76.0:
        return False

    result = await db.execute(
        select(LearningPath).where(
            LearningPath.user_id == user_id,
            LearningPath.topic_id == topic_id,
            LearningPath.status.notin_([PathStatus.completed, PathStatus.skipped]),
        )
    )
    lp = result.scalar_one_or_none()
    if lp is None:
        return False

    lp.status = PathStatus.completed
    db.add(lp)
    return True
