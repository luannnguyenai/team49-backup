from src.services.agent_graph_contracts import AgentSlots, PendingClarification
from src.services.agent_search_scope_service import AgentSearchScopeService


def test_default_scope_starts_current_path():
    slots = AgentSearchScopeService().resolve_initial_scope(
        slots=AgentSlots(raw_topic="attention mask"),
        current_path_ids=["computer_vision"],
    )

    assert slots.search_scope == "current_path"
    assert slots.resolved_search_path_ids == ["computer_vision"]


def test_explicit_path_uses_requested_scope_directly():
    slots = AgentSearchScopeService().resolve_initial_scope(
        slots=AgentSlots(raw_topic="attention mask", requested_path_id="nlp"),
        current_path_ids=["computer_vision"],
    )

    assert slots.search_scope == "explicit_path"
    assert slots.resolved_search_path_ids == ["nlp"]


def test_resolve_initial_scope_preserves_expanded_search_scope():
    slots = AgentSearchScopeService().resolve_initial_scope(
        slots=AgentSlots(
            raw_topic="attention mask",
            search_scope="expanded_paths",
            scope_expansion_approved=True,
            resolved_search_path_ids=["computer_vision", "nlp"],
        ),
        current_path_ids=["computer_vision"],
    )

    assert slots.search_scope == "expanded_paths"
    assert slots.scope_expansion_approved is True
    assert slots.resolved_search_path_ids == ["computer_vision", "nlp"]


def test_approved_expansion_uses_allowed_paths():
    slots = AgentSearchScopeService().approve_expansion(
        slots=AgentSlots(raw_topic="attention mask", scope_expansion_offered=True),
        allowed_path_ids=["computer_vision", "nlp"],
    )

    assert slots.scope_expansion_approved is True
    assert slots.search_scope == "expanded_paths"


def test_scope_expansion_approval_only_resolves_pending_clarification():
    service = AgentSearchScopeService()
    pending = PendingClarification(
        clarification_id="clar-1",
        type="search_scope_expansion",
        status="awaiting_response",
    )

    assert service.is_scope_expansion_approval("ok", pending) is True
    assert service.is_scope_expansion_approval("yes, search other paths", pending) is True
    assert service.is_scope_expansion_approval("ok", None) is False


def test_scope_expansion_rejection_only_resolves_pending_clarification():
    service = AgentSearchScopeService()
    pending = PendingClarification(
        clarification_id="clar-1",
        type="search_scope_expansion",
        status="awaiting_response",
    )

    assert service.is_scope_expansion_rejection("no, keep current path", pending) is True
    assert service.is_scope_expansion_rejection("no", None) is False
