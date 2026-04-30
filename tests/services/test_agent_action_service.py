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
async def test_replan_validation_requires_completed_assessment(monkeypatch):
    async def fake_get_results(*args, **kwargs):
        raise Exception("should not be called without a session id")

    monkeypatch.setattr("src.services.agent_action_service.get_assessment_results", fake_get_results)

    result = await validate_replan_request(
        None,
        RequestReplanActionRequest(
            sourceCanonicalUnitIds=["unit-a"],
            reason="User passed CNN verification.",
            dryRun=True,
        ),
        user=type("User", (), {"id": "user-1"})(),
    )

    assert result.accepted is False
    assert result.rejected_reason == "missing_assessment_session"


@pytest.mark.asyncio
async def test_replan_dry_run_derives_impact_from_owned_assessment(monkeypatch):
    session_id = "11111111-1111-1111-1111-111111111111"

    async def fake_get_results(db, user_id, assessment_session_id):
        assert str(assessment_session_id) == session_id

        decision = type("Decision", (), {"decision": "skip"})()
        return type(
            "Result",
            (),
            {
                "session_id": assessment_session_id,
                "overall_score_percent": 88.0,
                "topic_decisions": [decision],
                "learning_unit_results": [object()],
            },
        )()

    monkeypatch.setattr("src.services.agent_action_service.get_assessment_results", fake_get_results)

    result = await validate_replan_request(
        None,
        RequestReplanActionRequest(
            assessmentSessionId=session_id,
            sourceCanonicalUnitIds=["unit-a"],
            reason="User passed CNN verification.",
            dryRun=True,
        ),
        user=type("User", (), {"id": "user-1"})(),
    )

    assert result.accepted is True
    assert result.impact == {
        "assessmentSessionId": session_id,
        "overallScorePercent": 88.0,
        "decisionCounts": {"skip": 1, "review": 0, "relearn": 0},
        "evaluatedUnits": 1,
        "mode": "dry_run",
    }
