from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.canonical import ItemKPMap, ItemPhaseMap, QuestionBankItem


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
