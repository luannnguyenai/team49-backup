from __future__ import annotations

import pytest

from src.services.model_registry import (
    build_chat_model_kwargs_for_option,
    check_chat_model_health,
    get_chat_model_option,
    list_chat_model_options,
)


def test_chat_model_registry_exposes_default_and_qwen_options():
    options = list_chat_model_options()

    assert [option.id for option in options] == ["default", "qwen35_4b"]
    assert options[0].is_default is True
    assert options[1].label == "Qwen 3.5 4B"
    assert options[1].base_url == "https://vllm.a20-app-049.io.vn/v1"
    assert options[1].model == "qwen 3.5 4B"


def test_build_kwargs_for_qwen_uses_openai_compatible_base_url():
    kwargs = build_chat_model_kwargs_for_option("qwen35_4b", temperature=0.2)

    assert kwargs["model_provider"] == "openai"
    assert kwargs["model"] == "qwen 3.5 4B"
    assert kwargs["base_url"] == "https://vllm.a20-app-049.io.vn/v1"
    assert kwargs["api_key"] == "EMPTY"
    assert "reasoning" not in kwargs


def test_unknown_chat_model_id_is_rejected():
    with pytest.raises(ValueError, match="unsupported_chat_model"):
        get_chat_model_option("unknown-model")


@pytest.mark.asyncio
async def test_qwen_health_uses_openai_compatible_models_endpoint():
    calls: list[dict[str, object]] = []

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"id": "qwen 3.5 4B"}]}

    class FakeClient:
        async def get(self, url, **kwargs):
            calls.append({"url": url, **kwargs})
            return FakeResponse()

    result = await check_chat_model_health("qwen35_4b", client=FakeClient())

    assert result["id"] == "qwen35_4b"
    assert result["status"] == "healthy"
    assert result["base_url"] == "https://vllm.a20-app-049.io.vn/v1"
    assert calls[0]["url"] == "https://vllm.a20-app-049.io.vn/v1/models"
    assert calls[0]["headers"] == {"Authorization": "Bearer EMPTY"}
