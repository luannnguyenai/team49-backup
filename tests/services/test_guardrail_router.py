import json

import pytest

from src.services.guardrail_router import (
    GuardrailRouterClient,
    GuardrailRouterConfig,
    GuardrailRouterUnavailableError,
    GuardrailScopePacket,
    build_guardrail_prompt,
)


class FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http_{self.status_code}")

    def json(self):
        return self._payload


class FakeSyncHttpClient:
    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.requests = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.requests.append(
            {
                "url": url,
                "json": json,
                "headers": headers or {},
                "timeout": timeout,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response


class FakeFallbackModel:
    def __init__(self, content: str):
        self.content = content
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return type("Message", (), {"content": self.content})()


def _scope() -> GuardrailScopePacket:
    return GuardrailScopePacket(
        feature="tutor",
        scope_level="unit",
        scope_id="local::unit::1",
        allowed_scope_summary="This unit covers error analysis.",
        candidate_kps=[
            {"id": "kp_error_analysis", "text": "Error analysis identifies dominant error sources."}
        ],
        recent_context=[],
        selected_text="",
    )


def _chat_payload(content: str) -> dict:
    return {
        "choices": [
            {
                "message": {
                    "content": content,
                }
            }
        ]
    }


def test_guardrail_prompt_matches_training_format():
    prompt = build_guardrail_prompt("Explain error analysis.", _scope())

    assert "### TASK\nYou are a lesson-scope safety router. Return only valid JSON." in prompt
    assert "out_of_scope_policy: strict" in prompt
    assert "- kp_error_analysis: Error analysis identifies dominant error sources." in prompt
    assert "### RECENT_CONTEXT\n\n### SELECTED_TEXT\n\n### USER_QUERY" in prompt


def test_guardrail_router_uses_cloudflare_tunnel_vllm_first():
    http = FakeSyncHttpClient(
        response=FakeResponse(
            _chat_payload(
                json.dumps(
                    {
                        "safety_label": "SAFE",
                        "topic_label": "ON_TOPIC",
                        "action": "ALLOW_LESSON_ANSWER",
                        "attack_type": "none",
                        "selected_kp_ids": ["kp_error_analysis"],
                    }
                )
            )
        )
    )
    client = GuardrailRouterClient(
        GuardrailRouterConfig(
            enabled=True,
            base_url="https://router.example.com/v1",
            model="guardrail-router-merged",
            api_key="router-token",
            cf_access_client_id="cf-id",
            cf_access_client_secret="cf-secret",
            timeout_seconds=2.5,
        ),
        sync_http_client=http,
    )

    decision = client.route_sync(message="Explain error analysis.", scope=_scope())

    assert decision.action == "ALLOW_LESSON_ANSWER"
    assert decision.selected_kp_ids == ["kp_error_analysis"]
    assert http.requests[0]["url"] == "https://router.example.com/v1/chat/completions"
    assert http.requests[0]["json"]["model"] == "guardrail-router-merged"
    assert http.requests[0]["headers"]["Authorization"] == "Bearer router-token"
    assert http.requests[0]["headers"]["CF-Access-Client-Id"] == "cf-id"
    assert http.requests[0]["headers"]["CF-Access-Client-Secret"] == "cf-secret"
    assert http.requests[0]["timeout"] == 2.5


def test_guardrail_router_falls_back_to_provider_when_tunnel_fails():
    http = FakeSyncHttpClient(error=TimeoutError("local tunnel unavailable"))
    fallback = FakeFallbackModel(
        json.dumps(
            {
                "safety_label": "SAFE",
                "topic_label": "AMBIGUOUS",
                "action": "ASK_CLARIFY",
                "attack_type": "none",
                "selected_kp_ids": [],
            }
        )
    )
    client = GuardrailRouterClient(
        GuardrailRouterConfig(
            enabled=True,
            base_url="https://router.example.com/v1",
            model="guardrail-router-merged",
            fallback_provider="openai",
            fallback_model="gpt-5.4-nano",
        ),
        sync_http_client=http,
        fallback_model=fallback,
    )

    decision = client.route_sync(message="What is this?", scope=_scope())

    assert decision.action == "ASK_CLARIFY"
    assert fallback.messages is not None


def test_guardrail_router_raises_when_tunnel_and_provider_fail():
    http = FakeSyncHttpClient(error=TimeoutError("local tunnel unavailable"))

    class FailingFallbackModel:
        def invoke(self, messages):
            raise RuntimeError("fallback provider unavailable")

    client = GuardrailRouterClient(
        GuardrailRouterConfig(
            enabled=True,
            base_url="https://router.example.com/v1",
            model="guardrail-router-merged",
            fallback_provider="gemini",
            fallback_model="gemini-2.5-flash",
        ),
        sync_http_client=http,
        fallback_model=FailingFallbackModel(),
    )

    with pytest.raises(GuardrailRouterUnavailableError) as exc:
        client.route_sync(message="Explain error analysis.", scope=_scope())

    assert exc.value.error_code == "GUARDRAIL_ROUTER_UNAVAILABLE"


def test_guardrail_router_config_defaults_to_current_api_provider(monkeypatch):
    from src.config import Settings
    from src.services.guardrail_router import build_guardrail_config_from_settings

    monkeypatch.delenv("GUARDRAIL_ROUTER_BASE_URL", raising=False)
    monkeypatch.delenv("GUARDRAIL_ROUTER_FALLBACK_PROVIDER", raising=False)
    monkeypatch.delenv("GUARDRAIL_ROUTER_FALLBACK_MODEL", raising=False)
    monkeypatch.setenv("MODEL_PROVIDER", "gemini")
    monkeypatch.setenv("FAST_MODEL", "gemini-2.5-flash")

    settings = Settings(_env_file=None)
    config = build_guardrail_config_from_settings(settings)

    assert config.enabled is True
    assert config.base_url == ""
    assert config.fallback_provider == "gemini"
    assert config.fallback_model == "gemini-2.5-flash"
