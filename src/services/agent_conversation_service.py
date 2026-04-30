from __future__ import annotations

from uuid import UUID

from src.repositories.agent_conversation_repo import AgentConversationRepository
from src.schemas.agent import (
    AgentConversationMemory,
    AgentConversationMessage,
    AgentConversationSummary,
)


class AgentConversationService:
    def __init__(self, repo: AgentConversationRepository):
        self.repo = repo

    async def list_conversations(self, user_id: UUID) -> list[AgentConversationSummary]:
        rows = await self.repo.list_conversations(user_id)
        return [
            AgentConversationSummary(
                conversationId=str(row.id),
                title=row.title,
                preview=row.preview,
                updatedAt=row.updated_at,
                messageCount=row.message_count,
            )
            for row in rows
        ]

    async def create_conversation(self, user_id: UUID) -> AgentConversationSummary:
        row = await self.repo.create_conversation(user_id)
        return AgentConversationSummary(
            conversationId=str(row.id),
            title=row.title,
            preview=row.preview,
            updatedAt=row.updated_at,
            messageCount=row.message_count,
        )

    async def get_messages(self, conversation_id: UUID, user_id: UUID) -> list[AgentConversationMessage]:
        conversation = await self.repo.get_conversation(conversation_id, user_id)
        if not conversation:
            raise ValueError("conversation_not_found")
        rows = await self.repo.list_messages(conversation_id, user_id)
        return [
            AgentConversationMessage(
                messageId=str(row.id),
                role=row.role,
                markdown=row.markdown,
                createdAt=row.created_at,
                citations=row.citations_json or [],
                actions=row.actions_json or [],
            )
            for row in rows
        ]

    async def get_memory(self, conversation_id: UUID, user_id: UUID) -> AgentConversationMemory:
        conversation = await self.repo.get_conversation(conversation_id, user_id)
        if not conversation:
            raise ValueError("conversation_not_found")
        row = await self.repo.get_memory(conversation_id, user_id)
        if not row:
            return AgentConversationMemory(
                conversationId=str(conversation_id),
                summaryStatus="empty",
                recentMessageWindow=10,
                lastUpdatedAt=None,
                summary={},
            )
        return AgentConversationMemory(
            conversationId=str(conversation_id),
            summaryStatus=row.summary_status,
            recentMessageWindow=row.recent_message_window,
            lastUpdatedAt=row.last_updated_at,
            summary=row.summary_json or {},
        )
