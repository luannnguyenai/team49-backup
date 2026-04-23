"""
routers/content.py
------------------
Content management API:

    GET  /api/course-sections                        List course sections
    GET  /api/course-sections/{section_id}            Section detail + learning units
    GET  /api/learning-units/{learning_unit_id}/content  Learning-unit content
"""

import uuid
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.data_paths import MODULES_FILE, TOPICS_FILE
from src.database import get_async_db
from src.schemas.content import (
    CourseSectionDetailResponse,
    CourseSectionListItem,
    LearningUnitContentResponse,
    ModuleDetailResponse,
    ModuleListItem,
    TopicContentResponse,
    TopicDetailResponse,
)
from src.services.content_service import (
    get_course_section_detail,
    get_learning_unit_content,
    get_module_detail,
    get_topic_content,
    get_topic_detail,
    list_course_sections,
    list_modules,
)

content_router = APIRouter(prefix="/api", tags=["Content"])


def _use_canonical_content_compat() -> bool:
    """Keep old frontend routes alive while sourcing rows from canonical tables."""
    return not settings.allow_legacy_topic_content_reads


def _legacy_content_gone() -> None:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=(
            "Legacy module/topic routes are retired. Use canonical content routes: "
            "/api/course-sections, /api/course-sections/{section_id}, "
            "and /api/learning-units/{learning_unit_id}/content."
        ),
    )


# ---------------------------------------------------------------------------
# GET /api/course-sections
# ---------------------------------------------------------------------------


@content_router.get(
    "/course-sections",
    response_model=list[CourseSectionListItem],
    summary="List canonical course sections with learning-unit counts",
)
async def api_list_course_sections(
    db: AsyncSession = Depends(get_async_db),
) -> list[CourseSectionListItem]:
    return await list_course_sections(db)


# ---------------------------------------------------------------------------
# GET /api/course-sections/{section_id}
# ---------------------------------------------------------------------------


@content_router.get(
    "/course-sections/{section_id}",
    response_model=CourseSectionDetailResponse,
    summary="Get a canonical course section with its ordered learning units",
)
async def api_get_course_section(
    section_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
) -> CourseSectionDetailResponse:
    result = await get_course_section_detail(db, section_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course section {section_id} not found.",
        )
    return result


# ---------------------------------------------------------------------------
# GET /api/learning-units/{learning_unit_id}/content
# ---------------------------------------------------------------------------


@content_router.get(
    "/learning-units/{learning_unit_id}/content",
    response_model=LearningUnitContentResponse,
    summary="Get canonical learning-unit content",
)
async def api_get_learning_unit_content(
    learning_unit_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
) -> LearningUnitContentResponse:
    result = await get_learning_unit_content(db, learning_unit_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learning unit {learning_unit_id} not found.",
        )
    return result


# ---------------------------------------------------------------------------
# Retired legacy route: GET /api/modules
# ---------------------------------------------------------------------------


@content_router.get(
    "/modules",
    response_model=list[ModuleListItem],
    summary="List all curriculum modules with topic counts",
)
async def api_list_modules(
) -> list[ModuleListItem]:
    _legacy_content_gone()


# ---------------------------------------------------------------------------
# Retired legacy route: GET /api/modules/{module_id}
# ---------------------------------------------------------------------------


@content_router.get(
    "/modules/{module_id}",
    response_model=ModuleDetailResponse,
    summary="Get a module with its ordered topic list",
)
async def api_get_module(
    module_id: uuid.UUID,
) -> ModuleDetailResponse:
    _legacy_content_gone()


# ---------------------------------------------------------------------------
# Retired legacy route: GET /api/topics/{topic_id}
# ---------------------------------------------------------------------------


@content_router.get(
    "/topics/{topic_id}",
    response_model=TopicDetailResponse,
    summary="Get topic detail with resolved prerequisite graph",
)
async def api_get_topic(
    topic_id: uuid.UUID,
) -> TopicDetailResponse:
    _legacy_content_gone()


# ---------------------------------------------------------------------------
# Retired legacy route: GET /api/topics/{topic_id}/content
# ---------------------------------------------------------------------------


@content_router.get(
    "/topics/{topic_id}/content",
    response_model=TopicContentResponse,
    summary="Get learning content (markdown + video) for a topic",
)
async def api_get_topic_content(
    topic_id: uuid.UUID,
) -> TopicContentResponse:
    _legacy_content_gone()


# POST /api/seed (dev only)
@content_router.post(
    "/seed",
    summary="[DEV] Load modules and topics from data/*.json",
    tags=["Development"],
)
async def api_seed_data(db: AsyncSession = Depends(get_async_db)):
    """Load modules and topics from JSON files into database."""
    if _use_canonical_content_compat():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Legacy module/topic seed API is disabled in canonical content mode.",
        )
    from sqlalchemy import text

    modules_file = MODULES_FILE
    topics_file = TOPICS_FILE

    if not modules_file.exists() or not topics_file.exists():
        raise HTTPException(status_code=400, detail="data/*.json files not found")

    with open(modules_file) as f:
        modules_data = json.load(f)
    with open(topics_file) as f:
        topics_data = json.load(f)

    from src.models.content import KnowledgeComponent, Module, Topic

    # Clear existing data
    await db.execute(text("DELETE FROM topics CASCADE"))
    await db.execute(text("DELETE FROM modules CASCADE"))
    await db.commit()

    slug_to_module_id = {}

    # Create modules
    for m in modules_data:
        module_id = uuid.uuid4()
        slug_to_module_id[m["slug"]] = module_id

        prereq_ids = None
        if m.get("prerequisite_module_slugs"):
            prereq_ids = [
                slug_to_module_id[s]
                for s in m["prerequisite_module_slugs"]
                if s in slug_to_module_id
            ]

        module = Module(
            id=module_id,
            name=m["name"],
            description=m.get("description"),
            order_index=m["order_index"],
            prerequisite_module_ids=prereq_ids,
        )
        db.add(module)

    await db.commit()

    slug_to_topic_id = {}

    # Create topics
    for t in topics_data:
        topic_id = uuid.uuid4()
        slug_to_topic_id[t["slug"]] = topic_id

        module_id = slug_to_module_id.get(t["module_slug"])
        if not module_id:
            continue

        topic = Topic(
            id=topic_id,
            module_id=module_id,
            name=t["name"],
            description=t.get("description"),
            order_index=t["order_index"],
            content_markdown=t.get("content_markdown"),
            video_url=t.get("video_url"),
            estimated_hours_beginner=t.get("estimated_hours_beginner"),
            estimated_hours_intermediate=t.get("estimated_hours_intermediate"),
            estimated_hours_review=t.get("estimated_hours_review"),
        )
        db.add(topic)

    await db.commit()

    # Create knowledge components
    for t in topics_data:
        topic_id = slug_to_topic_id.get(t["slug"])
        if not topic_id:
            continue

        kcs = t.get("knowledge_components", [])
        for kc in kcs:
            knowledge_component = KnowledgeComponent(
                id=uuid.uuid4(),
                topic_id=topic_id,
                name=kc["name"],
                description=kc.get("description"),
            )
            db.add(knowledge_component)

    await db.commit()

    return {"status": "ok", "message": "Data seeded successfully"}
