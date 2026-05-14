from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.course import LearningUnit
from src.models.learning import SelectedAnswer
from src.repositories.canonical_question_repo import CanonicalQuestionRepository
from src.schemas.assessment import AnswerInput
from src.schemas.placement_assessment import (
    PlacementQuestion,
    PlacementStartResponse,
    PlacementSubmitResponse,
    TopicDecision,
)
from src.services.assessment_service import (
    _classify_decision,
    start_assessment,
    submit_assessment,
)


def _bucket_select_5(
    pairs: list[tuple[object, float | None]],
) -> list[tuple[object, float | None]]:
    easy = [pair for pair in pairs if pair[1] is not None and pair[1] <= -0.5]
    medium = [pair for pair in pairs if pair[1] is None or (-0.5 < pair[1] <= 0.5)]
    hard = [pair for pair in pairs if pair[1] is not None and pair[1] > 0.5]

    selected: list[tuple[object, float | None]] = []
    selected += easy[:1]
    selected += medium[:2]
    selected += hard[:2]

    selected_ids = {getattr(item, "item_id") for item, _ in selected}
    remaining = [pair for pair in pairs if getattr(pair[0], "item_id") not in selected_ids]
    target = min(5, len(pairs))
    while len(selected) < target and remaining:
        selected.append(remaining.pop(0))

    return selected[:5]


async def start_placement_assessment(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    topic_unit_ids: list[uuid.UUID],
) -> PlacementStartResponse:
    units_result = await db.execute(
        select(LearningUnit).where(LearningUnit.id.in_(topic_unit_ids))
    )
    units = units_result.scalars().all()
    unit_by_id = {unit.id: unit for unit in units}

    requested_units = [unit_by_id[unit_id] for unit_id in topic_unit_ids if unit_id in unit_by_id]
    if not requested_units:
        return PlacementStartResponse(
            session_id=uuid.uuid4(),
            total_questions=0,
            questions=[],
            topic_unit_ids=[],
            skipped_topics=list(topic_unit_ids),
            should_skip_step=True,
        )

    repo = CanonicalQuestionRepository(db)
    eligible_unit_ids: list[uuid.UUID] = []
    skipped_topics: list[uuid.UUID] = []
    unit_by_canonical_id: dict[str, LearningUnit] = {}

    for unit in requested_units:
        canonical_unit_id = str(unit.canonical_unit_id) if unit.canonical_unit_id else None
        if not canonical_unit_id:
            skipped_topics.append(unit.id)
            continue
        pairs = await repo.get_items_for_placement_bucketed(canonical_unit_ids=[canonical_unit_id])
        if not pairs:
            skipped_topics.append(unit.id)
            continue
        eligible_unit_ids.append(unit.id)
        unit_by_canonical_id[canonical_unit_id] = unit

    if not eligible_unit_ids:
        return PlacementStartResponse(
            session_id=uuid.uuid4(),
            total_questions=0,
            questions=[],
            topic_unit_ids=[],
            skipped_topics=skipped_topics,
            should_skip_step=True,
        )

    response = await start_assessment(
        db,
        user_id=user_id,
        learning_unit_ids=eligible_unit_ids,
        phase="placement",
        assessment_depth="deep",
    )

    questions = [
        PlacementQuestion(
            item_id=question.item_id,
            canonical_unit_id=str(question.canonical_unit_id),
            topic_unit_id=unit_by_canonical_id[str(question.canonical_unit_id)].id,
            stem_text=question.stem_text,
            option_a=question.option_a,
            option_b=question.option_b,
            option_c=question.option_c,
            option_d=question.option_d,
        )
        for question in response.questions
        if question.canonical_unit_id and str(question.canonical_unit_id) in unit_by_canonical_id
    ]

    return PlacementStartResponse(
        session_id=response.session_id,
        total_questions=len(questions),
        questions=questions,
        topic_unit_ids=eligible_unit_ids,
        skipped_topics=skipped_topics,
        should_skip_step=False,
    )


async def submit_placement_assessment(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    answers: list,
) -> PlacementSubmitResponse:
    response = await submit_assessment(
        db,
        user_id=user_id,
        session_id=session_id,
        answers=[
            AnswerInput(
                canonical_item_id=answer.item_id,
                selected_answer=SelectedAnswer(answer.selected_answer),
            )
            for answer in answers
        ],
    )

    topic_decisions = [
        TopicDecision(
            topic_unit_id=uuid.UUID(str(item.topic_unit_id)),
            score_pct=item.score_pct,
            decision=item.decision,
        )
        for item in (response.topic_decisions or [])
    ]

    return PlacementSubmitResponse(
        session_id=response.session_id,
        topic_decisions=topic_decisions,
        skipped_count=sum(1 for item in topic_decisions if item.decision == "skip"),
        review_count=sum(1 for item in topic_decisions if item.decision == "review"),
        relearn_count=sum(1 for item in topic_decisions if item.decision == "relearn"),
    )
