"""
routers/content.py
------------------
Content management API:

    GET  /api/modules                        List all modules with topic counts
    GET  /api/modules/{module_id}            Module detail + topic list
    GET  /api/topics/{topic_id}              Topic detail + prerequisite graph
    GET  /api/topics/{topic_id}/content      Learning material (markdown + video)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.schemas.content import (
    ModuleDetailResponse,
    ModuleListItem,
    TopicContentResponse,
    TopicDetailResponse,
)
from src.services.content_service import (
    get_module_detail,
    get_topic_content,
    get_topic_detail,
    list_modules,
)

content_router = APIRouter(prefix="/api", tags=["Content"])


# ---------------------------------------------------------------------------
# GET /api/modules
# ---------------------------------------------------------------------------

@content_router.get(
    "/modules",
    response_model=list[ModuleListItem],
    summary="List all curriculum modules with topic counts",
)
async def api_list_modules(
    db: AsyncSession = Depends(get_async_db),
) -> list[ModuleListItem]:
    return await list_modules(db)


# ---------------------------------------------------------------------------
# GET /api/modules/{module_id}
# ---------------------------------------------------------------------------

@content_router.get(
    "/modules/{module_id}",
    response_model=ModuleDetailResponse,
    summary="Get a module with its ordered topic list",
)
async def api_get_module(
    module_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
) -> ModuleDetailResponse:
    result = await get_module_detail(db, module_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module {module_id} not found.",
        )
    return result


# ---------------------------------------------------------------------------
# GET /api/topics/{topic_id}
# ---------------------------------------------------------------------------

@content_router.get(
    "/topics/{topic_id}",
    response_model=TopicDetailResponse,
    summary="Get topic detail with resolved prerequisite graph",
)
async def api_get_topic(
    topic_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
) -> TopicDetailResponse:
    result = await get_topic_detail(db, topic_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic {topic_id} not found.",
        )
    return result


# ---------------------------------------------------------------------------
# GET /api/topics/{topic_id}/content
# ---------------------------------------------------------------------------

@content_router.get(
    "/topics/{topic_id}/content",
    response_model=TopicContentResponse,
    summary="Get learning content (markdown + video) for a topic",
)
async def api_get_topic_content(
    topic_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
) -> TopicContentResponse:
    result = await get_topic_content(db, topic_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic {topic_id} not found.",
        )
    return result
