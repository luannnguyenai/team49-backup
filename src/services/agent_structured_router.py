from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.schemas.agent import AgentIntent, RouteContext
from src.services.agent_graph_contracts import AgentRoute, AgentSlots


class StructuredRouteOutput(BaseModel):
    intent: AgentIntent
    confidence: float = Field(ge=0.0, le=1.0)
    raw_topic: str | None = None
    target_path: Literal["computer_vision", "nlp"] | None = None
    rationale: str


class StructuredAgentRouter:
    def __init__(self, model, confidence_threshold: float = 0.65):
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.structured_model = model.with_structured_output(StructuredRouteOutput)

    def route(self, message: str, route_context: RouteContext | None) -> AgentRoute:
        result = self.structured_model.invoke(
            [
                {
                    "role": "system",
                    "content": (
                        "Classify the user's /agent request with structured output. "
                        "Do not use raw keyword matching as the source of truth. "
                        "Distinguish concept phrases such as skip connection from replan actions, "
                        "quiz eligibility questions from assessment creation, and path search from path switch. "
                        "Use request_path_switch only when the user asks to change the active learning path. "
                        "If intent or entity context is ambiguous, lower confidence so the graph clarifies."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Route context: {route_context.model_dump() if route_context else {}}\nMessage: {message}",
                },
            ]
        )
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
        )
