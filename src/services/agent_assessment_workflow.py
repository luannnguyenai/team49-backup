from __future__ import annotations

from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from src.schemas.agent import (
    AgentAction,
    AgentAssessmentWorkflowResponse,
    AssessmentPhase,
    AssessmentWorkflowDecision,
)


class AssessmentWorkflowState(TypedDict, total=False):
    workflow_id: str
    user_id: str
    candidate_canonical_unit_ids: list[str]
    question_budget: int
    phase: AssessmentPhase
    status: str
    decision: dict[str, Any] | AssessmentWorkflowDecision | None
    interrupt: dict[str, Any] | None
    actions: list[AgentAction]


class AgentAssessmentWorkflowService:
    """LangGraph-backed assessment proposal workflow with V1 in-process state."""

    def __init__(self):
        self._states: dict[str, dict] = {}
        self._graph = self._build_graph()

    def start(
        self,
        user_id: str,
        candidate_canonical_unit_ids: list[str],
        question_budget: int,
        phase: AssessmentPhase,
    ) -> AgentAssessmentWorkflowResponse:
        workflow_id = str(uuid4())
        state = {
            "workflow_id": workflow_id,
            "user_id": user_id,
            "candidate_canonical_unit_ids": candidate_canonical_unit_ids,
            "question_budget": max(1, min(question_budget, 70)),
            "phase": phase,
            "status": "waiting_user_approval",
        }
        next_state = self._graph.invoke(state)
        self._states[workflow_id] = next_state
        return self._response_from_state(next_state)

    def resume(
        self,
        workflow_id: str,
        user_id: str,
        decision: dict | AssessmentWorkflowDecision | None,
    ) -> AgentAssessmentWorkflowResponse:
        state = self._states.get(workflow_id)
        if not state:
            raise ValueError("workflow_not_found")
        if state["user_id"] != user_id:
            raise PermissionError("workflow_out_of_scope")
        state = {**state, "decision": decision}
        next_state = self._graph.invoke(state)
        self._states[workflow_id] = next_state
        return self._response_from_state(next_state)

    def _build_graph(self):
        graph = StateGraph(AssessmentWorkflowState)
        graph.add_node("proposal", self._proposal_node)
        graph.add_node("decision", self._decision_node)
        graph.add_conditional_edges(
            START,
            lambda state: "decision" if state.get("decision") is not None else "proposal",
            {"proposal": "proposal", "decision": "decision"},
        )
        graph.add_edge("proposal", END)
        graph.add_edge("decision", END)
        return graph.compile()

    def _proposal_node(self, state: AssessmentWorkflowState) -> AssessmentWorkflowState:
        next_state = dict(state)
        next_state["status"] = "waiting_user_approval"
        next_state["interrupt"] = self._build_interrupt(next_state)
        next_state["actions"] = []
        next_state.pop("decision", None)
        return next_state

    def _decision_node(self, state: AssessmentWorkflowState) -> AssessmentWorkflowState:
        next_state = dict(state)
        try:
            parsed = (
                decision
                if isinstance((decision := next_state.get("decision")), AssessmentWorkflowDecision)
                else AssessmentWorkflowDecision.model_validate(decision or {})
            )
        except ValidationError:
            next_state["status"] = "rejected"
            next_state["interrupt"] = None
            next_state["actions"] = []
            next_state.pop("decision", None)
            return next_state

        if parsed.action == "reject":
            next_state["status"] = "rejected"
            next_state["interrupt"] = None
            next_state["actions"] = []
            next_state.pop("decision", None)
            return next_state
        if parsed.action == "reduce":
            if parsed.reduction_id == "minimum-evidence":
                next_state["question_budget"] = max(10, int(next_state["question_budget"]) // 2)
            elif parsed.question_budget is not None:
                next_state["question_budget"] = max(
                    1,
                    min(parsed.question_budget, int(next_state["question_budget"])),
                )
            next_state["status"] = "waiting_user_approval"
            next_state["interrupt"] = self._build_interrupt(next_state)
            next_state["actions"] = []
            next_state.pop("decision", None)
            return next_state

        next_state["status"] = "assessment_ready"
        next_state["interrupt"] = None
        next_state["actions"] = [
            AgentAction(
                type="start_assessment",
                label="Start assessment",
                canonical_unit_ids=next_state["candidate_canonical_unit_ids"],
                default_phase=next_state["phase"],
                questionBudget=int(next_state["question_budget"]),
                eligible=True,
            )
        ]
        next_state.pop("decision", None)
        return next_state

    def _build_interrupt(self, state: AssessmentWorkflowState) -> dict[str, Any]:
        budget = int(state["question_budget"])
        return {
            "type": "assessment_proposal",
            "canonicalUnitIds": state["candidate_canonical_unit_ids"],
            "title": "Skip verification assessment",
            "purpose": "Verify whether selected units can be skipped with evidence.",
            "estimatedQuestions": budget,
            "estimatedTimeMinutes": max(10, int(budget * 1.5)),
            "scope": [
                {
                    "label": "Selected candidate units",
                    "unitCount": len(state["candidate_canonical_unit_ids"]),
                    "reason": "These units match the learner's self-reported prior knowledge.",
                }
            ],
            "difficultyMix": {
                "easy": max(1, budget // 5),
                "medium": max(1, budget // 2),
                "hard": max(0, budget // 4),
                "application": max(0, budget // 10),
            },
            "reductionOptions": [
                {
                    "id": "minimum-evidence",
                    "label": "Minimum evidence check",
                    "effect": "Keeps only high-signal questions. Evidence is weaker for borderline skips.",
                    "estimatedQuestionsAfterReduction": max(10, budget // 2),
                }
            ],
            "phase": state["phase"],
            "message": "Approve or reduce the assessment before starting.",
        }

    def _response_from_state(self, state: AssessmentWorkflowState) -> AgentAssessmentWorkflowResponse:
        return AgentAssessmentWorkflowResponse(
            workflowId=state["workflow_id"],
            status=state["status"],
            interrupt=state.get("interrupt"),
            actions=state.get("actions", []),
            trace={"orchestrator": "langgraph_assessment_workflow_v1"},
        )
