from datetime import datetime, timezone

from pydantic import ValidationError

from src.schemas.agent import (
    AgentAction,
    AgentActionResumeRequest,
    AgentChatRequest,
    AgentChatResponse,
    AgentCitation,
    AgentConversationMessage,
    AgentConversationSummary,
    AgentFallback,
    AgentInProgressResponse,
    AgentWarning,
    UnitSearchRequest,
    UnitSearchResponse,
)


def test_chat_request_accepts_minimal_message():
    request = AgentChatRequest(message="Where is receptive field taught?")

    assert request.message == "Where is receptive field taught?"
    assert request.incoming_message_id.startswith("msg_")
    assert request.response_mode == "non_streaming"
    assert request.trace_mode == "summary"


def test_chat_request_accepts_client_incoming_message_id():
    request = AgentChatRequest(
        message="Where is receptive field taught?",
        incomingMessageId="msg-client-1",
    )

    assert request.incoming_message_id == "msg-client-1"


def test_in_progress_and_resume_contracts_are_stable():
    progress = AgentInProgressResponse(
        conversationId="conv-1",
        threadId="thread-1",
        graphRunId="run-1",
        retryAfterMs=1000,
    )
    resume = AgentActionResumeRequest(
        conversationId="conv-1",
        actionId="act-1",
        decision="approve",
        incomingMessageId="msg-resume-1",
    )

    assert progress.model_dump(by_alias=True)["status"] == "in_progress"
    assert progress.model_dump(by_alias=True)["threadId"] == "thread-1"
    assert resume.action_id == "act-1"
    assert resume.incoming_message_id == "msg-resume-1"


def test_fallback_supports_error_code_alias():
    fallback = AgentFallback(
        reason="agent_unavailable",
        message="The agent request failed.",
        errorCode="AGENT_CHAT_ERROR",
    )

    assert fallback.error_code == "AGENT_CHAT_ERROR"
    assert fallback.model_dump(by_alias=True)["errorCode"] == "AGENT_CHAT_ERROR"


def test_chat_response_supports_citations_disabled_action_and_warning():
    response = AgentChatResponse(
        conversation_id="conv-1",
        message_id="msg-1",
        answer={"markdown": "Found it in CS231n Lecture 5.", "confidence": "grounded"},
        citations=[
            AgentCitation(
                canonical_unit_id="local::lecture_5::seg6",
                course_id="CS231n",
                lecture_id="lecture-05",
                lecture_title="Lecture 5: Image Classification with CNNs",
                unit_name="Receptive fields, stride, and convolution formulas",
                learn_href="/courses/cs231n/learn/lecture-05-seg6#t=3220",
                timestamp_s=3220,
                source="key_point",
            )
        ],
        actions=[
            AgentAction(
                type="start_assessment",
                label="Verify with a short quiz",
                actionId="act-quiz",
                status="awaiting_confirmation",
                canonical_unit_ids=["local::lecture_5::seg6"],
                default_phase="skip_verification",
                eligible=False,
                disabledReason="no_eligible_questions",
            )
        ],
        warning=AgentWarning(
            type="outside_current_path",
            message="This citation is outside your current path.",
        ),
    )

    assert response.actions[0].eligible is False
    assert response.actions[0].action_id == "act-quiz"
    assert response.actions[0].disabled_reason == "no_eligible_questions"
    assert response.warning and response.warning.type == "outside_current_path"


def test_agent_actions_support_prerequisite_path_and_target_choice():
    prereq = AgentAction(
        type="review_prerequisite_path",
        label="Review prerequisite order",
        canonical_unit_ids=["cs230-l01-u05", "cs230-l03-u02"],
        eligible=True,
    )
    target = AgentAction(type="choose_target_path", label="Computer Vision", eligible=True)
    path_switch = AgentAction(type="request_path_switch", label="Switch to NLP", eligible=True)

    assert prereq.canonical_unit_ids == ["cs230-l01-u05", "cs230-l03-u02"]
    assert target.type == "choose_target_path"
    assert path_switch.type == "request_path_switch"


def test_conversation_replay_accepts_datetime_and_raw_response_json():
    summary = AgentConversationSummary(
        conversationId="conv-1",
        title="CNN review",
        preview="Review CNN basics.",
        updatedAt=datetime(2026, 4, 30, 9, 4, tzinfo=timezone.utc),
        messageCount=1,
    )
    message = AgentConversationMessage(
        messageId="msg-1",
        role="assistant",
        markdown="Review CNN basics.",
        createdAt=datetime(2026, 4, 30, 9, 6, tzinfo=timezone.utc),
        citations=[{"canonicalUnitId": "unit-cnn", "title": "CNN basics"}],
        actions=[{"type": "open_unit", "label": "Open unit"}],
    )

    assert summary.updated_at.year == 2026
    assert message.citations[0]["canonicalUnitId"] == "unit-cnn"
    assert message.actions[0]["type"] == "open_unit"


def test_unit_search_request_does_not_accept_include_hidden():
    try:
        UnitSearchRequest.model_validate({"query": "course logistics", "includeHidden": True})
    except ValidationError as exc:
        assert "includeHidden" in str(exc)
    else:
        raise AssertionError("includeHidden must not be accepted on public request")


def test_unit_search_response_trace_uses_per_result_navigation_resolution():
    response = UnitSearchResponse(
        results=[],
        trace={
            "trace_id": "trace-1",
            "resolved_scope": "current_path",
            "normalized_query": "receptive field",
            "query_expansions": [],
            "applied_filters": ["course_scope:CS231n"],
            "ranking_version": "unit_search_v1",
            "runtime_navigation_resolution": [
                {
                    "canonical_unit_id": "local::lecture_5::seg6",
                    "source": "product_learning_unit",
                    "learn_href": "/courses/cs231n/learn/lecture-05-seg6",
                }
            ],
        },
    )

    assert response.trace.runtime_navigation_resolution[0].canonical_unit_id == "local::lecture_5::seg6"
