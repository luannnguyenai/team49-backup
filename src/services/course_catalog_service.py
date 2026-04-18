"""
services/course_catalog_service.py
----------------------------------
Shared catalog and overview queries for the course-first platform.
"""

from src.schemas.course import (
    CourseCatalogItem,
    CourseCatalogResponse,
    CourseOverviewContent,
    CourseOverviewResponse,
    StartLearningDecisionResponse,
)
from src.services.course_bootstrap_service import (
    get_bootstrap_course,
    get_bootstrap_overview,
    load_bootstrap_courses,
)


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
) -> CourseCatalogResponse:
    rows = load_bootstrap_courses()
    if not include_unavailable:
        rows = [row for row in rows if row["status"] == "ready"]
    if view == "recommended":
        rows = []

    items = [_to_catalog_item(row) for row in rows]
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
