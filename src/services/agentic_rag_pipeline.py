from __future__ import annotations

import json
import re
from collections.abc import AsyncGenerator
from typing import Any

from src.schemas.agent import RouteContext
from src.services.agent_graph_contracts import AgentRouterUnavailableError, AgentSlots, ToolResult
from src.services.agentic_rag_contracts import AgenticRAGFinal, AgenticRAGObservation


class AgenticRAGPipeline:
    def __init__(self, router, tool_executor, response_router=None):
        self.router = router
        self.tool_executor = tool_executor
        self.response_router = response_router or router

    async def run(
        self,
        *,
        message: str,
        intent: str,
        slots: AgentSlots,
        route_context: RouteContext | None,
        recent_messages: list[dict],
        allowed_course_ids: list[str],
        current_path_course_ids: list[str] | None = None,
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
            current_path_course_ids=current_path_course_ids,
            route_context=route_context,
        )
        try:
            observation = self.router.rag_observe(
                message=message,
                thought=thought,
                tool_call=tool_call,
                tool_observation=tool_observation,
                route_context=route_context,
                recent_messages=recent_messages,
            )
        except AgentRouterUnavailableError:
            observation = tool_observation
        observation = self._validated_observation(observation, tool_observation)
        final = self.response_router.rag_respond(
            message=message,
            thought=thought,
            observations=[observation.model_dump(mode="json")],
            route_context=route_context,
            recent_messages=recent_messages,
        )
        return self._result_from_final(final, observation)

    async def run_stream(
        self,
        *,
        message: str,
        intent: str,
        slots: AgentSlots,
        route_context: RouteContext | None,
        recent_messages: list[dict],
        allowed_course_ids: list[str],
        current_path_course_ids: list[str] | None = None,
    ) -> AsyncGenerator[str, None]:
        yield json.dumps({"status": "Analyzing your question"}) + "\n"

        thought = self.router.rag_think(
            message=message,
            intent=intent,
            slots=slots,
            route_context=route_context,
            recent_messages=recent_messages,
        )
        yield json.dumps({
            "thought": {
                "user_goal": thought.user_goal,
                "active_topic": thought.active_topic,
                "evidence_need": thought.evidence_need,
                "tool_plan": thought.tool_plan,
            },
        }) + "\n"

        yield json.dumps({"status": "Searching course content"}) + "\n"
        tool_call = self.router.rag_act(
            message=message,
            thought=thought,
            slots=slots,
            route_context=route_context,
            recent_messages=recent_messages,
            observations=[],
        )

        yield json.dumps({"status": "Reading sources"}) + "\n"
        tool_observation = await self.tool_executor.execute(
            tool_call,
            message=message,
            intent=intent,
            slots=slots,
            allowed_course_ids=allowed_course_ids,
            current_path_course_ids=current_path_course_ids,
            route_context=route_context,
        )
        try:
            observation = self.router.rag_observe(
                message=message,
                thought=thought,
                tool_call=tool_call,
                tool_observation=tool_observation,
                route_context=route_context,
                recent_messages=recent_messages,
            )
        except AgentRouterUnavailableError:
            observation = tool_observation
        observation = self._validated_observation(observation, tool_observation)

        yield json.dumps({"status": "Composing answer"}) + "\n"
        final = self.response_router.rag_respond(
            message=message,
            thought=thought,
            observations=[observation.model_dump(mode="json")],
            route_context=route_context,
            recent_messages=recent_messages,
        )
        result = self._result_from_final(final, observation)
        if result.answer_markdown:
            yield json.dumps({"chunk": result.answer_markdown}) + "\n"
        yield json.dumps({"done": result.model_dump(mode="json")}) + "\n"

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
        if not fallback_observation.result.requires_evidence:
            return fallback_observation.evidence_status
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
        if result.metadata.get("topic_selection_offered"):
            return result.model_copy(
                update={
                    "requires_evidence": False,
                    "metadata": {
                        **result.metadata,
                        "agentic_rag_evidence_status": observation.evidence_status,
                        "preserved_tool_topic_selection_answer": True,
                    },
                }
            )
        answer_markdown = (
            final.answer_markdown or final.clarification_question or result.answer_markdown
        )
        answer_markdown = self._strip_hidden_stage_text(answer_markdown or "")
        if final.evidence_sufficient and result.citations:
            return result.model_copy(
                update={
                    "answer_markdown": answer_markdown,
                    "requires_evidence": False,
                    "metadata": {
                        **result.metadata,
                        "agentic_rag_evidence_status": observation.evidence_status,
                    },
                }
            )
        if observation.evidence_status == "no_source" and not result.citations:
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
                    "agentic_rag_evidence_status": observation.evidence_status,
                },
            }
        )

    @staticmethod
    def _strip_hidden_stage_text(markdown: str) -> str:
        value = markdown.strip()
        value = re.sub(r"(?is)hidden\s+thought\s*:.*?(final\s*:)", r"\1", value).strip()
        value = re.sub(r"(?i)^final\s*:\s*", "", value).strip()
        return re.sub(r"\s*\[\^[^\]]+\]", "", value).strip()
