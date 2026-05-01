from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.services.agent_action_commit_service import AgentActionCommitService

pytestmark = pytest.mark.asyncio


async def test_commit_start_assessment_wraps_authoritative_service(monkeypatch):
    captured = {}

    async def fake_start_agent_assessment(db, *, user_id, request):
        captured["db"] = db
        captured["user_id"] = user_id
        captured["request"] = request
        return SimpleNamespace(
            session_id=uuid4(),
            total_questions=2,
            questions=[],
        )

    monkeypatch.setattr(
        "src.services.agent_action_commit_service.start_agent_assessment",
        fake_start_agent_assessment,
    )
    user_id = uuid4()

    result = await AgentActionCommitService().commit_start_assessment(
        object(),
        user_id=user_id,
        payload={
            "canonical_unit_ids": ["unit-a"],
            "phase": "skip_verification",
            "question_budget": 12,
            "reason": "verify attention",
        },
        idempotency_key="idem-assessment",
    )

    assert captured["user_id"] == user_id
    assert captured["request"].canonical_unit_ids == ["unit-a"]
    assert captured["request"].question_budget == 12
    assert result["type"] == "start_assessment"
    assert result["totalQuestions"] == 2


async def test_commit_replan_forces_non_dry_run(monkeypatch):
    captured = {}

    async def fake_validate_replan_request(db, request, user):
        captured["request"] = request
        return SimpleNamespace(
            accepted=True,
            rejected_reason=None,
            impact={"mode": "replanned"},
        )

    monkeypatch.setattr(
        "src.services.agent_action_commit_service.validate_replan_request",
        fake_validate_replan_request,
    )

    result = await AgentActionCommitService().commit_replan(
        object(),
        user=SimpleNamespace(id=uuid4()),
        payload={
            "assessment_session_id": str(uuid4()),
            "source_canonical_unit_ids": ["unit-a"],
            "reason": "passed assessment",
        },
        idempotency_key="idem-replan",
    )

    assert captured["request"].dry_run is False
    assert captured["request"].source_canonical_unit_ids == ["unit-a"]
    assert result["accepted"] is True
    assert result["impact"] == {"mode": "replanned"}
