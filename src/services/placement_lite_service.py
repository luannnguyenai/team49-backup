from __future__ import annotations

import logging
import uuid
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.exceptions import ValidationError
from src.models.learning import Session, SessionType
from src.repositories.canonical_question_repo import CanonicalQuestionRepository
from src.repositories.canonical_content_repo import CanonicalContentRepository
from src.repositories.goal_preference_repo import GoalPreferenceRepository
from src.schemas.placement_lite import PlacementLiteStartResponse
from src.services.assessment_service import _canonical_item_to_assessment_question
from src.services.placement.strategy_selector import get_strategy
from src.services.placement.strategies.legacy_selector import LegacySelectorStrategy  # noqa: F401

log = logging.getLogger(__name__)


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

    # Get pool of placement items and apply strategy
    repo = CanonicalQuestionRepository(db)
    pool = await repo.get_items_for_phase(
        phase="placement",
        canonical_unit_ids=canonical_unit_ids,
        limit=max(count * 4, count),
    )
    if not pool:
        raise ValidationError("No canonical placement questions found for selected courses.")

    # Commit B: use configured strategy (default: spread_by_prior)
    settings = Settings()
    strategy = get_strategy(mode=settings.cold_start_mode)
    items = await strategy.select(pool, n=count)
    if not items:
        raise ValidationError("Strategy selection returned no items.")

    # Commit B: populate audit fields
    calibration_mode = "prior_only"  # Commit B: all cold-start, no calibration yet

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

    log.info(
        f"placement_lite start: user={user_id} strategy={strategy.name} "
        f"total_items={len(items)} calibration_mode={calibration_mode}"
    )

    return PlacementLiteStartResponse(
        session_id=session.id,
        total_questions=len(items),
        questions=[_canonical_item_to_assessment_question(item) for item in items],
        selected_course_ids=course_ids,
        sampled_canonical_unit_ids=canonical_unit_ids,
        selection_strategy=strategy.name,
        calibration_mode=calibration_mode,
    )
