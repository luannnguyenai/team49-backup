"""
routers/courses.py
------------------
Shared course-platform routes for catalog, overview, entry decisions,
and canonical learning-unit payloads.
"""

from fastapi import APIRouter, HTTPException, Query, status

from src.schemas.course import (
    CourseCatalogResponse,
    CourseOverviewResponse,
    LearningUnitResponse,
    StartLearningDecisionResponse,
)
from src.services.course_catalog_service import get_course_overview, list_course_catalog
from src.services.course_entry_service import get_start_learning_decision
from src.services.learning_unit_service import get_learning_unit_payload

courses_router = APIRouter(prefix="/api/courses", tags=["Courses"])


@courses_router.get("", response_model=CourseCatalogResponse)
async def api_list_courses(
    view: str = Query(default="all", pattern="^(all|recommended)$"),
    include_unavailable: bool = True,
) -> CourseCatalogResponse:
    return await list_course_catalog(view=view, include_unavailable=include_unavailable)


@courses_router.get("/{course_slug}/overview", response_model=CourseOverviewResponse)
async def api_get_course_overview(course_slug: str) -> CourseOverviewResponse:
    result = await get_course_overview(course_slug)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{course_slug}' not found.",
        )
    return result


@courses_router.post("/{course_slug}/start", response_model=StartLearningDecisionResponse)
async def api_start_course(course_slug: str) -> StartLearningDecisionResponse:
    result = await get_start_learning_decision(course_slug)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{course_slug}' not found.",
        )
    return result


@courses_router.get(
    "/{course_slug}/units/{unit_slug}",
    response_model=LearningUnitResponse,
)
async def api_get_learning_unit(course_slug: str, unit_slug: str) -> LearningUnitResponse:
    result = await get_learning_unit_payload(course_slug, unit_slug)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learning unit '{unit_slug}' not found for course '{course_slug}'.",
        )
    return result
