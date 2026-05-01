from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.schemas.agent import AgentIntent, RouteContext
from src.services.agent_error_codes import classify_agent_error
from src.services.agent_graph_contracts import AgentRoute, AgentRouterUnavailableError, AgentSlots


class StructuredRouteOutput(BaseModel):
    intent: AgentIntent
    confidence: float = Field(ge=0.0, le=1.0)
    raw_topic: str | None = None
    target_path: Literal["computer_vision", "nlp"] | None = None
    rationale: str
    clarification_question: str | None = None


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
                            "Use assistant_help for greetings, capability questions, and broad help requests "
                            "that do not ask about a specific course content item, navigation target, assessment, "
                            "progress summary, or planning action. Broad help requests such as asking whether the "
                            "assistant can help should be assistant_help, not clarification. "
                            "Use request_path_switch only when the user asks to change the active learning path. "
                            "If intent or entity context is ambiguous, lower confidence and provide one concise "
                            "clarification_question."
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
        intent: AgentIntent = result.intent
        if result.confidence < self.confidence_threshold:
            intent = "clarify"
        search_scope = "explicit_path" if result.target_path and intent != "request_path_switch" else "current_path"
        return AgentRoute(
            intent=intent,
            confidence=result.confidence,
            extracted_slots=AgentSlots(
                raw_topic=result.raw_topic,
                target_path=result.target_path,
                requested_path_id=result.target_path if search_scope == "explicit_path" else None,
                resolved_search_path_ids=[result.target_path] if search_scope == "explicit_path" else [],
                search_scope=search_scope,
            ),
            rationale=result.rationale,
            clarification_question=result.clarification_question,
        )

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
                            "Reply naturally and briefly. "
                            "For greetings or broad help requests, answer directly "
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

    def compose_grounded_answer(self, message: str, citations: list[dict]) -> str:
        try:
            response = self.model.invoke(
                [
                    {
                        "role": "system",
                        "content": (
                            "Answer as the AI Learning Hub assistant. "
                            "Use only these retrieved learning units as evidence. "
                            "Most indexed course material is English; reply naturally in the user's language "
                            "when appropriate. "
                            "Do not invent missing course facts. If the evidence is insufficient, ask one concise "
                            "clarifying question instead of guessing."
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

        return self._response_text(response)
