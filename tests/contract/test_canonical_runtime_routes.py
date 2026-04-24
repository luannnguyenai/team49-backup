from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.models.content import BloomLevel, DifficultyBucket
from src.models.learning import PathAction, PathStatus
from src.schemas.module_test import (
    LearningUnitQuestionsGroup,
    ModuleTestStartResponse,
    QuestionForModuleTest,
)
from src.schemas.quiz import QuestionForQuiz, QuizStartResponse


pytestmark = pytest.mark.anyio


async def override_db():
    yield object()


@pytest.fixture(autouse=True)
def canonical_runtime_route_overrides():
    user = SimpleNamespace(id=uuid4(), is_onboarded=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_async_db] = override_db
    try:
        yield user
    finally:
        app.dependency_overrides.clear()


async def test_quiz_start_route_uses_learning_unit_contract():
    learning_unit_id = uuid4()
    session_id = uuid4()
    question_id = uuid4()
    expected = QuizStartResponse(
        session_id=session_id,
        learning_unit_id=learning_unit_id,
        total_questions=1,
        questions=[
            QuestionForQuiz(
                id=question_id,
                item_id="cs231n-q1",
                learning_unit_id=learning_unit_id,
                bloom_level=BloomLevel.understand,
                difficulty_bucket=DifficultyBucket.medium,
                stem_text="What does convolution share across spatial locations?",
                option_a="Weights",
                option_b="Labels",
                option_c="Losses",
                option_d="Epochs",
                time_expected_seconds=45,
            )
        ],
    )

    with patch("src.routers.quiz.start_quiz", new=AsyncMock(return_value=expected)) as start_quiz:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/quiz/start",
                json={"learning_unit_id": str(learning_unit_id)},
            )

    assert response.status_code == 201
    payload = response.json()
    assert payload["learning_unit_id"] == str(learning_unit_id)
    assert payload["questions"][0]["learning_unit_id"] == str(learning_unit_id)
    assert payload["questions"][0]["item_id"] == "cs231n-q1"
    assert "correct_answer" not in payload["questions"][0]
    start_quiz.assert_awaited_once()


async def test_module_test_start_route_uses_section_contract():
    section_id = uuid4()
    learning_unit_id = uuid4()
    expected = ModuleTestStartResponse(
        session_id=uuid4(),
        section_id=section_id,
        section_title="CNN Foundations",
        total_learning_units=1,
        total_questions=1,
        learning_units=[
            LearningUnitQuestionsGroup(
                learning_unit_id=learning_unit_id,
                learning_unit_title="Convolution basics",
                questions=[
                    QuestionForModuleTest(
                        id=uuid4(),
                        item_id="cs231n-module-q1",
                        learning_unit_id=learning_unit_id,
                        bloom_level=BloomLevel.apply,
                        difficulty_bucket=DifficultyBucket.hard,
                        stem_text="Which padding preserves feature map width?",
                        option_a="Valid",
                        option_b="Same",
                        option_c="Stride",
                        option_d="Pooling",
                        time_expected_seconds=60,
                    )
                ],
            )
        ],
    )

    with patch(
        "src.routers.module_test.start_module_test",
        new=AsyncMock(return_value=expected),
    ) as start_module_test:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/module-test/start",
                json={"section_id": str(section_id)},
            )

    assert response.status_code == 201
    payload = response.json()
    assert payload["section_id"] == str(section_id)
    assert payload["learning_units"][0]["learning_unit_id"] == str(learning_unit_id)
    assert payload["learning_units"][0]["questions"][0]["item_id"] == "cs231n-module-q1"
    assert "correct_answer" not in payload["learning_units"][0]["questions"][0]
    start_module_test.assert_awaited_once()


async def test_learning_path_status_route_returns_learning_unit_status():
    path_id = uuid4()
    learning_unit_id = uuid4()
    updated_at = datetime.now(UTC)
    expected = SimpleNamespace(
        id=path_id,
        learning_unit_id=learning_unit_id,
        action=PathAction.deep_practice,
        status=PathStatus.skipped,
        updated_at=updated_at,
    )

    with patch(
        "src.routers.learning_path.update_path_status",
        new=AsyncMock(return_value=expected),
    ) as update_path_status:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.put(
                f"/api/learning-path/{path_id}/status",
                json={"status": "skipped"},
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(path_id)
    assert payload["learning_unit_id"] == str(learning_unit_id)
    assert payload["status"] == "skipped"
    assert "topic_id" not in payload
    update_path_status.assert_awaited_once()
