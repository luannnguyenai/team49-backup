import pytest

from src.schemas.agent import RequestReplanActionRequest
from src.services.agent_action_service import (
    default_phase_for_intent,
    start_assessment_not_implemented,
    validate_replan_request,
)


def test_default_phase_for_intent_matches_assessment_use_case():
    assert default_phase_for_intent("assess_knowledge") == "skip_verification"
    assert default_phase_for_intent("summarize_progress") == "review"
    assert default_phase_for_intent("general_course_question") == "placement"


def test_start_assessment_action_is_explicitly_disabled_until_real_service_is_wired():
    result = start_assessment_not_implemented()

    assert result.accepted is False
    assert result.rejected_reason == "not_implemented"


@pytest.mark.asyncio
async def test_replan_validation_stub_does_not_accept_arbitrary_evidence():
    result = await validate_replan_request(
        RequestReplanActionRequest(
            assessmentSessionId="session-1",
            sourceCanonicalUnitIds=["unit-a"],
            reason="User passed CNN verification.",
            dryRun=True,
        ),
        user_id="user-1",
    )

    assert result.accepted is False
    assert result.rejected_reason == "not_implemented"
