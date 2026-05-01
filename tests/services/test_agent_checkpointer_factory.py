from types import SimpleNamespace

import pytest

from src.services.agent_checkpointer_factory import (
    AgentCheckpointerUnavailableError,
    build_agent_graph_checkpointer,
    langgraph_postgres_url,
    _setup_postgres_checkpointer_once,
)


def test_langgraph_postgres_url_converts_asyncpg_sqlalchemy_url():
    assert (
        langgraph_postgres_url("postgresql+asyncpg://user:pass@localhost:5432/app")
        == "postgresql://user:pass@localhost:5432/app"
    )


def test_langgraph_postgres_url_converts_postgres_alias():
    assert (
        langgraph_postgres_url("postgres://user:pass@localhost:5432/app")
        == "postgresql://user:pass@localhost:5432/app"
    )


@pytest.mark.asyncio
async def test_memory_backend_yields_none_checkpointer():
    settings = SimpleNamespace(
        agent_graph_checkpointer_backend="memory",
        agent_graph_checkpointer_setup=False,
        database_url="postgresql+asyncpg://user:pass@localhost/app",
    )

    async with build_agent_graph_checkpointer(app_settings=settings) as checkpointer:
        assert checkpointer is None


@pytest.mark.asyncio
async def test_unknown_backend_fails_safe():
    settings = SimpleNamespace(
        agent_graph_checkpointer_backend="redis",
        agent_graph_checkpointer_setup=False,
        database_url="postgresql+asyncpg://user:pass@localhost/app",
    )

    with pytest.raises(AgentCheckpointerUnavailableError):
        async with build_agent_graph_checkpointer(app_settings=settings):
            pass


@pytest.mark.asyncio
async def test_postgres_setup_runs_once_per_process(monkeypatch):
    import src.services.agent_checkpointer_factory as factory

    calls = []

    class Checkpointer:
        async def setup(self):
            calls.append("setup")

    monkeypatch.setattr(factory, "_postgres_setup_done", False)

    await _setup_postgres_checkpointer_once(Checkpointer())
    await _setup_postgres_checkpointer_once(Checkpointer())

    assert calls == ["setup"]
