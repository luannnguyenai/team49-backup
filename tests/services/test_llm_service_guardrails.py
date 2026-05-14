from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

from langchain_core.messages import AIMessage

from src.services.guardrail_router import GuardrailDecision
from src.services import llm_service


def test_tutor_llm_factory_uses_raw_http_model_for_selected_qwen_chat_model(monkeypatch) -> None:
    def fake_init_chat_model(**_kwargs):
        raise AssertionError("self-hosted Qwen must not use the OpenAI SDK client")

    monkeypatch.setattr(llm_service, "init_chat_model", fake_init_chat_model)
    llm_service._get_llm_with_tools.cache_clear()

    model = llm_service._get_llm_with_tools("qwen35_4b")

    assert model.model == "qwen3.5-4b-lora"
    assert model.base_url == "https://vllm.a20-app-049.io.vn/v1"


def test_tutor_call_model_uses_selected_chat_model_id(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeModel:
        def invoke(self, messages, config=None):
            captured["messages"] = messages
            captured["config"] = config
            return SimpleNamespace(content="answer")

    def fake_get_llm_with_tools(chat_model_id):
        captured["chat_model_id"] = chat_model_id
        return FakeModel()

    monkeypatch.setattr(llm_service, "_get_llm_with_tools", fake_get_llm_with_tools)
    monkeypatch.setattr(llm_service, "enforce_llm_rate_limit", lambda **kwargs: captured.update({"rate_limit": kwargs}))
    monkeypatch.setattr(llm_service, "llm_callbacks", lambda: [])

    result = llm_service.call_model({"messages": [], "chat_model_id": "qwen35_4b"})

    assert captured["chat_model_id"] == "qwen35_4b"
    assert captured["rate_limit"] == {"model": "qwen3.5-4b-lora", "model_provider": "openai"}
    assert result["messages"][0].content == "answer"


def test_tutor_simple_route_sanitizes_streamed_answer_and_persisted_payload(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_fetch_lecture_context(_lecture_id: str):
        lecture = SimpleNamespace(title="Lecture 1")
        return lecture, [], []

    async def fake_save_qa_history(
        lecture_id,
        question,
        answer,
        thoughts,
        current_timestamp,
        context_binding_id,
        image_base64,
        langfuse_trace_id=None,
        langfuse_observation_id=None,
    ):
        captured["saved"] = {
            "lecture_id": lecture_id,
            "question": question,
            "answer": answer,
            "thoughts": thoughts,
            "current_timestamp": current_timestamp,
            "context_binding_id": context_binding_id,
            "image_base64": image_base64,
        }
        return 77

    def fake_log_qa(lecture_id, current_timestamp, user_question, full_answer, thoughts=""):
        captured["logged"] = {
            "lecture_id": lecture_id,
            "current_timestamp": current_timestamp,
            "user_question": user_question,
            "full_answer": full_answer,
            "thoughts": thoughts,
        }

    monkeypatch.setattr(llm_service, "_fetch_lecture_context", fake_fetch_lecture_context)
    monkeypatch.setattr(llm_service, "_save_qa_history", fake_save_qa_history)
    monkeypatch.setattr(llm_service, "_log_qa", fake_log_qa)
    monkeypatch.setattr(llm_service, "get_lecture_scope_metadata", lambda lecture_id: {})
    monkeypatch.setattr(
        llm_service,
        "build_guardrail_router_client",
        lambda: SimpleNamespace(route_sync=lambda **_kwargs: GuardrailDecision.allow()),
    )
    monkeypatch.setattr(
        llm_service,
        "route_question",
        lambda *args, **kwargs: {
            "route": "SIMPLE",
            "direct_answer": "Call me at 555-123-4567 or email alice@example.com.",
            "reason": "simple",
        },
    )
    monkeypatch.setattr(llm_service, "build_langfuse_metadata", lambda **kwargs: {})
    monkeypatch.setattr(llm_service, "get_langfuse_client", lambda: None)
    monkeypatch.setattr(llm_service, "start_langfuse_root_span", lambda **kwargs: nullcontext(None))
    monkeypatch.setattr(llm_service, "start_langfuse_observation", lambda **kwargs: nullcontext(None))
    monkeypatch.setattr(llm_service, "propagate_langfuse_attributes", lambda **kwargs: nullcontext(None))
    monkeypatch.setattr(llm_service, "observe_tutor_stream_first_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(llm_service, "observe_tutor_stream_first_answer", lambda *args, **kwargs: None)
    monkeypatch.setattr(llm_service, "observe_tutor_stream_total", lambda *args, **kwargs: None)

    chunks = list(
        llm_service.get_context_and_stream_langgraph(
            lecture_id="lecture-1",
            current_timestamp=120.0,
            user_question="Email me at alice@example.com",
            context_binding_id="ctx_123",
        )
    )

    output = "".join(chunks)
    assert "[REDACTED_PHONE]" in output
    assert "[REDACTED_EMAIL]" in output
    assert "555-123-4567" not in output
    assert "alice@example.com" not in output

    saved = captured["saved"]
    assert saved["question"] == "Email me at [REDACTED_EMAIL]"
    assert saved["answer"] == "Call me at [REDACTED_PHONE] or email [REDACTED_EMAIL]."

    logged = captured["logged"]
    assert logged["user_question"] == "Email me at [REDACTED_EMAIL]"
    assert logged["full_answer"] == "Call me at [REDACTED_PHONE] or email [REDACTED_EMAIL]."


def test_tutor_complex_route_streams_non_chunk_ai_message(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeGraph:
        def stream(self, *_args, **_kwargs):
            yield AIMessage(content="Qwen tutor answer."), {"node": "agent"}

    async def fake_fetch_lecture_context(_lecture_id: str):
        lecture = SimpleNamespace(title="Lecture 1")
        chapter = {"title": "Intro", "summary": "Intro summary", "start_time": 0, "end_time": 120}
        return lecture, [chapter], []

    async def fake_fetch_transcript_window(*_args, **_kwargs):
        return [SimpleNamespace(start_time=10, content="Transcript evidence.")]

    async def fake_save_qa_history(
        lecture_id,
        question,
        answer,
        thoughts,
        current_timestamp,
        context_binding_id,
        image_base64,
        langfuse_trace_id=None,
        langfuse_observation_id=None,
    ):
        captured["saved_answer"] = answer
        return 88

    monkeypatch.setattr(llm_service, "compiled_graph", FakeGraph())
    monkeypatch.setattr(llm_service, "_fetch_lecture_context", fake_fetch_lecture_context)
    monkeypatch.setattr(llm_service, "_fetch_transcript_window", fake_fetch_transcript_window)
    monkeypatch.setattr(llm_service, "_save_qa_history", fake_save_qa_history)
    monkeypatch.setattr(llm_service, "_log_qa", lambda *args, **kwargs: None)
    monkeypatch.setattr(llm_service, "get_lecture_scope_metadata", lambda lecture_id: {})
    monkeypatch.setattr(
        llm_service,
        "build_guardrail_router_client",
        lambda: SimpleNamespace(route_sync=lambda **_kwargs: GuardrailDecision.allow()),
    )
    monkeypatch.setattr(
        llm_service,
        "route_question",
        lambda *args, **kwargs: {"route": "COMPLEX", "reason": "needs tutor model"},
    )
    monkeypatch.setattr(llm_service, "build_langfuse_metadata", lambda **kwargs: {})
    monkeypatch.setattr(llm_service, "get_langfuse_client", lambda: None)
    monkeypatch.setattr(llm_service, "start_langfuse_root_span", lambda **kwargs: nullcontext(None))
    monkeypatch.setattr(llm_service, "start_langfuse_observation", lambda **kwargs: nullcontext(None))
    monkeypatch.setattr(llm_service, "propagate_langfuse_attributes", lambda **kwargs: nullcontext(None))
    monkeypatch.setattr(llm_service, "llm_callbacks", lambda: [])
    monkeypatch.setattr(llm_service, "observe_tutor_stream_first_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(llm_service, "observe_tutor_stream_first_answer", lambda *args, **kwargs: None)
    monkeypatch.setattr(llm_service, "observe_tutor_stream_total", lambda *args, **kwargs: None)

    chunks = list(
        llm_service.get_context_and_stream_langgraph(
            lecture_id="lecture-1",
            current_timestamp=10.0,
            user_question="hello",
            chat_model_id="qwen35_4b",
        )
    )

    output = "".join(chunks)
    assert "Qwen tutor answer." in output
    assert captured["saved_answer"] == "Qwen tutor answer."
