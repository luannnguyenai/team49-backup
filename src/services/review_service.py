from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError, ValidationError
from src.models.learning import Session, SessionType
from src.repositories.canonical_content_repo import CanonicalContentRepository
from src.repositories.canonical_question_repo import CanonicalQuestionRepository
from src.repositories.goal_preference_repo import GoalPreferenceRepository
from src.repositories.learner_mastery_kp_repo import LearnerMasteryKPRepository
from src.schemas.review import ReviewStartResponse
from src.services.assessment_service import _canonical_item_to_assessment_question
from src.services.canonical_question_selector import CanonicalQuestionSelector


class MasteryForReview(Protocol):
    mastery_mean_cached: float
    updated_at: datetime


def pick_review_kp_ids(
    kp_ids: list[str],
    mastery_by_kp: dict[str, MasteryForReview],
    *,
    now: datetime,
    weak_threshold: float = 0.6,
    stale_days: int = 7,
) -> list[str]:
    selected: list[str] = []
    for kp_id in kp_ids:
        mastery = mastery_by_kp.get(kp_id)
        if mastery is None:
            selected.append(kp_id)
            continue
        age_days = (now - mastery.updated_at).total_seconds() / 86_400
        if mastery.mastery_mean_cached < weak_threshold or age_days > stale_days:
            selected.append(kp_id)
    return selected


async def start_review_session(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    learning_unit_ids: list[uuid.UUID],
    count: int = 5,
) -> ReviewStartResponse:
    content_repo = CanonicalContentRepository(db)
    units = []
    if learning_unit_ids:
        unit_by_id = await content_repo.get_learning_units_by_ids(learning_unit_ids)
        units = [unit_by_id[unit_id] for unit_id in learning_unit_ids if unit_id in unit_by_id]
    else:
        goal = await GoalPreferenceRepository(db).get_by_user_id(user_id)
        if goal is None or not goal.selected_course_ids:
            raise ValidationError("Review requires learning_unit_ids or goal_preferences.selected_course_ids.")
        units = await content_repo.get_linked_learning_units(goal.selected_course_ids)

    canonical_unit_ids = [unit.canonical_unit_id for unit in units if unit.canonical_unit_id]
    if not canonical_unit_ids:
        raise NotFoundError("No canonical learning units available for review.")

    unit_kp_rows = await content_repo.get_unit_kp_rows(canonical_unit_ids)
    kp_ids = sorted({row.kp_id for row in unit_kp_rows})
    mastery_by_kp = await LearnerMasteryKPRepository(db).bulk_get_for_user(user_id, kp_ids)
    review_kp_ids = pick_review_kp_ids(kp_ids, mastery_by_kp, now=datetime.now(UTC))
    if not review_kp_ids:
        review_kp_ids = kp_ids[:count]

    items = await CanonicalQuestionSelector(CanonicalQuestionRepository(db)).select_for_phase(
        phase="review",
        canonical_unit_ids=canonical_unit_ids,
        kp_ids=review_kp_ids,
        count=count,
    )
    if not items:
        raise ValidationError("No canonical review questions found for selected learning units.")

    session = Session(
        user_id=user_id,
        session_type=SessionType.assessment,
        topic_id=None,
        module_id=None,
        canonical_phase="review",
        total_questions=len(items),
        correct_count=0,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    return ReviewStartResponse(
        session_id=session.id,
        total_questions=len(items),
        questions=[_canonical_item_to_assessment_question(item) for item in items],
        review_kp_ids=review_kp_ids,
    )
