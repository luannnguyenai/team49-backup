from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_waived_unit_repo_importable():
    from src.repositories.waived_unit_repo import WaivedUnitRepository  # noqa


@pytest.mark.asyncio
async def test_waived_unit_repo_upsert_creates_and_updates():
    from src.repositories.waived_unit_repo import WaivedUnitRepository

    session = AsyncMock()
    user_id = uuid4()
    learning_unit_id = uuid4()
    created = Mock(
        id=uuid4(),
        user_id=user_id,
        learning_unit_id=learning_unit_id,
        evidence_items=["item_1", "item_2"],
    )
    updated = Mock(
        id=created.id,
        evidence_items=["item_3"],
        mastery_lcb_at_waive=0.88,
        skip_quiz_score=96.0,
    )
    result_1 = Mock()
    result_1.scalar_one.return_value = created
    result_2 = Mock()
    result_2.scalar_one.return_value = updated
    session.execute.side_effect = [result_1, result_2]

    repo = WaivedUnitRepository(session)

    created_row = await repo.upsert(
        user_id=user_id,
        learning_unit_id=learning_unit_id,
        evidence_items=["item_1", "item_2"],
        mastery_lcb_at_waive=0.81,
        skip_quiz_score=92.0,
    )
    assert created_row.user_id == user_id
    assert created_row.learning_unit_id == learning_unit_id
    assert created_row.evidence_items == ["item_1", "item_2"]

    updated_row = await repo.upsert(
        user_id=user_id,
        learning_unit_id=learning_unit_id,
        evidence_items=["item_3"],
        mastery_lcb_at_waive=0.88,
        skip_quiz_score=96.0,
    )
    assert updated_row.id == created.id
    assert updated_row.evidence_items == ["item_3"]
    assert updated_row.mastery_lcb_at_waive == pytest.approx(0.88)
    assert updated_row.skip_quiz_score == pytest.approx(96.0)
    assert session.execute.await_count == 2
    assert session.flush.await_count == 2


@pytest.mark.asyncio
async def test_waived_unit_repo_list_for_user():
    from src.repositories.waived_unit_repo import WaivedUnitRepository

    session = AsyncMock()
    row = Mock(learning_unit_id=uuid4())
    scalar_result = Mock()
    scalar_result.all.return_value = [row]
    result = Mock()
    result.scalars.return_value = scalar_result
    session.execute.return_value = result

    repo = WaivedUnitRepository(session)

    result = await repo.list_for_user(uuid4())

    assert len(result) == 1
    assert result[0].learning_unit_id == row.learning_unit_id
