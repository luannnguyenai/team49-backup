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

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.content import (
    BloomLevel,
    KnowledgeComponent,
    Question,
    QuestionStatus,
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
from src.services.mastery_evaluator import (
    QuestionResult,
    TopicMasteryResult,
    evaluate_topic,
)

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
    # 1. Validate all requested topics exist
    topics_result = await db.execute(select(Topic).where(Topic.id.in_(topic_ids)))
    found_ids = {t.id for t in topics_result.scalars().all()}
    missing = [tid for tid in topic_ids if tid not in found_ids]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topics not found: {[str(m) for m in missing]}",
        )

    # 2. Collect question_ids the user has already answered (dedup across sessions)
    answered_result = await db.execute(
        select(Interaction.question_id).where(Interaction.user_id == user_id).distinct()
    )
    excluded_ids: set[uuid.UUID] = {row[0] for row in answered_result}

    # 3. Select questions for each topic
    all_questions: list[Question] = []
    for topic_id in topic_ids:
        topic_qs = await _select_questions_for_topic(db, topic_id, excluded_ids)
        all_questions.extend(topic_qs)

    if not all_questions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No eligible assessment questions found for the requested topics.",
        )

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
    topic_id: uuid.UUID,
    excluded_ids: set[uuid.UUID],
) -> list[Question]:
    """
    Select up to 5 questions for a single topic following the bloom distribution.
    Questions already in `excluded_ids` (previously answered) are skipped.
    If a bloom slot has fewer questions than requested, we take what's available.
    """
    selected: list[Question] = []

    for bloom_levels, count in _BLOOM_SLOTS:
        # Grow exclusion set as we pick within this topic (avoid intra-topic dupes)
        exclusion = excluded_ids | {q.id for q in selected}

        stmt = (
            select(Question)
            .where(
                Question.topic_id == topic_id,
                Question.status == QuestionStatus.active,
                # JSONB containment: usage_context must include "assessment"
                text("usage_context::jsonb @> '[\"assessment\"]'::jsonb"),
                Question.bloom_level.in_(bloom_levels),
            )
            .order_by(func.random())
            .limit(count)
        )
        if exclusion:
            stmt = stmt.where(Question.id.not_in(list(exclusion)))

        result = await db.execute(stmt)
        selected.extend(result.scalars().all())

    return selected


# ===========================================================================
# POST /api/assessment/{session_id}/submit
# ===========================================================================


async def submit_assessment(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    answers: list[AnswerInput],
) -> AssessmentResultResponse:
    # 1. Load + validate session ownership
    session = await _get_session(db, user_id, session_id)
    if session.completed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This assessment has already been submitted.",
        )

    # 2. Reject duplicate question_ids in the submission
    question_ids = [a.question_id for a in answers]
    if len(question_ids) != len(set(question_ids)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Duplicate question_id entries in answers.",
        )

    # 3. Batch-load all referenced questions
    questions_result = await db.execute(select(Question).where(Question.id.in_(question_ids)))
    questions: dict[uuid.UUID, Question] = {q.id: q for q in questions_result.scalars().all()}
    missing = [qid for qid in question_ids if qid not in questions]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown question IDs: {[str(m) for m in missing]}",
        )

    # 4. Determine next global_sequence_position for this user
    max_global_result = await db.execute(
        select(func.max(Interaction.global_sequence_position)).where(Interaction.user_id == user_id)
    )
    base_global: int = max_global_result.scalar() or 0

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

    # 7. Evaluate mastery per topic
    grouped: dict[uuid.UUID, list[QuestionResult]] = {}
    for qr in question_results:
        grouped.setdefault(qr.topic_id, []).append(qr)

    topic_results_map: dict[uuid.UUID, TopicMasteryResult] = {
        topic_id: evaluate_topic(qrs) for topic_id, qrs in grouped.items()
    }

    # 8. Upsert topic-grain MasteryScore records
    await _upsert_mastery_scores(db, user_id, topic_results_map, now)
    await db.flush()

    return await _build_result_response(db, session_id, topic_results_map, now)


# ===========================================================================
# GET /api/assessment/{session_id}/results
# ===========================================================================


async def get_assessment_results(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> AssessmentResultResponse:
    session = await _get_session(db, user_id, session_id)
    if session.completed_at is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not yet submitted.",
        )

    # Load all interactions joined with their questions
    rows_result = await db.execute(
        select(Interaction, Question)
        .join(Question, Interaction.question_id == Question.id)
        .where(Interaction.session_id == session_id)
        .order_by(Interaction.sequence_position)
    )
    rows = rows_result.all()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No interaction data found for this session.",
        )

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
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
            Session.session_type == SessionType.assessment,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment session not found.",
        )
    return session


async def _upsert_mastery_scores(
    db: AsyncSession,
    user_id: uuid.UUID,
    results: dict[uuid.UUID, TopicMasteryResult],
    now: datetime,
) -> None:
    """Insert or update topic-grain MasteryScore for every evaluated topic."""
    for topic_id, r in results.items():
        existing_result = await db.execute(
            select(MasteryScore).where(
                MasteryScore.user_id == user_id,
                MasteryScore.topic_id == topic_id,
                MasteryScore.kc_id.is_(None),  # topic-grain (not KC-grain)
            )
        )
        score = existing_result.scalar_one_or_none()

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
) -> AssessmentResultResponse:
    """Construct the API response, resolving topic names and KC names."""

    topic_ids = list(topic_results_map.keys())

    # Batch-fetch topic names
    topics_result = await db.execute(select(Topic).where(Topic.id.in_(topic_ids)))
    topics: dict[uuid.UUID, Topic] = {t.id: t for t in topics_result.scalars().all()}

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
        kcs_result = await db.execute(
            select(KnowledgeComponent).where(KnowledgeComponent.id.in_(all_weak_kc_uuids))
        )
        kc_name_by_id = {str(kc.id): kc.name for kc in kcs_result.scalars().all()}

    # Compute overall weighted score across all topics
    total_earned = sum(r.earned_points for r in topic_results_map.values())
    total_max = sum(r.max_points for r in topic_results_map.values())
    overall_score = round(total_earned / total_max * 100, 1) if total_max > 0 else 0.0

    # Build per-topic result list
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
                # Resolve UUID → KC name; fall back to raw string if not found
                weak_kcs=[kc_name_by_id.get(kc_id, kc_id) for kc_id in r.weak_kc_ids],
                misconceptions_detected=r.misconceptions_detected,
            )
        )

    return AssessmentResultResponse(
        session_id=session_id,
        completed_at=completed_at,
        overall_score_percent=overall_score,
        topic_results=topic_results,
    )
