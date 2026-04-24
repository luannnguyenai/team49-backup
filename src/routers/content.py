"""
routers/content.py
------------------
Content management API:

    GET  /api/course-sections                        List course sections
    GET  /api/course-sections/{section_id}            Section detail + learning units
    GET  /api/learning-units/{learning_unit_id}/content  Learning-unit content
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.schemas.content import (
    CourseSectionDetailResponse,
    CourseSectionListItem,
    LearningUnitContentResponse,
)
from src.services.content_service import (
    get_course_section_detail,
    get_learning_unit_content,
    list_course_sections,
)

content_router = APIRouter(prefix="/api", tags=["Content"])


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
