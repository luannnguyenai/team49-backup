from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.database import get_async_db
from src.dependencies.auth import get_current_user


pytestmark = pytest.mark.anyio


async def _client_for_user(user_id):
    async def override_user():
        return SimpleNamespace(id=user_id)

    async def override_db():
        yield SimpleNamespace()

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_async_db] = override_db
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


async def test_assessment_workflow_start_validates_event_and_returns_proposal():
    user_id = uuid4()
    with (
        patch(
            "src.routers.agent._agent_context_for_user",
            new=AsyncMock(return_value=SimpleNamespace(allowed_course_ids=["CS231n"])),
        ),
        patch(
            "src.routers.agent._validate_workflow_candidates_in_scope",
            new=AsyncMock(return_value=None),
        ),
    ):
        client = await _client_for_user(user_id)
        try:
            bad = await client.post(
                "/api/agent/assessment-workflows",
                json={"event": "resume", "candidateCanonicalUnitIds": ["unit-cnn"]},
            )
            assert bad.status_code == 422

            response = await client.post(
                "/api/agent/assessment-workflows",
                json={
                    "event": "start",
                    "candidateCanonicalUnitIds": ["unit-cnn"],
                    "questionBudget": 24,
                    "phase": "skip_verification",
                },
            )
        finally:
            await client.aclose()
            app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "waiting_user_approval"
    assert payload["interrupt"]["estimatedQuestions"] == 24


async def test_assessment_workflow_resume_requires_owner_and_resume_event():
    first_user = uuid4()
    second_user = uuid4()
    with (
        patch(
            "src.routers.agent._agent_context_for_user",
            new=AsyncMock(return_value=SimpleNamespace(allowed_course_ids=["CS231n"])),
        ),
        patch(
            "src.routers.agent._validate_workflow_candidates_in_scope",
            new=AsyncMock(return_value=None),
        ),
    ):
        client = await _client_for_user(first_user)
        try:
            started = await client.post(
                "/api/agent/assessment-workflows",
                json={
                    "event": "start",
                    "candidateCanonicalUnitIds": ["unit-cnn"],
                    "questionBudget": 20,
                },
            )
        finally:
            await client.aclose()
            app.dependency_overrides.clear()

    workflow_id = started.json()["workflowId"]

    client = await _client_for_user(first_user)
    try:
        bad_event = await client.post(
            f"/api/agent/assessment-workflows/{workflow_id}/resume",
            json={"event": "start", "decision": {"action": "approve"}},
        )
        assert bad_event.status_code == 422
    finally:
        await client.aclose()
        app.dependency_overrides.clear()

    client = await _client_for_user(second_user)
    try:
        forbidden = await client.post(
            f"/api/agent/assessment-workflows/{workflow_id}/resume",
            json={"event": "resume", "decision": {"action": "approve"}},
        )
    finally:
        await client.aclose()
        app.dependency_overrides.clear()

    assert forbidden.status_code == 403
