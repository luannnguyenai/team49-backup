from __future__ import annotations

from typing import Any
from uuid import UUID

from src.schemas.agent import RequestReplanActionRequest, StartAssessmentActionRequest
from src.services.agent_action_service import start_agent_assessment, validate_replan_request


class AgentActionCommitService:
    async def commit_start_assessment(
        self,
        db,
        *,
        user_id: UUID,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        request = StartAssessmentActionRequest(
            canonicalUnitIds=payload.get("canonical_unit_ids") or [],
            phase=payload.get("phase") or "skip_verification",
            reason=payload.get("reason") or f"agent_pending_action:{idempotency_key}",
            questionBudget=payload.get("question_budget"),
        )
        assessment = await start_agent_assessment(db, user_id=user_id, request=request)
        return {
            "type": "start_assessment",
            "status": "committed",
            "sessionId": str(assessment.session_id),
            "totalQuestions": assessment.total_questions,
            "questions": [question.model_dump(mode="json") for question in assessment.questions],
            "canonicalUnitIds": request.canonical_unit_ids,
            "phase": request.phase,
            "href": "/assessment",
        }

    async def commit_replan(
        self,
        db,
        *,
        user,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        request = RequestReplanActionRequest(
            assessmentSessionId=payload.get("assessment_session_id"),
            sourceCanonicalUnitIds=payload.get("source_canonical_unit_ids") or [],
            reason=payload.get("reason") or f"agent_pending_action:{idempotency_key}",
            dryRun=False,
        )
        result = await validate_replan_request(db, request, user)
        return {
            "type": "request_replan",
            "status": "committed" if result.accepted else "rejected",
            "accepted": result.accepted,
            "rejectedReason": result.rejected_reason,
            "dryRun": False,
            "impact": result.impact,
        }
