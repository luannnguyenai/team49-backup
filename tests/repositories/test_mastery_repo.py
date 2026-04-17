"""
tests/repositories/test_mastery_repo.py
-----------------------------------------
RED phase: MasteryRepository — upsert, get, bulk_get.
"""
import pytest
from uuid import uuid4

from src.models.learning import MasteryLevel


@pytest.mark.asyncio
async def test_mastery_repo_importable():
    from src.repositories.mastery_repo import MasteryRepository  # noqa


@pytest.mark.asyncio
async def test_get_by_user_topic_returns_none_if_not_exists(db_session):
    """get_by_user_topic trả về None nếu chưa có record."""
    from src.repositories.mastery_repo import MasteryRepository

    repo = MasteryRepository(db_session)
    result = await repo.get_by_user_topic(
        user_id=uuid4(),
        topic_id=uuid4(),
        kc_id=None,
    )
    assert result is None


@pytest.mark.asyncio
async def test_bulk_get_for_user_returns_empty_dict_for_new_user(db_session):
    """bulk_get_for_user trả về empty dict nếu user chưa có mastery."""
    from src.repositories.mastery_repo import MasteryRepository

    repo = MasteryRepository(db_session)
    result = await repo.bulk_get_for_user(
        user_id=uuid4(),
        topic_ids=[uuid4(), uuid4()],
    )
    assert isinstance(result, dict)
    assert len(result) == 0
