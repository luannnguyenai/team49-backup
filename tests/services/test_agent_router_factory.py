import pytest

from src.services.agent_graph_contracts import AgentRouterUnavailableError
from src.services.agent_graph_router import DeterministicAgentRouter
from src.services.agent_router_factory import build_production_agent_router
from src.services.agent_structured_router import StructuredAgentRouter


class Settings:
    model_provider = "openai"
    fast_model = "gpt-5.4-mini"


class FakeChatModel:
    def with_structured_output(self, schema):
        return self


def test_production_router_factory_builds_structured_router():
    router = build_production_agent_router(
        app_settings=Settings(),
        init_model=lambda **kwargs: FakeChatModel(),
    )

    assert isinstance(router, StructuredAgentRouter)
    assert not isinstance(router, DeterministicAgentRouter)


def test_production_router_factory_fails_safe_without_provider():
    class MissingSettings:
        model_provider = ""
        fast_model = "gpt-5.4-mini"

    with pytest.raises(AgentRouterUnavailableError):
        build_production_agent_router(
            app_settings=MissingSettings(),
            init_model=lambda **kwargs: FakeChatModel(),
        )


def test_production_router_factory_fails_safe_without_model():
    class MissingSettings:
        model_provider = "openai"
        fast_model = ""

    with pytest.raises(AgentRouterUnavailableError):
        build_production_agent_router(
            app_settings=MissingSettings(),
            init_model=lambda **kwargs: FakeChatModel(),
        )


def test_production_router_factory_does_not_return_deterministic_router_on_model_error():
    def fail_model(**kwargs):
        raise RuntimeError("provider unavailable")

    with pytest.raises(AgentRouterUnavailableError):
        build_production_agent_router(app_settings=Settings(), init_model=fail_model)
