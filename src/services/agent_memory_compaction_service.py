from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CompactedThreadMemory:
    summary_version: int
    summary: dict[str, Any]
    recent_messages: list[Any]
    pending_action: dict[str, Any] | None
    active_slots: dict[str, Any]
    clarification_target: dict[str, Any] | None


class AgentMemoryCompactionService:
    def __init__(self, max_recent_turns: int = 10, max_messages_before_compaction: int = 30):
        self.max_recent_turns = max_recent_turns
        self.max_messages_before_compaction = max_messages_before_compaction

    def should_compact(self, messages: list[Any]) -> bool:
        return len(messages) > self.max_messages_before_compaction

    def compact(
        self,
        messages: list[Any],
        pending_action: dict[str, Any] | None,
        active_slots: dict[str, Any],
        clarification_target: dict[str, Any] | None,
        previous_summary_version: int = 0,
    ) -> CompactedThreadMemory:
        recent = messages[-self.max_recent_turns :]
        older = messages[: max(0, len(messages) - self.max_recent_turns)]
        summary_text = "\n".join(
            f"{getattr(message, 'role', 'unknown')}: {getattr(message, 'markdown', '')}"
            for message in older
        )
        return CompactedThreadMemory(
            summary_version=previous_summary_version + 1,
            summary={"summaryText": summary_text, "messageCount": len(older)},
            recent_messages=recent,
            pending_action=pending_action,
            active_slots=active_slots,
            clarification_target=clarification_target,
        )
