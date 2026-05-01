from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.schemas.agent import (
    AgentAction,
    AgentCitation,
    AgentFallback,
    AgentWarning,
    PathRequirementsRequest,
    UnitSearchRequest,
)
from src.services.agent_evidence_quality import AgentEvidenceQualityService
from src.services.agent_graph_contracts import AgentSlots, ToolResult
from src.services.agent_search_scope_service import AgentSearchScopeService


class AgentToolNodes:
    TOO_MANY_RESULTS_THRESHOLD = 20

    def __init__(self, search_service, requirement_service):
        self.search_service = search_service
        self.requirement_service = requirement_service
        self.scope_service = AgentSearchScopeService()
        self.evidence_quality = AgentEvidenceQualityService()

    async def clarify(self, message: str, reason: str = "ambiguous_target") -> ToolResult:
        clarification = "Could you clarify the course, unit, or learning goal you want help with?"
        answer_markdown = clarification if reason == "ambiguous_target" else reason
        return ToolResult(
            kind="clarification",
            answer_markdown=answer_markdown,
            warning=AgentWarning(type="ambiguous_target", message=answer_markdown),
            requires_evidence=False,
        )

    async def assistant_help(self, answer_markdown: str) -> ToolResult:
        return ToolResult(
            kind="clarification",
            answer_markdown=answer_markdown,
            requires_evidence=False,
        )

    async def find_content(
        self,
        message: str,
        intent: str,
        slots: AgentSlots,
        allowed_course_ids: list[str],
    ) -> ToolResult:
        course_ids = self.scope_service.course_ids_for_paths(
            slots.resolved_search_path_ids,
            allowed_course_ids,
        )
        search_queries = self._search_queries(message, slots)
        searches = [
            await self.search_service.search(
                UnitSearchRequest(
                    query=query,
                    scope="global_catalog" if slots.search_scope == "expanded_paths" else "current_path",
                    courseIds=course_ids,
                    intent=intent,
                    limit=20,
                ),
                allowed_course_ids=allowed_course_ids,
            )
            for query in search_queries
        ]
        search = searches[0]
        merged_results = {}
        for response in searches:
            for result in response.results:
                if result.score <= 0:
                    continue
                existing = merged_results.get(result.canonical_unit_id)
                if existing is None or result.score > existing.score:
                    merged_results[result.canonical_unit_id] = result
        all_results = sorted(
            merged_results.values(),
            key=lambda result: result.score,
            reverse=True,
        )
        verdict = self.evidence_quality.score(slots.raw_topic or search_queries[0], all_results)
        if (
            len(all_results) >= self.TOO_MANY_RESULTS_THRESHOLD
            and not slots.show_top_results_approved
            and not (verdict.label == "direct_match" and len(verdict.selected_unit_ids) < 3)
        ):
            raw_topic = slots.raw_topic or message
            trace = search.trace.model_copy(
                update={
                    "intent": intent,
                    "selected_path": slots.search_scope,
                    "candidate_courses": course_ids,
                    "selected_unit_ids": [],
                }
            )
            return ToolResult(
                kind="clarification",
                answer_markdown=(
                    f"I found {len(all_results)} results related to {raw_topic}. "
                    "Do you want to describe it more specifically, or should I show the top results?"
                ),
                warning=AgentWarning(
                    type="ambiguous_target",
                    message="Search returned many matching results; refinement is recommended.",
                ),
                requires_evidence=False,
                metadata={
                    "too_many_results_offered": True,
                    "result_count": len(all_results),
                    "top_results_allowed": True,
                },
                trace=trace,
            )
        if verdict.label == "weak_match" and slots.search_scope == "current_path" and len(allowed_course_ids) > len(course_ids):
            trace = search.trace.model_copy(
                update={
                    "intent": intent,
                    "selected_path": slots.search_scope,
                    "candidate_courses": course_ids,
                    "selected_unit_ids": [],
                }
            )
            return ToolResult(
                kind="clarification",
                answer_markdown=(
                    "I only found weakly related results in your current path. "
                    "Do you want me to expand the search to other allowed paths?"
                ),
                warning=AgentWarning(
                    type="ambiguous_target",
                    message="Current-path evidence was weak; expansion requires confirmation.",
                ),
                requires_evidence=False,
                metadata={
                    "scope_expansion_offered": True,
                    "evidence_verdict": verdict.label,
                    "evidence_reason_codes": verdict.reason_codes,
                },
                trace=trace,
            )
        selected_ids = set(verdict.selected_unit_ids)
        results = [
            result for result in all_results if result.canonical_unit_id in selected_ids
        ][:3] or all_results[:3]
        citations = [
            AgentCitation(
                canonical_unit_id=result.canonical_unit_id,
                course_id=result.course_id,
                lecture_id=result.lecture_id,
                lecture_title=result.lecture_title,
                unit_name=result.unit_name,
                learn_href=result.learn_href,
                quote=result.summary,
                source="summary",
            )
            for result in results
        ]
        actions = [
            AgentAction(
                type="open_unit",
                label=f"Open {result.unit_name}",
                learn_href=result.learn_href,
                canonical_unit_id=result.canonical_unit_id,
            )
            for result in results
            if result.learn_href
        ]
        trace = search.trace.model_copy(
            update={
                "intent": intent,
                "selected_path": slots.search_scope,
                "candidate_courses": course_ids,
                "selected_unit_ids": [citation.canonical_unit_id for citation in citations],
            }
        )
        if verdict.label == "weak_match" and not actions:
            return ToolResult(
                kind="find_content",
                answer_markdown="I could not find a direct grounded source for that request.",
                citations=[],
                actions=[],
                requires_evidence=True,
                metadata={
                    "evidence_verdict": verdict.label,
                    "evidence_reason_codes": verdict.reason_codes,
                },
                trace=trace,
            )
        if not citations and slots.search_scope == "current_path":
            return ToolResult(
                kind="clarification",
                answer_markdown=(
                    "I could not find this in your current path. "
                    "Do you want me to expand the search to other allowed paths?"
                ),
                warning=AgentWarning(
                    type="ambiguous_target",
                    message="No result was found in the current path; expansion requires confirmation.",
                ),
                fallback=AgentFallback(
                    reason="no_retrieval_result",
                    message="Current-path search returned no grounded result.",
                ),
                requires_evidence=False,
                metadata={"scope_expansion_offered": True},
                trace=trace,
            )
        if not citations:
            return ToolResult(
                kind="find_content",
                answer_markdown="I could not find a grounded source for that request.",
                citations=[],
                actions=[],
                fallback=AgentFallback(
                    reason="no_retrieval_result",
                    message="No matching learning unit was found in the selected search scope.",
                ),
                requires_evidence=True,
                metadata={
                    "evidence_verdict": verdict.label,
                    "evidence_reason_codes": verdict.reason_codes,
                },
                trace=trace,
            )
        if slots.search_scope == "expanded_paths" and citations:
            allowed_path_ids = slots.resolved_search_path_ids
            path_hits: dict[str, list[AgentCitation]] = {}
            for citation in citations:
                for path_id in self.scope_service.path_ids_for_course(
                    citation.course_id,
                    allowed_path_ids,
                ):
                    path_hits.setdefault(path_id, []).append(citation)
            if len(path_hits) > 1:
                non_current_path_hits = {
                    path_id: hits
                    for path_id, hits in path_hits.items()
                    if path_id not in set(slots.excluded_search_path_ids)
                }
                if non_current_path_hits:
                    path_hits = non_current_path_hits
                if len(path_hits) < 3:
                    allowed_course_ids_for_path = {
                        citation.course_id
                        for hits in path_hits.values()
                        for citation in hits
                    }
                    citations = [
                        citation
                        for citation in citations
                        if citation.course_id in allowed_course_ids_for_path
                    ]
                    actions = [
                        action
                        for action in actions
                        if action.canonical_unit_id
                        in {citation.canonical_unit_id for citation in citations}
                    ]
                else:
                    raw_topic = slots.raw_topic or message
                    actions = [
                        AgentAction(
                            type="choose_target_path",
                            label=f"{raw_topic} in {self.scope_service.path_label(path_id)}",
                            workflowId=path_id,
                        )
                        for path_id in path_hits
                    ]
                    return ToolResult(
                        kind="clarification",
                        answer_markdown=(
                            f"I found information related to {raw_topic} in multiple paths. "
                            "Which path do you want me to search more deeply?"
                        ),
                        actions=actions,
                        warning=AgentWarning(
                            type="ambiguous_target",
                            message="Expanded search found multiple matching paths.",
                        ),
                        requires_evidence=False,
                        metadata={
                            "path_selection_offered": True,
                            "path_options": list(path_hits.keys()),
                        },
                        trace=trace,
                    )
        disclosure = ""
        if slots.search_scope == "expanded_paths" and citations:
            disclosure = "\n\nI found this outside the original current-path search scope."
        answer_markdown = disclosure.strip() or None
        metadata = {
            "evidence_verdict": verdict.label,
            "evidence_reason_codes": verdict.reason_codes,
            "match_reasons": verdict.match_reasons,
        }
        if verdict.label in {"related_match", "weak_match"}:
            answer_markdown = answer_markdown or (
                f"I found related results for {slots.raw_topic or message}, but they may not be an exact match. "
                "If these are not what you need, describe the target more specifically."
            )
            metadata["answer_confidence"] = "partial"
        return ToolResult(
            kind="find_content",
            answer_markdown=answer_markdown,
            citations=citations,
            actions=actions,
            requires_evidence=verdict.requires_grounded_answer,
            metadata=metadata,
            trace=trace,
        )

    def _search_queries(self, message: str, slots: AgentSlots) -> list[str]:
        candidates = [query.strip() for query in slots.search_queries if query and query.strip()]
        if not candidates and slots.raw_topic and slots.raw_topic.strip():
            candidates.insert(0, slots.raw_topic.strip())
        if not candidates:
            candidates.append(message.strip())

        deduped: list[str] = []
        seen = set()
        for candidate in candidates:
            key = candidate.casefold()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(candidate)
        return deduped[:5]

    async def planner_decision(
        self,
        message: str,
        slots: AgentSlots,
        allowed_course_ids: list[str],
        user_id: str | None,
    ) -> ToolResult:
        requirements = await self.requirement_service.get_requirements(
            PathRequirementsRequest(targetPathKey=slots.target_path),
            allowed_course_ids=allowed_course_ids,
            user_id=user_id,
        )
        citations = [
            AgentCitation(
                canonical_unit_id=unit.canonical_unit_id,
                course_id=unit.course_id,
                unit_name=unit.unit_name,
                learn_href=unit.learn_href,
                source="planner",
            )
            for unit in requirements.required_units[:5]
        ]
        return ToolResult(
            kind="planner_decision",
            answer_markdown="I checked the prerequisite graph for that path.",
            citations=citations,
            requires_evidence=True,
        )

    async def assessment_proposal(self, slots: AgentSlots) -> ToolResult:
        expires_at = datetime.now(UTC) + timedelta(minutes=30)
        return ToolResult(
            kind="assessment_proposal",
            answer_markdown="I can prepare an assessment after you confirm.",
            actions=[
                AgentAction(
                    type="start_assessment_workflow",
                    label="Prepare assessment proposal",
                    actionId=f"act_{uuid4()}",
                    status="awaiting_confirmation",
                    expiresAt=expires_at,
                    canonical_unit_ids=slots.canonical_unit_ids,
                    eligible=True,
                )
            ],
        )

    async def replan_proposal(self) -> ToolResult:
        expires_at = datetime.now(UTC) + timedelta(minutes=30)
        return ToolResult(
            kind="replan_proposal",
            answer_markdown="I can propose a replan after you confirm.",
            actions=[
                AgentAction(
                    type="request_replan",
                    label="Confirm replan",
                    actionId=f"act_{uuid4()}",
                    status="awaiting_confirmation",
                    expiresAt=expires_at,
                    eligible=True,
                )
            ],
        )

    async def path_switch_proposal(self, slots: AgentSlots) -> ToolResult:
        expires_at = datetime.now(UTC) + timedelta(minutes=30)
        return ToolResult(
            kind="path_switch_proposal",
            answer_markdown="I can switch your active learning path after you confirm.",
            actions=[
                AgentAction(
                    type="request_path_switch",
                    label="Confirm path switch",
                    actionId=f"act_{uuid4()}",
                    status="awaiting_confirmation",
                    expiresAt=expires_at,
                    eligible=True,
                )
            ],
        )
