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

# Load .env into os.environ BEFORE any src imports so LangChain/OpenAI
# can find the API keys at module-level initialization time.
import asyncio

from dotenv import load_dotenv
load_dotenv()

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.api.app import app
from src.config import settings
from src.database import get_async_db
from src.models.base import Base


# ---------------------------------------------------------------------------
# Test database engine (re-created once per session)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_engine():
    """Per-test engine — avoids event-loop mismatch with session-scoped fixtures."""
    engine = create_async_engine(settings.database_url, echo=False)
    # Tables already exist (migrated via Alembic) — don't create/drop in tests.
    yield engine
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
    try:
        conn = await asyncio.wait_for(test_engine.connect(), timeout=2.0)
    except Exception as exc:
        pytest.skip(f"Test database unavailable: {exc}")

    async with conn:
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
async def client():
    """AsyncClient for routes that do not require DB overrides."""

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def db_client(db_session: AsyncSession):
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
