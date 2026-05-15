from __future__ import annotations

from uuid import UUID

from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.canonical import (
    CanonicalUnit,
    ConceptKP,
    ItemPhaseMap,
    PrerequisiteEdge,
    QuestionBankItem,
    UnitKPMap,
)
from src.models.course import Course, CourseSection, LearningUnit
from src.models.store import Lecture as LegacyLecture


class CanonicalContentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_linked_learning_units(
        self, selected_course_ids: list[str | UUID]
    ) -> list[LearningUnit]:
        if not selected_course_ids:
            return []
        selected = [str(course_id) for course_id in selected_course_ids]
        selected_lower = [course_id.lower() for course_id in selected]
        uuid_ids = []
        for course_id in selected:
            try:
                uuid_ids.append(UUID(course_id))
            except ValueError:
                pass

        filters = [func.lower(Course.canonical_course_id).in_(selected_lower)]
        if uuid_ids:
            filters.append(Course.id.in_(uuid_ids))

        result = await self.session.execute(
            select(LearningUnit)
            .join(Course, LearningUnit.course_id == Course.id)
            .join(CourseSection, LearningUnit.section_id == CourseSection.id)
            .where(
                or_(*filters),
                LearningUnit.canonical_unit_id.isnot(None),
            )
            .order_by(Course.sort_order, CourseSection.sort_order, LearningUnit.sort_order)
        )
        return list(result.scalars().all())

    async def get_learning_units_by_ids(
        self, learning_unit_ids: list[UUID]
    ) -> dict[UUID, LearningUnit]:
        if not learning_unit_ids:
            return {}
        result = await self.session.execute(
            select(LearningUnit).where(LearningUnit.id.in_(learning_unit_ids))
        )
        return {unit.id: unit for unit in result.scalars().all()}

    async def get_courses_by_ids(self, course_ids: list[UUID]) -> dict[UUID, Course]:
        if not course_ids:
            return {}
        result = await self.session.execute(select(Course).where(Course.id.in_(course_ids)))
        return {course.id: course for course in result.scalars().all()}

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

    async def get_unit_kp_rows_by_kp_ids(self, kp_ids: list[str]) -> list[UnitKPMap]:
        if not kp_ids:
            return []
        result = await self.session.execute(select(UnitKPMap).where(UnitKPMap.kp_id.in_(kp_ids)))
        return list(result.scalars().all())

    async def get_canonical_units_by_ids(
        self, canonical_unit_ids: list[str]
    ) -> dict[str, CanonicalUnit]:
        if not canonical_unit_ids:
            return {}
        result = await self.session.execute(
            select(CanonicalUnit).where(CanonicalUnit.unit_id.in_(canonical_unit_ids))
        )
        return {unit.unit_id: unit for unit in result.scalars().all()}

    async def get_concepts_by_ids(self, kp_ids: list[str]) -> dict[str, ConceptKP]:
        if not kp_ids:
            return {}
        result = await self.session.execute(select(ConceptKP).where(ConceptKP.kp_id.in_(kp_ids)))
        return {concept.kp_id: concept for concept in result.scalars().all()}

    async def get_quiz_item_counts_by_unit_ids(
        self,
        canonical_unit_ids: list[str],
        phases: tuple[str, ...] = (
            "placement",
            "mini_quiz",
            "skip_verification",
            "bridge_check",
            "final_quiz",
            "review",
        ),
    ) -> dict[str, int]:
        if not canonical_unit_ids:
            return {}
        result = await self.session.execute(
            select(
                QuestionBankItem.unit_id,
                func.count(func.distinct(QuestionBankItem.item_id)),
            )
            .join(ItemPhaseMap, ItemPhaseMap.item_id == QuestionBankItem.item_id)
            .where(
                QuestionBankItem.unit_id.in_(canonical_unit_ids),
                ItemPhaseMap.phase.in_(phases),
                QuestionBankItem.qa_gate_passed.is_not(False),
            )
            .group_by(QuestionBankItem.unit_id)
        )
        return {str(unit_id): int(count) for unit_id, count in result.all()}

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

    async def search_canonical_units(
        self,
        query_terms: list[str],
        course_ids: list[str],
        limit: int = 20,
        include_reference: bool = False,
        title_only: bool = False,
    ) -> list[CanonicalUnit]:
        if not query_terms or not course_ids:
            return []

        normalized_courses = [course_id.lower() for course_id in course_ids]
        like_filters = []
        searchable_columns = [
            CanonicalUnit.unit_name,
            func.coalesce(CanonicalUnit.lecture_title, ""),
        ]
        if not title_only:
            searchable_columns.extend(
                [
                    func.coalesce(CanonicalUnit.summary, ""),
                    func.coalesce(CanonicalUnit.description, ""),
                ]
            )
        for term in query_terms:
            pattern = f"%{term.lower()}%"
            compact_term = "".join(ch for ch in term.lower() if ch.isalnum())
            compact_pattern = f"%{compact_term}%"
            for column in searchable_columns:
                like_filters.append(func.lower(column).like(pattern))
            if compact_term:
                for column in searchable_columns:
                    like_filters.append(
                        func.regexp_replace(
                            func.lower(column),
                            "[-_]+",
                            "",
                            "g",
                        ).like(compact_pattern)
                    )

        content_filters = [
            CanonicalUnit.active.is_not(False),
            func.lower(CanonicalUnit.course_id).in_(normalized_courses),
        ]
        if not include_reference:
            section_flags_text = cast(CanonicalUnit.section_flags, String)
            content_filters.append(
                or_(
                    CanonicalUnit.section_flags.is_(None),
                    and_(
                        ~section_flags_text.like("%logistics%"),
                        ~section_flags_text.like("%admin%"),
                    ),
                )
            )

        result = await self.session.execute(
            select(CanonicalUnit)
            .where(*content_filters, or_(*like_filters))
            .order_by(
                CanonicalUnit.course_id, CanonicalUnit.lecture_order, CanonicalUnit.ordering_index
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_learning_units_by_canonical_ids(
        self,
        canonical_unit_ids: list[str],
    ) -> dict[str, tuple[LearningUnit, Course, CourseSection]]:
        if not canonical_unit_ids:
            return {}
        result = await self.session.execute(
            select(LearningUnit, Course, CourseSection)
            .join(Course, LearningUnit.course_id == Course.id)
            .join(CourseSection, LearningUnit.section_id == CourseSection.id)
            .where(LearningUnit.canonical_unit_id.in_(canonical_unit_ids))
        )
        return {
            unit.canonical_unit_id: (unit, course, section)
            for unit, course, section in result.all()
            if unit.canonical_unit_id
        }

    async def get_lecture_context_for_unit(
        self,
        canonical_unit_id: str,
        *,
        allowed_course_ids: list[str],
        limit: int = 40,
    ) -> dict | None:
        if not canonical_unit_id:
            return None
        normalized_courses = [str(course_id).lower() for course_id in allowed_course_ids]
        current_result = await self.session.execute(
            select(CanonicalUnit).where(CanonicalUnit.unit_id == canonical_unit_id).limit(1)
        )
        current = current_result.scalar_one_or_none()
        if current is None:
            return None
        if normalized_courses and current.course_id.lower() not in normalized_courses:
            return None

        legacy_lecture = None
        legacy_filters = []
        if current.lecture_id:
            legacy_filters.append(LegacyLecture.id == current.lecture_id)
        if current.lecture_title:
            legacy_filters.append(func.lower(LegacyLecture.title) == current.lecture_title.lower())
        if legacy_filters:
            legacy_result = await self.session.execute(
                select(LegacyLecture).where(or_(*legacy_filters)).limit(1)
            )
            legacy_lecture = legacy_result.scalar_one_or_none()
        lecture_summary = (
            str(legacy_lecture.description).strip()
            if legacy_lecture is not None and legacy_lecture.description
            else None
        )

        lecture_filters = [CanonicalUnit.course_id == current.course_id]
        if current.lecture_id:
            lecture_filters.append(CanonicalUnit.lecture_id == current.lecture_id)
        elif current.lecture_order is not None:
            lecture_filters.append(CanonicalUnit.lecture_order == current.lecture_order)
        elif current.lecture_title:
            lecture_filters.append(CanonicalUnit.lecture_title == current.lecture_title)
        else:
            lecture_filters.append(CanonicalUnit.unit_id == current.unit_id)

        result = await self.session.execute(
            select(CanonicalUnit)
            .where(
                *lecture_filters,
                CanonicalUnit.active.is_not(False),
            )
            .order_by(CanonicalUnit.ordering_index, CanonicalUnit.unit_id)
            .limit(limit)
        )
        units = list(result.scalars().all())
        return {
            "course_id": current.course_id,
            "lecture_id": current.lecture_id,
            "lecture_order": current.lecture_order,
            "lecture_title": current.lecture_title,
            "source": "lecture_description" if lecture_summary else "unit_summaries",
            "lecture_summary": lecture_summary,
            "units": [
                {
                    "canonical_unit_id": unit.unit_id,
                    "course_id": unit.course_id,
                    "lecture_id": unit.lecture_id,
                    "lecture_order": unit.lecture_order,
                    "lecture_title": unit.lecture_title,
                    "unit_name": unit.unit_name,
                    "summary": unit.summary,
                    "description": unit.description,
                    "duration_min": unit.duration_min,
                    "ordering_index": unit.ordering_index,
                }
                for unit in units
            ],
        }

    async def get_mastery_lcb_by_kp_ids(self, user_id, kp_ids: list[str]) -> dict[str, float]:
        if not kp_ids:
            return {}
        from src.models.learning import LearnerMasteryKP

        result = await self.session.execute(
            select(LearnerMasteryKP).where(
                LearnerMasteryKP.user_id == user_id,
                LearnerMasteryKP.kp_id.in_(kp_ids),
            )
        )
        mastery = {}
        for row in result.scalars().all():
            mastery[row.kp_id] = max(
                0.0, float(row.mastery_mean_cached) - float(row.theta_sigma) * 0.5
            )
        return mastery

    async def get_user_learning_status_by_canonical_ids(
        self,
        user_id,
        canonical_unit_ids: list[str],
    ) -> dict[str, str]:
        if not canonical_unit_ids:
            return {}

        from src.models.course import LearningProgressStatus
        from src.repositories.learning_progress_repo import LearningProgressRepository
        from src.repositories.waived_unit_repo import WaivedUnitRepository

        linked_units = await self.get_learning_units_by_canonical_ids(canonical_unit_ids)
        learning_unit_ids = [unit.id for unit, _course, _section in linked_units.values()]
        if not learning_unit_ids:
            return {}

        waived_by_unit = await WaivedUnitRepository(self.session).list_for_user_units(
            user_id,
            learning_unit_ids,
        )
        progress_by_unit = await LearningProgressRepository(self.session).list_for_user_units(
            user_id,
            learning_unit_ids,
        )

        status_by_canonical_id: dict[str, str] = {}
        for canonical_unit_id, (unit, _course, _section) in linked_units.items():
            if unit.id in waived_by_unit:
                status_by_canonical_id[canonical_unit_id] = "skipped"
                continue
            progress = progress_by_unit.get(unit.id)
            if progress is None:
                status_by_canonical_id[canonical_unit_id] = "not_started"
                continue
            if progress.status == LearningProgressStatus.skipped:
                status_by_canonical_id[canonical_unit_id] = "skipped"
            elif progress.status == LearningProgressStatus.completed:
                status_by_canonical_id[canonical_unit_id] = "completed"
            elif progress.status == LearningProgressStatus.in_progress:
                status_by_canonical_id[canonical_unit_id] = "in_progress"
            else:
                status_by_canonical_id[canonical_unit_id] = "not_started"

        return status_by_canonical_id
