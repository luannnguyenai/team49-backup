from __future__ import annotations

from dataclasses import dataclass

from src.repositories.canonical_content_repo import CanonicalContentRepository
from src.schemas.agent import RuntimeNavigationTrace


@dataclass(frozen=True)
class RuntimeNavigation:
    canonical_unit_id: str
    learning_unit_id: str | None
    course_id: str | None
    course_slug: str | None
    unit_slug: str | None
    learn_href: str | None
    source: str


class AgentNavigationService:
    def __init__(self, repo: CanonicalContentRepository):
        self.repo = repo

    async def resolve_many(self, canonical_unit_ids: list[str]) -> dict[str, RuntimeNavigation]:
        linked = await self.repo.get_learning_units_by_canonical_ids(canonical_unit_ids)
        resolved: dict[str, RuntimeNavigation] = {}
        for canonical_unit_id in canonical_unit_ids:
            row = linked.get(canonical_unit_id)
            if not row:
                resolved[canonical_unit_id] = RuntimeNavigation(
                    canonical_unit_id=canonical_unit_id,
                    learning_unit_id=None,
                    course_id=None,
                    course_slug=None,
                    unit_slug=None,
                    learn_href=None,
                    source="missing",
                )
                continue
            unit, course, _section = row
            resolved[canonical_unit_id] = RuntimeNavigation(
                canonical_unit_id=canonical_unit_id,
                learning_unit_id=str(unit.id),
                course_id=course.canonical_course_id,
                course_slug=course.slug,
                unit_slug=unit.slug,
                learn_href=f"/courses/{course.slug}/learn/{unit.slug}",
                source="product_learning_unit",
            )
        return resolved

    @staticmethod
    def to_trace(nav: RuntimeNavigation) -> RuntimeNavigationTrace:
        return RuntimeNavigationTrace(
            canonical_unit_id=nav.canonical_unit_id,
            source=nav.source,  # type: ignore[arg-type]
            learning_unit_id=nav.learning_unit_id,
            course_slug=nav.course_slug,
            unit_slug=nav.unit_slug,
            learn_href=nav.learn_href,
        )
