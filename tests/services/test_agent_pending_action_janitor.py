from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.services.agent_pending_action_janitor import AgentPendingActionJanitor

pytestmark = pytest.mark.asyncio


async def test_janitor_expires_pending_actions():
    calls = []

    async def expire_pending_actions(now):
        calls.append(now)
        return 2

    repo = SimpleNamespace(expire_pending_actions=expire_pending_actions)
    count = await AgentPendingActionJanitor(repo).run_once(now=datetime.now(UTC))

    assert count == 2
    assert calls


async def test_legacy_expire_pending_actions_method_delegates_to_run_once():
    calls = []

    async def expire_pending_actions(now):
        calls.append(now)
        return 1

    repo = SimpleNamespace(expire_pending_actions=expire_pending_actions)
    count = await AgentPendingActionJanitor(repo).expire_pending_actions()

    assert count == 1
    assert isinstance(calls[0], datetime)
