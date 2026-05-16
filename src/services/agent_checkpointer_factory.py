from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.config import settings
from src.services.agent_error_codes import agent_system_error_message

_postgres_setup_done = False
_postgres_setup_lock = asyncio.Lock()


class AgentCheckpointerUnavailableError(RuntimeError):
    def to_response(self, conversation_id: str = "", message_id: str = ""):
        from src.schemas.agent import AgentAnswer, AgentChatResponse, AgentFallback, AgentWarning

        return AgentChatResponse(
            conversation_id=conversation_id,
            message_id=message_id,
            answer=AgentAnswer(
                markdown=agent_system_error_message("AGENT_CHECKPOINTER_UNAVAILABLE"),
                confidence="fallback",
            ),
            warning=AgentWarning(
                type="agent_unavailable",
                message="AGENT_CHECKPOINTER_UNAVAILABLE",
            ),
            fallback=AgentFallback(
                reason="agent_unavailable",
                message="The durable graph checkpointer is unavailable.",
                errorCode="AGENT_CHECKPOINTER_UNAVAILABLE",
            ),
        )


def langgraph_postgres_url(database_url: str) -> str:
    def _to_psycopg_url(url: str) -> str:
        parts = urlsplit(url)
        query = parse_qsl(parts.query, keep_blank_values=True)
        rewritten_query = []
        for key, value in query:
            if key == "ssl":
                rewritten_query.append(("sslmode", value))
            else:
                rewritten_query.append((key, value))

        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                urlencode(rewritten_query),
                parts.fragment,
            )
        )

    if database_url.startswith("postgresql+asyncpg://"):
        return _to_psycopg_url(
            "postgresql://" + database_url.removeprefix("postgresql+asyncpg://")
        )
    if database_url.startswith("postgresql+psycopg://"):
        return "postgresql://" + database_url.removeprefix("postgresql+psycopg://")
    if database_url.startswith("postgres://"):
        return "postgresql://" + database_url.removeprefix("postgres://")
    return database_url


async def _setup_postgres_checkpointer_once(checkpointer) -> None:
    global _postgres_setup_done
    if _postgres_setup_done:
        return
    async with _postgres_setup_lock:
        if _postgres_setup_done:
            return
        await checkpointer.setup()
        _postgres_setup_done = True


@asynccontextmanager
async def build_agent_graph_checkpointer(
    *,
    app_settings=settings,
) -> AsyncIterator[object | None]:
    backend = str(app_settings.agent_graph_checkpointer_backend or "").strip().lower()
    if backend == "memory":
        yield None
        return
    if backend != "postgres":
        raise AgentCheckpointerUnavailableError(f"unsupported_checkpointer_backend:{backend}")

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional production package
        raise AgentCheckpointerUnavailableError(
            "langgraph_postgres_checkpointer_not_installed"
        ) from exc

    db_uri = langgraph_postgres_url(app_settings.database_url)
    async with AsyncPostgresSaver.from_conn_string(db_uri) as checkpointer:
        if app_settings.agent_graph_checkpointer_setup:
            await _setup_postgres_checkpointer_once(checkpointer)
        yield checkpointer
