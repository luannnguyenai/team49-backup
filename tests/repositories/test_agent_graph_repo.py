from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from src.models.agent_conversation import AgentConversation
from src.models.user import User
from src.repositories.agent_graph_repo import AgentGraphRepository
from src.schemas.agent import AgentAnswer, AgentChatResponse

pytestmark = pytest.mark.asyncio


async def _conversation(db_session, thread_id: str = "thread-repo"):
    column_exists = await db_session.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'agent_conversations' AND column_name = 'thread_id'"
        )
    )
    if column_exists.scalar_one_or_none() is None:
        pytest.skip("agent graph runtime migration has not been applied to the test database")
    user = User(
        email=f"{uuid4()}@example.com",
        full_name="Test User",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()
    conversation = AgentConversation(
        user_id=user.id,
        title="Test",
        preview="",
        message_count=0,
        thread_id=thread_id,
    )
    db_session.add(conversation)
    await db_session.flush()
    return user, conversation


async def test_graph_repo_run_response_and_dedupe_round_trip(db_session):
    _user, conversation = await _conversation(db_session)
    repo = AgentGraphRepository(db_session)
    run = await repo.create_run(
        conversation_id=str(conversation.id),
        thread_id=conversation.thread_id,
        incoming_message_id="msg-1",
    )
    response = AgentChatResponse(
        conversation_id=str(conversation.id),
        message_id="assistant-1",
        answer=AgentAnswer(markdown="Done", confidence="partial"),
    )

    response_ref = await repo.store_response_payload(
        graph_run_id=run.graph_run_id,
        response=response,
        deterministic_key=f"{conversation.thread_id}:msg-1",
    )
    await repo.mark_run_succeeded(run.graph_run_id, response_ref=response_ref, checkpoint_id="chk-1")
    completed = await repo.get_completed_response_by_incoming_message(
        conversation_id=str(conversation.id),
        thread_id=conversation.thread_id,
        incoming_message_id="msg-1",
    )

    assert completed == response


async def test_graph_repo_pending_action_idempotency_and_expiry(db_session):
    user, conversation = await _conversation(db_session, thread_id="thread-action")
    repo = AgentGraphRepository(db_session)

    first = await repo.create_pending_action(
        conversation_id=str(conversation.id),
        thread_id=conversation.thread_id,
        user_id=str(user.id),
        action_type="request_replan",
        payload={"payload_version": 1},
        payload_version=1,
        idempotency_key="idem-1",
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    second = await repo.create_pending_action(
        conversation_id=str(conversation.id),
        thread_id=conversation.thread_id,
        user_id=str(user.id),
        action_type="request_replan",
        payload={"payload_version": 1},
        payload_version=1,
        idempotency_key="idem-1",
        expires_at=datetime.now(UTC) + timedelta(minutes=1),
    )
    expired = await repo.expire_pending_actions(datetime.now(UTC))

    assert second.action_id == first.action_id
    assert expired == 1
