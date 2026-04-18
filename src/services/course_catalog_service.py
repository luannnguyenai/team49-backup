"""
services/course_catalog_service.py
----------------------------------
Shared catalog and overview queries for the course-first platform.

Extended for US2: recommendation-aware catalog responses.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from src.schemas.course import (
    CourseCatalogItem,
    CourseCatalogResponse,
    CourseOverviewContent,
    CourseOverviewResponse,
    StartLearningDecisionResponse,
)
from src.repositories.course_recommendation_repo import CourseRecommendationRepository
from src.services.course_bootstrap_service import (
    get_bootstrap_course,
    get_bootstrap_overview,
    load_bootstrap_courses,
)

if TYPE_CHECKING:
    from src.models.user import User


def _to_catalog_item(row: dict, *, is_recommended: bool = False) -> CourseCatalogItem:
    return CourseCatalogItem(
        id=row["id"],
        slug=row["slug"],
        title=row["title"],
        short_description=row["short_description"],
        status=row["status"],
        cover_image_url=row.get("cover_image_url"),
        hero_badge=row.get("hero_badge"),
        is_recommended=is_recommended,
    )


async def list_course_catalog(
    *,
    view: str = "all",
    include_unavailable: bool = True,
    user: User | None = None,
) -> CourseCatalogResponse:
    """
    Return the course catalog, optionally filtered by recommendation status.

    Parameters
    ----------
    view : str
        'all' for full catalog, 'recommended' for personalized view.
    include_unavailable : bool
        Whether to include non-ready courses.
    user : User | None
        The authenticated user. Required for 'recommended' view.
    """
    rows = load_bootstrap_courses()

    if not include_unavailable:
        rows = [row for row in rows if row["status"] == "ready"]

    if view == "recommended":
        if user is None:
            # Contract: unauthenticated recommended view returns empty
            return CourseCatalogResponse(items=[])

        # Try to load recommendations from DB
        recommended_slugs = await _get_recommended_course_slugs(user.id)
        if recommended_slugs:
            # Return only recommended courses, marked as recommended
            items = [
                _to_catalog_item(row, is_recommended=True)
                for row in rows
                if row["slug"] in recommended_slugs
            ]
            return CourseCatalogResponse(items=items)
        else:
            # No recommendations yet — return empty list
            # (frontend should fall back to all-courses tab)
            return CourseCatalogResponse(items=[])

    # Default: all courses
    items = []
    recommended_slugs: set[str] = set()
    if user is not None:
        recommended_slugs = await _get_recommended_course_slugs(user.id)

    for row in rows:
        items.append(
            _to_catalog_item(
                row,
                is_recommended=row["slug"] in recommended_slugs,
            )
        )

    return CourseCatalogResponse(items=items)


async def get_course_overview(course_slug: str) -> CourseOverviewResponse | None:
    course_row = get_bootstrap_course(course_slug)
    overview_row = get_bootstrap_overview(course_slug)
    if course_row is None or overview_row is None:
        return None

    entry_reason = "learning_ready" if course_row["status"] == "ready" else "course_unavailable"
    entry_target = (
        f"/courses/{course_slug}/start"
        if course_row["status"] == "ready"
        else f"/courses/{course_slug}"
    )

    return CourseOverviewResponse(
        course=_to_catalog_item(course_row),
        overview=CourseOverviewContent(
            headline=overview_row["headline"],
            subheadline=overview_row.get("subheadline"),
            summary_markdown=overview_row["summary_markdown"],
            learning_outcomes=overview_row.get("learning_outcomes", []),
            target_audience=overview_row.get("target_audience"),
            prerequisites_summary=overview_row.get("prerequisites_summary"),
            estimated_duration_text=overview_row.get("estimated_duration_text"),
            structure_snapshot={"summary": overview_row.get("structure_snapshot")},
            cta_label=overview_row.get("cta_label"),
        ),
        entry=StartLearningDecisionResponse(
            decision="redirect",
            target=entry_target,
            reason=entry_reason,
        ),
    )


async def _get_recommended_course_slugs(user_id: uuid.UUID) -> set[str]:
    """
    Query the CourseRecommendation table for this user's recommended courses.

    Falls back to empty set when the database is not available (bootstrap mode).
    """
    try:
        from src.database import async_session_factory

        async with async_session_factory() as db:
            repo = CourseRecommendationRepository(db)
            return await repo.get_recommended_slugs_for_user(user_id)
    except Exception:
        return set()
