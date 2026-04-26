from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.canonical import ItemCalibration, ItemKPMap, ItemPhaseMap, QuestionBankItem


class CanonicalQuestionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_items_for_phase(
        self,
        *,
        phase: str,
        canonical_unit_ids: list[str],
        kp_ids: list[str] | None = None,
        limit: int = 50,
    ) -> list[QuestionBankItem]:
        if not canonical_unit_ids:
            return []

        stmt = (
            select(QuestionBankItem)
            .join(ItemPhaseMap, ItemPhaseMap.item_id == QuestionBankItem.item_id)
            .where(
                ItemPhaseMap.phase == phase,
                QuestionBankItem.unit_id.in_(canonical_unit_ids),
            )
            .order_by(QuestionBankItem.item_id)
            .limit(limit)
        )
        if kp_ids:
            stmt = stmt.join(ItemKPMap, ItemKPMap.item_id == QuestionBankItem.item_id).where(
                ItemKPMap.kp_id.in_(kp_ids)
            )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_items_for_placement_bucketed(
        self,
        *,
        canonical_unit_ids: list[str],
        phase: str = "placement",
    ) -> list[tuple[QuestionBankItem, float | None]]:
        """
        Returns (item, difficulty_prior) pairs filtered by phase and unit IDs.
        difficulty_prior is None when ItemCalibration row is absent.
        Caller uses _bucket_select_5 to pick 1 easy / 2 medium / 2 hard per unit.
        """
        if not canonical_unit_ids:
            return []

        stmt = (
            select(QuestionBankItem, ItemCalibration.difficulty_prior)
            .join(ItemPhaseMap, ItemPhaseMap.item_id == QuestionBankItem.item_id)
            .outerjoin(
                ItemCalibration, ItemCalibration.item_id == QuestionBankItem.item_id
            )
            .where(
                ItemPhaseMap.phase == phase,
                QuestionBankItem.unit_id.in_(canonical_unit_ids),
            )
            .order_by(
                QuestionBankItem.unit_id,
                ItemCalibration.difficulty_prior.asc().nulls_last(),
            )
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]
