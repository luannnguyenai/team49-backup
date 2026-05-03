from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.services.agent_graph_contracts import ToolResult


AgenticRAGToolName = Literal[
    "search_current_path_units",
    "get_unit_summary",
    "ask_clarification",
    "offer_scope_expansion",
    "search_allowed_other_paths",
]

AgenticRAGEvidenceStatus = Literal[
    "grounded",
    "partial",
    "too_many_results",
    "scope_expansion_required",
    "no_source",
    "needs_clarification",
]


class AgenticRAGThought(BaseModel):
    user_goal: str
    active_topic: str | None = None
    missing_information: list[str] = Field(default_factory=list)
    evidence_need: Literal["none", "retrieval", "clarification"] = "retrieval"
    tool_plan: list[str] = Field(default_factory=list)


class AgenticRAGToolCall(BaseModel):
    tool: AgenticRAGToolName
    arguments: dict[str, Any] = Field(default_factory=dict)
    rationale: str


class AgenticRAGObservation(BaseModel):
    tool: AgenticRAGToolName
    success: bool
    evidence_status: AgenticRAGEvidenceStatus
    result: ToolResult


class AgenticRAGFinal(BaseModel):
    answer_markdown: str
    evidence_status: AgenticRAGEvidenceStatus
    evidence_sufficient: bool = False
    clarification_question: str | None = None
