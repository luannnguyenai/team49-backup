from __future__ import annotations

from uuid import uuid4

from pydantic import ValidationError

from src.schemas.agent import (
    AgentAction,
    AgentAssessmentWorkflowResponse,
    AssessmentPhase,
    AssessmentWorkflowDecision,
)


class AgentAssessmentWorkflowService:
    """Narrow assessment proposal workflow.

    The environment may not have LangGraph installed, so V1 keeps state in a
    tiny in-process store while preserving the same start/resume contract.
    """

    def __init__(self):
        self._states: dict[str, dict] = {}

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
        self._states[workflow_id] = state
        return self._proposal_response(state)

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
        try:
            parsed = (
                decision
                if isinstance(decision, AssessmentWorkflowDecision)
                else AssessmentWorkflowDecision.model_validate(decision or {})
            )
        except ValidationError:
            state["status"] = "rejected"
            return self._final_response(state, actions=[])

        if parsed.action == "reject":
            state["status"] = "rejected"
            return self._final_response(state, actions=[])
        if parsed.action == "reduce":
            if parsed.reduction_id == "minimum-evidence":
                state["question_budget"] = max(10, state["question_budget"] // 2)
            elif parsed.question_budget is not None:
                state["question_budget"] = max(1, min(parsed.question_budget, state["question_budget"]))
            return self._proposal_response(state)

        state["status"] = "assessment_ready"
        return self._final_response(
            state,
            actions=[
                AgentAction(
                    type="start_assessment",
                    label="Start assessment",
                    canonical_unit_ids=state["candidate_canonical_unit_ids"],
                    default_phase=state["phase"],
                    eligible=False,
                    disabledReason="not_implemented",
                )
            ],
        )

    def _proposal_response(self, state: dict) -> AgentAssessmentWorkflowResponse:
        budget = int(state["question_budget"])
        interrupt = {
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
        return AgentAssessmentWorkflowResponse(
            workflowId=state["workflow_id"],
            status="waiting_user_approval",
            interrupt=interrupt,
            actions=[],
            trace={"orchestrator": "workflow_v1"},
        )

    def _final_response(self, state: dict, actions: list[AgentAction]) -> AgentAssessmentWorkflowResponse:
        return AgentAssessmentWorkflowResponse(
            workflowId=state["workflow_id"],
            status=state["status"],
            interrupt=None,
            actions=actions,
            trace={"orchestrator": "workflow_v1"},
        )
