from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.schemas.agent import AgentIntent, RouteContext
from src.services.agent_error_codes import classify_agent_error
from src.services.agent_graph_contracts import AgentRoute, AgentRouterUnavailableError, AgentSlots
from src.services.agent_prompt_manager import get_agent_prompt_manager
from src.services.agentic_rag_tools import AgentRAGToolRegistry
from src.services.agentic_rag_contracts import (
    AgenticRAGFinal,
    AgenticRAGObservation,
    AgenticRAGThought,
    AgenticRAGToolCall,
)


class StructuredRouteOutput(BaseModel):
    intent: AgentIntent
    candidate_intent: AgentIntent | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    raw_topic: str | None = None
    search_queries: list[str] = Field(default_factory=list)
    target_path: Literal["computer_vision", "nlp"] | None = None
    explicit_scope_requested: bool = False
    rationale: str
    clarification_question: str | None = None


class GroundedAnswerOutput(BaseModel):
    answer_markdown: str
    evidence_sufficient: bool
    confidence: Literal["grounded", "partial", "no_source"] = "grounded"
    clarification_question: str | None = None


class PendingFollowupDecisionOutput(BaseModel):
    action: Literal["approve", "reject", "refine", "clarify", "new_request"]
    refined_query: str | None = None
    clarification_question: str | None = None
    rationale: str


class RetrievalRefinementOutput(BaseModel):
    answer_markdown: str


class StructuredAgentRouter:
    def __init__(
        self,
        model,
        confidence_threshold: float = 0.65,
        prompt_manager=None,
        tool_registry: AgentRAGToolRegistry | None = None,
    ):
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.prompt_manager = prompt_manager or get_agent_prompt_manager()
        self.tool_registry = tool_registry or AgentRAGToolRegistry()
        self.structured_model = self._with_structured_output(StructuredRouteOutput)

    def _with_structured_output(self, schema):
        try:
            return self.model.with_structured_output(schema, method="function_calling")
        except TypeError:
            return self.model.with_structured_output(schema)

    def _agentic_prompt(self, key: str, **kwargs: Any) -> str:
        return self.prompt_manager.render("agentic_rag", key, **kwargs)

    def _rag_tool_prompt_text(self) -> str:
        return self.tool_registry.build_prompt_text()

    def route(
        self,
        message: str,
        route_context: RouteContext | None,
        recent_messages: list[dict] | None = None,
    ) -> AgentRoute:
        try:
            result = self.structured_model.invoke(
                [
                    {
                        "role": "system",
                        "content": self._agentic_prompt("route.system"),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Route context: {route_context.model_dump() if route_context else {}}\n"
                            f"Recent thread messages: {recent_messages or []}\n"
                            f"Message: {message}"
                        ),
                    },
                ]
            )
        except Exception as exc:
            raise AgentRouterUnavailableError(
                "agent_router_model_error",
                classify_agent_error(exc, default="AGENT_ROUTER_UNAVAILABLE"),
            ) from exc
        candidate_intent: AgentIntent | None = result.candidate_intent
        intent: AgentIntent = result.intent
        if result.confidence < self.confidence_threshold:
            candidate_intent = result.candidate_intent or result.intent
            intent = "clarify"
        effective_target_path = result.target_path
        if intent != "request_path_switch" and not result.explicit_scope_requested:
            effective_target_path = None
        search_scope = "explicit_path" if effective_target_path and intent != "request_path_switch" else "current_path"
        search_queries = result.search_queries
        if recent_messages and len(message.split()) <= 8 and result.raw_topic:
            search_queries = [result.raw_topic]
        return AgentRoute(
            intent=intent,
            confidence=result.confidence,
            extracted_slots=AgentSlots(
                raw_topic=result.raw_topic,
                search_queries=search_queries,
                target_path=effective_target_path,
                requested_path_id=effective_target_path if search_scope == "explicit_path" else None,
                resolved_search_path_ids=[effective_target_path] if search_scope == "explicit_path" else [],
                search_scope=search_scope,
            ),
            rationale=result.rationale,
            clarification_question=result.clarification_question,
            candidate_intent=candidate_intent,
        )

    def rag_think(
        self,
        *,
        message: str,
        intent: str,
        slots,
        route_context: RouteContext | None,
        recent_messages: list[dict],
    ) -> AgenticRAGThought:
        try:
            slots_dump = slots.model_dump(mode="json") if hasattr(slots, "model_dump") else slots
            response = self._with_structured_output(AgenticRAGThought).invoke(
                [
                    {
                        "role": "system",
                        "content": self._agentic_prompt(
                            "thinking.system",
                            tool_list=self._rag_tool_prompt_text(),
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Intent: {intent}\n"
                            f"Route context: {route_context.model_dump() if route_context else {}}\n"
                            f"Slots: {slots_dump}\n"
                            f"Recent visible thread messages: {recent_messages}\n"
                            f"User message: {message}"
                        ),
                    },
                ]
            )
        except Exception as exc:
            raise AgentRouterUnavailableError(
                "agentic_rag_thinking_model_error",
                classify_agent_error(exc, default="AGENT_LLM_UNAVAILABLE"),
            ) from exc
        return self._validate_structured(response, AgenticRAGThought)

    def rag_act(
        self,
        *,
        message: str,
        thought,
        slots,
        route_context: RouteContext | None,
        recent_messages: list[dict],
        observations: list[dict],
    ) -> AgenticRAGToolCall:
        try:
            response = self._with_structured_output(AgenticRAGToolCall).invoke(
                [
                    {
                        "role": "system",
                        "content": self._agentic_prompt(
                            "acting.system",
                            tool_list=self._rag_tool_prompt_text(),
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Route context: {route_context.model_dump() if route_context else {}}\n"
                            f"Slots: {self._dump_like(slots)}\n"
                            f"Recent visible thread messages: {recent_messages}\n"
                            f"Thought: {self._dump_like(thought)}\n"
                            f"Observation history: {observations}\n"
                            f"User message: {message}"
                        ),
                    },
                ]
            )
        except Exception as exc:
            raise AgentRouterUnavailableError(
                "agentic_rag_acting_model_error",
                classify_agent_error(exc, default="AGENT_LLM_UNAVAILABLE"),
            ) from exc
        return self._validate_structured(response, AgenticRAGToolCall)

    def rag_observe(
        self,
        *,
        message: str,
        thought,
        tool_call: AgenticRAGToolCall,
        tool_observation: AgenticRAGObservation,
        route_context: RouteContext | None,
        recent_messages: list[dict],
    ) -> AgenticRAGObservation:
        try:
            response = self._with_structured_output(AgenticRAGObservation).invoke(
                [
                    {
                        "role": "system",
                        "content": self._agentic_prompt(
                            "observing.system",
                            tool_list=self._rag_tool_prompt_text(),
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Route context: {route_context.model_dump() if route_context else {}}\n"
                            f"Recent visible thread messages: {recent_messages}\n"
                            f"Thought: {self._dump_like(thought)}\n"
                            f"Tool call: {tool_call.model_dump(mode='json')}\n"
                            f"Tool observation: {tool_observation.model_dump(mode='json')}\n"
                            f"User message: {message}"
                        ),
                    },
                ]
            )
        except Exception as exc:
            raise AgentRouterUnavailableError(
                "agentic_rag_observing_model_error",
                classify_agent_error(exc, default="AGENT_LLM_UNAVAILABLE"),
            ) from exc
        return self._validate_structured(response, AgenticRAGObservation)

    def rag_respond(
        self,
        *,
        message: str,
        thought,
        observations: list[dict],
        route_context: RouteContext | None,
        recent_messages: list[dict],
    ) -> AgenticRAGFinal:
        try:
            response = self._with_structured_output(AgenticRAGFinal).invoke(
                [
                    {
                        "role": "system",
                        "content": self._agentic_prompt("responding.system"),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Route context: {route_context.model_dump() if route_context else {}}\n"
                            f"Recent visible thread messages: {recent_messages}\n"
                            f"Thought summary: {self._dump_like(thought)}\n"
                            f"Validated observations: {observations}\n"
                            f"User message: {message}"
                        ),
                    },
                ]
            )
        except Exception as exc:
            raise AgentRouterUnavailableError(
                "agentic_rag_responding_model_error",
                classify_agent_error(exc, default="AGENT_LLM_UNAVAILABLE"),
            ) from exc
        final = self._validate_structured(response, AgenticRAGFinal)
        if final.evidence_sufficient:
            return final.model_copy(
                update={
                    "answer_markdown": self._strip_trailing_followup_question(
                        final.answer_markdown
                    )
                }
            )
        return final

    def resolve_pending_followup(
        self,
        message: str,
        pending_payload: dict[str, Any],
        route_context: RouteContext | None,
        recent_messages: list[dict] | None = None,
    ) -> PendingFollowupDecisionOutput:
        try:
            response = self._with_structured_output(PendingFollowupDecisionOutput).invoke(
                [
                    {
                        "role": "system",
                        "content": (
                            "Resolve the user's reply to a pending agent clarification with structured output. "
                            "Do not use keyword matching or phrase matching as the source of truth. "
                            "Use the pending payload and conversation context to decide whether the user approved "
                            "the pending option, rejected it, refined the retrieval query, or still needs clarification. "
                            "Only approve offered actions that exist in the pending payload; never invent a new "
                            "option, ranking mode, path choice, or tool capability from the user's wording alone. "
                            "For failed_request_retry payloads, approve only when the user is asking to retry or continue "
                            "the failed request; refine when they restate the request with more detail; clarify when it "
                            "is unclear whether they mean the failed request or a new request. "
                            "If the user's reply is a new standalone request or a question about the conversation "
                            "itself instead of an answer to the pending clarification, set action=new_request. "
                            "If the user provides more detail for a retrieval query, set action=refine and return a "
                            "single BM25-ready refined_query that combines the pending topic with the new detail. "
                            "If the user approves showing offered top results or expanding search scope, set "
                            "action=approve and leave refined_query empty. If the reply is unclear, set action=clarify "
                            "with one concise clarification_question."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Route context: {route_context.model_dump() if route_context else {}}\n"
                            f"Recent visible thread messages: {recent_messages or []}\n"
                            f"Pending payload: {pending_payload}\n"
                            f"User reply: {message}"
                        ),
                    },
                ]
            )
        except Exception as exc:
            raise AgentRouterUnavailableError(
                "agent_pending_followup_model_error",
                classify_agent_error(exc, default="AGENT_LLM_UNAVAILABLE"),
            ) from exc

        if isinstance(response, PendingFollowupDecisionOutput):
            return response
        if isinstance(response, dict):
            return PendingFollowupDecisionOutput.model_validate(response)
        return PendingFollowupDecisionOutput.model_validate(response.model_dump())

    def compose_retrieval_refinement(
        self,
        *,
        message: str,
        raw_topic: str | None,
        result_count: int,
        route_context: RouteContext | None,
    ) -> str:
        try:
            response = self._with_structured_output(RetrievalRefinementOutput).invoke(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are the AI Learning Hub assistant. "
                            "The catalog search found many title-level learning units for the user's topic. "
                            "Write one concise, natural clarification in the user's language. "
                            "Ask whether they want to narrow the topic with more detail or see the strongest "
                            "current results. Do not invent course facts and do not mention implementation details. "
                            "Do not mention examples, versions, subtypes, rankings, or choice dimensions that are "
                            "not present in the user message, raw topic, route context, or retrieved tool metadata. "
                            "The only allowed choices are: provide a more specific description, or show the stored "
                            "top results."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Route context: {route_context.model_dump() if route_context else {}}\n"
                            f"User message: {message}\n"
                            f"Raw topic: {raw_topic or ''}\n"
                            f"Result count: {result_count}"
                        ),
                    },
                ]
            )
        except Exception as exc:
            raise AgentRouterUnavailableError(
                "agent_retrieval_refinement_model_error",
                classify_agent_error(exc, default="AGENT_LLM_UNAVAILABLE"),
            ) from exc

        if isinstance(response, RetrievalRefinementOutput):
            return response.answer_markdown
        if isinstance(response, dict):
            return RetrievalRefinementOutput.model_validate(response).answer_markdown
        return RetrievalRefinementOutput.model_validate(response.model_dump()).answer_markdown

    @staticmethod
    def _dump_like(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        return value

    @staticmethod
    def _validate_structured(value: Any, schema):
        if isinstance(value, schema):
            return value
        if isinstance(value, dict):
            return schema.model_validate(value)
        return schema.model_validate(value.model_dump())

    def _response_text(self, response: Any) -> str:
        content = getattr(response, "content", response)
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "reasoning":
                        continue
                    text = part.get("text")
                    if text is not None:
                        parts.append(str(text))
                    continue
                part_type = getattr(part, "type", None)
                if part_type == "reasoning":
                    continue
                text = getattr(part, "text", None)
                parts.append(str(text if text is not None else part))
            content = " ".join(parts)
        return str(content).strip()

    def _strip_trailing_followup_question(self, answer: str) -> str:
        paragraphs = answer.rstrip().split("\n\n")
        if not paragraphs:
            return answer.strip()
        tail = paragraphs[-1].strip()
        optional_offer_starts = (
            "if you want",
            "if you'd like",
            "would you like",
            "do you want",
            "nếu bạn muốn",
            "nếu bạn cần",
            "bạn muốn",
            "bạn có muốn",
        )
        if tail.endswith("?") or tail.lower().startswith(optional_offer_starts):
            paragraphs = paragraphs[:-1]
        return "\n\n".join(part for part in paragraphs if part.strip()).strip()

    def compose_assistant_help(
        self,
        message: str,
        route_context: RouteContext | None,
        recent_messages: list[dict] | None = None,
    ) -> str:
        try:
            response = self.model.invoke(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are the AI Learning Hub assistant for AI/ML course learning. "
                            "Most indexed course material is English; do not force the reply language. "
                            "Reply naturally and briefly. Use clean markdown when structure helps. "
                            "For simple greetings, greet briefly and ask what the user needs. "
                            "For broad help requests, answer directly "
                            "and explain what you can help with: finding course content, suggesting what to "
                            "review next, explaining planner decisions, proposing assessments, and helping with replans. "
                            "When the user asks what the current topic is, answer from recent visible thread "
                            "messages instead of asking them to clarify. "
                            "Do not invent course facts or claim tool results."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Route context: {route_context.model_dump() if route_context else {}}\n"
                            f"Recent visible thread messages: {recent_messages or []}\n"
                            f"Message: {message}"
                        ),
                    },
                ]
            )
        except Exception as exc:
            raise AgentRouterUnavailableError(
                "agent_assistant_help_model_error",
                classify_agent_error(exc, default="AGENT_LLM_UNAVAILABLE"),
            ) from exc

        return self._response_text(response)

    def compose_grounded_answer(self, message: str, citations: list[dict]) -> GroundedAnswerOutput:
        try:
            response = self._with_structured_output(GroundedAnswerOutput).invoke(
                [
                    {
                        "role": "system",
                        "content": (
                            "Answer as the AI Learning Hub assistant. "
                            "Use only these retrieved learning units as evidence. "
                            "Most indexed course material is English; reply naturally in the user's language "
                            "when appropriate. "
                            "Use clean markdown with short paragraphs or bullets when helpful, and write math "
                            "with standard LaTeX delimiters only when the answer needs formulas. "
                            "Do not include raw URLs, course hrefs, or source links in the answer text; "
                            "navigation is provided by citations/source cards. "
                            "Do not invent missing course facts. If the retrieved units do not directly support "
                            "the user's requested topic, set evidence_sufficient=false, choose no_source or partial "
                            "confidence, and ask one concise clarifying question or say that no direct grounded "
                            "source was found. When evidence_sufficient=true, do not end with a follow-up question; "
                            "answer the user's request directly and stop. "
                            "Do not suggest variants, rankings, comparisons, or choices unless they are explicitly "
                            "supported by the retrieved units or by an already-persisted pending tool action. "
                            "If the retrieved units are related but not exact, say that you found "
                            "related results below and ask the user to describe the target more specifically if those "
                            "results are not what they need. Do not answer from outside the retrieved evidence."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"User message: {message}\nRetrieved learning units: {citations}",
                    },
                ]
            )
        except Exception as exc:
            raise AgentRouterUnavailableError(
                "agent_grounded_answer_model_error",
                classify_agent_error(exc, default="AGENT_LLM_UNAVAILABLE"),
            ) from exc

        if isinstance(response, GroundedAnswerOutput):
            if response.evidence_sufficient:
                return response.model_copy(
                    update={
                        "answer_markdown": self._strip_trailing_followup_question(
                            response.answer_markdown
                        )
                    }
                )
            return response
        if isinstance(response, dict):
            answer = GroundedAnswerOutput.model_validate(response)
        else:
            answer = GroundedAnswerOutput.model_validate(response.model_dump())
        if answer.evidence_sufficient:
            return answer.model_copy(
                update={"answer_markdown": self._strip_trailing_followup_question(answer.answer_markdown)}
            )
        return answer
