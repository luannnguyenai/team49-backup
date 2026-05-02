from __future__ import annotations

from dataclasses import dataclass

from src.schemas.agent import AgentFallback, AgentWarning
from src.services.agent_graph_contracts import AgentSlots, ToolResult
from src.services.agentic_rag_contracts import (
    AgenticRAGEvidenceStatus,
    AgenticRAGObservation,
    AgenticRAGToolCall,
)


@dataclass(frozen=True)
class AgentRAGToolSpec:
    name: str
    description: str
    requires_evidence: bool
    timeout_ms: int = 15_000


class AgentRAGToolRegistry:
    def __init__(self):
        self._tools = {
            "search_current_path_units": AgentRAGToolSpec(
                name="search_current_path_units",
                description="Search title-level course units in the learner's current path first.",
                requires_evidence=True,
            ),
            "get_unit_summary": AgentRAGToolSpec(
                name="get_unit_summary",
                description="Retrieve normalized summary evidence for a selected learning unit.",
                requires_evidence=True,
            ),
            "ask_clarification": AgentRAGToolSpec(
                name="ask_clarification",
                description="Ask the learner for missing or ambiguous retrieval context.",
                requires_evidence=False,
            ),
            "offer_scope_expansion": AgentRAGToolSpec(
                name="offer_scope_expansion",
                description="Ask approval before searching outside the learner's current path.",
                requires_evidence=False,
            ),
            "search_allowed_other_paths": AgentRAGToolSpec(
                name="search_allowed_other_paths",
                description="Search other allowed paths only after explicit expansion approval.",
                requires_evidence=True,
            ),
        }

    def resolve(self, name: str) -> AgentRAGToolSpec | None:
        return self._tools.get(name)

    def list_specs(self) -> list[AgentRAGToolSpec]:
        return list(self._tools.values())


class AgenticRAGToolExecutor:
    def __init__(self, tools, registry: AgentRAGToolRegistry | None = None):
        self.tools = tools
        self.registry = registry or AgentRAGToolRegistry()

    async def execute(
        self,
        tool_call: AgenticRAGToolCall,
        *,
        message: str,
        intent: str,
        slots: AgentSlots,
        allowed_course_ids: list[str],
    ) -> AgenticRAGObservation:
        spec = self.registry.resolve(tool_call.tool)
        if spec is None:
            result = await self.tools.clarify(
                message,
                reason="The agent selected an unsupported retrieval tool.",
            )
            return self._observation("ask_clarification", result, "needs_clarification")

        if tool_call.tool == "ask_clarification":
            question = str(tool_call.arguments.get("question") or "").strip()
            result = await self.tools.clarify(
                message,
                reason=question or "Could you clarify what you want me to search for?",
            )
            return self._observation(tool_call.tool, result, "needs_clarification")

        if tool_call.tool == "offer_scope_expansion":
            topic = str(tool_call.arguments.get("topic") or slots.raw_topic or message).strip()
            answer = (
                f"I could not find a direct match for {topic} in your current path. "
                "Do you want me to expand the search to other allowed paths?"
            )
            result = ToolResult(
                kind="clarification",
                answer_markdown=answer,
                warning=AgentWarning(
                    type="ambiguous_target",
                    message="Current-path evidence was missing or weak; expansion requires confirmation.",
                ),
                fallback=AgentFallback(
                    reason="no_retrieval_result",
                    message="Current-path search returned no grounded result.",
                ),
                requires_evidence=False,
                metadata={
                    "scope_expansion_offered": True,
                    "raw_topic": topic,
                    "search_queries": [topic] if topic else [],
                },
            )
            return self._observation(tool_call.tool, result, "scope_expansion_required")

        if tool_call.tool == "search_allowed_other_paths":
            if not slots.scope_expansion_approved and slots.search_scope != "expanded_paths":
                return await self.execute(
                    AgenticRAGToolCall(
                        tool="offer_scope_expansion",
                        arguments={"topic": tool_call.arguments.get("query") or slots.raw_topic},
                        rationale="Expanded search requires user approval before execution.",
                    ),
                    message=message,
                    intent=intent,
                    slots=slots,
                    allowed_course_ids=allowed_course_ids,
                )
            search_slots = slots.model_copy(update={"search_scope": "expanded_paths"})
            return await self._search(tool_call, message, intent, search_slots, allowed_course_ids)

        if tool_call.tool in {"search_current_path_units", "get_unit_summary"}:
            search_slots = slots.model_copy(update={"search_scope": "current_path"})
            return await self._search(tool_call, message, intent, search_slots, allowed_course_ids)

        result = await self.tools.clarify(message, reason=f"Tool {spec.name} is not available yet.")
        return self._observation("ask_clarification", result, "needs_clarification")

    async def _search(
        self,
        tool_call: AgenticRAGToolCall,
        message: str,
        intent: str,
        slots: AgentSlots,
        allowed_course_ids: list[str],
    ) -> AgenticRAGObservation:
        query = str(tool_call.arguments.get("query") or "").strip()
        search_queries = [
            str(item).strip()
            for item in tool_call.arguments.get("search_queries", []) or []
            if str(item).strip()
        ]
        if query and query.casefold() not in {item.casefold() for item in search_queries}:
            search_queries.insert(0, query)
        if not search_queries:
            search_queries = slots.search_queries or [slots.raw_topic or message]
        search_slots = slots.model_copy(update={"search_queries": search_queries[:5]})
        if query:
            search_slots = search_slots.model_copy(update={"raw_topic": query})
        result = await self.tools.find_content(
            message,
            intent,
            search_slots,
            allowed_course_ids,
        )
        return self._observation(tool_call.tool, result, self._status_from_result(result))

    def _status_from_result(self, result: ToolResult) -> AgenticRAGEvidenceStatus:
        if result.metadata.get("too_many_results_offered"):
            return "too_many_results"
        if result.metadata.get("scope_expansion_offered"):
            return "scope_expansion_required"
        if result.kind == "clarification":
            return "needs_clarification"
        if result.citations and result.metadata.get("answer_confidence") == "partial":
            return "partial"
        if result.citations:
            return "grounded"
        if result.fallback or result.requires_evidence:
            return "no_source"
        return "partial"

    @staticmethod
    def _observation(
        tool: str,
        result: ToolResult,
        status: AgenticRAGEvidenceStatus,
    ) -> AgenticRAGObservation:
        return AgenticRAGObservation(
            tool=tool,
            success=not bool(result.fallback),
            evidence_status=status,
            result=result,
        )
