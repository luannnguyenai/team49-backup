from __future__ import annotations

import re
from uuid import uuid4

from src.repositories.canonical_content_repo import CanonicalContentRepository
from src.schemas.agent import RetrievalTrace, UnitSearchRequest, UnitSearchResponse, UnitSearchResult
from src.services.agent_navigation_service import AgentNavigationService
from src.services.agent_query_normalizer import normalize_query


def _compact_text(value: str) -> str:
    return re.sub(r"[-_]+", "", value.lower())


def _compact_phrase(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _term_matches(term: str, text: str, compact_text: str) -> bool:
    if term in text:
        return True
    compact_term = _compact_text(term)
    return bool(compact_term and compact_term in compact_text)


def _coverage(terms: list[str], text: str, compact_text: str) -> float:
    if not terms:
        return 0.0
    matches = sum(1 for term in terms if _term_matches(term, text, compact_text))
    return matches / len(terms)


def _is_single_technical_query(query: str, terms: list[str]) -> bool:
    if len(terms) != 1:
        return False
    term = terms[0]
    raw_tokens = re.findall(r"[A-Za-z0-9_-]+", query)
    return len(term) >= 3 and (
        any(token.isupper() and len(token) >= 3 for token in raw_tokens)
        or any(char.isdigit() for char in term)
        or "-" in query
        or "_" in query
    )


def _overview_title_score(title_text: str) -> float:
    title = title_text.lower()
    markers = (
        "family",
        "overview",
        "introduction",
        "intro",
        "foundation",
        "foundations",
        "basics",
        "what ",
    )
    return 8.0 if any(marker in title for marker in markers) else 0.0


def _rerank_score(query: str, terms: list[str], *, title_text: str, body_text: str) -> float:
    title = title_text.lower()
    body = body_text.lower()
    compact_title = _compact_text(title)
    compact_body = _compact_text(body)
    phrase_query = _compact_phrase(query)
    phrase_title = _compact_phrase(title_text)
    phrase_body = _compact_phrase(body_text)

    title_coverage = _coverage(terms, title, compact_title)
    body_coverage = _coverage(terms, body, compact_body)
    score = title_coverage * 20.0 + body_coverage * 12.0

    if phrase_query and len(phrase_query) >= 3:
        if len(terms) > 1:
            title_phrase_match = phrase_query in phrase_title
            body_phrase_match = phrase_query in phrase_body
        else:
            compact_query = _compact_text(query)
            title_phrase_match = bool(compact_query and compact_query in compact_title)
            body_phrase_match = bool(compact_query and compact_query in compact_body)
        if title_phrase_match:
            score += 22.0
        elif body_phrase_match:
            score += 10.0
        if title_phrase_match or body_phrase_match:
            score += 20.0

    if _is_single_technical_query(query, terms):
        score += _overview_title_score(title_text)

    if len(terms) >= 2 and title_coverage < 0.35 and body_coverage < 0.5:
        score -= 10.0
    if title_coverage == 0.0 and body_coverage > 0.0:
        score -= 8.0

    return max(score, 0.0)


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
            score = _rerank_score(
                request.query,
                terms,
                title_text=title_haystack,
                body_text=body_haystack,
            )
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
            ranking_version="unit_title_rerank_v1",
            runtime_navigation_resolution=[
                self.navigation_service.to_trace(nav_by_id[result.canonical_unit_id])
                for result in results
                if result.canonical_unit_id in nav_by_id
            ],
            selected_unit_ids=[result.canonical_unit_id for result in results],
        )
        return UnitSearchResponse(results=results, trace=trace)
