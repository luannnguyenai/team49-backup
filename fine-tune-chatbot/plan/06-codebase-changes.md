# P6 — Codebase Changes

**Goal**: integrate `tutor-v1` self-hosted endpoint with **minimal code
changes**. The LangChain abstraction in `chat_model_factory.py` already
supports OpenAI-compatible endpoints — we extend it with a `self_hosted`
provider.

**Files touched**: 3
**Files NOT touched**: `llm_service.py`, `router.py`, `agent.py`, all routers/services using LLM

## Change 1 — `src/config.py`

Add 3 new settings and adjust defaults.

### Diff

Locate the `Settings` class (around line 25). Add fields after the
existing `model_provider` line:

```python
    # ---- Self-hosted LLM (vLLM) ----
    self_hosted_base_url: str = Field(
        default="http://tutor-llm:8000/v1",
        description="OpenAI-compatible base URL of the self-hosted vLLM server",
    )
    self_hosted_api_key: str = Field(
        default="dummy",
        description="API key for self-hosted vLLM (vLLM ignores by default but client requires non-empty)",
    )
    tutor_provider_override: str = Field(
        default="",
        description="If set ('self_hosted' or 'gemini'), overrides model_provider for tutor only. Empty = use model_provider.",
    )
    tutor_fallback_provider: str = Field(
        default="google_genai",
        description="Provider to fall back to when self-hosted endpoint fails (timeout / 5xx)",
    )
    tutor_fallback_model: str = Field(
        default="gemini-2.0-flash",
        description="Model name to use with fallback provider",
    )
    tutor_shadow_ratio: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Fraction of tutor requests to also send to fallback for shadow comparison (logged, not returned)",
    )
```

At the bottom (around line 165 where module-level constants are exported),
add:

```python
SELF_HOSTED_BASE_URL = settings.self_hosted_base_url
TUTOR_PROVIDER_OVERRIDE = settings.tutor_provider_override
TUTOR_FALLBACK_PROVIDER = settings.tutor_fallback_provider
TUTOR_FALLBACK_MODEL = settings.tutor_fallback_model
```

### `.env.example` additions

```dotenv
# Self-hosted tutor LLM (vLLM)
SELF_HOSTED_BASE_URL=http://tutor-llm:8000/v1
SELF_HOSTED_API_KEY=dummy
TUTOR_PROVIDER_OVERRIDE=          # leave empty until rollout
TUTOR_FALLBACK_PROVIDER=google_genai
TUTOR_FALLBACK_MODEL=gemini-2.0-flash
TUTOR_SHADOW_RATIO=0.0
```

### `docker-compose.yml` env additions

In `x-backend-env: &backend-env` block, add:

```yaml
  SELF_HOSTED_BASE_URL: ${SELF_HOSTED_BASE_URL:-http://tutor-llm:8000/v1}
  SELF_HOSTED_API_KEY: ${SELF_HOSTED_API_KEY:-dummy}
  TUTOR_PROVIDER_OVERRIDE: ${TUTOR_PROVIDER_OVERRIDE:-}
  TUTOR_FALLBACK_PROVIDER: ${TUTOR_FALLBACK_PROVIDER:-google_genai}
  TUTOR_FALLBACK_MODEL: ${TUTOR_FALLBACK_MODEL:-gemini-2.0-flash}
  TUTOR_SHADOW_RATIO: ${TUTOR_SHADOW_RATIO:-0.0}
```

Add `depends_on: tutor-llm` to the `backend` service so it waits for
vLLM healthcheck before starting.

## Change 2 — `src/services/chat_model_factory.py`

Add `self_hosted` branch. Keep all existing logic untouched.

### New version (full file)

```python
"""
services/chat_model_factory.py
------------------------------
Shared helpers for constructing LangChain chat model kwargs with the
appropriate provider credential.

Supports providers: openai, google_genai, anthropic, self_hosted.
"""

from __future__ import annotations

from src.config import settings


def _resolve_api_key(model_provider: str) -> str:
    provider = model_provider.lower()
    if provider == "openai":
        return settings.openai_api_key
    if provider in {"google_genai", "google", "gemini"}:
        return settings.gemini_api_key
    if provider == "anthropic":
        return settings.anthropic_api_key
    if provider == "self_hosted":
        return settings.self_hosted_api_key or "dummy"
    return ""


def build_chat_model_kwargs(
    *,
    model: str,
    temperature: float,
    max_tokens: int | None = None,
    model_provider: str | None = None,
) -> dict:
    provider = model_provider or settings.model_provider

    # Self-hosted vLLM is consumed via OpenAI-compatible client.
    if provider == "self_hosted":
        kwargs = {
            "model": model,
            "model_provider": "openai",
            "temperature": temperature,
            "base_url": settings.self_hosted_base_url,
            "api_key": settings.self_hosted_api_key or "dummy",
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        return kwargs

    kwargs = {
        "model": model,
        "model_provider": provider,
        "temperature": temperature,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    api_key = _resolve_api_key(provider)
    if api_key:
        kwargs["api_key"] = api_key

    return kwargs
```

This is **backward compatible** — when `provider != "self_hosted"`,
behavior is identical to current.

## Change 3 — `src/services/llm_service.py` (minimal, safe)

Two surgical changes:

### 3a. Provider-aware tutor model resolution

Replace the `_get_llm_with_tools` function (around line 138) to:
- Use `tutor_provider_override` if set (override-only-tutor pattern)
- Use `tutor-v1` as model name when self-hosted

```python
@lru_cache(maxsize=1)
def _get_llm_with_tools():
    """Lazily create the main tutor LLM. Provider-aware:
    - if settings.tutor_provider_override is set, use it (and its default model)
    - else fall back to settings.model_provider + DEFAULT_MODEL
    """
    provider = settings.tutor_provider_override or settings.model_provider
    model_name = "tutor-v1" if provider == "self_hosted" else DEFAULT_MODEL

    llm = init_chat_model(
        **build_chat_model_kwargs(
            model=model_name,
            temperature=0.2,
            model_provider=provider,
        )
    )
    try:
        return llm.bind_tools(tools)
    except Exception:
        return llm
```

### 3b. Vision routing for self-hosted

Self-hosted Qwen2.5-VL handles `image_base64` natively — no special
handling needed in this file because the LangChain
`{"type":"image_url","image_url":{"url":"data:image/..."}}` format already
matches what vLLM expects.

**No changes** required to the `content_list` building logic at lines
358–363.

### 3c. Fallback wrapper (added, not replacing)

Wrap `compiled_graph.stream(...)` call in a try/except that, on failure,
re-runs with the fallback provider. Add a private helper near the bottom:

```python
def _run_with_fallback(inputs):
    """Stream from primary tutor; on failure (timeout/5xx) re-stream from fallback."""
    try:
        for chunk_meta in compiled_graph.stream(inputs, stream_mode="messages"):
            yield chunk_meta
    except Exception as primary_err:
        if not settings.tutor_provider_override or settings.tutor_provider_override != "self_hosted":
            raise  # only fallback when primary is self-hosted
        qa_logger.error(f"Self-hosted failed: {primary_err}. Falling back to {settings.tutor_fallback_provider}")

        from langchain.chat_models import init_chat_model as _init
        fallback_llm = _init(
            **build_chat_model_kwargs(
                model=settings.tutor_fallback_model,
                temperature=0.2,
                model_provider=settings.tutor_fallback_provider,
            )
        ).bind_tools(tools)

        # Build a minimal one-shot fallback graph (re-use existing nodes)
        from langgraph.graph import StateGraph, START, END
        b = StateGraph(AgentState)
        b.add_node("agent", lambda s: {"messages":[fallback_llm.invoke(s["messages"])]})
        b.add_node("tools", tool_node)
        b.add_node("give_up", give_up_node)
        b.add_edge(START, "agent")
        b.add_conditional_edges("agent", should_continue, ["tools","give_up",END])
        b.add_edge("tools","agent")
        b.add_edge("give_up", END)
        for chunk_meta in b.compile().stream(inputs, stream_mode="messages"):
            yield chunk_meta
```

Then in `get_context_and_stream_langgraph`, replace the line:

```python
for chunk, metadata in compiled_graph.stream(inputs, stream_mode="messages"):
```

with:

```python
for chunk, metadata in _run_with_fallback(inputs):
```

This keeps Gemini as a runtime safety net.

## Change 4 — Rate limiter

`src/services/llm_rate_limiter.py` currently throttles for Gemini API quota.
For self-hosted, no API quota → bypass when provider is `self_hosted`.

Read the file and add an early return at the top of `enforce_llm_rate_limit`:

```python
def enforce_llm_rate_limit(model: str, model_provider: str) -> None:
    if model_provider == "self_hosted":
        return  # no external quota to respect
    # ... existing logic ...
```

(Verify exact function signature when applying — do not break existing code.)

## What NOT to change

- `src/agent.py` — uses Anthropic SDK directly, unrelated to tutor flow
- `src/services/router.py` — keep on Gemini for now (router quality matters
  more than tutor latency; defer in v2)
- `src/tools.py` — tool schemas unchanged (vLLM expects same JSON schema)
- LangGraph structure (`graph_builder`, `compiled_graph`, `should_continue`,
  `give_up_node`) — all stays
- All API routers / endpoints — fully unchanged

## Verification after applying

1. **No-op verification** (provider unchanged):
   - Set `TUTOR_PROVIDER_OVERRIDE=` (empty)
   - Existing tests pass: `pytest tests/services/test_llm_service.py`
   - One real lecture question via API returns same as before

2. **Self-hosted dry run**:
   - Start `docker compose up tutor-llm` (P5)
   - Set `TUTOR_PROVIDER_OVERRIDE=self_hosted` in `.env`
   - Restart backend
   - Same lecture question now routes through vLLM
   - Inspect `logs/qa_history.jsonl` for new entries

3. **Fallback verification**:
   - Stop tutor-llm container mid-stream
   - Verify next request falls back to Gemini, no user-visible error
   - Re-start tutor-llm; next request routes to self-hosted again

## Exit criteria

- [ ] All 3 file changes applied (config.py, chat_model_factory.py, llm_service.py)
- [ ] `.env.example` and `docker-compose.yml` env vars added
- [ ] Existing test suite green
- [ ] With `TUTOR_PROVIDER_OVERRIDE=self_hosted`: real tutor question end-to-end works
- [ ] Fallback verified by killing tutor-llm container
