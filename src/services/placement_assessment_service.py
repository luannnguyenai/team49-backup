# src/services/placement_assessment_service.py
"""
Placement assessment service — 2PL IRT bucketed question selection + scoring.

Per topic (learning_unit): selects 5 questions with distribution:
  - 1 Easy:   difficulty_prior <= -0.5
  - 2 Medium: -0.5 < difficulty_prior <= 0.5  (None treated as medium)
  - 2 Hard:   difficulty_prior > 0.5
Falls back to any available questions if a bucket is empty.

Decision gate (per topic):
  score_pct >= 70  → skip
  50 <= score_pct < 70 → review
  score_pct < 50   → relearn
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.models.canonical import QuestionBankItem
from src.models.course import LearningUnit
from src.models.learning import Session, SessionType
from src.repositories.canonical_question_repo import CanonicalQuestionRepository
from src.repositories.placement_assessment_repo import PlacementAssessmentRepository
from src.schemas.placement_assessment import (
    PlacementAnswerInput,
    PlacementQuestion,
    PlacementStartResponse,
    PlacementSubmitResponse,
    TopicDecision,
)

log = logging.getLogger(__name__)


_ANSWER_INDEX: dict[str, int] = {"A": 0, "B": 1, "C": 2, "D": 3}


def _bucket_select_5(
    pairs: list[tuple[QuestionBankItem, float | None]],
) -> list[tuple[QuestionBankItem, float | None]]:
    """Pick 1 easy, 2 medium, 2 hard from (item, difficulty_prior) pairs."""
    easy = [p for p in pairs if p[1] is not None and p[1] <= -0.5]
    medium = [p for p in pairs if p[1] is None or (-0.5 < p[1] <= 0.5)]
    hard = [p for p in pairs if p[1] is not None and p[1] > 0.5]

    selected: list[tuple[QuestionBankItem, float | None]] = []
    selected += easy[:1]
    selected += medium[:2]
    selected += hard[:2]

    # Fill gaps if any bucket was thin
    selected_ids = {p[0].item_id for p in selected}
    remaining = [p for p in pairs if p[0].item_id not in selected_ids]
    while len(selected) < 5 and remaining:
        selected.append(remaining.pop(0))

    return selected[:5]


def _classify_decision(score_pct: float) -> str:
    if score_pct >= 70.0:
        return "skip"
    if score_pct >= 50.0:
        return "review"
    return "relearn"


def _item_to_placement_question(
    item: QuestionBankItem, topic_unit_id: uuid.UUID
) -> PlacementQuestion:
    choices = list(item.choices or [])
    padded = (choices + ["", "", "", ""])[:4]
    return PlacementQuestion(
        item_id=item.item_id,
        canonical_unit_id=item.unit_id,
        topic_unit_id=topic_unit_id,
        stem_text=item.question,
        option_a=str(padded[0]),
        option_b=str(padded[1]),
        option_c=str(padded[2]),
        option_d=str(padded[3]),
    )


async def start_placement_assessment(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    topic_unit_ids: list[uuid.UUID],
) -> PlacementStartResponse:
    log.info(
        "placement_start user=%s requested_units=%d",
        user_id,
        len(topic_unit_ids),
    )

    if not topic_unit_ids:
        # No units selected — signal frontend to skip the placement step entirely
        log.info("placement_start: no units requested, returning should_skip_step=True")
        return PlacementStartResponse(
            session_id=uuid.uuid4(),
            total_questions=0,
            questions=[],
            topic_unit_ids=[],
            skipped_topics=[],
            should_skip_step=True,
        )

    result = await db.execute(
        select(LearningUnit).where(LearningUnit.id.in_(topic_unit_ids))
    )
    units = {u.id: u for u in result.scalars().all()}
    if not units:
        raise NotFoundError("None of the requested learning units were found.")

    question_repo = CanonicalQuestionRepository(db)
    all_questions: list[PlacementQuestion] = []
    processed_unit_ids: list[uuid.UUID] = []
    skipped_unit_ids: list[uuid.UUID] = []

    for unit_id in topic_unit_ids:
        unit = units.get(unit_id)
        if unit is None or not unit.canonical_unit_id:
            log.warning("placement_start: unit %s not found or missing canonical_unit_id", unit_id)
            skipped_unit_ids.append(unit_id)
            continue

        pairs = await question_repo.get_items_for_placement_bucketed(
            canonical_unit_ids=[unit.canonical_unit_id],
            phase="placement",
        )
        log.info(
            "placement_start: unit=%s canonical=%s candidates=%d",
            unit_id,
            unit.canonical_unit_id,
            len(pairs),
        )

        selected = _bucket_select_5(pairs)
        if not selected:
            log.warning(
                "placement_start: unit %s has no placement items — skipping",
                unit_id,
            )
            skipped_unit_ids.append(unit_id)
            continue

        easy = sum(1 for _, d in selected if d is not None and d <= -0.5)
        medium = sum(1 for _, d in selected if d is None or (-0.5 < (d or 0) <= 0.5))
        hard = sum(1 for _, d in selected if d is not None and d > 0.5)
        log.info(
            "placement_start: unit=%s selected=%d (easy=%d medium=%d hard=%d)",
            unit_id, len(selected), easy, medium, hard,
        )

        all_questions += [_item_to_placement_question(item, unit_id) for item, _ in selected]
        processed_unit_ids.append(unit_id)

    # All requested units had no items → tell frontend to skip this step
    if not all_questions:
        log.warning(
            "placement_start: all %d units had no placement items; returning should_skip_step=True",
            len(topic_unit_ids),
        )
        return PlacementStartResponse(
            session_id=uuid.uuid4(),
            total_questions=0,
            questions=[],
            topic_unit_ids=[],
            skipped_topics=skipped_unit_ids,
            should_skip_step=True,
        )

    session = Session(
        user_id=user_id,
        session_type=SessionType.assessment,
        canonical_phase="placement_assessment",
        total_questions=len(all_questions),
        correct_count=0,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    log.info(
        "placement_start: session=%s total_questions=%d skipped_topics=%d",
        session.id,
        len(all_questions),
        len(skipped_unit_ids),
    )

    return PlacementStartResponse(
        session_id=session.id,
        total_questions=len(all_questions),
        questions=all_questions,
        topic_unit_ids=processed_unit_ids,
        skipped_topics=skipped_unit_ids,
    )


async def submit_placement_assessment(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    answers: list[PlacementAnswerInput],
) -> PlacementSubmitResponse:
    # 1. Validate session ownership FIRST
    sess_result = await db.execute(select(Session).where(Session.id == session_id))
    session = sess_result.scalar_one_or_none()
    if session is None or session.user_id != user_id:
        raise ValidationError("Session not found or does not belong to this user.")

    if session.completed_at is not None:
        raise ConflictError("Placement assessment session already submitted.")

    # 2. Load items
    item_ids = [a.item_id for a in answers]
    result = await db.execute(select(QuestionBankItem).where(QuestionBankItem.item_id.in_(item_ids)))
    items_by_id = {item.item_id: item for item in result.scalars().all()}

    by_unit: dict[uuid.UUID, list[PlacementAnswerInput]] = defaultdict(list)
    for ans in answers:
        by_unit[ans.topic_unit_id].append(ans)

    placement_repo = PlacementAssessmentRepository(db)
    topic_decisions: list[TopicDecision] = []
    total_correct_sum = 0

    for topic_unit_id, unit_answers in by_unit.items():
        correct = sum(
            1
            for ans in unit_answers
            if (item := items_by_id.get(ans.item_id)) is not None
            and _ANSWER_INDEX.get(ans.selected_answer, -1) == item.answer_index
        )
        total_correct_sum += correct
        score_pct = round((correct / len(unit_answers) * 100) if unit_answers else 0.0, 1)
        decision = _classify_decision(score_pct)
        raw_answers = [
            {"item_id": a.item_id, "selected": a.selected_answer}
            for a in unit_answers
        ]
        await placement_repo.upsert(
            user_id=user_id,
            topic_unit_id=topic_unit_id,
            score_pct=score_pct,
            decision=decision,
            raw_answers=raw_answers,
        )
        topic_decisions.append(
            TopicDecision(
                topic_unit_id=topic_unit_id,
                score_pct=score_pct,
                decision=decision,
            )
        )

    # 3. Mark session complete (session already validated above)
    session.correct_count = total_correct_sum
    session.score_percent = round(
        (total_correct_sum / len(answers) * 100) if answers else 0.0, 1
    )
    session.completed_at = datetime.now(timezone.utc)
    db.add(session)
    await db.flush()

    skip_count = sum(1 for d in topic_decisions if d.decision == "skip")
    review_count = sum(1 for d in topic_decisions if d.decision == "review")
    relearn_count = sum(1 for d in topic_decisions if d.decision == "relearn")

    return PlacementSubmitResponse(
        session_id=session_id,
        topic_decisions=topic_decisions,
        skipped_count=skip_count,
        review_count=review_count,
        relearn_count=relearn_count,
    )
