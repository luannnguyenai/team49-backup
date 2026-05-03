from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError, ValidationError
from src.schemas.learning_path import GeneratePathRequest
from src.services.assessment_service import start_assessment
from src.services.assessment_service import get_assessment_results
from src.services.recommendation_engine import generate_learning_path


@dataclass(frozen=True)
class ActionValidationResult:
    accepted: bool
    rejected_reason: str | None = None
    impact: dict | None = None


def default_phase_for_intent(intent: str, reason: str | None = None) -> str:
    if intent == "assess_knowledge" or reason == "self_report_skip":
        return "skip_verification"
    if intent == "summarize_progress" or reason == "stale_mastery":
        return "review"
    return "placement"


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


def _decision_counts(result) -> dict[str, int]:
    counts = {"skip": 0, "review": 0, "relearn": 0}
    for decision in result.topic_decisions or []:
        key = str(decision.decision)
        if key in counts:
            counts[key] += 1
    return counts


async def validate_replan_request(db: AsyncSession, request, user) -> ActionValidationResult:
    if not getattr(request, "assessment_session_id", None):
        return ActionValidationResult(accepted=False, rejected_reason="missing_assessment_session")

    try:
        session_id = UUID(str(request.assessment_session_id))
    except ValueError:
        return ActionValidationResult(accepted=False, rejected_reason="invalid_assessment_session")

    try:
        assessment_result = await get_assessment_results(db, user.id, session_id)
    except NotFoundError:
        return ActionValidationResult(accepted=False, rejected_reason="assessment_not_completed_or_missing")

    impact = {
        "assessmentSessionId": str(assessment_result.session_id),
        "overallScorePercent": assessment_result.overall_score_percent,
        "decisionCounts": _decision_counts(assessment_result),
        "evaluatedUnits": len(assessment_result.learning_unit_results),
    }

    if request.dry_run:
        return ActionValidationResult(accepted=True, impact={**impact, "mode": "dry_run"})

    generated = await generate_learning_path(db, user, GeneratePathRequest())
    return ActionValidationResult(
        accepted=True,
        impact={
            **impact,
            "mode": "replanned",
            "totalUnits": generated.total_units,
            "totalHours": generated.total_hours,
            "warnings": generated.warnings,
        },
    )
