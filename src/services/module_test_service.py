"""
services/module_test_service.py
--------------------------------
Canonical-only module-test runtime.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.models.canonical import ConceptKP, ItemKPMap, QuestionBankItem
from src.models.content import DifficultyBucket
from src.models.course import CourseSection, LearningUnit
from src.models.learning import Interaction, SelectedAnswer, Session, SessionType
from src.repositories.canonical_question_repo import CanonicalQuestionRepository
from src.schemas.module_test import (
    ModuleTestResultResponse,
    ModuleTestStartResponse,
    ModuleTestSubmitRequest,
    NextSectionInfo,
    LearningUnitQuestionsGroup,
    LearningUnitTestResult,
    ReviewLearningUnitSuggestion,
    WrongAnswerDetail,
)
from src.services.canonical_assessor_compat import (
    answer_index_to_correct_answer,
    canonical_item_to_module_test_question,
    canonical_question_uuid,
    selected_answer_to_index,
)
from src.services.canonical_mastery_service import update_kp_mastery_from_item
from src.services.canonical_question_selector import CanonicalQuestionSelector


_MODULE_TEST_SLOTS: list[tuple[DifficultyBucket, int]] = [
    (DifficultyBucket.easy, 2),
    (DifficultyBucket.medium, 1),
    (DifficultyBucket.hard, 2),
]

PASS_THRESHOLD: float = 70.0
WEAK_THRESHOLD: float = 60.0


async def start_module_test(
    db: AsyncSession,
    user_id: uuid.UUID,
    section_id: uuid.UUID,
) -> ModuleTestStartResponse:
    return await _start_canonical_module_test(db, user_id, section_id)


async def submit_module_test(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    req: ModuleTestSubmitRequest,
) -> ModuleTestResultResponse:
    session = await _get_module_test_session(db, user_id, session_id)
    if session.canonical_section_id is None:
        raise ValidationError("Legacy module-test sessions are no longer supported.")
    return await _submit_canonical_module_test(db, user_id, session, req)


async def get_module_test_results(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> ModuleTestResultResponse:
    session = await _get_module_test_session(db, user_id, session_id)
    if session.canonical_section_id is None:
        raise ValidationError("Legacy module-test sessions are no longer supported.")
    if session.completed_at is None:
        raise ConflictError("Module test chưa được nộp.")
    return await _build_canonical_module_test_result(db, user_id, session, mutate=False)


async def _start_canonical_module_test(
    db: AsyncSession,
    user_id: uuid.UUID,
    section_id: uuid.UUID,
) -> ModuleTestStartResponse:
    section = await _get_canonical_section_or_404(db, section_id)
    units = await _get_canonical_units_for_section(db, section.id)
    if not units:
        raise ValidationError(f"Module '{section.title}' không có canonical learning unit nào.")

    incomplete = await _canonical_units_without_completed_quiz(db, user_id, units)
    if incomplete:
        raise ValidationError(
            "Bạn chưa hoàn thành quiz cho các learning unit sau: "
            + ", ".join(f"'{unit.title}'" for unit in incomplete)
            + ". Hãy hoàn thành quiz tất cả units trước khi thi module test."
        )

    selector = CanonicalQuestionSelector(CanonicalQuestionRepository(db))
    learning_unit_groups: list[LearningUnitQuestionsGroup] = []
    total_question_count = 0
    for unit in units:
        if not unit.canonical_unit_id:
            continue
        items = await selector.select_for_phase(
            phase="final_quiz",
            canonical_unit_ids=[unit.canonical_unit_id],
            count=5,
        )
        if not items:
            raise ValidationError(f"Không tìm thấy câu hỏi final_quiz cho learning unit '{unit.title}'.")
        total_question_count += len(items)
        learning_unit_groups.append(
            LearningUnitQuestionsGroup(
                learning_unit_id=unit.id,
                learning_unit_title=unit.title,
                questions=[
                    canonical_item_to_module_test_question(item, learning_unit_id=unit.id)
                    for item in items
                ],
            )
        )

    session = Session(
        user_id=user_id,
        session_type=SessionType.module_test,
        topic_id=None,
        module_id=None,
        canonical_section_id=section.id,
        canonical_phase="final_quiz",
        total_questions=total_question_count,
        correct_count=0,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    return ModuleTestStartResponse(
        session_id=session.id,
        section_id=section.id,
        section_title=section.title,
        total_learning_units=len(learning_unit_groups),
        total_questions=total_question_count,
        learning_units=learning_unit_groups,
    )


async def _submit_canonical_module_test(
    db: AsyncSession,
    user_id: uuid.UUID,
    session: Session,
    req: ModuleTestSubmitRequest,
) -> ModuleTestResultResponse:
    if session.completed_at is not None:
        raise ConflictError("Module test đã được nộp trước đó.")
    if not settings.write_canonical_interactions_enabled:
        raise ValidationError("Canonical module-test submit is not enabled.")

    section = await _get_canonical_section_or_404(db, session.canonical_section_id)
    units = await _get_canonical_units_for_section(db, section.id)
    item_by_question_id = await _canonical_item_lookup_for_units(db, units)
    max_global_result = await db.execute(
        select(func.max(Interaction.global_sequence_position)).where(Interaction.user_id == user_id)
    )
    global_base: int = max_global_result.scalar() or 0

    seen: set[str] = set()
    timestamp = datetime.now(UTC)
    for index, answer in enumerate(req.answers, start=1):
        item = item_by_question_id.get(answer.question_id)
        if item is None:
            raise ValidationError("Question does not belong to this canonical module test.")
        if item.item_id in seen:
            raise ConflictError("Duplicate question in module-test submission.")
        seen.add(item.item_id)
        is_correct = item.answer_index == selected_answer_to_index(answer.selected_answer.value)
        db.add(
            Interaction(
                user_id=user_id,
                session_id=session.id,
                question_id=None,
                canonical_item_id=item.item_id,
                sequence_position=index,
                global_sequence_position=global_base + index,
                selected_answer=SelectedAnswer(answer.selected_answer.value),
                is_correct=is_correct,
                response_time_ms=answer.response_time_ms,
                changed_answer=False,
                hint_used=False,
                explanation_viewed=bool(item.explanation),
                timestamp=timestamp,
            )
        )

    await db.flush()
    return await _build_canonical_module_test_result(db, user_id, session, mutate=True)


async def _build_canonical_module_test_result(
    db: AsyncSession,
    user_id: uuid.UUID,
    session: Session,
    *,
    mutate: bool,
) -> ModuleTestResultResponse:
    section = await _get_canonical_section_or_404(db, session.canonical_section_id)
    units = await _get_canonical_units_for_section(db, section.id)
    unit_by_canonical_id = {unit.canonical_unit_id: unit for unit in units if unit.canonical_unit_id}
    rows_result = await db.execute(
        select(Interaction, QuestionBankItem)
        .join(QuestionBankItem, Interaction.canonical_item_id == QuestionBankItem.item_id)
        .where(Interaction.session_id == session.id)
        .order_by(Interaction.sequence_position)
    )
    rows = rows_result.all()
    if not rows:
        raise ValidationError("Module test submission không có câu trả lời nào.")

    per_unit_rows: dict[uuid.UUID, list[tuple[Interaction, QuestionBankItem]]] = {}
    for interaction, item in rows:
        unit = unit_by_canonical_id.get(item.unit_id)
        if unit is not None:
            per_unit_rows.setdefault(unit.id, []).append((interaction, item))

    total = len(rows)
    correct = sum(1 for interaction, _ in rows if interaction.is_correct)
    total_score_pct = round(correct / total * 100, 1) if total else 0.0
    passed = total_score_pct >= PASS_THRESHOLD
    per_learning_unit: list[LearningUnitTestResult] = []
    review_suggestions: list[ReviewLearningUnitSuggestion] = []
    wrong_answers: list[WrongAnswerDetail] = []

    for unit in units:
        unit_rows = per_unit_rows.get(unit.id, [])
        if not unit_rows:
            continue
        unit_total = len(unit_rows)
        unit_correct = sum(1 for interaction, _ in unit_rows if interaction.is_correct)
        unit_pct = round(unit_correct / unit_total * 100, 1)
        wrong_item_ids = [item.item_id for interaction, item in unit_rows if not interaction.is_correct]
        weak_kcs = await _canonical_kp_names(db, wrong_item_ids)
        per_learning_unit.append(
            LearningUnitTestResult(
                learning_unit_id=unit.id,
                learning_unit_title=unit.title,
                score=f"{unit_correct}/{unit_total}",
                score_percent=unit_pct,
                bloom_max=None,
                verdict="pass" if unit_pct >= WEAK_THRESHOLD else "fail",
                weak_kcs=weak_kcs,
            )
        )
        if unit_pct < WEAK_THRESHOLD:
            review_suggestions.append(
                ReviewLearningUnitSuggestion(
                    learning_unit_id=unit.id,
                    learning_unit_title=unit.title,
                    weak_kcs=weak_kcs,
                    misconceptions=[],
                    estimated_review_hours=_unit_review_hours(unit),
                )
            )
        for interaction, item in unit_rows:
            if interaction.is_correct or interaction.selected_answer is None:
                continue
            question = canonical_item_to_module_test_question(
                item, learning_unit_id=unit.id
            )
            wrong_answers.append(
                WrongAnswerDetail(
                    question_id=question.id,
                    learning_unit_id=unit.id,
                    learning_unit_title=unit.title,
                    stem_text=question.stem_text,
                    option_a=question.option_a,
                    option_b=question.option_b,
                    option_c=question.option_c,
                    option_d=question.option_d,
                    selected_answer=interaction.selected_answer,
                    correct_answer=answer_index_to_correct_answer(item.answer_index).value,
                    explanation_text=item.explanation,
                )
            )

    next_module = await _next_section_info(db, section) if passed else None

    if mutate:
        now = datetime.now(UTC)
        for interaction, item in rows:
            await update_kp_mastery_from_item(
                db,
                user_id=user_id,
                canonical_item_id=item.item_id,
                is_correct=interaction.is_correct,
            )
        session.completed_at = now
        session.total_questions = total
        session.correct_count = correct
        session.score_percent = total_score_pct
        db.add(session)
        await db.flush()

    return ModuleTestResultResponse(
        session_id=session.id,
        section_id=section.id,
        section_title=section.title,
        total_score_percent=total_score_pct,
        passed=passed,
        per_learning_unit=per_learning_unit,
        recommended_review_units=review_suggestions if not passed else [],
        estimated_review_hours=sum(item.estimated_review_hours for item in review_suggestions)
        if not passed
        else 0.0,
        next_section=next_module,
        wrong_answers=wrong_answers,
    )


async def _get_canonical_section_or_404(db: AsyncSession, section_id: uuid.UUID) -> CourseSection:
    result = await db.execute(select(CourseSection).where(CourseSection.id == section_id))
    section = result.scalar_one_or_none()
    if section is None:
        raise NotFoundError(f"Canonical course section {section_id} not found.")
    return section


async def _get_canonical_units_for_section(
    db: AsyncSession,
    section_id: uuid.UUID,
) -> list[LearningUnit]:
    result = await db.execute(
        select(LearningUnit)
        .where(
            LearningUnit.section_id == section_id,
            LearningUnit.canonical_unit_id.isnot(None),
        )
        .order_by(LearningUnit.sort_order)
    )
    return list(result.scalars().all())


async def _canonical_units_without_completed_quiz(
    db: AsyncSession,
    user_id: uuid.UUID,
    units: list[LearningUnit],
) -> list[LearningUnit]:
    missing: list[LearningUnit] = []
    for unit in units:
        result = await db.execute(
            select(Session.id)
            .where(
                Session.user_id == user_id,
                Session.session_type == SessionType.quiz,
                Session.canonical_unit_id == unit.id,
                Session.completed_at.isnot(None),
            )
            .limit(1)
        )
        if result.scalar_one_or_none() is None:
            missing.append(unit)
    return missing


async def _canonical_item_lookup_for_units(
    db: AsyncSession,
    units: list[LearningUnit],
) -> dict[uuid.UUID, QuestionBankItem]:
    canonical_unit_ids = [unit.canonical_unit_id for unit in units if unit.canonical_unit_id]
    if not canonical_unit_ids:
        return {}
    result = await db.execute(
        select(QuestionBankItem).where(QuestionBankItem.unit_id.in_(canonical_unit_ids))
    )
    return {canonical_question_uuid(item.item_id): item for item in result.scalars().all()}


async def _canonical_kp_names(db: AsyncSession, item_ids: list[str]) -> list[str]:
    if not item_ids:
        return []
    result = await db.execute(
        select(ConceptKP.name)
        .join(ItemKPMap, ItemKPMap.kp_id == ConceptKP.kp_id)
        .where(ItemKPMap.item_id.in_(item_ids))
    )
    return sorted({str(name) for name in result.scalars().all() if name})


def _unit_review_hours(unit: LearningUnit) -> float:
    if unit.estimated_minutes is None:
        return 1.0
    return max(0.25, round(unit.estimated_minutes / 60, 2))


async def _next_section_info(
    db: AsyncSession,
    section: CourseSection,
) -> NextSectionInfo | None:
    result = await db.execute(
        select(CourseSection)
        .where(
            CourseSection.course_id == section.course_id,
            CourseSection.sort_order > section.sort_order,
        )
        .order_by(CourseSection.sort_order)
        .limit(1)
    )
    next_section = result.scalar_one_or_none()
    if next_section is None:
        return None
    return NextSectionInfo(
        section_id=next_section.id,
        section_title=next_section.title,
    )


async def _get_module_test_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> Session:
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
            Session.session_type == SessionType.module_test,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise NotFoundError("Module test session not found.")
    return session
