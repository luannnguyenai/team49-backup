from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.models.course import (
    Course,
    CourseStatus,
    CourseVisibility,
    LearnerAssessmentProfile,
)
from src.models.user import User
from src.repositories.course_recommendation_repo import CourseRecommendationRepository
from src.services.course_bootstrap_service import get_bootstrap_course

test_support_router = APIRouter(prefix="/api/test-support", tags=["Test Support"])


class SeedCourseRecommendationsRequest(BaseModel):
    course_slugs: list[str] = Field(default_factory=list)


class SeedCourseRecommendationsResponse(BaseModel):
    status: str
    course_slugs: list[str]


def _require_debug_mode() -> None:
    if not settings.debug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


async def _ensure_bootstrap_course_rows(
    db: AsyncSession,
    course_slugs: list[str],
) -> list[Course]:
    if not course_slugs:
        return []

    existing_rows = await db.execute(select(Course).where(Course.slug.in_(course_slugs)))
    course_by_slug = {course.slug: course for course in existing_rows.scalars().all()}

    for slug in course_slugs:
        if slug in course_by_slug:
            continue

        bootstrap_row = get_bootstrap_course(slug)
        if bootstrap_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bootstrap course '{slug}' not found.",
            )

        course = Course(
            slug=bootstrap_row["slug"],
            title=bootstrap_row["title"],
            short_description=bootstrap_row["short_description"],
            status=CourseStatus(bootstrap_row["status"]),
            visibility=CourseVisibility(bootstrap_row.get("visibility", "public")),
            cover_image_url=bootstrap_row.get("cover_image_url"),
            hero_badge=bootstrap_row.get("hero_badge"),
            primary_subject=bootstrap_row.get("primary_subject"),
            sort_order=bootstrap_row.get("sort_order", 0),
        )
        db.add(course)
        await db.flush()
        course_by_slug[slug] = course

    return [course_by_slug[slug] for slug in course_slugs]


async def _upsert_assessment_profile(
    db: AsyncSession,
    user: User,
    *,
    recommendation_ready: bool,
) -> None:
    result = await db.execute(
        select(LearnerAssessmentProfile).where(LearnerAssessmentProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = LearnerAssessmentProfile(
            user_id=user.id,
            is_onboarded=user.is_onboarded,
        )
        db.add(profile)

    profile.is_onboarded = user.is_onboarded
    profile.recommendation_ready = recommendation_ready
    profile.skill_test_completed_at = datetime.now(UTC) if recommendation_ready else None


@test_support_router.post(
    "/course-recommendations",
    response_model=SeedCourseRecommendationsResponse,
)
async def api_seed_course_recommendations(
    body: SeedCourseRecommendationsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> SeedCourseRecommendationsResponse:
    _require_debug_mode()

    courses = await _ensure_bootstrap_course_rows(db, body.course_slugs)

    recommendation_repo = CourseRecommendationRepository(db)
    await recommendation_repo.delete_for_user(user.id)

    for rank, course in enumerate(courses, start=1):
        await recommendation_repo.create(
            user_id=user.id,
            course_id=course.id,
            rank=rank,
            reason_summary="Seeded for e2e verification.",
        )

    await _upsert_assessment_profile(
        db,
        user,
        recommendation_ready=bool(body.course_slugs),
    )
    await db.commit()

    return SeedCourseRecommendationsResponse(
        status="ok",
        course_slugs=body.course_slugs,
    )
