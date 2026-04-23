"""
services/content_service.py
----------------------------
Business logic for the content management APIs.
All functions are async and accept an AsyncSession.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.canonical import CanonicalUnit
from src.models.content import Module, Topic
from src.models.course import Course, CourseAsset, CourseAssetType, CourseSection, LearningUnit
from src.schemas.content import (
    CourseSectionDetailResponse,
    CourseSectionListItem,
    LearningUnitContentResponse,
    LearningUnitSelectionItem,
    ModuleDetailResponse,
    ModuleListItem,
    PrerequisiteTopic,
    TopicContentResponse,
    TopicDetailResponse,
    TopicSummary,
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
# Retired legacy module/topic service adapters.
#
# Public routes now use canonical course section and learning-unit services.
# These functions are kept temporarily for seed/dev compatibility until the
# legacy ORM tables are fully removed.
# ---------------------------------------------------------------------------


async def list_modules(db: AsyncSession) -> list[ModuleListItem]:
    """Return all modules ordered by order_index with their topic counts."""
    if not settings.allow_legacy_topic_content_reads:
        return await _list_modules_from_canonical_sections(db)

    # Fetch modules
    modules_result = await db.execute(select(Module).order_by(Module.order_index))
    modules = modules_result.scalars().all()

    if not modules:
        return []

    # Count topics per module in a single query
    counts_result = await db.execute(
        select(Topic.module_id, func.count(Topic.id).label("cnt")).group_by(Topic.module_id)
    )
    counts: dict[uuid.UUID, int] = {row.module_id: row.cnt for row in counts_result}

    return [
        ModuleListItem(
            id=m.id,
            name=m.name,
            description=m.description,
            order_index=m.order_index,
            prerequisite_module_ids=_parse_uuid_list(m.prerequisite_module_ids),
            topics_count=counts.get(m.id, 0),
        )
        for m in modules
    ]


# ---------------------------------------------------------------------------
# Retired legacy adapter for module detail
# ---------------------------------------------------------------------------


async def get_module_detail(db: AsyncSession, module_id: uuid.UUID) -> ModuleDetailResponse | None:
    """Return module + its ordered topic list. None if module not found."""
    if not settings.allow_legacy_topic_content_reads:
        return await _get_module_detail_from_canonical_section(db, module_id)

    module_result = await db.execute(select(Module).where(Module.id == module_id))
    module = module_result.scalar_one_or_none()
    if module is None:
        return None

    topics_result = await db.execute(
        select(Topic).where(Topic.module_id == module_id).order_by(Topic.order_index)
    )
    topics = topics_result.scalars().all()

    topic_list = [TopicSummary.model_validate(t) for t in topics]
    return ModuleDetailResponse(
        id=module.id,
        name=module.name,
        description=module.description,
        order_index=module.order_index,
        prerequisite_module_ids=_parse_uuid_list(module.prerequisite_module_ids),
        topics_count=len(topic_list),
        topics=topic_list,
        created_at=module.created_at,
        updated_at=module.updated_at,
    )


# ---------------------------------------------------------------------------
# Retired legacy adapter for topic detail
# ---------------------------------------------------------------------------


async def get_topic_detail(db: AsyncSession, topic_id: uuid.UUID) -> TopicDetailResponse | None:
    """Return topic detail with resolved prerequisite graph nodes."""
    if not settings.allow_legacy_topic_content_reads:
        return await _get_topic_detail_from_canonical_unit(db, topic_id)

    topic_result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = topic_result.scalar_one_or_none()
    if topic is None:
        return None

    prereq_ids = _parse_uuid_list(topic.prerequisite_topic_ids) or []
    prerequisites: list[PrerequisiteTopic] = []

    if prereq_ids:
        prereq_result = await db.execute(
            select(Topic).where(Topic.id.in_(prereq_ids)).order_by(Topic.order_index)
        )
        prerequisites = [PrerequisiteTopic.model_validate(p) for p in prereq_result.scalars().all()]

    return TopicDetailResponse(
        id=topic.id,
        module_id=topic.module_id,
        name=topic.name,
        description=topic.description,
        order_index=topic.order_index,
        estimated_hours_beginner=topic.estimated_hours_beginner,
        estimated_hours_intermediate=topic.estimated_hours_intermediate,
        estimated_hours_review=topic.estimated_hours_review,
        prerequisite_topic_ids=prereq_ids,
        prerequisites=prerequisites,
        created_at=topic.created_at,
        updated_at=topic.updated_at,
    )


# ---------------------------------------------------------------------------
# Retired legacy adapter for topic content
# ---------------------------------------------------------------------------


async def get_topic_content(db: AsyncSession, topic_id: uuid.UUID) -> TopicContentResponse | None:
    """Return the markdown content and video URL for a topic."""
    if not settings.allow_legacy_topic_content_reads:
        return await _get_topic_content_from_canonical_unit(db, topic_id)

    result = await db.execute(
        select(Topic, Module.name.label("module_name"))
        .join(Module, Topic.module_id == Module.id)
        .where(Topic.id == topic_id)
    )
    row = result.first()
    if row is None:
        return None

    topic, module_name = row

    return TopicContentResponse(
        topic_id=topic.id,
        topic_name=topic.name,
        module_id=topic.module_id,
        module_name=module_name,
        content_markdown=topic.content_markdown,
        video_url=topic.video_url,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_uuid_list(raw: list | None) -> list[uuid.UUID] | None:
    """Convert a JSON-stored list of UUID strings to list[uuid.UUID]."""
    if not raw:
        return None
    try:
        return [uuid.UUID(str(item)) for item in raw]
    except (ValueError, AttributeError):
        return None


async def _list_modules_from_canonical_sections(db: AsyncSession) -> list[ModuleListItem]:
    """Expose course sections through the legacy module-list response shape."""
    result = await db.execute(
        select(CourseSection, Course, func.count(LearningUnit.id).label("topics_count"))
        .join(Course, CourseSection.course_id == Course.id)
        .outerjoin(LearningUnit, LearningUnit.section_id == CourseSection.id)
        .group_by(CourseSection.id, Course.id)
        .order_by(Course.sort_order, CourseSection.sort_order)
    )
    rows = result.all()
    return [
        ModuleListItem(
            id=section.id,
            name=section.title,
            description=course.short_description,
            order_index=section.sort_order,
            prerequisite_module_ids=None,
            topics_count=int(topics_count or 0),
        )
        for section, course, topics_count in rows
        if int(topics_count or 0) > 0
    ]


async def _get_module_detail_from_canonical_section(
    db: AsyncSession,
    section_id: uuid.UUID,
) -> ModuleDetailResponse | None:
    result = await db.execute(
        select(CourseSection, Course).join(Course, CourseSection.course_id == Course.id).where(
            CourseSection.id == section_id
        )
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
    units = units_result.scalars().all()
    topics = [
        TopicSummary(
            id=unit.id,
            canonical_unit_id=unit.canonical_unit_id,
            name=unit.title,
            description=unit.content_body,
            order_index=unit.sort_order,
            estimated_hours_beginner=_minutes_to_hours(unit.estimated_minutes),
            estimated_hours_intermediate=_minutes_to_hours(unit.estimated_minutes),
        )
        for unit in units
    ]
    return ModuleDetailResponse(
        id=section.id,
        name=section.title,
        description=course.short_description,
        order_index=section.sort_order,
        prerequisite_module_ids=None,
        topics_count=len(topics),
        topics=topics,
        created_at=section.created_at,
        updated_at=section.updated_at,
    )


async def _get_topic_detail_from_canonical_unit(
    db: AsyncSession,
    unit_id: uuid.UUID,
) -> TopicDetailResponse | None:
    result = await db.execute(
        select(LearningUnit, CourseSection).join(CourseSection, LearningUnit.section_id == CourseSection.id).where(
            LearningUnit.id == unit_id
        )
    )
    row = result.first()
    if row is None:
        return None

    unit, section = row
    return TopicDetailResponse(
        id=unit.id,
        module_id=section.id,
        name=unit.title,
        description=unit.content_body,
        order_index=unit.sort_order,
        estimated_hours_beginner=_minutes_to_hours(unit.estimated_minutes),
        estimated_hours_intermediate=_minutes_to_hours(unit.estimated_minutes),
        estimated_hours_review=_minutes_to_hours(unit.estimated_minutes, divisor=120),
        prerequisite_topic_ids=None,
        prerequisites=[],
        created_at=unit.created_at,
        updated_at=unit.updated_at,
    )


async def _get_topic_content_from_canonical_unit(
    db: AsyncSession,
    unit_id: uuid.UUID,
) -> TopicContentResponse | None:
    result = await db.execute(
        select(LearningUnit, CourseSection, Course, CanonicalUnit)
        .join(CourseSection, LearningUnit.section_id == CourseSection.id)
        .join(Course, LearningUnit.course_id == Course.id)
        .outerjoin(CanonicalUnit, LearningUnit.canonical_unit_id == CanonicalUnit.unit_id)
        .where(LearningUnit.id == unit_id)
    )
    row = result.first()
    if row is None:
        return None

    unit, section, _course, canonical_unit = row
    video_url = await _canonical_unit_video_url(db, unit, canonical_unit)
    content_markdown = unit.content_body
    if not content_markdown and canonical_unit is not None:
        content_markdown = canonical_unit.summary or canonical_unit.description

    return TopicContentResponse(
        topic_id=unit.id,
        topic_name=unit.title,
        module_id=section.id,
        module_name=section.title,
        content_markdown=content_markdown,
        video_url=video_url,
    )


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
