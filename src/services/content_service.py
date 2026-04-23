"""
services/content_service.py
----------------------------
Business logic for the content management APIs.
All functions are async and accept an AsyncSession.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.canonical import CanonicalUnit
from src.models.course import Course, CourseAsset, CourseAssetType, CourseSection, LearningUnit
from src.schemas.content import (
    CourseSectionDetailResponse,
    CourseSectionListItem,
    LearningUnitContentResponse,
    LearningUnitSelectionItem,
)

# ---------------------------------------------------------------------------
# Canonical content route surface
# ---------------------------------------------------------------------------


async def list_course_sections(db: AsyncSession) -> list[CourseSectionListItem]:
    """Return canonical course sections with learning-unit counts."""
    result = await db.execute(
        select(CourseSection, Course, func.count(LearningUnit.id).label("learning_units_count"))
        .join(Course, CourseSection.course_id == Course.id)
        .outerjoin(LearningUnit, LearningUnit.section_id == CourseSection.id)
        .group_by(CourseSection.id, Course.id)
        .order_by(Course.sort_order, CourseSection.sort_order)
    )
    return [
        CourseSectionListItem(
            id=section.id,
            title=section.title,
            description=course.short_description,
            order_index=section.sort_order,
            prerequisite_section_ids=None,
            learning_units_count=int(learning_units_count or 0),
        )
        for section, course, learning_units_count in result.all()
        if int(learning_units_count or 0) > 0
    ]


async def get_course_section_detail(
    db: AsyncSession,
    section_id: uuid.UUID,
) -> CourseSectionDetailResponse | None:
    """Return a canonical section and its ordered learning units."""
    result = await db.execute(
        select(CourseSection, Course)
        .join(Course, CourseSection.course_id == Course.id)
        .where(CourseSection.id == section_id)
    )
    row = result.first()
    if row is None:
        return None

    section, course = row
    units_result = await db.execute(
        select(LearningUnit)
        .where(LearningUnit.section_id == section_id)
        .order_by(LearningUnit.sort_order)
    )
    units = [
        LearningUnitSelectionItem(
            id=unit.id,
            canonical_unit_id=unit.canonical_unit_id,
            title=unit.title,
            description=unit.content_body,
            order_index=unit.sort_order,
            estimated_hours_beginner=_minutes_to_hours(unit.estimated_minutes),
            estimated_hours_intermediate=_minutes_to_hours(unit.estimated_minutes),
        )
        for unit in units_result.scalars().all()
    ]

    return CourseSectionDetailResponse(
        id=section.id,
        title=section.title,
        description=course.short_description,
        order_index=section.sort_order,
        prerequisite_section_ids=None,
        learning_units_count=len(units),
        learning_units=units,
        created_at=section.created_at,
        updated_at=section.updated_at,
    )


async def get_learning_unit_content(
    db: AsyncSession,
    learning_unit_id: uuid.UUID,
) -> LearningUnitContentResponse | None:
    """Return canonical learning-unit content by product learning-unit id."""
    result = await db.execute(
        select(LearningUnit, CourseSection, CanonicalUnit)
        .join(CourseSection, LearningUnit.section_id == CourseSection.id)
        .outerjoin(CanonicalUnit, LearningUnit.canonical_unit_id == CanonicalUnit.unit_id)
        .where(LearningUnit.id == learning_unit_id)
    )
    row = result.first()
    if row is None:
        return None

    unit, section, canonical_unit = row
    video_url = await _canonical_unit_video_url(db, unit, canonical_unit)
    content_markdown = unit.content_body
    if not content_markdown and canonical_unit is not None:
        content_markdown = canonical_unit.summary or canonical_unit.description

    return LearningUnitContentResponse(
        learning_unit_id=unit.id,
        title=unit.title,
        section_id=section.id,
        section_title=section.title,
        content_markdown=content_markdown,
        video_url=video_url,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _canonical_unit_video_url(
    db: AsyncSession,
    unit: LearningUnit,
    canonical_unit: CanonicalUnit | None,
) -> str | None:
    asset_result = await db.execute(
        select(CourseAsset)
        .where(
            CourseAsset.learning_unit_id == unit.id,
            CourseAsset.asset_type == CourseAssetType.video,
        )
        .order_by(CourseAsset.created_at)
        .limit(1)
    )
    asset = asset_result.scalar_one_or_none()
    if asset is not None:
        return asset.delivery_url or asset.storage_key

    if canonical_unit is None or not canonical_unit.content_ref:
        return None
    content_ref = canonical_unit.content_ref
    if isinstance(content_ref, dict):
        value = content_ref.get("video_url") or content_ref.get("url")
        return str(value) if value else None
    return None


def _minutes_to_hours(minutes: int | None, *, divisor: int = 60) -> float | None:
    if minutes is None:
        return None
    return round(minutes / divisor, 2)
