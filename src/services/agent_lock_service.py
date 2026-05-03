from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.agent_graph_contracts import AgentInProgressError


def advisory_lock_key(thread_id: str) -> int:
    digest = hashlib.sha256(thread_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


class AgentThreadLock:
    def __init__(self, session: AsyncSession):
        self.session = session

    @asynccontextmanager
    async def acquire(self, *, conversation_id: str, thread_id: str, graph_run_id: str):
        result = await self.session.execute(
            text("SELECT pg_try_advisory_xact_lock(:key)"),
            {"key": advisory_lock_key(thread_id)},
        )
        if not bool(result.scalar()):
            raise AgentInProgressError(
                conversation_id=conversation_id,
                thread_id=thread_id,
                graph_run_id=graph_run_id,
                retry_after_ms=1000,
            )
        yield
