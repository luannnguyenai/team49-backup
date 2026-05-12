from __future__ import annotations

import re
from uuid import uuid4

from src.repositories.canonical_content_repo import CanonicalContentRepository
from src.schemas.agent import (
    RetrievalTrace,
    UnitSearchRequest,
    UnitSearchResponse,
    UnitSearchResult,
)
from src.services.agent_navigation_service import AgentNavigationService
from src.services.agent_query_normalizer import normalize_query


def _compact_text(value: str) -> str:
    return re.sub(r"[-_]+", "", value.lower())


def _term_matches(term: str, text: str, compact_text: str) -> bool:
    if term in text:
        return True
    compact_term = _compact_text(term)
    return bool(compact_term and compact_term in compact_text)


class AgentUnitSearchService:
    def __init__(
        self,
        repo: CanonicalContentRepository,
        navigation_service: AgentNavigationService | None = None,
    ):
        self.repo = repo
        self.navigation_service = navigation_service or AgentNavigationService(repo)

    async def search(
        self,
        request: UnitSearchRequest,
        allowed_course_ids: list[str],
    ) -> UnitSearchResponse:
        course_ids = request.course_ids or allowed_course_ids
        scoped_courses = [course_id for course_id in course_ids if course_id in allowed_course_ids]
        normalized, terms, expansions = normalize_query(request.query)
        units = await self.repo.search_canonical_units(
            terms,
            scoped_courses,
            limit=max(request.limit * 4, request.limit),
            title_only=True,
        )
        nav_by_id = await self.navigation_service.resolve_many([unit.unit_id for unit in units])
        scored = []
        for unit in units:
            title_haystack = " ".join(
                [
                    unit.unit_name or "",
                    unit.lecture_title or "",
                ]
            ).lower()
            body_haystack = " ".join(
                [
                    unit.summary or "",
                    unit.description or "",
                ]
            ).lower()
            compact_title = _compact_text(title_haystack)
            compact_body = _compact_text(body_haystack)
            title_score = sum(
                1 for term in terms if _term_matches(term, title_haystack, compact_title)
            )
            body_score = sum(
                1 for term in terms if _term_matches(term, body_haystack, compact_body)
            )
            score = float(title_score * 3 + body_score)
            nav = nav_by_id.get(unit.unit_id)
            scored.append(
                UnitSearchResult(
                    canonical_unit_id=unit.unit_id,
                    learning_unit_id=nav.learning_unit_id if nav else None,
                    course_id=unit.course_id,
                    course_slug=nav.course_slug if nav else None,
                    lecture_id=unit.lecture_id,
                    lecture_title=unit.lecture_title,
                    unit_name=unit.unit_name,
                    summary=unit.summary,
                    learn_href=nav.learn_href if nav else None,
                    score=score,
                    quiz_available=bool(getattr(unit, "has_quiz_items", False)),
                )
            )

        results = sorted(scored, key=lambda item: item.score, reverse=True)[: request.limit]
        trace = RetrievalTrace(
            trace_id=str(uuid4()),
            intent=request.intent,
            raw_query=request.query,
            normalized_query=normalized,
            resolved_scope=request.scope or "current_path",
            candidate_courses=scoped_courses,
            query_expansions=expansions,
            applied_filters=[
                "hidden_logistics_excluded",
                "allowed_course_intersection",
                "unit_title_only",
            ],
            ranking_version="unit_title_search_v1",
            runtime_navigation_resolution=[
                self.navigation_service.to_trace(nav_by_id[result.canonical_unit_id])
                for result in results
                if result.canonical_unit_id in nav_by_id
            ],
            selected_unit_ids=[result.canonical_unit_id for result in results],
        )
        return UnitSearchResponse(results=results, trace=trace)
