from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.schemas.agent import (
    AgentAction,
    AgentAnswer,
    AgentChatResponse,
    AgentCitation,
    AgentFallback,
    AgentIntent,
    AgentWarning,
    RetrievalTrace,
    RouteContext,
)
from src.services.agent_error_codes import agent_system_error_message

AGENT_INTENT_NODE_REGISTRY: dict[AgentIntent, str] = {
    "explain_concept": "explain_concept_node",
    "find_content": "find_content_node",
    "navigate_to_unit": "navigate_to_unit_node",
    "ask_what_next": "ask_what_next_node",
    "assess_knowledge": "assess_knowledge_node",
    "request_replan": "request_replan_node",
    "explain_planner_decision": "explain_planner_decision_node",
    "summarize_progress": "summarize_progress_node",
    "general_course_question": "general_course_question_node",
    "assistant_help": "assistant_help_node",
    "request_path_switch": "request_path_switch_node",
    "clarify": "clarify_node",
}

GRAPH_RUN_STATUSES = {
    "created",
    "running",
    "interrupted",
    "succeeded",
    "failed_retryable",
    "failed_terminal",
    "cancelled",
}


class AgentInProgressError(RuntimeError):
    def __init__(
        self,
        conversation_id: str,
        thread_id: str,
        graph_run_id: str,
        retry_after_ms: int = 1000,
    ):
        super().__init__("agent_graph_run_in_progress")
        self.conversation_id = conversation_id
        self.thread_id = thread_id
        self.graph_run_id = graph_run_id
        self.retry_after_ms = retry_after_ms

    def to_response(self):
        from src.schemas.agent import AgentInProgressResponse

        return AgentInProgressResponse(
            conversationId=self.conversation_id,
            threadId=self.thread_id,
            graphRunId=self.graph_run_id,
            retryAfterMs=self.retry_after_ms,
        )


class AgentRouterUnavailableError(RuntimeError):
    def __init__(
        self,
        message: str = "agent_router_unavailable",
        error_code: str = "AGENT_ROUTER_UNAVAILABLE",
    ):
        super().__init__(message)
        self.error_code = error_code

    def to_response(self, conversation_id: str = "", message_id: str = "") -> AgentChatResponse:
        return AgentChatResponse(
            conversation_id=conversation_id,
            message_id=message_id,
            answer=AgentAnswer(
                markdown=agent_system_error_message(self.error_code),
                confidence="fallback",
            ),
            warning=AgentWarning(
                type="agent_unavailable",
                message=self.error_code,
            ),
            fallback=AgentFallback(
                reason="agent_unavailable",
                message="The production router model is unavailable.",
                errorCode=self.error_code,
            ),
        )


class AgentSlots(BaseModel):
    raw_topic: str | None = None
    search_queries: list[str] = Field(default_factory=list)
    target_path: str | None = None
    assessment_phase: str | None = None
    canonical_unit_ids: list[str] = Field(default_factory=list)
    course_ids: list[str] = Field(default_factory=list)
    lecture_scope: Literal["learned", "all"] | None = None
    ambiguity_options: list[dict[str, Any]] = Field(default_factory=list)
    search_scope: Literal["current_path", "explicit_path", "expanded_paths"] = "current_path"
    scope_expansion_offered: bool = False
    scope_expansion_approved: bool = False
    requested_path_id: str | None = None
    resolved_search_path_ids: list[str] = Field(default_factory=list)
    excluded_search_path_ids: list[str] = Field(default_factory=list)
    show_top_results_approved: bool = False
    topic_choice_approved: bool = False


class RouteContextSnapshot(BaseModel):
    route_context: RouteContext | None = None
    current_path_course_ids: list[str] = Field(default_factory=list)


class AgentRoute(BaseModel):
    intent: AgentIntent
    confidence: float = Field(ge=0.0, le=1.0)
    extracted_slots: AgentSlots = Field(default_factory=AgentSlots)
    rationale: str | None = None
    clarification_question: str | None = None
    candidate_intent: AgentIntent | None = None


class PolicyDecision(BaseModel):
    allow: bool = True
    codes: list[str] = Field(default_factory=list)
    user_safe_message: str | None = None
    audit_context: dict[str, Any] | None = None


class PendingAction(BaseModel):
    action_id: str
    type: Literal[
        "propose_assessment",
        "start_assessment",
        "request_replan",
        "request_path_switch",
    ]
    status: Literal[
        "proposed",
        "awaiting_confirmation",
        "confirmed",
        "cancelled",
        "committed",
        "expired",
    ]
    payload_ref: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    payload_version: int = 1
    idempotency_key: str
    expires_at: datetime


class PendingClarification(BaseModel):
    clarification_id: str
    type: Literal["search_scope_expansion", "slot_disambiguation", "intent_clarification"]
    status: Literal["awaiting_response", "resolved", "cancelled", "expired"]
    payload: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None


class ToolResult(BaseModel):
    kind: Literal[
        "find_content",
        "explain_concept",
        "navigation",
        "planner_decision",
        "what_next",
        "assessment_proposal",
        "replan_proposal",
        "path_switch_proposal",
        "progress_summary",
        "clarification",
    ]
    answer_markdown: str | None = None
    citations: list[AgentCitation] = Field(default_factory=list)
    actions: list[AgentAction] = Field(default_factory=list)
    warning: AgentWarning | None = None
    fallback: AgentFallback | None = None
    requires_evidence: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    trace: RetrievalTrace | None = None


class AgentCheckpointState(BaseModel):
    state_version: int = 1
    thread_id: str
    conversation_id: str
    user_id: str
    incoming_message_id: str
    route_context: RouteContext | None = None
    intent: AgentIntent | None = None
    intent_confidence: float = 0.0
    slots: AgentSlots = Field(default_factory=AgentSlots)
    policy: PolicyDecision = Field(default_factory=PolicyDecision)
    pending_action: PendingAction | None = None
    pending_clarification: PendingClarification | None = None
    learning_context_ref: str | None = None
    memory_ref: str | None = None
    tool_result: ToolResult | None = None
    citations: list[AgentCitation] = Field(default_factory=list)
    answer: AgentAnswer | None = None
    warning: AgentWarning | None = None
    fallback: AgentFallback | None = None
    trace_id: str
