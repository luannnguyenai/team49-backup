"""
services/quiz_service.py
------------------------
Canonical-only quiz runtime.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.models.canonical import ConceptKP, ItemKPMap, QuestionBankItem
from src.models.content import DifficultyBucket
from src.models.course import LearningProgressStatus, LearningUnit
from src.models.learning import (
    Interaction,
    SelectedAnswer,
    Session,
    SessionType,
)
from src.repositories.canonical_question_repo import CanonicalQuestionRepository
from src.repositories.learner_mastery_kp_repo import LearnerMasteryKPRepository
from src.repositories.learning_progress_repo import LearningProgressRepository
from src.repositories.planner_audit_repo import PlannerAuditRepository
from src.repositories.waived_unit_repo import WaivedUnitRepository
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
from src.services.learning_session_service import CANONICAL_SESSION_ID
from src.services.mastery_evaluator import classify_mastery

log = logging.getLogger(__name__)

_DIFFICULTY_SLOTS: list[tuple[DifficultyBucket, int]] = [
    (DifficultyBucket.easy, 3),
    (DifficultyBucket.medium, 4),
    (DifficultyBucket.hard, 3),
]
_RECENT_ASSESSMENT_LOOKBACK = 2
_SELECTOR_DIFFICULTY_ORDER = {"medium": 0, "easy": 1, "hard": 2}
_INLINE_QUIZ_CHECKPOINTS = {"midpoint", "end"}
_QUIZ_ANSWER_TIMING_LOG_THRESHOLD_MS = 150.0


async def start_quiz(
    db: AsyncSession,
    user_id: uuid.UUID,
    learning_unit_id: uuid.UUID,
    *,
    count: int | None = None,
    source: str = "standalone",
    checkpoint: str | None = None,
    exclude_item_ids: list[str] | None = None,
) -> QuizStartResponse:
    if source == "standalone" and (count is not None or checkpoint is not None or exclude_item_ids):
        raise ValidationError(
            "Standalone quiz does not accept inline-only count/checkpoint/exclude options."
        )
    if source == "standalone":
        return await _start_canonical_quiz(db, user_id, learning_unit_id)
    if source != "inline_video":
        raise ValidationError(f"Unsupported quiz source: {source}")
    if checkpoint is not None and checkpoint not in _INLINE_QUIZ_CHECKPOINTS:
        raise ValidationError(f"Invalid inline quiz checkpoint: {checkpoint}")
    return await _start_canonical_quiz(
        db,
        user_id,
        learning_unit_id,
        count=count,
        source=source,
        checkpoint=checkpoint,
        exclude_item_ids=exclude_item_ids,
    )


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
    *,
    count: int | None = None,
    source: str = "standalone",
    checkpoint: str | None = None,
    exclude_item_ids: list[str] | None = None,
) -> QuizStartResponse:
    unit = await _get_learning_unit_or_404(db, learning_unit_id)
    if source == "inline_video":
        return await _start_inline_video_quiz(
            db,
            user_id=user_id,
            unit=unit,
            count=count or 3,
            checkpoint=checkpoint or "midpoint",
            exclude_item_ids=exclude_item_ids or [],
        )

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
    await _sync_quiz_progress_state(
        db,
        user_id=user_id,
        learning_unit_id=unit.id,
        session_id=session.id,
        item_ids=[item.item_id for item in items],
        answered_item_ids=[],
        current_stage="quiz_in_progress",
    )

    return QuizStartResponse(
        session_id=session.id,
        learning_unit_id=unit.id,
        total_questions=len(items),
        questions=[
            canonical_item_to_quiz_question(item, learning_unit_id=unit.id) for item in items
        ],
    )


async def _start_inline_video_quiz(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    unit: LearningUnit,
    count: int,
    checkpoint: str,
    exclude_item_ids: list[str],
) -> QuizStartResponse:
    planner_repo = PlannerAuditRepository(db)
    state = await planner_repo.get_session_state(user_id, CANONICAL_SESSION_ID)
    current_progress = (
        state.current_progress
        if state is not None and isinstance(state.current_progress, dict)
        else {}
    )
    inline_quiz_state = (
        current_progress.get("inline_quiz")
        if isinstance(current_progress, dict)
        and isinstance(current_progress.get("inline_quiz"), dict)
        else {}
    )
    canonical_unit_ids = await _inline_quiz_canonical_unit_scope(db, unit)
    checkpoint_state = _inline_quiz_checkpoint_state(inline_quiz_state, checkpoint)
    midpoint_state = _inline_quiz_checkpoint_state(inline_quiz_state, "midpoint")

    if (
        checkpoint == "end"
        and isinstance(midpoint_state, dict)
        and midpoint_state.get("active_session_id")
        and current_progress.get("learning_unit_id") == str(unit.id)
    ):
        raise ConflictError(
            "Cannot start end checkpoint while midpoint inline quiz is in progress."
        )

    if (
        isinstance(checkpoint_state, dict)
        and checkpoint_state.get("active_session_id")
        and current_progress.get("learning_unit_id") == str(unit.id)
    ):
        session_id = checkpoint_state.get("active_session_id")
        if session_id:
            session = await _get_existing_inline_quiz_session(
                db, user_id, uuid.UUID(str(session_id))
            )
            if session is not None and session.completed_at is None:
                item_ids = [str(item_id) for item_id in checkpoint_state.get("item_ids") or []]
                items = await _get_quiz_items_by_ids(db, unit, item_ids)
                return QuizStartResponse(
                    session_id=session.id,
                    learning_unit_id=unit.id,
                    total_questions=len(items),
                    questions=[
                        canonical_item_to_quiz_question(item, learning_unit_id=unit.id)
                        for item in items
                    ],
                    source="inline_video",
                    checkpoint=checkpoint,
                )

    selector = CanonicalQuestionSelector(CanonicalQuestionRepository(db))
    items = await _select_quiz_items(
        selector=selector,
        count=count,
        canonical_unit_ids=canonical_unit_ids,
        exclude_item_ids=exclude_item_ids,
    )
    if not items:
        raise ValidationError("Không tìm thấy câu hỏi quiz canonical cho learning unit này.")

    phase = "inline_midpoint_quiz" if checkpoint == "midpoint" else "inline_end_quiz"
    session = Session(
        user_id=user_id,
        session_type=SessionType.quiz,
        topic_id=None,
        module_id=None,
        canonical_unit_id=unit.id,
        canonical_phase=phase,
        total_questions=len(items),
        correct_count=0,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    await _sync_quiz_progress_state(
        db,
        user_id=user_id,
        learning_unit_id=unit.id,
        session_id=session.id,
        item_ids=[item.item_id for item in items],
        answered_item_ids=[],
        current_stage="quiz_in_progress",
        source="inline_video",
        checkpoint=checkpoint,
        quiz_phase=phase,
        excluded_item_ids=exclude_item_ids,
    )

    return QuizStartResponse(
        session_id=session.id,
        learning_unit_id=unit.id,
        total_questions=len(items),
        questions=[
            canonical_item_to_quiz_question(item, learning_unit_id=unit.id) for item in items
        ],
        source="inline_video",
        checkpoint=checkpoint,
    )


async def _answer_canonical_quiz_question(
    db: AsyncSession,
    user_id: uuid.UUID,
    session: Session,
    req: QuizAnswerRequest,
) -> QuizAnswerResponse:
    started_at = perf_counter()
    if session.completed_at is not None:
        raise ConflictError("Quiz đã hoàn thành. Không thể ghi thêm câu trả lời.")

    unit = await _get_learning_unit_or_404(db, session.canonical_unit_id)
    unit_loaded_at = perf_counter()
    existing_progress = await _current_quiz_progress_state(db, user_id)
    item_ids_for_session = _quiz_item_ids_from_progress(existing_progress, session.id)
    item = await _get_canonical_quiz_item_for_session(
        db,
        user_id=user_id,
        session=session,
        unit=unit,
        question_id=req.question_id,
        candidate_item_ids=item_ids_for_session,
    )
    item_loaded_at = perf_counter()
    if item is None:
        raise ValidationError("Question does not belong to this canonical quiz unit.")

    existing = await db.execute(
        select(Interaction).where(
            Interaction.session_id == session.id,
            Interaction.canonical_item_id == item.item_id,
        )
    )
    duplicate_check_at = perf_counter()
    existing_interaction = existing.scalar_one_or_none()
    if existing_interaction is not None:
        all_interactions_result = await db.execute(
            select(Interaction.is_correct).where(Interaction.session_id == session.id)
        )
        all_correct_flags = all_interactions_result.scalars().all()
        tally_loaded_at = perf_counter()
        total_ms = round((tally_loaded_at - started_at) * 1000, 1)
        log.info(
            "quiz_answer_timing session=%s phase=%s duplicate_reused=1 unit_lookup_ms=%.1f "
            "item_lookup_ms=%.1f duplicate_check_ms=%.1f tally_ms=%.1f total_ms=%.1f",
            session.id,
            session.canonical_phase or "mini_quiz",
            (unit_loaded_at - started_at) * 1000,
            (item_loaded_at - unit_loaded_at) * 1000,
            (duplicate_check_at - item_loaded_at) * 1000,
            (tally_loaded_at - duplicate_check_at) * 1000,
            total_ms,
        )
        return _build_quiz_answer_response(
            item=item,
            is_correct=bool(existing_interaction.is_correct),
            all_correct_flags=all_correct_flags,
        )

    is_correct = item.answer_index == selected_answer_to_index(req.selected_answer.value)
    count_result = await db.execute(
        select(func.count()).where(Interaction.session_id == session.id)
    )
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
    interaction_written_at = perf_counter()

    answered_result = await db.execute(
        select(Interaction.canonical_item_id)
        .where(Interaction.session_id == session.id)
        .order_by(Interaction.sequence_position)
    )
    answered_item_ids = [
        str(item_id) for item_id in answered_result.scalars().all() if item_id is not None
    ]
    if not item_ids_for_session:
        item_ids_for_session = await _fallback_quiz_item_ids_for_session(
            db, session=session, unit=unit
        )
    await _sync_quiz_progress_state(
        db,
        user_id=user_id,
        learning_unit_id=unit.id,
        session_id=session.id,
        item_ids=item_ids_for_session,
        answered_item_ids=answered_item_ids,
        current_stage="quiz_in_progress",
        source=_quiz_source_for_session(session),
        checkpoint=_quiz_checkpoint_for_session(session),
        quiz_phase=session.canonical_phase or "mini_quiz",
        existing_progress=existing_progress,
    )
    progress_synced_at = perf_counter()

    all_interactions_result = await db.execute(
        select(Interaction.is_correct).where(Interaction.session_id == session.id)
    )
    all_correct_flags = all_interactions_result.scalars().all()
    tally_loaded_at = perf_counter()
    total_ms = round((tally_loaded_at - started_at) * 1000, 1)
    timing_log = (
        "quiz_answer_timing session=%s phase=%s unit_lookup_ms=%.1f item_lookup_ms=%.1f "
        "duplicate_check_ms=%.1f write_ms=%.1f progress_sync_ms=%.1f tally_ms=%.1f total_ms=%.1f"
    )
    timing_args = (
        session.id,
        session.canonical_phase or "mini_quiz",
        (unit_loaded_at - started_at) * 1000,
        (item_loaded_at - unit_loaded_at) * 1000,
        (duplicate_check_at - item_loaded_at) * 1000,
        (interaction_written_at - duplicate_check_at) * 1000,
        (progress_synced_at - interaction_written_at) * 1000,
        (tally_loaded_at - progress_synced_at) * 1000,
        total_ms,
    )
    if (
        session.canonical_phase in {"inline_midpoint_quiz", "inline_end_quiz"}
        or total_ms >= _QUIZ_ANSWER_TIMING_LOG_THRESHOLD_MS
    ):
        log.info(timing_log, *timing_args)
    else:
        log.debug(timing_log, *timing_args)
    return _build_quiz_answer_response(
        item=item,
        is_correct=is_correct,
        all_correct_flags=all_correct_flags,
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
        raise ValidationError(
            "Không có câu trả lời nào trong phiên quiz. Hãy trả lời ít nhất 1 câu trước khi hoàn thành."
        )

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

    should_complete_learning_unit = _should_complete_learning_unit(session)
    if should_complete_learning_unit:
        await LearningProgressRepository(db).upsert(
            user_id=user_id,
            course_id=unit.course_id,
            learning_unit_id=unit.id,
            status=LearningProgressStatus.completed,
            last_opened_at=now,
            completed_at=now,
        )
        await WaivedUnitRepository(db).delete_for_user_unit(user_id, unit.id)
    await _sync_quiz_progress_state(
        db,
        user_id=user_id,
        learning_unit_id=unit.id,
        session_id=session.id,
        item_ids=item_ids,
        answered_item_ids=item_ids,
        current_stage="post_quiz" if should_complete_learning_unit else "watching",
        source=_quiz_source_for_session(session),
        checkpoint=_quiz_checkpoint_for_session(session),
        quiz_phase=session.canonical_phase or "mini_quiz",
        extra_progress={
            "score_percent": quiz_score_percent,
            "completed_at": now.isoformat(),
        },
    )

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
        learning_path_updated=should_complete_learning_unit,
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


async def _get_canonical_quiz_item_for_session(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    session: Session,
    unit: LearningUnit,
    question_id: uuid.UUID,
    candidate_item_ids: list[str] | None = None,
) -> QuestionBankItem | None:
    normalized_item_ids = [str(item_id) for item_id in (candidate_item_ids or []) if item_id]
    if not normalized_item_ids:
        candidate_item_ids = await _current_quiz_item_ids(
            db,
            user_id=user_id,
            session_id=session.id,
            fallback_unit_canonical_id=unit.canonical_unit_id,
        )
        normalized_item_ids = [str(item_id) for item_id in candidate_item_ids if item_id]
    if normalized_item_ids:
        result = await db.execute(
            select(QuestionBankItem).where(QuestionBankItem.item_id.in_(normalized_item_ids))
        )
        items_by_question_id = {
            canonical_question_uuid(item.item_id): item for item in result.scalars().all()
        }
        resolved = items_by_question_id.get(question_id)
        if resolved is not None:
            return resolved

    if session.canonical_phase in {"inline_midpoint_quiz", "inline_end_quiz"}:
        canonical_unit_ids = await _inline_quiz_canonical_unit_scope(db, unit)
        result = await db.execute(
            select(QuestionBankItem).where(QuestionBankItem.unit_id.in_(canonical_unit_ids))
        )
        items_by_question_id = {
            canonical_question_uuid(item.item_id): item for item in result.scalars().all()
        }
        resolved = items_by_question_id.get(question_id)
        if resolved is not None:
            return resolved

    return await _get_canonical_quiz_item_by_surrogate(db, unit, question_id)


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


def _build_quiz_answer_response(
    *,
    item: QuestionBankItem,
    is_correct: bool,
    all_correct_flags: list[bool],
) -> QuizAnswerResponse:
    return QuizAnswerResponse(
        is_correct=is_correct,
        correct_answer=answer_index_to_correct_answer(item.answer_index),
        explanation_text=item.explanation,
        questions_answered=len(all_correct_flags),
        questions_correct=sum(1 for correct in all_correct_flags if correct),
    )


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


async def _current_quiz_item_ids(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    fallback_unit_canonical_id: str,
) -> list[str]:
    progress = await _current_quiz_progress_state(db, user_id)
    item_ids = _quiz_item_ids_from_progress(progress, session_id)
    if item_ids:
        return item_ids
    unit_item_result = await db.execute(
        select(QuestionBankItem.item_id).where(
            QuestionBankItem.unit_id == fallback_unit_canonical_id
        )
    )
    return [str(item_id) for item_id in unit_item_result.scalars().all()]


async def _current_quiz_progress_state(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> dict:
    repo = PlannerAuditRepository(db)
    get_state = getattr(repo, "get_session_state", None)
    if get_state is None:
        return {}
    state = await get_state(user_id, CANONICAL_SESSION_ID)
    current_progress = getattr(state, "current_progress", None) if state is not None else None
    if isinstance(current_progress, dict):
        return dict(current_progress)
    return {}


def _quiz_item_ids_from_progress(progress: dict | None, session_id: uuid.UUID) -> list[str]:
    if not isinstance(progress, dict):
        return []
    if progress.get("quiz_id") == str(session_id):
        answered = [str(item_id) for item_id in progress.get("items_answered") or []]
        remaining = [str(item_id) for item_id in progress.get("items_remaining") or []]
        return list(dict.fromkeys(answered + remaining))

    inline_quiz = progress.get("inline_quiz")
    if not isinstance(inline_quiz, dict):
        return []
    for checkpoint_state in inline_quiz.values():
        if not isinstance(checkpoint_state, dict):
            continue
        if str(checkpoint_state.get("active_session_id") or "") != str(session_id) and str(
            checkpoint_state.get("completed_session_id") or ""
        ) != str(session_id):
            continue
        answered = [str(item_id) for item_id in checkpoint_state.get("answered_item_ids") or []]
        item_ids = [str(item_id) for item_id in checkpoint_state.get("item_ids") or []]
        return list(dict.fromkeys(answered + item_ids))
    return []


async def _fallback_quiz_item_ids_for_session(
    db: AsyncSession,
    *,
    session: Session,
    unit: LearningUnit,
) -> list[str]:
    if session.canonical_phase in {"inline_midpoint_quiz", "inline_end_quiz"}:
        canonical_unit_ids = await _inline_quiz_canonical_unit_scope(db, unit)
        result = await db.execute(
            select(QuestionBankItem.item_id).where(QuestionBankItem.unit_id.in_(canonical_unit_ids))
        )
        return [str(item_id) for item_id in result.scalars().all() if item_id]

    result = await db.execute(
        select(QuestionBankItem.item_id).where(QuestionBankItem.unit_id == unit.canonical_unit_id)
    )
    return [str(item_id) for item_id in result.scalars().all() if item_id]


async def _sync_quiz_progress_state(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    learning_unit_id: uuid.UUID,
    session_id: uuid.UUID,
    item_ids: list[str],
    answered_item_ids: list[str],
    current_stage: str,
    source: str = "standalone",
    checkpoint: str | None = None,
    quiz_phase: str = "mini_quiz",
    excluded_item_ids: list[str] | None = None,
    extra_progress: dict | None = None,
    existing_progress: dict | None = None,
) -> None:
    answered = list(dict.fromkeys(answered_item_ids))
    normalized_item_ids = [str(item_id) for item_id in item_ids]
    answered_set = set(answered)
    remaining = [item_id for item_id in normalized_item_ids if item_id not in answered_set]
    planner_repo = PlannerAuditRepository(db)
    existing_progress = (
        dict(existing_progress)
        if isinstance(existing_progress, dict)
        else dict(await _current_quiz_progress_state(db, user_id))
    )
    progress = {
        **existing_progress,
        "learning_unit_id": str(learning_unit_id),
        "quiz_id": str(session_id),
        "quiz_phase": quiz_phase,
        "items_answered": answered,
        "items_remaining": remaining,
    }
    if source == "inline_video":
        inline_quiz = (
            dict(existing_progress.get("inline_quiz"))
            if isinstance(existing_progress.get("inline_quiz"), dict)
            else {}
        )
        existing_checkpoint_state = _inline_quiz_checkpoint_state(inline_quiz, checkpoint)
        inline_quiz[checkpoint] = {
            **(existing_checkpoint_state if isinstance(existing_checkpoint_state, dict) else {}),
            "shown": True,
            "active_session_id": None if current_stage == "post_quiz" else str(session_id),
            "completed_session_id": str(session_id) if current_stage == "post_quiz" else None,
            "excluded_item_ids": list(excluded_item_ids)
            if excluded_item_ids is not None
            else (
                list(existing_checkpoint_state.get("excluded_item_ids") or [])
                if isinstance(existing_checkpoint_state, dict)
                else []
            ),
            "item_ids": normalized_item_ids,
            "answered_item_ids": answered,
            "quiz_phase": quiz_phase,
        }
        progress["inline_quiz"] = inline_quiz
    if extra_progress:
        progress.update(extra_progress)
        if (
            source == "inline_video"
            and checkpoint
            and isinstance(progress.get("inline_quiz"), dict)
            and isinstance(progress["inline_quiz"].get(checkpoint), dict)
        ):
            progress["inline_quiz"][checkpoint].update(extra_progress)

    await planner_repo.upsert_session_state(
        user_id=user_id,
        session_id=CANONICAL_SESSION_ID,
        current_unit_id=learning_unit_id,
        current_stage=current_stage,
        current_progress=progress,
        last_activity=datetime.now(UTC),
        state_json={"canonical_runtime": True, "source": "quiz_progress"},
    )


async def _select_quiz_items(
    *,
    selector: CanonicalQuestionSelector,
    count: int,
    canonical_unit_ids: list[str],
    exclude_item_ids: list[str],
) -> list[QuestionBankItem]:
    exclude_set = {str(item_id) for item_id in exclude_item_ids}
    selected = await selector.select_for_phase(
        phase="mini_quiz",
        canonical_unit_ids=canonical_unit_ids,
        count=count,
    )
    filtered = [item for item in selected if str(item.item_id) not in exclude_set]
    if len(filtered) >= count or not exclude_set:
        return filtered[:count]

    remaining_candidates = await selector.repo.get_items_for_phase(
        phase="mini_quiz",
        canonical_unit_ids=canonical_unit_ids,
        limit=max(count * 4, count + len(exclude_set) * 4),
    )
    ranked_remaining = sorted(
        remaining_candidates,
        key=lambda item: (
            _SELECTOR_DIFFICULTY_ORDER.get(str(getattr(item, "difficulty", "medium")), 1),
            str(getattr(item, "item_id", "")),
        ),
    )
    chosen_ids = {str(item.item_id) for item in filtered}
    for item in ranked_remaining:
        item_id = str(item.item_id)
        if item_id in exclude_set or item_id in chosen_ids:
            continue
        filtered.append(item)
        chosen_ids.add(item_id)
        if len(filtered) >= count:
            break
    return filtered[:count]


async def _inline_quiz_canonical_unit_scope(
    db: AsyncSession,
    unit: LearningUnit,
) -> list[str]:
    section_id = getattr(unit, "section_id", None)
    if not section_id:
        return [unit.canonical_unit_id]

    result = await db.execute(
        select(LearningUnit.canonical_unit_id)
        .where(
            LearningUnit.section_id == section_id,
            LearningUnit.canonical_unit_id.isnot(None),
        )
        .order_by(LearningUnit.sort_order, LearningUnit.slug)
    )
    canonical_unit_ids = [str(unit_id) for unit_id in result.scalars().all() if unit_id]
    return canonical_unit_ids or [unit.canonical_unit_id]


def _inline_quiz_checkpoint_state(inline_quiz: dict | None, checkpoint: str | None) -> dict | None:
    if checkpoint is None or not isinstance(inline_quiz, dict):
        return None
    checkpoint_state = inline_quiz.get(checkpoint)
    return checkpoint_state if isinstance(checkpoint_state, dict) else None


async def _get_existing_inline_quiz_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> Session | None:
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
            Session.session_type == SessionType.quiz,
        )
    )
    return result.scalar_one_or_none()


async def _get_quiz_items_by_ids(
    db: AsyncSession,
    unit: LearningUnit,
    item_ids: list[str],
) -> list[QuestionBankItem]:
    if not item_ids:
        return []
    result = await db.execute(
        select(QuestionBankItem).where(
            QuestionBankItem.unit_id == unit.canonical_unit_id,
            QuestionBankItem.item_id.in_(item_ids),
        )
    )
    items_by_id = {str(item.item_id): item for item in result.scalars().all()}
    return [items_by_id[item_id] for item_id in item_ids if item_id in items_by_id]


def _quiz_source_for_session(session: Session) -> str:
    if session.canonical_phase in {"inline_midpoint_quiz", "inline_end_quiz"}:
        return "inline_video"
    return "standalone"


def _quiz_checkpoint_for_session(session: Session) -> str | None:
    if session.canonical_phase == "inline_midpoint_quiz":
        return "midpoint"
    if session.canonical_phase == "inline_end_quiz":
        return "end"
    return None


def _should_complete_learning_unit(session: Session) -> bool:
    """A lesson completes after standalone quiz completion or the final inline quiz.

    Video watch progress is resume/analytics state only and must not gate completion.
    """
    checkpoint = _quiz_checkpoint_for_session(session)
    if checkpoint is None:
        return True
    return checkpoint == "end"
