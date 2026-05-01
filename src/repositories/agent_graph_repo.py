from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent_graph import AgentGraphRun, AgentPendingAction, AgentResponsePayload
from src.schemas.agent import AgentChatResponse


ACTIVE_RUN_STATUSES = {"created", "running", "interrupted"}


class AgentGraphRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_run_by_incoming_message(
        self,
        conversation_id: str,
        thread_id: str,
        incoming_message_id: str,
    ) -> AgentGraphRun | None:
        result = await self.session.execute(
            select(AgentGraphRun).where(
                AgentGraphRun.conversation_id == UUID(str(conversation_id)),
                AgentGraphRun.thread_id == thread_id,
                AgentGraphRun.incoming_message_id == incoming_message_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_completed_response_by_incoming_message(
        self,
        *,
        conversation_id: str,
        thread_id: str,
        incoming_message_id: str,
    ) -> AgentChatResponse | None:
        run = await self.get_run_by_incoming_message(
            conversation_id,
            thread_id,
            incoming_message_id,
        )
        if run is None or run.status != "succeeded" or not run.response_ref:
            return None
        return await self.load_response_payload(run.response_ref)

    async def get_active_run(self, *, thread_id: str) -> SimpleNamespace | None:
        result = await self.session.execute(
            select(AgentGraphRun)
            .where(AgentGraphRun.thread_id == thread_id, AgentGraphRun.status.in_(ACTIVE_RUN_STATUSES))
            .order_by(AgentGraphRun.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return SimpleNamespace(graph_run_id=str(row.id), status=row.status)

    async def create_run(
        self,
        *,
        conversation_id: str,
        thread_id: str,
        incoming_message_id: str,
    ) -> SimpleNamespace:
        row = AgentGraphRun(
            conversation_id=UUID(str(conversation_id)),
            thread_id=thread_id,
            incoming_message_id=incoming_message_id,
            status="created",
        )
        self.session.add(row)
        await self.session.flush()
        return SimpleNamespace(graph_run_id=str(row.id))

    async def mark_run_running(self, graph_run_id: str) -> None:
        await self._mark_run_status(graph_run_id, "running")

    async def mark_run_succeeded(
        self,
        graph_run_id: str,
        *,
        response_ref: str,
        checkpoint_id: str | None = None,
    ) -> None:
        await self.session.execute(
            update(AgentGraphRun)
            .where(AgentGraphRun.id == UUID(str(graph_run_id)))
            .values(
                status="succeeded",
                response_ref=response_ref,
                checkpoint_id=checkpoint_id,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.flush()

    async def mark_run_interrupted(
        self,
        graph_run_id: str,
        *,
        response_ref: str | None = None,
        checkpoint_id: str | None = None,
    ) -> None:
        await self.session.execute(
            update(AgentGraphRun)
            .where(AgentGraphRun.id == UUID(str(graph_run_id)))
            .values(
                status="interrupted",
                response_ref=response_ref,
                checkpoint_id=checkpoint_id,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.flush()

    async def mark_run_failed(self, graph_run_id: str, *, error: str, retryable: bool) -> None:
        status = "failed_retryable" if retryable else "failed_terminal"
        await self.session.execute(
            update(AgentGraphRun)
            .where(AgentGraphRun.id == UUID(str(graph_run_id)))
            .values(status=status, error=error, updated_at=datetime.now(UTC))
        )
        await self.session.flush()

    async def _mark_run_status(self, graph_run_id: str, status: str) -> None:
        await self.session.execute(
            update(AgentGraphRun)
            .where(AgentGraphRun.id == UUID(str(graph_run_id)))
            .values(status=status, updated_at=datetime.now(UTC))
        )
        await self.session.flush()

    async def store_response_payload(
        self,
        *,
        graph_run_id: str,
        response: AgentChatResponse,
        deterministic_key: str,
    ) -> str:
        response_ref = f"agent_response:{deterministic_key}"
        payload = response.model_dump(mode="json", by_alias=True)
        stmt = (
            pg_insert(AgentResponsePayload)
            .values(
                response_ref=response_ref,
                graph_run_id=UUID(str(graph_run_id)),
                payload_json=payload,
            )
            .on_conflict_do_update(
                index_elements=[AgentResponsePayload.response_ref],
                set_={
                    "graph_run_id": UUID(str(graph_run_id)),
                    "payload_json": payload,
                    "updated_at": datetime.now(UTC),
                },
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()
        return response_ref

    async def load_response_payload(self, response_ref: str) -> AgentChatResponse | None:
        result = await self.session.execute(
            select(AgentResponsePayload).where(AgentResponsePayload.response_ref == response_ref)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return AgentChatResponse.model_validate(row.payload_json)

    async def create_pending_action(
        self,
        *,
        conversation_id: str,
        thread_id: str,
        user_id: str,
        action_type: str,
        payload: dict,
        payload_version: int,
        idempotency_key: str,
        expires_at: datetime,
    ) -> AgentPendingAction:
        action_id = f"act_{uuid4()}"
        row = AgentPendingAction(
            action_id=action_id,
            conversation_id=UUID(str(conversation_id)),
            thread_id=thread_id,
            user_id=UUID(str(user_id)),
            type=action_type,
            status="awaiting_confirmation",
            payload_json=payload,
            payload_version=payload_version,
            idempotency_key=idempotency_key,
            expires_at=expires_at,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_pending_action(self, *, action_id: str) -> AgentPendingAction | None:
        result = await self.session.execute(
            select(AgentPendingAction).where(AgentPendingAction.action_id == action_id)
        )
        return result.scalar_one_or_none()

    async def get_committed_action_result(self, action_id: str) -> dict | None:
        action = await self.get_pending_action(action_id=action_id)
        if action is None or action.status != "committed":
            return None
        return action.result_json

    async def mark_action_committed(self, action_id: str, *, result: dict) -> None:
        await self.session.execute(
            update(AgentPendingAction)
            .where(AgentPendingAction.action_id == action_id)
            .values(
                status="committed",
                result_json=result,
                committed_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.flush()

    async def mark_action_cancelled(self, action_id: str) -> None:
        await self.session.execute(
            update(AgentPendingAction)
            .where(AgentPendingAction.action_id == action_id)
            .values(status="cancelled", updated_at=datetime.now(UTC))
        )
        await self.session.flush()

    async def mark_action_expired(self, action_id: str) -> None:
        await self.session.execute(
            update(AgentPendingAction)
            .where(AgentPendingAction.action_id == action_id)
            .values(status="expired", updated_at=datetime.now(UTC))
        )
        await self.session.flush()

    async def expire_pending_actions(self, now: datetime) -> int:
        result = await self.session.execute(
            update(AgentPendingAction)
            .where(
                AgentPendingAction.status == "awaiting_confirmation",
                AgentPendingAction.expires_at <= now,
            )
            .values(status="expired", updated_at=now)
        )
        await self.session.flush()
        return int(result.rowcount or 0)
