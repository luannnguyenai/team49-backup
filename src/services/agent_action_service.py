from __future__ import annotations

from dataclasses import dataclass


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


async def validate_replan_request(request, user_id: str) -> ActionValidationResult:
    if not getattr(request, "assessment_session_id", None) and not getattr(
        request, "source_canonical_unit_ids", []
    ):
        return ActionValidationResult(accepted=False, rejected_reason="missing_evidence")
    return ActionValidationResult(accepted=False, rejected_reason="not_implemented")
