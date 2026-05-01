from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from src.services.agent_graph_contracts import PendingClarification
from src.services.agent_memory_compaction_service import AgentMemoryCompactionService


class AgentThreadMemoryStateStore:
    def __init__(
        self,
        conversation_repo,
        memory_compaction: AgentMemoryCompactionService,
    ):
        self.conversation_repo = conversation_repo
        self.memory_compaction = memory_compaction
        self._pending_clarifications: dict[str, PendingClarification] = {}

    async def load_memory_ref(self, conversation_id: str, user_id: str) -> str | None:
        if self.conversation_repo is None:
            return None
        memory = await self.conversation_repo.get_memory(UUID(str(conversation_id)), UUID(str(user_id)))
        if memory is None or not isinstance(memory.summary_json, dict):
            return None
        return memory.summary_json.get("memoryRef")

    def coerce_pending_clarification(self, value) -> PendingClarification | None:
        if isinstance(value, PendingClarification):
            return value
        if isinstance(value, dict):
            try:
                return PendingClarification.model_validate(value)
            except Exception:
                return None
        return None

    async def load_pending_clarification(
        self,
        conversation_id: str,
        user_id: str,
        thread_id: str,
    ) -> PendingClarification | None:
        cached = self._pending_clarifications.get(thread_id)
        if cached is not None:
            if cached.expires_at is not None and cached.expires_at <= datetime.now(UTC):
                self._pending_clarifications.pop(thread_id, None)
            else:
                return cached
        if self.conversation_repo is None:
            return None
        memory = await self.conversation_repo.get_memory(UUID(str(conversation_id)), UUID(str(user_id)))
        summary = memory.summary_json if memory and isinstance(memory.summary_json, dict) else {}
        stored = summary.get("pendingClarification")
        if not isinstance(stored, dict) or stored.get("threadId") != thread_id:
            return None
        pending = self.coerce_pending_clarification(stored.get("clarification"))
        if pending is None:
            return None
        if pending.expires_at is not None and pending.expires_at <= datetime.now(UTC):
            await self.persist_pending_clarification(
                conversation_id=conversation_id,
                user_id=user_id,
                thread_id=thread_id,
                pending=None,
            )
            return None
        self._pending_clarifications[thread_id] = pending
        return pending

    async def persist_pending_clarification(
        self,
        *,
        conversation_id: str,
        user_id: str,
        thread_id: str,
        pending: PendingClarification | None,
    ) -> None:
        if pending is None:
            self._pending_clarifications.pop(thread_id, None)
        else:
            self._pending_clarifications[thread_id] = pending
        if self.conversation_repo is None:
            return
        conversation_uuid = UUID(str(conversation_id))
        user_uuid = UUID(str(user_id))
        memory = await self.conversation_repo.get_memory(conversation_uuid, user_uuid)
        summary = dict(memory.summary_json) if memory and isinstance(memory.summary_json, dict) else {}
        if pending is None:
            existing = summary.get("pendingClarification")
            if not isinstance(existing, dict) or existing.get("threadId") != thread_id:
                return
            summary.pop("pendingClarification", None)
        else:
            summary["pendingClarification"] = {
                "threadId": thread_id,
                "clarification": pending.model_dump(mode="json"),
            }
        await self.conversation_repo.upsert_memory(
            conversation_id=conversation_uuid,
            user_id=user_uuid,
            summary_status=getattr(memory, "summary_status", None) or "fresh",
            recent_message_window=getattr(
                memory,
                "recent_message_window",
                self.memory_compaction.max_recent_turns,
            ),
            summary_json=summary,
            last_updated_at=datetime.now(UTC),
        )

    async def compact_if_needed(self, conversation_id: str, user_id: str) -> None:
        if self.conversation_repo is None:
            return
        conversation_uuid = UUID(str(conversation_id))
        user_uuid = UUID(str(user_id))
        messages = await self.conversation_repo.list_messages(conversation_uuid, user_uuid, limit=200)
        if not self.memory_compaction.should_compact(messages):
            return
        memory = await self.conversation_repo.get_memory(conversation_uuid, user_uuid)
        previous_summary = memory.summary_json if memory and isinstance(memory.summary_json, dict) else {}
        pending_clarification = previous_summary.get("pendingClarification")
        compacted = self.memory_compaction.compact(
            messages,
            pending_action=None,
            active_slots={},
            clarification_target=pending_clarification
            if isinstance(pending_clarification, dict)
            else None,
            previous_summary_version=int(previous_summary.get("summaryVersion") or 0),
        )
        memory_ref = f"agent_memory:{conversation_id}:v{compacted.summary_version}"
        summary_json = {
            "memoryRef": memory_ref,
            "summaryVersion": compacted.summary_version,
            **compacted.summary,
            "activeSlots": compacted.active_slots,
            "pendingAction": compacted.pending_action,
            "clarificationTarget": compacted.clarification_target,
        }
        if isinstance(pending_clarification, dict):
            summary_json["pendingClarification"] = pending_clarification
        await self.conversation_repo.upsert_memory(
            conversation_id=conversation_uuid,
            user_id=user_uuid,
            summary_status="fresh",
            recent_message_window=self.memory_compaction.max_recent_turns,
            summary_json=summary_json,
            last_updated_at=datetime.now(UTC),
        )
