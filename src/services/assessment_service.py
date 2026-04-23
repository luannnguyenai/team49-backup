"""
services/assessment_service.py
--------------------------------
Canonical-only assessment runtime.

The API surface still accepts the old payload shape, but execution now reads
only from canonical units/question_bank/item_kp_map and writes only canonical
interactions plus learner_mastery_kp updates.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.models.canonical import ConceptKP, ItemKPMap, QuestionBankItem
from src.models.content import DifficultyBucket
from src.models.course import LearningUnit
from src.models.learning import Interaction, SelectedAnswer, Session, SessionType
from src.schemas.assessment import (
    AnswerInput,
    AssessmentResultResponse,
    AssessmentStartResponse,
    QuestionForAssessment,
    TopicResult,
)
from src.services.canonical_mastery_service import update_kp_mastery_from_item
from src.services.canonical_question_selector import CanonicalQuestionSelector
from src.repositories.canonical_question_repo import CanonicalQuestionRepository
from src.services.mastery_evaluator import classify_mastery


def _selected_answer_to_index(answer: SelectedAnswer) -> int:
    return {"A": 0, "B": 1, "C": 2, "D": 3}[answer.value]


def _canonical_item_to_assessment_question(item: QuestionBankItem) -> QuestionForAssessment:
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


async def start_assessment(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic_ids: list[uuid.UUID],
    canonical_unit_ids: list[str] | None = None,
    phase: str = "placement",
) -> AssessmentStartResponse:
    selected_unit_ids = await _resolve_canonical_unit_ids(
        db,
        topic_ids=topic_ids,
        canonical_unit_ids=canonical_unit_ids,
    )
    items = await _select_canonical_questions_for_units(
        db=db,
        canonical_unit_ids=selected_unit_ids,
        phase=phase,
        count=5,
    )
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
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    return AssessmentStartResponse(
        session_id=session.id,
        total_questions=len(items),
        questions=[_canonical_item_to_assessment_question(item) for item in items],
    )


async def _resolve_canonical_unit_ids(
    db: AsyncSession,
    *,
    topic_ids: list[uuid.UUID],
    canonical_unit_ids: list[str] | None,
) -> list[str]:
    if canonical_unit_ids:
        return list(dict.fromkeys(str(unit_id) for unit_id in canonical_unit_ids))

    if not topic_ids:
        raise ValidationError(
            "Assessment requires canonical_unit_ids. Legacy topic-based assessments are removed."
        )

    result = await db.execute(
        select(LearningUnit).where(LearningUnit.id.in_(topic_ids))
    )
    units = result.scalars().all()
    unit_by_id = {unit.id: unit for unit in units if unit.canonical_unit_id}
    missing = [str(topic_id) for topic_id in topic_ids if topic_id not in unit_by_id]
    if missing:
        raise ValidationError(
            "Assessment requires canonical learning unit IDs. Missing canonical mapping for: "
            + ", ".join(missing)
        )
    return [str(unit_by_id[topic_id].canonical_unit_id) for topic_id in topic_ids]


async def _select_canonical_questions_for_units(
    db: AsyncSession,
    *,
    canonical_unit_ids: list[str],
    phase: str,
    count: int,
) -> list[QuestionBankItem]:
    selector = CanonicalQuestionSelector(CanonicalQuestionRepository(db))
    return await selector.select_for_phase(
        phase=phase,
        canonical_unit_ids=canonical_unit_ids,
        count=count,
    )


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

    base_global_result = await db.execute(
        select(func.max(Interaction.global_sequence_position)).where(Interaction.user_id == user_id)
    )
    base_global = base_global_result.scalar() or 0
    now = datetime.now(UTC)
    correct_count = 0

    for seq, answer in enumerate(answers, start=1):
        item_id = str(answer.canonical_item_id)
        item = items[item_id]
        is_correct = int(item.answer_index) == _selected_answer_to_index(answer.selected_answer)
        if is_correct:
            correct_count += 1

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
    )


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

    return await _build_canonical_assessment_response(
        db=db,
        session_id=session_id,
        completed_at=session.completed_at,
        rows=rows,
    )


async def _build_canonical_assessment_response(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    completed_at: datetime,
    rows: list[tuple[Interaction, QuestionBankItem]],
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

    topic_results: list[TopicResult] = []
    total_correct = 0
    total_questions = 0
    for unit_id, unit_rows in per_unit_rows.items():
        correct = sum(1 for interaction, _ in unit_rows if interaction.is_correct)
        total = len(unit_rows)
        total_correct += correct
        total_questions += total
        score_percent = round(correct / total * 100, 1) if total else 0.0
        unit = unit_by_canonical_id.get(unit_id)
        topic_results.append(
            TopicResult(
                topic_id=unit.id if unit is not None else uuid.uuid5(uuid.NAMESPACE_URL, unit_id),
                topic_name=unit.title if unit is not None else unit_id,
                score_percent=score_percent,
                mastery_level=classify_mastery(score_percent),
                bloom_breakdown={"canonical": f"{correct}/{total}"},
                weak_kcs=weak_kps.get(unit_id, []),
                misconceptions_detected=[],
                theta_estimate=0.0,
            )
        )

    topic_results.sort(key=lambda item: item.topic_name.lower())
    overall_score = round(total_correct / total_questions * 100, 1) if total_questions else 0.0
    return AssessmentResultResponse(
        session_id=session_id,
        completed_at=completed_at,
        overall_score_percent=overall_score,
        topic_results=topic_results,
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
