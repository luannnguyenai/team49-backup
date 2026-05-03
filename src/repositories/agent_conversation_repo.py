from __future__ import annotations

from uuid import UUID, uuid4

from datetime import UTC, datetime

from sqlalchemy import delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent_conversation import (
    AgentConversation,
    AgentConversationMemory,
    AgentConversationMessage,
)
from src.models.agent_graph import AgentGraphRun, AgentPendingAction


class AgentConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_conversations(self, user_id: UUID) -> list[AgentConversation]:
        result = await self.session.execute(
            select(AgentConversation)
            .where(AgentConversation.user_id == user_id)
            .order_by(desc(AgentConversation.updated_at))
            .limit(50)
        )
        return list(result.scalars().all())

    async def create_conversation(self, user_id: UUID, title: str = "New chat") -> AgentConversation:
        row = AgentConversation(
            user_id=user_id,
            title=title,
            preview="",
            message_count=0,
            thread_id=f"thread_{uuid4()}",
        )
        self.session.add(row)
        await self.session.flush()

        memory = AgentConversationMemory(
            conversation_id=row.id,
            thread_id=row.thread_id,
            user_id=user_id,
            summary_status="empty",
            recent_message_window=10,
            summary_json={},
            last_updated_at=None,
        )
        self.session.add(memory)
        await self.session.flush()
        await self.session.refresh(row)
        await self.session.refresh(memory)
        return row

    async def get_conversation(self, conversation_id: UUID, user_id: UUID) -> AgentConversation | None:
        result = await self.session.execute(
            select(AgentConversation).where(
                AgentConversation.id == conversation_id,
                AgentConversation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def rename_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID,
        title: str,
    ) -> AgentConversation | None:
        conversation = await self.get_conversation(conversation_id, user_id)
        if conversation is None:
            return None
        conversation.title = title
        await self.session.flush()
        await self.session.refresh(conversation)
        return conversation

    async def delete_conversation(self, conversation_id: UUID, user_id: UUID) -> bool:
        result = await self.session.execute(
            delete(AgentConversation).where(
                AgentConversation.id == conversation_id,
                AgentConversation.user_id == user_id,
            )
        )
        await self.session.flush()
        return bool(result.rowcount)

    async def clear_conversation(self, conversation_id: UUID, user_id: UUID) -> AgentConversation | None:
        conversation = await self.get_conversation(conversation_id, user_id)
        if conversation is None:
            return None

        await self.session.execute(
            delete(AgentPendingAction).where(
                AgentPendingAction.conversation_id == conversation_id,
                AgentPendingAction.user_id == user_id,
            )
        )
        await self.session.execute(
            delete(AgentGraphRun).where(AgentGraphRun.conversation_id == conversation_id)
        )
        await self.session.execute(
            delete(AgentConversationMessage).where(
                AgentConversationMessage.conversation_id == conversation_id,
                AgentConversationMessage.user_id == user_id,
            )
        )

        conversation.title = "New chat"
        conversation.preview = ""
        conversation.message_count = 0
        conversation.thread_id = f"thread_{uuid4()}"

        memory = await self.get_memory(conversation_id, user_id)
        if memory is not None:
            memory.thread_id = conversation.thread_id
            memory.summary_status = "empty"
            memory.recent_message_window = 10
            memory.summary_json = {}
            memory.last_updated_at = None

        await self.session.flush()
        await self.session.refresh(conversation)
        return conversation

    async def list_messages(
        self,
        conversation_id: UUID,
        user_id: UUID,
        limit: int = 100,
    ) -> list[AgentConversationMessage]:
        result = await self.session.execute(
            select(AgentConversationMessage)
            .where(
                AgentConversationMessage.conversation_id == conversation_id,
                AgentConversationMessage.user_id == user_id,
            )
            .order_by(AgentConversationMessage.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_message(
        self,
        conversation_id: UUID,
        user_id: UUID,
        role: str,
        markdown: str,
        citations: list[dict] | None = None,
        actions: list[dict] | None = None,
    ) -> AgentConversationMessage:
        row = AgentConversationMessage(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            markdown=markdown,
            citations_json=citations or [],
            actions_json=actions or [],
        )
        self.session.add(row)
        await self.session.flush()

        preview = markdown[:180]
        title = preview[:60] or "New chat"
        await self.session.execute(
            update(AgentConversation)
            .where(AgentConversation.id == conversation_id, AgentConversation.user_id == user_id)
            .values(
                preview=preview,
                title=title,
                message_count=AgentConversation.message_count + 1,
                updated_at=func.now(),
            )
        )
        await self.session.flush()
        return row

    async def get_memory(
        self,
        conversation_id: UUID,
        user_id: UUID,
        thread_id: str | None = None,
    ) -> AgentConversationMemory | None:
        filters = [
            AgentConversationMemory.conversation_id == conversation_id,
            AgentConversationMemory.user_id == user_id,
        ]
        if thread_id is not None:
            filters.append(AgentConversationMemory.thread_id == thread_id)
        result = await self.session.execute(
            select(AgentConversationMemory).where(*filters)
        )
        return result.scalar_one_or_none()

    async def upsert_memory(
        self,
        *,
        conversation_id: UUID,
        user_id: UUID,
        thread_id: str,
        summary_status: str,
        recent_message_window: int,
        summary_json: dict,
        last_updated_at: datetime | None = None,
    ) -> AgentConversationMemory:
        memory = await self.get_memory(conversation_id, user_id, thread_id=thread_id)
        now = last_updated_at or datetime.now(UTC)
        if memory is None:
            memory = AgentConversationMemory(
                conversation_id=conversation_id,
                thread_id=thread_id,
                user_id=user_id,
                summary_status=summary_status,
                recent_message_window=recent_message_window,
                summary_json=summary_json,
                last_updated_at=now,
            )
            self.session.add(memory)
        else:
            memory.thread_id = thread_id
            memory.summary_status = summary_status
            memory.recent_message_window = recent_message_window
            memory.summary_json = summary_json
            memory.last_updated_at = now
        await self.session.flush()
        return memory

    async def clear_memory(self, conversation_id: UUID, user_id: UUID) -> AgentConversationMemory | None:
        conversation = await self.get_conversation(conversation_id, user_id)
        if conversation is None:
            return None
        memory = await self.get_memory(conversation_id, user_id, thread_id=conversation.thread_id)
        if memory is None:
            memory = AgentConversationMemory(
                conversation_id=conversation_id,
                thread_id=conversation.thread_id,
                user_id=user_id,
                summary_status="empty",
                recent_message_window=10,
                summary_json={},
                last_updated_at=None,
            )
            self.session.add(memory)
        else:
            memory.summary_status = "empty"
            memory.recent_message_window = 10
            memory.summary_json = {}
            memory.last_updated_at = None
        await self.session.flush()
        await self.session.refresh(memory)
        return memory
