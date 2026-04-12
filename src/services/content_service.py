"""
services/content_service.py
----------------------------
Business logic for the content management APIs.
All functions are async and accept an AsyncSession.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.content import Module, Topic
from src.schemas.content import (
    ModuleDetailResponse,
    ModuleListItem,
    PrerequisiteTopic,
    TopicContentResponse,
    TopicDetailResponse,
    TopicSummary,
)

# ---------------------------------------------------------------------------
# GET /api/modules
# ---------------------------------------------------------------------------


async def list_modules(db: AsyncSession) -> list[ModuleListItem]:
    """Return all modules ordered by order_index with their topic counts."""

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
# GET /api/modules/{module_id}
# ---------------------------------------------------------------------------


async def get_module_detail(db: AsyncSession, module_id: uuid.UUID) -> ModuleDetailResponse | None:
    """Return module + its ordered topic list. None if module not found."""

    module_result = await db.execute(select(Module).where(Module.id == module_id))
    module = module_result.scalar_one_or_none()
    if module is None:
        return None

    topics_result = await db.execute(
        select(Topic).where(Topic.module_id == module_id).order_by(Topic.order_index)
    )
    topics = topics_result.scalars().all()

    return ModuleDetailResponse(
        id=module.id,
        name=module.name,
        description=module.description,
        order_index=module.order_index,
        prerequisite_module_ids=_parse_uuid_list(module.prerequisite_module_ids),
        topics=[TopicSummary.model_validate(t) for t in topics],
        created_at=module.created_at,
        updated_at=module.updated_at,
    )


# ---------------------------------------------------------------------------
# GET /api/topics/{topic_id}
# ---------------------------------------------------------------------------


async def get_topic_detail(db: AsyncSession, topic_id: uuid.UUID) -> TopicDetailResponse | None:
    """Return topic detail with resolved prerequisite graph nodes."""

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
# GET /api/topics/{topic_id}/content
# ---------------------------------------------------------------------------


async def get_topic_content(db: AsyncSession, topic_id: uuid.UUID) -> TopicContentResponse | None:
    """Return the markdown content and video URL for a topic."""

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
