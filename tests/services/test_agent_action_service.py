import pytest

from src.schemas.agent import RequestReplanActionRequest
from src.services.agent_action_service import (
    default_phase_for_intent,
    start_agent_assessment,
    validate_replan_request,
)


def test_default_phase_for_intent_matches_assessment_use_case():
    assert default_phase_for_intent("assess_knowledge") == "skip_verification"
    assert default_phase_for_intent("summarize_progress") == "review"
    assert default_phase_for_intent("general_course_question") == "placement"


@pytest.mark.asyncio
async def test_start_assessment_action_calls_assessment_service(monkeypatch):
    captured = {}

    async def fake_start_assessment(*args, **kwargs):
        captured["args"] = args
        captured.update(kwargs)

        class Response:
            total_questions = 12

        return Response()

    monkeypatch.setattr("src.services.agent_action_service.start_assessment", fake_start_assessment)

    request = type(
        "Request",
        (),
        {
            "canonical_unit_ids": ["unit-a"],
            "phase": "skip_verification",
            "question_budget": 40,
        },
    )()

    result = await start_agent_assessment(None, user_id="user-1", request=request)

    assert result.total_questions == 12
    assert captured["canonical_unit_ids"] == ["unit-a"]
    assert captured["phase"] == "skip_verification"
    assert captured["assessment_depth"] == "deep"
    assert captured["question_budget"] == 40


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
