"""
repositories/planner_audit_repo.py
----------------------------------
Data access for planner audit persistence tables.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.learning import PlanHistory, PlannerSessionState, RationaleLog


class PlannerAuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_plan(self, **plan_data) -> PlanHistory:
        obj = PlanHistory(**plan_data)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def add_rationale(self, **rationale_data) -> RationaleLog:
        obj = RationaleLog(**rationale_data)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def get_latest_plan_for_user(
        self,
        user_id: UUID,
        *,
        trigger: str | None = None,
    ) -> PlanHistory | None:
        stmt = select(PlanHistory).where(PlanHistory.user_id == user_id)
        if trigger is not None:
            stmt = stmt.where(PlanHistory.trigger == trigger)
        result = await self.session.execute(stmt.order_by(PlanHistory.created_at.desc()).limit(1))
        return result.scalar_one_or_none()

    async def get_session_state(
        self,
        user_id: UUID,
        session_id: str,
    ) -> PlannerSessionState | None:
        result = await self.session.execute(
            select(PlannerSessionState).where(
                PlannerSessionState.user_id == user_id,
                PlannerSessionState.session_id == session_id,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_session_state(
        self,
        user_id: UUID,
        session_id: str,
        **state_data,
    ) -> PlannerSessionState:
        values = {"user_id": user_id, "session_id": session_id, **state_data}
        stmt = (
            pg_insert(PlannerSessionState)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_planner_session_state_user_session",
                set_=state_data,
            )
            .returning(PlannerSessionState)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()
