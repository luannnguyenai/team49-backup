from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_async_db
from src.repositories.agent_graph_repo import AgentGraphRepository
from src.services.agent_pending_action_janitor import AgentPendingActionJanitor


agent_ops_router = APIRouter(prefix="/api/agent/ops", tags=["agent-ops"])


class AgentJanitorResponse(BaseModel):
    expired_actions: int


def require_agent_ops_token(x_admin_token: str | None = Header(default=None)) -> None:
    if not settings.admin_token:
        raise HTTPException(status_code=403, detail="agent_ops_disabled")
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=403, detail="invalid_admin_token")


@agent_ops_router.post(
    "/pending-actions/janitor",
    response_model=AgentJanitorResponse,
    dependencies=[Depends(require_agent_ops_token)],
)
async def run_pending_action_janitor(
    db: AsyncSession = Depends(get_async_db),
) -> AgentJanitorResponse:
    expired = await AgentPendingActionJanitor(AgentGraphRepository(db)).run_once()
    return AgentJanitorResponse(expired_actions=expired)
