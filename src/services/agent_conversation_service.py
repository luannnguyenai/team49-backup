from __future__ import annotations

from uuid import UUID

from src.repositories.agent_conversation_repo import AgentConversationRepository
from src.schemas.agent import (
    AgentConversationMutationResponse,
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

    async def rename_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID,
        title: str,
    ) -> AgentConversationSummary:
        row = await self.repo.rename_conversation(conversation_id, user_id, title.strip())
        if not row:
            raise ValueError("conversation_not_found")
        return AgentConversationSummary(
            conversationId=str(row.id),
            title=row.title,
            preview=row.preview,
            updatedAt=row.updated_at,
            messageCount=row.message_count,
        )

    async def delete_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID,
    ) -> AgentConversationMutationResponse:
        deleted = await self.repo.delete_conversation(conversation_id, user_id)
        if not deleted:
            raise ValueError("conversation_not_found")
        return AgentConversationMutationResponse(ok=True)

    async def clear_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID,
    ) -> AgentConversationSummary:
        row = await self.repo.clear_conversation(conversation_id, user_id)
        if not row:
            raise ValueError("conversation_not_found")
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
        row = await self.repo.get_memory(conversation_id, user_id, thread_id=conversation.thread_id)
        if not row:
            return AgentConversationMemory(
                conversationId=str(conversation_id),
                threadId=conversation.thread_id,
                summaryStatus="empty",
                recentMessageWindow=10,
                lastUpdatedAt=None,
                summary={},
            )
        return AgentConversationMemory(
            conversationId=str(conversation_id),
            threadId=row.thread_id,
            summaryStatus=row.summary_status,
            recentMessageWindow=row.recent_message_window,
            lastUpdatedAt=row.last_updated_at,
            summary=row.summary_json or {},
        )

    async def clear_memory(self, conversation_id: UUID, user_id: UUID) -> AgentConversationMemory:
        row = await self.repo.clear_memory(conversation_id, user_id)
        if not row:
            raise ValueError("conversation_not_found")
        return AgentConversationMemory(
            conversationId=str(conversation_id),
            threadId=row.thread_id,
            summaryStatus=row.summary_status,
            recentMessageWindow=row.recent_message_window,
            lastUpdatedAt=row.last_updated_at,
            summary=row.summary_json or {},
        )
