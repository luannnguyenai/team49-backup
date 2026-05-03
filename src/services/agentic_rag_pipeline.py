from __future__ import annotations

import re
from typing import Any

from src.schemas.agent import RouteContext
from src.services.agent_graph_contracts import AgentSlots, ToolResult
from src.services.agentic_rag_contracts import AgenticRAGFinal, AgenticRAGObservation


class AgenticRAGPipeline:
    def __init__(self, router, tool_executor):
        self.router = router
        self.tool_executor = tool_executor

    async def run(
        self,
        *,
        message: str,
        intent: str,
        slots: AgentSlots,
        route_context: RouteContext | None,
        recent_messages: list[dict],
        allowed_course_ids: list[str],
    ) -> ToolResult:
        thought = self.router.rag_think(
            message=message,
            intent=intent,
            slots=slots,
            route_context=route_context,
            recent_messages=recent_messages,
        )
        tool_call = self.router.rag_act(
            message=message,
            thought=thought,
            slots=slots,
            route_context=route_context,
            recent_messages=recent_messages,
            observations=[],
        )
        tool_observation = await self.tool_executor.execute(
            tool_call,
            message=message,
            intent=intent,
            slots=slots,
            allowed_course_ids=allowed_course_ids,
        )
        observation = self.router.rag_observe(
            message=message,
            thought=thought,
            tool_call=tool_call,
            tool_observation=tool_observation,
            route_context=route_context,
            recent_messages=recent_messages,
        )
        observation = self._validated_observation(observation, tool_observation)
        final = self.router.rag_respond(
            message=message,
            thought=thought,
            observations=[observation.model_dump(mode="json")],
            route_context=route_context,
            recent_messages=recent_messages,
        )
        return self._result_from_final(final, observation)

    def _validated_observation(
        self,
        observation: Any,
        fallback_observation: AgenticRAGObservation,
    ) -> AgenticRAGObservation:
        if not isinstance(observation, AgenticRAGObservation):
            if isinstance(observation, dict):
                observation = AgenticRAGObservation.model_validate(observation)
            else:
                observation = AgenticRAGObservation.model_validate(observation.model_dump())
        # The retrieval tool result is authoritative. The observing model may judge
        # evidence quality, but it must not mutate citations/actions/trace returned
        # from database-backed tools.
        return fallback_observation.model_copy(
            update={
                "success": fallback_observation.success,
                "evidence_status": self._validated_evidence_status(
                    observation.evidence_status,
                    fallback_observation,
                ),
                "result": fallback_observation.result,
            }
        )

    def _validated_evidence_status(
        self,
        observed_status: str,
        fallback_observation: AgenticRAGObservation,
    ) -> str:
        if fallback_observation.result.citations:
            return fallback_observation.evidence_status
        if observed_status == "grounded":
            return "no_source"
        return observed_status

    def _result_from_final(
        self,
        final: Any,
        observation: AgenticRAGObservation,
    ) -> ToolResult:
        if not isinstance(final, AgenticRAGFinal):
            if isinstance(final, dict):
                final = AgenticRAGFinal.model_validate(final)
            else:
                final = AgenticRAGFinal(
                    answer_markdown=getattr(final, "answer_markdown"),
                    evidence_status=getattr(final, "evidence_status"),
                    evidence_sufficient=getattr(final, "evidence_sufficient", False),
                    clarification_question=getattr(final, "clarification_question", None),
                )
        result = observation.result
        answer_markdown = final.answer_markdown or final.clarification_question or result.answer_markdown
        answer_markdown = self._strip_hidden_stage_text(answer_markdown or "")
        if final.evidence_sufficient and result.citations:
            return result.model_copy(
                update={
                    "answer_markdown": answer_markdown,
                    "requires_evidence": False,
                    "metadata": {
                        **result.metadata,
                        "agentic_rag_evidence_status": final.evidence_status,
                    },
                }
            )
        if final.evidence_status == "no_source" and not result.citations:
            return result.model_copy(
                update={
                    "answer_markdown": answer_markdown,
                    "requires_evidence": True,
                    "metadata": {
                        **result.metadata,
                        "agentic_rag_evidence_status": "no_source",
                    },
                }
            )
        return result.model_copy(
            update={
                "answer_markdown": answer_markdown,
                "requires_evidence": False,
                "metadata": {
                    **result.metadata,
                    "agentic_rag_evidence_status": final.evidence_status,
                },
            }
        )

    @staticmethod
    def _strip_hidden_stage_text(markdown: str) -> str:
        value = markdown.strip()
        value = re.sub(r"(?is)hidden\s+thought\s*:.*?(final\s*:)", r"\1", value).strip()
        return re.sub(r"(?i)^final\s*:\s*", "", value).strip()
