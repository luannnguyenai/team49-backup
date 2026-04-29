"""
services/course_catalog_service.py
----------------------------------
Shared catalog and overview queries for the course-first platform.

Extended for US2: recommendation-aware catalog responses.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.models.course import Course, CourseOverview, LearningProgressRecord, LearningProgressStatus, LearningUnit
from src.schemas.course import (
    CourseCatalogItem,
    CourseCatalogResponse,
    CourseOverviewContent,
    CourseOverviewResponse,
    StartLearningDecisionResponse,
)
from src.repositories.course_recommendation_repo import CourseRecommendationRepository
from src.repositories.goal_preference_repo import GoalPreferenceRepository
from src.services.course_bootstrap_service import (
    get_bootstrap_course,
    get_bootstrap_overview,
    load_bootstrap_courses,
)

if TYPE_CHECKING:
    from src.models.user import User


def _to_catalog_item(
    row: dict,
    *,
    is_recommended: bool = False,
    progress_percent: int | None = None,
) -> CourseCatalogItem:
    return CourseCatalogItem(
        id=row["id"],
        slug=row["slug"],
        title=row["title"],
        short_description=row["short_description"],
        status=row["status"],
        cover_image_url=row.get("cover_image_url"),
        hero_badge=row.get("hero_badge"),
        is_recommended=is_recommended,
        progress_percent=progress_percent,
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
    rows = await _list_catalog_from_db()
    if not rows:
        rows = load_bootstrap_courses()

    if not include_unavailable:
        rows = [row for row in rows if row["status"] == "ready"]

    progress_percents: dict[str, int] = {}
    if user is not None:
        progress_percents = await _get_course_progress_percents(
            user.id,
            [row["id"] for row in rows],
        )

    if view == "recommended":
        if user is None:
            # Contract: unauthenticated recommended view returns empty
            return CourseCatalogResponse(items=[])

        # Try to load recommendations from DB
        recommended_slugs = await _get_recommended_course_slugs(user.id)
        if recommended_slugs:
            # Return only recommended courses, marked as recommended
            items = [
                _to_catalog_item(
                    row,
                    is_recommended=True,
                    progress_percent=progress_percents.get(row["id"]),
                )
                for row in rows
                if row["slug"] in recommended_slugs
            ]
            return CourseCatalogResponse(items=items)

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
                progress_percent=progress_percents.get(row["id"]),
            )
        )

    return CourseCatalogResponse(items=items)


async def get_course_overview(course_slug: str) -> CourseOverviewResponse | None:
    db_row = await _get_course_overview_from_db(course_slug)
    if db_row is not None:
        return CourseOverviewResponse(
            course=CourseCatalogItem(**db_row["course"]),
            overview=CourseOverviewContent(**db_row["overview"]),
            entry=StartLearningDecisionResponse(
                decision="redirect",
                target=(
                    f"/courses/{course_slug}/start"
                    if db_row["course"]["status"] == "ready"
                    else f"/courses/{course_slug}"
                ),
                reason=(
                    "learning_ready"
                    if db_row["course"]["status"] == "ready"
                    else "course_unavailable"
                ),
            ),
        )

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
            recommendation_repo = CourseRecommendationRepository(db)
            recommended_slugs = await recommendation_repo.get_recommended_slugs_for_user(user_id)
            if recommended_slugs:
                return recommended_slugs

            goal_repo = GoalPreferenceRepository(db)
            goal = await goal_repo.get_by_user_id(user_id)
            selected_course_ids = list(goal.selected_course_ids or []) if goal is not None else []
            if not selected_course_ids:
                return set()

            return await recommendation_repo.get_slugs_by_course_ids(selected_course_ids)
    except Exception:
        return set()


async def _get_course_progress_percents(
    user_id: uuid.UUID,
    course_ids: list[str],
) -> dict[str, int]:
    if not course_ids:
        return {}

    try:
        course_uuid_ids = [uuid.UUID(course_id) for course_id in course_ids]
    except (TypeError, ValueError):
        return {}

    try:
        from src.database import async_session_factory

        async with async_session_factory() as db:
            total_result = await db.execute(
                select(LearningUnit.course_id, func.count(LearningUnit.id))
                .where(LearningUnit.course_id.in_(course_uuid_ids))
                .group_by(LearningUnit.course_id)
            )
            totals = {str(course_id): total_units for course_id, total_units in total_result.all()}

            completed_result = await db.execute(
                select(
                    LearningProgressRecord.course_id,
                    func.count(LearningProgressRecord.learning_unit_id),
                )
                .where(
                    LearningProgressRecord.user_id == user_id,
                    LearningProgressRecord.course_id.in_(course_uuid_ids),
                    LearningProgressRecord.status == LearningProgressStatus.completed,
                )
                .group_by(LearningProgressRecord.course_id)
            )
            completed = {
                str(course_id): completed_units
                for course_id, completed_units in completed_result.all()
            }

            progress_percents: dict[str, int] = {}
            for course_id in course_ids:
                total_units = totals.get(course_id)
                if total_units is None:
                    continue
                completed_units = completed.get(course_id, 0)
                progress_percents[course_id] = (
                    round((completed_units / total_units) * 100) if total_units else 0
                )
            return progress_percents
    except Exception:
        return {}


async def _list_catalog_from_db() -> list[dict]:
    try:
        from src.database import async_session_factory

        async with async_session_factory() as db:
            result = await db.execute(select(Course).order_by(Course.sort_order, Course.title))
            rows = result.scalars().all()
            if not rows:
                return []
            bootstrap_slugs = {row["slug"] for row in load_bootstrap_courses()}
            db_slugs = {row.slug for row in rows}
            if bootstrap_slugs and not bootstrap_slugs.issubset(db_slugs):
                return []
            return [
                {
                    "id": str(row.id),
                    "slug": row.slug,
                    "title": row.title,
                    "short_description": row.short_description,
                    "status": row.status.value,
                    "cover_image_url": row.cover_image_url,
                    "hero_badge": row.hero_badge,
                    "is_recommended": False,
                }
                for row in rows
            ]
    except Exception:
        return []


async def _get_course_overview_from_db(course_slug: str) -> dict | None:
    try:
        from src.database import async_session_factory

        async with async_session_factory() as db:
            result = await db.execute(
                select(Course)
                .options(selectinload(Course.overview))
                .where(Course.slug == course_slug)
            )
            course = result.scalar_one_or_none()
            if course is None or course.overview is None:
                return None

            overview: CourseOverview = course.overview
            return {
                "course": {
                    "id": str(course.id),
                    "slug": course.slug,
                    "title": course.title,
                    "short_description": course.short_description,
                    "status": course.status.value,
                    "cover_image_url": course.cover_image_url,
                    "hero_badge": course.hero_badge,
                    "is_recommended": False,
                },
                "overview": {
                    "headline": overview.headline,
                    "subheadline": overview.subheadline,
                    "summary_markdown": overview.summary_markdown,
                    "learning_outcomes": overview.learning_outcomes or [],
                    "target_audience": overview.target_audience,
                    "prerequisites_summary": overview.prerequisites_summary,
                    "estimated_duration_text": overview.estimated_duration_text,
                    "structure_snapshot": overview.structure_snapshot,
                    "cta_label": overview.cta_label,
                },
            }
    except Exception:
        return None
