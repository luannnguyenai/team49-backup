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
from src.services.agent_graph_contracts import AgentSlots, ToolResult
from src.services.agent_search_scope_service import AgentSearchScopeService


class AgentToolNodes:
    def __init__(self, search_service, requirement_service):
        self.search_service = search_service
        self.requirement_service = requirement_service
        self.scope_service = AgentSearchScopeService()

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
        search = await self.search_service.search(
            UnitSearchRequest(
                query=slots.raw_topic or message,
                scope="current_path",
                courseIds=course_ids,
                intent=intent,
                limit=5,
            ),
            allowed_course_ids=allowed_course_ids,
        )
        results = [result for result in search.results if result.score > 0][:3]
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
        return ToolResult(
            kind="find_content",
            answer_markdown=disclosure.strip() or None,
            citations=citations,
            actions=actions,
            requires_evidence=True,
            trace=trace,
        )

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
