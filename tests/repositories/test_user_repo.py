"""
tests/repositories/test_user_repo.py
------------------------------------
RED phase: UserRepository — user/auth state data access.
"""

import pytest
from unittest.mock import AsyncMock, Mock

from src.models.user import User


@pytest.mark.asyncio
async def test_user_repo_importable():
    from src.repositories.user_repo import UserRepository  # noqa


@pytest.mark.asyncio
async def test_get_by_email_returns_none_for_unknown_user():
    from src.repositories.user_repo import UserRepository

    session = AsyncMock()
    result = Mock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    repo = UserRepository(session)
    result = await repo.get_by_email("missing@example.com")
    assert result is None


@pytest.mark.asyncio
async def test_get_by_email_normalizes_case():
    from src.repositories.user_repo import UserRepository

    user = User(
        email="learner@example.com",
        full_name="Learner Example",
        hashed_password="hashed",
    )
    session = AsyncMock()
    result = Mock()
    result.scalar_one_or_none.return_value = user
    session.execute.return_value = result

    repo = UserRepository(session)
    result = await repo.get_by_email("Learner@Example.com")

    assert result is not None
    assert result.email == user.email
    query = session.execute.await_args.args[0]
    compiled = str(query.compile(compile_kwargs={"literal_binds": True}))
    assert "learner@example.com" in compiled
