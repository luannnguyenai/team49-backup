from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session
from src.models.canonical import ItemKPMap, ItemPhaseMap, QuestionBankItem
from src.models.course import LearningUnit
from src.models.learning import Interaction, PlanHistory


def classify_parity_status(
    *,
    linked_units: int,
    unlinked_units: int,
    missing_question_phase_maps: int,
    missing_question_kp_maps: int,
) -> str:
    if (
        linked_units <= 0
        or unlinked_units > 0
        or missing_question_phase_maps > 0
        or missing_question_kp_maps > 0
    ):
        return "blocked"
    return "ready"


async def build_parity_report(session: AsyncSession) -> dict[str, Any]:
    linked_units = int(
        (
            await session.execute(
                select(func.count()).select_from(LearningUnit).where(LearningUnit.canonical_unit_id.isnot(None))
            )
        ).scalar_one()
    )
    unlinked_units = int(
        (
            await session.execute(
                select(func.count()).select_from(LearningUnit).where(LearningUnit.canonical_unit_id.is_(None))
            )
        ).scalar_one()
    )
    missing_question_phase_maps = int(
        (
            await session.execute(
                select(func.count())
                .select_from(QuestionBankItem)
                .outerjoin(ItemPhaseMap, ItemPhaseMap.item_id == QuestionBankItem.item_id)
                .where(ItemPhaseMap.item_id.is_(None))
            )
        ).scalar_one()
    )
    missing_question_kp_maps = int(
        (
            await session.execute(
                select(func.count())
                .select_from(QuestionBankItem)
                .outerjoin(ItemKPMap, ItemKPMap.item_id == QuestionBankItem.item_id)
                .where(ItemKPMap.item_id.is_(None))
            )
        ).scalar_one()
    )
    interactions_missing_canonical_item = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Interaction)
                .where(
                    Interaction.question_id.is_(None),
                    Interaction.canonical_item_id.is_(None),
                )
            )
        ).scalar_one()
    )
    canonical_planner_plan_count = int(
        (
            await session.execute(
                select(func.count()).select_from(PlanHistory).where(
                    PlanHistory.trigger == "generate_canonical_learning_path"
                )
            )
        ).scalar_one()
    )
    canonical_interaction_count = int(
        (
            await session.execute(
                select(func.count()).select_from(Interaction).where(
                    Interaction.canonical_item_id.isnot(None),
                )
            )
        ).scalar_one()
    )
    return {
        "status": classify_parity_status(
            linked_units=linked_units,
            unlinked_units=unlinked_units,
            missing_question_phase_maps=missing_question_phase_maps,
            missing_question_kp_maps=missing_question_kp_maps,
        ),
        "linked_units": linked_units,
        "unlinked_units": unlinked_units,
        "missing_question_phase_maps": missing_question_phase_maps,
        "missing_question_kp_maps": missing_question_kp_maps,
        "interactions_missing_canonical_item": interactions_missing_canonical_item,
        "canonical_interaction_count": canonical_interaction_count,
        "canonical_planner_plan_count": canonical_planner_plan_count,
    }


async def _run() -> dict[str, Any]:
    async with async_session() as session:
        return await build_parity_report(session)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check canonical runtime cutover parity.")
    parser.parse_args()
    print(json.dumps(asyncio.run(_run()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
