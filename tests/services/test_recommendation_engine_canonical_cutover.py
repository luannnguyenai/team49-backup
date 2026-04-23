from uuid import uuid4

import pytest

from src.exceptions import ValidationError
from src.models.learning import PathAction, PathStatus
from src.schemas.learning_path import PathItemResponse
from src.services import recommendation_engine


@pytest.mark.asyncio
async def test_generate_learning_path_uses_canonical_branch_when_flag_enabled(monkeypatch):
    captured = {}

    async def fake_generate_canonical_path(db, user, request):
        captured["called"] = True
        return "canonical-response"

    monkeypatch.setattr(recommendation_engine.settings, "read_canonical_planner_enabled", True)
    monkeypatch.setattr(recommendation_engine, "_generate_canonical_learning_path", fake_generate_canonical_path)

    result = await recommendation_engine.generate_learning_path(object(), object(), object())

    assert result == "canonical-response"
    assert captured["called"] is True


@pytest.mark.asyncio
async def test_generate_learning_path_blocks_legacy_branch_when_disabled(monkeypatch):
    monkeypatch.setattr(recommendation_engine.settings, "read_canonical_planner_enabled", False)
    monkeypatch.setattr(recommendation_engine.settings, "allow_legacy_planner_writes", False)

    with pytest.raises(ValidationError, match="Legacy planner writes are disabled"):
        await recommendation_engine.generate_learning_path(object(), object(), object())


def test_path_item_response_allows_canonical_unit_without_topic_id():
    item = PathItemResponse(
        id=uuid4(),
        topic_id=None,
        topic_name="Unit 1",
        module_name="canonical_unit",
        action=PathAction.deep_practice,
        estimated_hours=0.5,
        order_index=0,
        week_number=None,
        status=PathStatus.pending,
        learning_unit_id=uuid4(),
        canonical_unit_id="local::lecture01::seg1",
    )

    assert item.topic_id is None
    assert item.canonical_unit_id == "local::lecture01::seg1"
