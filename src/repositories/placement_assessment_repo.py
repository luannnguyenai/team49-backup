from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.placement import PlacementAssessmentResult


class PlacementAssessmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[PlacementAssessmentResult]:
        stmt = select(PlacementAssessmentResult).where(
            PlacementAssessmentResult.user_id == user_id
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
        score_pct: float,
        decision: str,
        raw_answers: list[dict],
        theta_estimate: float | None = None,
        user_choice: str | None = None,
    ) -> PlacementAssessmentResult:
        existing = await self.get_by_user_and_unit(user_id, topic_unit_id)
        if existing is not None:
            existing.score_pct = score_pct  # type: ignore[assignment]
            existing.decision = decision
            existing.raw_answers = raw_answers
            existing.theta_estimate = theta_estimate  # type: ignore[assignment]
            existing.user_choice = user_choice
            self.session.add(existing)
            return existing

        row = PlacementAssessmentResult(
            user_id=user_id,
            topic_unit_id=topic_unit_id,
            score_pct=score_pct,
            decision=decision,
            raw_answers=raw_answers,
            theta_estimate=theta_estimate,
            user_choice=user_choice,
        )
        self.session.add(row)
        await self.session.flush()
        return row
