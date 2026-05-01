from __future__ import annotations

from uuid import uuid4

from src.schemas.agent import AgentAnswer, AgentChatResponse, AgentFallback
from src.services.agent_graph_contracts import ToolResult


class AgentResponseComposer:
    def compose(
        self,
        *,
        conversation_id: str,
        message_id: str | None = None,
        result: ToolResult,
    ) -> AgentChatResponse:
        if result.requires_evidence and not result.citations:
            return AgentChatResponse(
                conversation_id=conversation_id,
                message_id=message_id or str(uuid4()),
                answer=AgentAnswer(
                    markdown=(
                        result.answer_markdown
                        or "I could not find a grounded source for that request."
                    ),
                    confidence="no_source",
                ),
                warning=result.warning,
                fallback=result.fallback
                or AgentFallback(
                    reason="no_retrieval_result",
                    message="No grounded evidence was returned for a grounded answer.",
                ),
            )
        return AgentChatResponse(
            conversation_id=conversation_id,
            message_id=message_id or str(uuid4()),
            answer=AgentAnswer(
                markdown=result.answer_markdown or "I need a little more context before I can help.",
                confidence="grounded" if result.citations else "partial",
            ),
            citations=result.citations,
            actions=result.actions,
            warning=result.warning,
            fallback=result.fallback,
        )

    def compose_action_error(self, conversation_id: str, reason: str) -> AgentChatResponse:
        return AgentChatResponse(
            conversation_id=conversation_id,
            message_id=str(uuid4()),
            answer=AgentAnswer(markdown="That action can no longer be completed.", confidence="fallback"),
            fallback=AgentFallback(reason="action_error", message=reason),
        )

    def compose_action_cancelled(self, conversation_id: str) -> AgentChatResponse:
        return AgentChatResponse(
            conversation_id=conversation_id,
            message_id=str(uuid4()),
            answer=AgentAnswer(markdown="Cancelled.", confidence="partial"),
        )
