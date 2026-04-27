from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.placement import PlacementAssessmentResult


class PlacementAssessmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[PlacementAssessmentResult]:
        stmt = (
            select(PlacementAssessmentResult)
            .where(PlacementAssessmentResult.user_id == user_id)
            .order_by(PlacementAssessmentResult.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_user_and_unit(
        self, user_id: uuid.UUID, topic_unit_id: uuid.UUID
    ) -> PlacementAssessmentResult | None:
        stmt = select(PlacementAssessmentResult).where(
            PlacementAssessmentResult.user_id == user_id,
            PlacementAssessmentResult.topic_unit_id == topic_unit_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        user_id: uuid.UUID,
        topic_unit_id: uuid.UUID,
        score_pct: float | Decimal,
        decision: str,
        raw_answers: list[dict],
        theta_estimate: float | Decimal | None = None,
        user_choice: str | None = None,
    ) -> PlacementAssessmentResult:
        stmt = (
            pg_insert(PlacementAssessmentResult)
            .values(
                user_id=user_id,
                topic_unit_id=topic_unit_id,
                score_pct=score_pct,
                decision=decision,
                raw_answers=raw_answers,
                theta_estimate=theta_estimate,
                user_choice=user_choice,
            )
            .on_conflict_do_update(
                constraint="uq_placement_results_user_unit",
                set_={
                    "score_pct": score_pct,
                    "decision": decision,
                    "raw_answers": raw_answers,
                    "theta_estimate": theta_estimate,
                    "user_choice": user_choice,
                },
            )
            .returning(PlacementAssessmentResult)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()
