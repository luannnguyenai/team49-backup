from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.schemas.quiz import QuizStartResponse


pytestmark = pytest.mark.anyio


async def override_db():
    yield object()


@pytest.fixture(autouse=True)
def inline_quiz_route_overrides():
    user = SimpleNamespace(id=uuid4(), is_onboarded=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_async_db] = override_db
    try:
        yield user
    finally:
        app.dependency_overrides.clear()


async def test_quiz_start_route_accepts_inline_checkpoint_payload(inline_quiz_route_overrides):
    learning_unit_id = uuid4()
    expected = QuizStartResponse(
        session_id=uuid4(),
        learning_unit_id=learning_unit_id,
        total_questions=3,
        questions=[],
        source="inline_video",
        checkpoint="midpoint",
    )

    with patch("src.routers.quiz.start_quiz", new=AsyncMock(return_value=expected)) as start_quiz:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/quiz/start",
                json={
                    "learning_unit_id": str(learning_unit_id),
                    "count": 3,
                    "source": "inline_video",
                    "checkpoint": "midpoint",
                    "exclude_item_ids": ["item_a", "item_b"],
                },
            )

    assert response.status_code == 201
    assert response.json()["source"] == "inline_video"
    assert response.json()["checkpoint"] == "midpoint"
    start_quiz.assert_awaited_once_with(
        ANY,
        inline_quiz_route_overrides.id,
        learning_unit_id,
        count=3,
        source="inline_video",
        checkpoint="midpoint",
        exclude_item_ids=["item_a", "item_b"],
    )


async def test_quiz_start_route_rejects_invalid_checkpoint(inline_quiz_route_overrides):
    learning_unit_id = uuid4()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/quiz/start",
            json={
                "learning_unit_id": str(learning_unit_id),
                "source": "inline_video",
                "checkpoint": "chapter_break",
            },
        )

    assert response.status_code == 422


async def test_quiz_history_route_forwards_only_learning_unit_id(inline_quiz_route_overrides):
    learning_unit_id = uuid4()

    with patch("src.routers.quiz.get_quiz_history", new=AsyncMock(return_value={"total": 0, "items": []})) as get_quiz_history:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get(
                "/api/quiz/history",
                params={
                    "learning_unit_id": str(learning_unit_id),
                    "topic_id": str(uuid4()),
                },
            )

    assert response.status_code == 200
    get_quiz_history.assert_awaited_once_with(ANY, inline_quiz_route_overrides.id, learning_unit_id)
