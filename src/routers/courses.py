"""
routers/courses.py
------------------
Shared course-platform routes for catalog, overview, entry decisions,
and canonical learning-unit payloads.

US2 changes: optional auth on catalog and start endpoints to support
auth-gated decision logic and recommendation-aware catalog.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.dependencies.auth import get_current_onboarded_user
from src.models.user import User
from src.schemas.course import (
    CourseCatalogResponse,
    CourseOverviewResponse,
    LearningUnitResponse,
    StartLearningDecisionResponse,
)
from src.services.course_catalog_service import get_course_overview, list_course_catalog
from src.services.course_entry_service import assert_learning_access, get_start_learning_decision
from src.services.learning_unit_service import get_learning_unit_payload, list_course_units

courses_router = APIRouter(prefix="/api/courses", tags=["Courses"])

# ---------------------------------------------------------------------------
# Optional auth: returns User | None without raising 401
# ---------------------------------------------------------------------------

_optional_bearer = HTTPBearer(auto_error=False)


async def _get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
):
    """
    Resolve the current user from an optional Bearer token.
    Returns None if no token is provided or if the token is invalid.
    """
    if credentials is None:
        return None

    try:
        from src.services.auth_service import decode_token, get_user_by_id
        from src.database import async_session_factory

        payload = decode_token(credentials.credentials)
        if payload.type != "access":
            return None

        import uuid

        user_id = uuid.UUID(payload.sub)

        async with async_session_factory() as db:
            user = await get_user_by_id(db, user_id)
            return user
    except Exception:
        return None


# ---------------------------------------------------------------------------
# GET /api/courses — public catalog with optional recommendation awareness
# ---------------------------------------------------------------------------


@courses_router.get("", response_model=CourseCatalogResponse)
async def api_list_courses(
    view: str = Query(default="all", pattern="^(all|recommended)$"),
    include_unavailable: bool = True,
    user=Depends(_get_optional_user),
) -> CourseCatalogResponse:
    return await list_course_catalog(
        view=view,
        include_unavailable=include_unavailable,
        user=user,
    )


# ---------------------------------------------------------------------------
# GET /api/courses/{slug}/overview — public overview (unchanged)
# ---------------------------------------------------------------------------


@courses_router.get("/{course_slug}/overview", response_model=CourseOverviewResponse)
async def api_get_course_overview(course_slug: str) -> CourseOverviewResponse:
    result = await get_course_overview(course_slug)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{course_slug}' not found.",
        )
    return result


# ---------------------------------------------------------------------------
# POST /api/courses/{slug}/start — auth-aware start decision
# ---------------------------------------------------------------------------


@courses_router.post("/{course_slug}/start", response_model=StartLearningDecisionResponse)
async def api_start_course(
    course_slug: str,
    user=Depends(_get_optional_user),
) -> StartLearningDecisionResponse:
    result = await get_start_learning_decision(course_slug, user=user)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{course_slug}' not found.",
        )
    return result


# ---------------------------------------------------------------------------
# GET /api/courses/{slug}/units — list all units for a course
# ---------------------------------------------------------------------------


@courses_router.get("/{course_slug}/units")
async def api_list_course_units(course_slug: str) -> dict:
    units = list_course_units(course_slug)
    return {
        "units": [
            {
                "slug": u["slug"],
                "title": u["title"],
                "status": u["status"],
                "unit_type": u["unit_type"],
                "order_index": u["order_index"],
            }
            for u in units
        ]
    }


# ---------------------------------------------------------------------------
# GET /api/courses/{slug}/units/{unit_slug} — learning unit payload
# ---------------------------------------------------------------------------


@courses_router.get(
    "/{course_slug}/units/{unit_slug}",
    response_model=LearningUnitResponse,
)
async def api_get_learning_unit(
    course_slug: str,
    unit_slug: str,
    current_user: User = Depends(get_current_onboarded_user),
) -> LearningUnitResponse:
    await assert_learning_access(course_slug, current_user)
    result = await get_learning_unit_payload(course_slug, unit_slug)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learning unit '{unit_slug}' not found for course '{course_slug}'.",
        )
    return result
