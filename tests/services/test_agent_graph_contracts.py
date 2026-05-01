from src.schemas.agent import AgentIntent
from src.services.agent_graph_contracts import (
    AGENT_INTENT_NODE_REGISTRY,
    GRAPH_RUN_STATUSES,
    AgentInProgressError,
    AgentSlots,
    PendingClarification,
)


def test_every_agent_intent_has_registered_node():
    intents = set(AgentIntent.__args__)

    assert intents == set(AGENT_INTENT_NODE_REGISTRY)
    assert "request_path_switch" in intents
    assert "clarify" in intents


def test_graph_run_status_machine_values_are_stable():
    assert GRAPH_RUN_STATUSES == {
        "created",
        "running",
        "interrupted",
        "succeeded",
        "failed_retryable",
        "failed_terminal",
        "cancelled",
    }


def test_in_progress_error_payload_is_stable():
    response = AgentInProgressError("conv-1", "thread-1", "run-1", 1000).to_response()

    assert response.model_dump(by_alias=True) == {
        "status": "in_progress",
        "conversationId": "conv-1",
        "threadId": "thread-1",
        "graphRunId": "run-1",
        "retryAfterMs": 1000,
    }


def test_agent_slots_track_search_scope_state():
    slots = AgentSlots(
        raw_topic="attention mask",
        search_scope="explicit_path",
        requested_path_id="nlp",
        resolved_search_path_ids=["nlp"],
    )

    assert slots.search_scope == "explicit_path"
    assert slots.scope_expansion_offered is False
    assert slots.scope_expansion_approved is False


def test_pending_clarification_tracks_scope_expansion():
    pending = PendingClarification(
        clarification_id="clar-scope-1",
        type="search_scope_expansion",
        status="awaiting_response",
        payload={"original_message": "attention mask", "allowed_path_ids": ["computer_vision", "nlp"]},
    )

    assert pending.type == "search_scope_expansion"
    assert pending.payload["allowed_path_ids"] == ["computer_vision", "nlp"]
