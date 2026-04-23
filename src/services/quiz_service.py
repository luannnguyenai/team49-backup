"""
services/quiz_service.py
------------------------
Canonical-only quiz runtime.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.models.canonical import ConceptKP, ItemKPMap, QuestionBankItem
from src.models.content import DifficultyBucket
from src.models.course import LearningUnit
from src.models.learning import (
    Interaction,
    SelectedAnswer,
    Session,
    SessionType,
)
from src.repositories.canonical_question_repo import CanonicalQuestionRepository
from src.repositories.learner_mastery_kp_repo import LearnerMasteryKPRepository
from src.schemas.quiz import (
    QuizAnswerRequest,
    QuizAnswerResponse,
    QuizCompleteResponse,
    QuizHistoryResponse,
    QuizHistorySummary,
    QuizStartResponse,
)
from src.services.canonical_assessor_compat import (
    answer_index_to_correct_answer,
    canonical_item_to_quiz_question,
    canonical_question_uuid,
    selected_answer_to_index,
)
from src.services.canonical_mastery_service import update_kp_mastery_from_item
from src.services.canonical_question_selector import CanonicalQuestionSelector
from src.services.mastery_evaluator import classify_mastery


_DIFFICULTY_SLOTS: list[tuple[DifficultyBucket, int]] = [
    (DifficultyBucket.easy, 3),
    (DifficultyBucket.medium, 4),
    (DifficultyBucket.hard, 3),
]
_RECENT_ASSESSMENT_LOOKBACK = 2


async def start_quiz(
    db: AsyncSession,
    user_id: uuid.UUID,
    learning_unit_id: uuid.UUID,
) -> QuizStartResponse:
    return await _start_canonical_quiz(db, user_id, learning_unit_id)


async def answer_question(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    req: QuizAnswerRequest,
) -> QuizAnswerResponse:
    session = await _get_quiz_session(db, user_id, session_id)
    if session.canonical_unit_id is None:
        raise ValidationError("Legacy quiz sessions are no longer supported.")
    return await _answer_canonical_quiz_question(db, user_id, session, req)


async def complete_quiz(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> QuizCompleteResponse:
    session = await _get_quiz_session(db, user_id, session_id)
    if session.canonical_unit_id is None:
        raise ValidationError("Legacy quiz sessions are no longer supported.")
    return await _complete_canonical_quiz(db, user_id, session)


async def get_quiz_history(
    db: AsyncSession,
    user_id: uuid.UUID,
    learning_unit_id: uuid.UUID | None = None,
) -> QuizHistoryResponse:
    stmt = (
        select(Session, LearningUnit.title)
        .outerjoin(LearningUnit, Session.canonical_unit_id == LearningUnit.id)
        .where(
            Session.user_id == user_id,
            Session.session_type == SessionType.quiz,
            Session.canonical_unit_id.isnot(None),
        )
        .order_by(Session.started_at.desc())
    )
    if learning_unit_id is not None:
        stmt = stmt.where(Session.canonical_unit_id == learning_unit_id)

    result = await db.execute(stmt)
    rows = result.all()
    items = [
        QuizHistorySummary(
            session_id=session.id,
            learning_unit_id=session.canonical_unit_id,
            learning_unit_title=unit_title or str(session.canonical_unit_id),
            score_percent=session.score_percent,
            correct_count=session.correct_count,
            total_questions=session.total_questions,
            completed_at=session.completed_at,
            started_at=session.started_at,
        )
        for session, unit_title in rows
        if session.canonical_unit_id is not None
    ]
    return QuizHistoryResponse(total=len(items), items=items)


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
        learning_unit_id=unit.id,
        total_questions=len(items),
        questions=[
            canonical_item_to_quiz_question(item, learning_unit_id=unit.id) for item in items
        ],
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

    item_ids = [item.item_id for _, item in rows]
    mastery_before = await _canonical_mastery_percent_for_items(db, user_id, item_ids)
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

    mastery_after = await _canonical_mastery_percent_for_items(db, user_id, item_ids)
    now = datetime.now(UTC)
    session.completed_at = now
    session.total_questions = total_answered
    session.correct_count = correct_count
    session.score_percent = quiz_score_percent
    db.add(session)
    await db.flush()

    weak_kcs = await _canonical_kp_names(db, wrong_item_ids)
    time_total_ms = sum((interaction.response_time_ms or 0) for interaction, _ in rows)
    time_total_sec = round(time_total_ms / 1000, 1)
    avg_time_sec = round(time_total_sec / total_answered, 1) if total_answered else 0.0

    return QuizCompleteResponse(
        session_id=session.id,
        learning_unit_id=unit.id,
        learning_unit_title=unit.title,
        score=f"{correct_count}/{total_answered}",
        percent=quiz_score_percent,
        mastery_before=mastery_before,
        mastery_after=mastery_after,
        mastery_level=classify_mastery(mastery_after),
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
    result = await db.execute(
        select(QuestionBankItem).where(QuestionBankItem.unit_id == unit.canonical_unit_id)
    )
    for item in result.scalars().all():
        if canonical_question_uuid(item.item_id) == question_id:
            return item
    return None


async def _canonical_kp_names(db: AsyncSession, item_ids: list[str]) -> list[str]:
    if not item_ids:
        return []
    result = await db.execute(
        select(ConceptKP.name)
        .join(ItemKPMap, ItemKPMap.kp_id == ConceptKP.kp_id)
        .where(ItemKPMap.item_id.in_(item_ids))
    )
    return sorted({str(name) for name in result.scalars().all() if name})


async def _canonical_mastery_percent_for_items(
    db: AsyncSession,
    user_id: uuid.UUID,
    item_ids: list[str],
) -> float:
    if not item_ids:
        return 0.0
    result = await db.execute(select(ItemKPMap.kp_id).where(ItemKPMap.item_id.in_(item_ids)))
    kp_ids = sorted({str(kp_id) for kp_id in result.scalars().all()})
    if not kp_ids:
        return 0.0
    mastery_by_kp = await LearnerMasteryKPRepository(db).bulk_get_for_user(user_id, kp_ids)
    values = [row.mastery_mean_cached for row in mastery_by_kp.values()]
    if not values:
        return 0.0
    return round(sum(values) / len(values) * 100, 1)


def _canonical_bloom_breakdown(rows: list[tuple[Interaction, QuestionBankItem]]) -> dict[str, str]:
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
