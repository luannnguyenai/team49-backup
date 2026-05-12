import pytest

from src.services.agent_graph_contracts import AgentRouterUnavailableError
from src.services.agent_graph_router import DeterministicAgentRouter
from src.services.agent_router_factory import (
    _FallbackChatModel,
    build_production_agent_response_router,
    build_production_agent_router,
)
from src.services.agent_structured_router import StructuredAgentRouter


class Settings:
    model_provider = "openai"
    fast_model = "gpt-5.4-mini"
    guardrail_router_base_url = "https://router.example.com/v1"
    guardrail_router_model = "guardrail-router-merged"
    guardrail_router_api_key = "router-token"
    guardrail_router_timeout_seconds = 10.0
    llm_request_timeout_seconds = 30
    llm_max_retries = 1


class FakeChatModel:
    def with_structured_output(self, schema):
        return self


class FailingStructuredModel:
    def invoke(self, messages):
        raise RuntimeError("local router down")


class SuccessfulStructuredModel:
    def __init__(self):
        self.called = False

    def invoke(self, messages):
        self.called = True
        return {"ok": True}


class FailingModel:
    def with_structured_output(self, schema):
        return FailingStructuredModel()


class SuccessfulModel:
    def __init__(self):
        self.structured = SuccessfulStructuredModel()

    def with_structured_output(self, schema):
        return self.structured


def test_production_router_factory_uses_guardrail_router_before_fast_model(monkeypatch):
    monkeypatch.setattr("src.services.chat_model_factory.settings.openai_api_key", "openai-key")

    router = build_production_agent_router(
        app_settings=Settings(),
        init_model=lambda **kwargs: FakeChatModel(),
    )

    assert isinstance(router, StructuredAgentRouter)
    assert not isinstance(router, DeterministicAgentRouter)
    assert router.model.primary.model == "guardrail-router-merged"
    assert router.model.primary.base_url == "https://router.example.com/v1"
    assert router.model.fallback is not None


def test_agent_router_model_falls_back_when_local_structured_call_fails():
    fallback = SuccessfulModel()
    model = _FallbackChatModel(primary=FailingModel(), fallback=fallback)

    result = model.with_structured_output(dict).invoke([{"role": "user", "content": "route"}])

    assert result == {"ok": True}
    assert fallback.structured.called is True


def test_production_response_router_uses_raw_http_model_for_selected_qwen_model(monkeypatch):
    def init_model(**_kwargs):
        raise AssertionError("self-hosted Qwen must not use the OpenAI SDK client")

    router = build_production_agent_response_router(
        chat_model_id="qwen35_4b",
        init_model=init_model,
    )

    assert isinstance(router, StructuredAgentRouter)
    assert router.model.model == "qwen3.5-4b-lora"
    assert router.model.base_url == "https://vllm.a20-app-049.io.vn/v1"


def test_production_router_factory_fails_safe_without_provider():
    class MissingSettings:
        model_provider = ""
        fast_model = "gpt-5.4-mini"
        guardrail_router_base_url = ""
        guardrail_router_model = "guardrail-router-merged"
        guardrail_router_api_key = ""

    with pytest.raises(AgentRouterUnavailableError):
        build_production_agent_router(
            app_settings=MissingSettings(),
            init_model=lambda **kwargs: FakeChatModel(),
        )


def test_production_router_factory_fails_safe_without_model():
    class MissingSettings:
        model_provider = "openai"
        fast_model = ""
        guardrail_router_base_url = ""
        guardrail_router_model = "guardrail-router-merged"
        guardrail_router_api_key = ""

    with pytest.raises(AgentRouterUnavailableError):
        build_production_agent_router(
            app_settings=MissingSettings(),
            init_model=lambda **kwargs: FakeChatModel(),
        )


def test_production_router_factory_does_not_return_deterministic_router_on_model_error(monkeypatch):
    monkeypatch.setattr("src.services.chat_model_factory.settings.openai_api_key", "openai-key")

    class NoLocalRouterSettings(Settings):
        guardrail_router_base_url = ""

    def fail_model(**kwargs):
        raise RuntimeError("provider unavailable")

    with pytest.raises(AgentRouterUnavailableError):
        build_production_agent_router(app_settings=NoLocalRouterSettings(), init_model=fail_model)
