"""
database.py
-----------
Async SQLAlchemy engine + session factory using asyncpg driver.
Provides get_async_db() dependency for FastAPI async routes.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.config import settings

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
def _build_async_engine(*, use_pool: bool):
    kwargs = {
        "echo": settings.db_echo,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }
    if use_pool:
        kwargs.update(
            {
                "pool_size": settings.db_pool_size,
                "max_overflow": settings.db_max_overflow,
            }
        )
    else:
        kwargs["poolclass"] = NullPool
    return create_async_engine(settings.database_url, **kwargs)


engine = _build_async_engine(use_pool=True)

# Dedicated no-pool engine for sync tutor helpers that call asyncio.run() in a
# threadpool. Reusing pooled asyncpg connections across event loops causes
# "Future attached to a different loop" failures.
tutor_thread_engine = _build_async_engine(use_pool=False)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Backward-compatible alias used by newer course-platform services.
async_session_factory = async_session

tutor_thread_async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=tutor_thread_engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession; automatically commit on success, rollback on error."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Utility: create / drop all tables (useful for testing / first-run)
# ---------------------------------------------------------------------------
async def create_all_tables() -> None:
    """Create all tables defined in the metadata (dev / test only)."""
    from src.models.base import Base  # avoid circular import at module level

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)


async def drop_all_tables() -> None:
    """Drop all tables (dev / test only)."""
    from src.models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
