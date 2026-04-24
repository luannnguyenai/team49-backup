from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import ValidationError
from src.models.learning import Session, SessionType
from src.repositories.canonical_question_repo import CanonicalQuestionRepository
from src.repositories.canonical_content_repo import CanonicalContentRepository
from src.repositories.goal_preference_repo import GoalPreferenceRepository
from src.schemas.placement_lite import PlacementLiteStartResponse
from src.services.assessment_service import _canonical_item_to_assessment_question
from src.services.canonical_question_selector import CanonicalQuestionSelector


class PlacementUnit(Protocol):
    canonical_unit_id: str | None


def select_placement_units(units: list[PlacementUnit], *, max_units: int) -> list[PlacementUnit]:
    if len(units) <= max_units:
        return units
    if max_units <= 1:
        return [units[0]]
    step = (len(units) - 1) / (max_units - 1)
    indexes = [round(index * step) for index in range(max_units)]
    return [units[index] for index in indexes]


async def start_placement_lite_session(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    selected_course_ids: list[str],
    count: int = 10,
    max_units: int = 10,
) -> PlacementLiteStartResponse:
    course_ids = selected_course_ids
    if not course_ids:
        goal = await GoalPreferenceRepository(db).get_by_user_id(user_id)
        course_ids = list(goal.selected_course_ids or []) if goal is not None else []
    if not course_ids:
        raise ValidationError("Placement-lite requires selected_course_ids or goal preferences.")

    units = await CanonicalContentRepository(db).get_linked_learning_units(course_ids)
    sampled_units = select_placement_units(units, max_units=max_units)
    canonical_unit_ids = [unit.canonical_unit_id for unit in sampled_units if unit.canonical_unit_id]
    if not canonical_unit_ids:
        raise ValidationError("Placement-lite could not find canonical units for selected courses.")

    items = await CanonicalQuestionSelector(CanonicalQuestionRepository(db)).select_for_phase(
        phase="placement",
        canonical_unit_ids=canonical_unit_ids,
        count=count,
    )
    if not items:
        raise ValidationError("No canonical placement questions found for selected courses.")

    session = Session(
        user_id=user_id,
        session_type=SessionType.assessment,
        topic_id=None,
        module_id=None,
        canonical_phase="placement_lite",
        total_questions=len(items),
        correct_count=0,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    return PlacementLiteStartResponse(
        session_id=session.id,
        total_questions=len(items),
        questions=[_canonical_item_to_assessment_question(item) for item in items],
        selected_course_ids=course_ids,
        sampled_canonical_unit_ids=canonical_unit_ids,
    )
