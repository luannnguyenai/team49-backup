from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.canonical import PrerequisiteEdge, UnitKPMap
from src.models.course import LearningUnit


class CanonicalContentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_linked_learning_units(self, course_ids: list[UUID]) -> list[LearningUnit]:
        if not course_ids:
            return []
        result = await self.session.execute(
            select(LearningUnit)
            .where(
                LearningUnit.course_id.in_(course_ids),
                LearningUnit.canonical_unit_id.isnot(None),
            )
            .order_by(LearningUnit.sort_order)
        )
        return list(result.scalars().all())

    async def get_unit_kp_rows(self, canonical_unit_ids: list[str]) -> list[UnitKPMap]:
        if not canonical_unit_ids:
            return []
        result = await self.session.execute(
            select(UnitKPMap).where(UnitKPMap.unit_id.in_(canonical_unit_ids))
        )
        return list(result.scalars().all())

    async def get_prerequisite_edges_for_kps(self, kp_ids: list[str]) -> list[PrerequisiteEdge]:
        if not kp_ids:
            return []
        result = await self.session.execute(
            select(PrerequisiteEdge).where(
                or_(
                    PrerequisiteEdge.source_kp_id.in_(kp_ids),
                    PrerequisiteEdge.target_kp_id.in_(kp_ids),
                )
            )
        )
        return list(result.scalars().all())
