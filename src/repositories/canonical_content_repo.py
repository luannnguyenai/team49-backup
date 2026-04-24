from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.canonical import PrerequisiteEdge, UnitKPMap
from src.models.course import Course, CourseSection, LearningUnit


class CanonicalContentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_linked_learning_units(self, selected_course_ids: list[str | UUID]) -> list[LearningUnit]:
        if not selected_course_ids:
            return []
        selected = [str(course_id) for course_id in selected_course_ids]
        uuid_ids = []
        for course_id in selected:
            try:
                uuid_ids.append(UUID(course_id))
            except ValueError:
                pass

        filters = [Course.canonical_course_id.in_(selected)]
        if uuid_ids:
            filters.append(Course.id.in_(uuid_ids))

        result = await self.session.execute(
            select(LearningUnit)
            .join(Course, LearningUnit.course_id == Course.id)
            .where(
                or_(*filters),
                LearningUnit.canonical_unit_id.isnot(None),
            )
            .order_by(Course.sort_order, LearningUnit.sort_order)
        )
        return list(result.scalars().all())

    async def get_learning_units_by_ids(self, learning_unit_ids: list[UUID]) -> dict[UUID, LearningUnit]:
        if not learning_unit_ids:
            return {}
        result = await self.session.execute(
            select(LearningUnit).where(LearningUnit.id.in_(learning_unit_ids))
        )
        return {unit.id: unit for unit in result.scalars().all()}

    async def get_sections_by_ids(self, section_ids: list[UUID]) -> dict[UUID, CourseSection]:
        if not section_ids:
            return {}
        result = await self.session.execute(
            select(CourseSection).where(CourseSection.id.in_(section_ids))
        )
        return {section.id: section for section in result.scalars().all()}

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
