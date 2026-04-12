"""
tests/conftest.py
-----------------
Pytest fixtures shared across all test modules.

Requirements:
  - Async PostgreSQL test database (set DATABASE_URL env var to a test DB)
  - Each test gets a fresh transaction that is rolled back on teardown

Usage:
    pytest tests/ -v
    # With env override:
    DATABASE_URL=postgresql+asyncpg://test:test@localhost/test_ai_learning pytest tests/
"""

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.api.app import app
from src.config import settings
from src.database import get_async_db
from src.models.base import Base


# ---------------------------------------------------------------------------
# Event loop — use one loop for the whole test session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Test database engine (re-created once per session)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create all tables in the test DB, yield the engine, drop tables after."""
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ---------------------------------------------------------------------------
# Per-test transaction rollback (keeps tests isolated)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_session(test_engine):
    """
    Yield an AsyncSession wrapped in a savepoint.
    Any changes made during the test are rolled back automatically.
    """
    async with test_engine.connect() as conn:
        await conn.begin()
        session_factory = async_sessionmaker(bind=conn, expire_on_commit=False)
        session: AsyncSession = session_factory()
        await conn.begin_nested()  # savepoint

        yield session

        await session.close()
        await conn.rollback()


# ---------------------------------------------------------------------------
# FastAPI test client with injected DB
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """AsyncClient wired to the FastAPI app with the test DB session injected."""

    async def override_db():
        yield db_session

    app.dependency_overrides[get_async_db] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
