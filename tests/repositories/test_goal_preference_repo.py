from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_goal_preference_repo_importable():
    from src.repositories.goal_preference_repo import GoalPreferenceRepository  # noqa


@pytest.mark.asyncio
async def test_goal_preference_repo_upsert_creates_and_updates():
    from src.repositories.goal_preference_repo import GoalPreferenceRepository

    session = AsyncMock()
    created = Mock(
        user_id=uuid4(),
        goal_weights_json={"career": 0.7, "speed": 0.3},
        selected_course_ids=["course_cs231n"],
        derived_from_course_set_hash="hash-v1",
        notes=None,
    )
    updated = Mock(
        id=uuid4(),
        goal_weights_json={"career": 0.4, "depth": 0.6},
        selected_course_ids=["course_cs224n", "course_cs231n"],
        derived_from_course_set_hash="hash-v2",
        notes="updated",
    )
    result_1 = Mock()
    result_1.scalar_one.return_value = created
    result_2 = Mock()
    result_2.scalar_one.return_value = updated
    session.execute.side_effect = [result_1, result_2]

    repo = GoalPreferenceRepository(session)
    user_id = uuid4()

    created_row = await repo.upsert_for_user(
        user_id=user_id,
        goal_weights_json={"career": 0.7, "speed": 0.3},
        selected_course_ids=["course_cs231n"],
        derived_from_course_set_hash="hash-v1",
    )

    updated.id = created.id = uuid4()

    updated_row = await repo.upsert_for_user(
        user_id=user_id,
        goal_weights_json={"career": 0.4, "depth": 0.6},
        selected_course_ids=["course_cs224n", "course_cs231n"],
        derived_from_course_set_hash="hash-v2",
        notes="updated",
    )

    assert created_row.goal_weights_json == {"career": 0.7, "speed": 0.3}
    assert created_row.selected_course_ids == ["course_cs231n"]
    assert updated_row.id == created.id
    assert updated_row.goal_weights_json == {"career": 0.4, "depth": 0.6}
    assert updated_row.selected_course_ids == ["course_cs224n", "course_cs231n"]
    assert updated_row.derived_from_course_set_hash == "hash-v2"
    assert updated_row.notes == "updated"
    assert session.execute.await_count == 2
    assert session.flush.await_count == 2


@pytest.mark.asyncio
async def test_goal_preference_repo_get_by_user_returns_none_for_new_user():
    from src.repositories.goal_preference_repo import GoalPreferenceRepository

    session = AsyncMock()
    result = Mock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    repo = GoalPreferenceRepository(session)

    assert await repo.get_by_user_id(uuid4()) is None
