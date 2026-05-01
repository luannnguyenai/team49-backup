from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.schemas.agent import AgentIntent, RouteContext
from src.services.agent_error_codes import classify_agent_error
from src.services.agent_graph_contracts import AgentRoute, AgentRouterUnavailableError, AgentSlots


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
    action: Literal["approve", "reject", "refine", "clarify"]
    refined_query: str | None = None
    clarification_question: str | None = None
    rationale: str


class StructuredAgentRouter:
    def __init__(self, model, confidence_threshold: float = 0.65):
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.structured_model = model.with_structured_output(StructuredRouteOutput)

    def route(self, message: str, route_context: RouteContext | None) -> AgentRoute:
        try:
            result = self.structured_model.invoke(
                [
                    {
                        "role": "system",
                        "content": (
                            "Classify the user's /agent request with structured output. "
                            "The product domain is AI/ML course learning. "
                            "Most indexed course material is English; do not force the reply language. "
                            "Do not use raw keyword matching as the source of truth. "
                            "Lexical tokens may only be weak context signals. "
                            "Distinguish concept phrases such as skip connection from replan actions, "
                            "quiz eligibility questions from assessment creation, and path search from path switch. "
                            "Requests like 'where should I review X' or 'what should I review for X' are usually "
                            "course-content review/navigation requests with raw_topic=X. "
                            "For content retrieval intents, provide search_queries as concise BM25-ready queries. "
                            "The model may include spelling, punctuation, abbreviation, or contextual variants it "
                            "infers from the user message and route context. Do not rely on application code to add "
                            "domain synonyms. If the user request lacks enough searchable terms, lower confidence "
                            "and ask for clarification instead of guessing. "
                            "Set target_path only when the user explicitly names a path, course, or track scope. "
                            "Set explicit_scope_requested=true only when the user's words explicitly request "
                            "another path, course, track, or broader catalog scope. "
                            "Do not infer target_path from the topic domain alone; for example CNN topics do not "
                            "automatically mean computer_vision and dependency parsing topics do not automatically "
                            "mean nlp unless the user named that scope. "
                            "For underspecified content/navigation requests, keep the likely content intent with "
                            "low confidence and a clarification_question instead of choosing clarify as the primary intent. "
                            "Use assistant_help for greetings, capability questions, and broad help requests "
                            "that do not ask about a specific course content item, navigation target, assessment, "
                            "progress summary, or planning action. Broad help requests such as asking whether the "
                            "assistant can help should be assistant_help, not clarification. "
                            "Use request_path_switch only when the user asks to change the active learning path. "
                            "If intent or entity context is ambiguous, lower confidence and provide one concise "
                            "clarification_question. If you choose clarify, set candidate_intent to the likely "
                            "business intent being clarified when one exists."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Route context: {route_context.model_dump() if route_context else {}}\nMessage: {message}",
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
        return AgentRoute(
            intent=intent,
            confidence=result.confidence,
            extracted_slots=AgentSlots(
                raw_topic=result.raw_topic,
                search_queries=result.search_queries,
                target_path=effective_target_path,
                requested_path_id=effective_target_path if search_scope == "explicit_path" else None,
                resolved_search_path_ids=[effective_target_path] if search_scope == "explicit_path" else [],
                search_scope=search_scope,
            ),
            rationale=result.rationale,
            clarification_question=result.clarification_question,
            candidate_intent=candidate_intent,
        )

    def resolve_pending_followup(
        self,
        message: str,
        pending_payload: dict[str, Any],
        route_context: RouteContext | None,
    ) -> PendingFollowupDecisionOutput:
        try:
            response = self.model.with_structured_output(PendingFollowupDecisionOutput).invoke(
                [
                    {
                        "role": "system",
                        "content": (
                            "Resolve the user's reply to a pending agent clarification with structured output. "
                            "Do not use keyword matching or phrase matching as the source of truth. "
                            "Use the pending payload and conversation context to decide whether the user approved "
                            "the pending option, rejected it, refined the retrieval query, or still needs clarification. "
                            "For failed_request_retry payloads, approve only when the user is asking to retry or continue "
                            "the failed request; refine when they restate the request with more detail; clarify when it "
                            "is unclear whether they mean the failed request or a new request. "
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

    def _response_text(self, response: Any) -> str:
        content = getattr(response, "content", response)
        if isinstance(content, list):
            content = " ".join(
                str(part.get("text", part)) if isinstance(part, dict) else str(part)
                for part in content
            )
        return str(content).strip()

    def compose_assistant_help(self, message: str, route_context: RouteContext | None) -> str:
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
                            "Do not invent course facts or claim tool results."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Route context: {route_context.model_dump() if route_context else {}}\nMessage: {message}",
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
            response = self.model.with_structured_output(GroundedAnswerOutput).invoke(
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
                            "Do not invent missing course facts. If the retrieved units do not directly support "
                            "the user's requested topic, set evidence_sufficient=false, choose no_source or partial "
                            "confidence, and ask one concise clarifying question or say that no direct grounded "
                            "source was found. If the retrieved units are related but not exact, say that you found "
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
            return response
        if isinstance(response, dict):
            return GroundedAnswerOutput.model_validate(response)
        return GroundedAnswerOutput.model_validate(response.model_dump())
