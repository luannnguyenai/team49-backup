from __future__ import annotations

from pydantic import BaseModel

from src.services.openai_compatible_http_chat_model import OpenAICompatibleHTTPChatModel


class FakeResponse:
    def __init__(self, content: str) -> None:
        self._content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "choices": [
                {
                    "message": {
                        "content": self._content,
                    }
                }
            ]
        }


class FakeClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.requests: list[dict] = []
        self.closed = False

    def post(self, url, *, headers, json, timeout):
        self.requests.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return self.responses.pop(0)

    def close(self) -> None:
        self.closed = True


def test_http_chat_model_omits_openai_sdk_headers() -> None:
    client = FakeClient([FakeResponse("Hello there!")])
    model = OpenAICompatibleHTTPChatModel(
        model="qwen3.5-4b-lora",
        base_url="https://vllm.a20-app-049.io.vn/v1",
        api_key="EMPTY",
        temperature=0.2,
        timeout=30,
        client_factory=lambda: client,
    )

    response = model.invoke([{"role": "user", "content": "Say hello."}])

    assert response.content == "Hello there!"
    request = client.requests[0]
    assert request["url"] == "https://vllm.a20-app-049.io.vn/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer EMPTY"
    assert not any(name.lower().startswith("x-stainless") for name in request["headers"])
    assert request["headers"].get("User-Agent") != "OpenAI/Python 2.31.0"


def test_http_chat_model_structured_output_uses_json_object_and_local_parsing() -> None:
    class SimpleOut(BaseModel):
        answer: str

    client = FakeClient([FakeResponse('{"answer": "Hello!"}')])
    model = OpenAICompatibleHTTPChatModel(
        model="qwen3.5-4b-lora",
        base_url="https://vllm.a20-app-049.io.vn/v1",
        api_key="EMPTY",
        temperature=0.2,
        timeout=30,
        client_factory=lambda: client,
    )

    result = model.with_structured_output(SimpleOut, method="function_calling").invoke(
        [{"role": "user", "content": "Say hello."}]
    )

    assert result == SimpleOut(answer="Hello!")
    payload = client.requests[0]["json"]
    assert payload["response_format"] == {"type": "json_object"}
    assert "JSON schema" in payload["messages"][0]["content"]


def test_http_chat_model_structured_output_merges_existing_system_prompt() -> None:
    class SimpleOut(BaseModel):
        answer: str

    client = FakeClient([FakeResponse('{"answer": "Hello!"}')])
    model = OpenAICompatibleHTTPChatModel(
        model="qwen3.5-4b-lora",
        base_url="https://vllm.a20-app-049.io.vn/v1",
        api_key="EMPTY",
        temperature=0.2,
        timeout=30,
        client_factory=lambda: client,
    )

    model.with_structured_output(SimpleOut).invoke(
        [
            {"role": "system", "content": "Original system prompt."},
            {"role": "user", "content": "Say hello."},
        ]
    )

    messages = client.requests[0]["json"]["messages"]
    assert [message["role"] for message in messages] == ["system", "user"]
    assert "JSON schema" in messages[0]["content"]
    assert "Original system prompt." in messages[0]["content"]
