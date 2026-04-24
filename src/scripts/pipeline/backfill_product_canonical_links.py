from __future__ import annotations

import argparse
import asyncio
import re
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import async_session
from src.models.canonical import CanonicalUnit
from src.models.course import Course

_LECTURE_RE = re.compile(r"(?:lecture|lec)[-_ ]?0*(\d+)", re.IGNORECASE)


def canonical_course_id_from_slug(slug: str) -> str | None:
    normalized = slug.strip().lower()
    if normalized == "cs224n":
        return "CS224n"
    if normalized == "cs231n":
        return "CS231n"
    return None


def _lecture_number(value: str | None) -> int | None:
    if not value:
        return None
    match = _LECTURE_RE.search(value)
    return int(match.group(1)) if match else None


def match_canonical_unit(product_unit, canonical_course_id: str, canonical_units: Iterable) -> str | None:
    product_lecture = _lecture_number(getattr(product_unit, "slug", None)) or _lecture_number(
        getattr(product_unit, "title", None)
    )
    if product_lecture is None:
        return None

    candidates = []
    for unit in canonical_units:
        if getattr(unit, "course_id", None) != canonical_course_id:
            continue
        canonical_lecture = _lecture_number(getattr(unit, "lecture_id", None)) or _lecture_number(
            getattr(unit, "unit_id", None)
        )
        if canonical_lecture == product_lecture:
            candidates.append(unit)

    if len(candidates) != 1:
        return None
    return candidates[0].unit_id


async def backfill_links(session: AsyncSession, *, dry_run: bool = True) -> dict[str, int]:
    courses = (
        (
            await session.execute(
                select(Course).options(selectinload(Course.learning_units)).order_by(Course.slug)
            )
        )
        .unique()
        .scalars()
        .all()
    )
    canonical_units = (await session.execute(select(CanonicalUnit))).scalars().all()

    updated_courses = 0
    updated_units = 0
    unmatched_units = 0

    for course in courses:
        canonical_course_id = canonical_course_id_from_slug(course.slug)
        if canonical_course_id and course.canonical_course_id != canonical_course_id:
            updated_courses += 1
            if not dry_run:
                course.canonical_course_id = canonical_course_id

        if not canonical_course_id:
            continue

        for unit in course.learning_units:
            canonical_unit_id = match_canonical_unit(unit, canonical_course_id, canonical_units)
            if canonical_unit_id is None:
                unmatched_units += 1
                continue
            if unit.canonical_unit_id != canonical_unit_id:
                updated_units += 1
                if not dry_run:
                    unit.canonical_unit_id = canonical_unit_id

    if not dry_run:
        await session.flush()

    return {
        "updated_courses": updated_courses,
        "updated_units": updated_units,
        "unmatched_units": unmatched_units,
    }


async def _run(*, dry_run: bool) -> dict[str, int]:
    async with async_session() as session:
        result = await backfill_links(session, dry_run=dry_run)
        if not dry_run:
            await session.commit()
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill product rows with canonical course/unit IDs.")
    parser.add_argument("--apply", action="store_true", help="Write updates. Omit for dry-run.")
    args = parser.parse_args()

    result = asyncio.run(_run(dry_run=not args.apply))
    print(result)


if __name__ == "__main__":
    main()
