from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import ValidationError
from src.services.assessment_service import start_assessment


@dataclass(frozen=True)
class ActionValidationResult:
    accepted: bool
    rejected_reason: str | None = None


def default_phase_for_intent(intent: str, reason: str | None = None) -> str:
    if intent == "assess_knowledge" or reason == "self_report_skip":
        return "skip_verification"
    if intent == "summarize_progress" or reason == "stale_mastery":
        return "review"
    return "placement"


def start_assessment_not_implemented() -> ActionValidationResult:
    return ActionValidationResult(accepted=False, rejected_reason="not_implemented")


def _assessment_depth_for_budget(question_budget: int | None) -> str:
    if question_budget is None:
        return "standard"
    if question_budget <= 15:
        return "quick"
    if question_budget > 30:
        return "deep"
    return "standard"


async def start_agent_assessment(
    db: AsyncSession,
    *,
    user_id: UUID,
    request,
):
    assessment = await start_assessment(
        db,
        user_id,
        learning_unit_ids=[],
        canonical_unit_ids=request.canonical_unit_ids,
        phase=request.phase,
        assessment_depth=_assessment_depth_for_budget(request.question_budget),
        question_budget=request.question_budget,
    )
    if assessment.total_questions == 0:
        raise ValidationError("No eligible assessment questions found.")
    return assessment


async def validate_replan_request(request, user_id: str) -> ActionValidationResult:
    if not getattr(request, "assessment_session_id", None) and not getattr(
        request, "source_canonical_unit_ids", []
    ):
        return ActionValidationResult(accepted=False, rejected_reason="missing_evidence")
    return ActionValidationResult(accepted=False, rejected_reason="not_implemented")
