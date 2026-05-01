from __future__ import annotations

from datetime import UTC, datetime


class AgentPendingActionJanitor:
    def __init__(self, graph_repo):
        self.graph_repo = graph_repo

    async def expire_pending_actions(self, now: datetime | None = None) -> int:
        return await self.graph_repo.expire_pending_actions(now or datetime.now(UTC))
