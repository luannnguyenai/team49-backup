from types import SimpleNamespace

from src.services.agent_memory_compaction_service import AgentMemoryCompactionService


def test_compaction_preserves_active_context_and_versions_summary():
    messages = [SimpleNamespace(role="user", markdown=f"old {index}") for index in range(12)] + [
        SimpleNamespace(role="assistant", markdown="recent answer"),
        SimpleNamespace(role="user", markdown="recent question"),
    ]

    result = AgentMemoryCompactionService(max_recent_turns=2).compact(
        messages=messages,
        pending_action={"action_id": "act-1"},
        active_slots={"canonical_unit_ids": ["unit-1"]},
        clarification_target={"field": "canonical_unit_id"},
    )

    assert result.summary_version == 1
    assert len(result.recent_messages) == 2
    assert result.pending_action == {"action_id": "act-1"}
    assert result.active_slots == {"canonical_unit_ids": ["unit-1"]}
