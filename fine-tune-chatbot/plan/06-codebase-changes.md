# P7 — Codebase Changes

**Goal**: integrate `tutor-v1` self-hosted endpoint with minimal-but-correct
changes. The LangChain abstraction in `chat_model_factory.py` already
supports OpenAI-compatible endpoints — we extend it with a `self_hosted`
provider, add provider-specific compiled graphs, and inject a pre-stream
fallback (no mid-stream graph rebuild).

## Preflight — GitNexus impact analysis (mandatory per project CLAUDE.md)

Before editing any symbol below, run:

```
gitnexus_impact({target: "init_chat_model", direction: "upstream"})
gitnexus_impact({target: "_get_llm_with_tools", direction: "upstream"})
gitnexus_impact({target: "build_chat_model_kwargs", direction: "upstream"})
gitnexus_impact({target: "compiled_graph", direction: "upstream"})
gitnexus_impact({target: "enforce_llm_rate_limit", direction: "upstream"})
gitnexus_impact({target: "get_context_and_stream_langgraph", direction: "upstream"})
```

For each target, report blast radius (direct callers, affected processes,
risk level) before applying the diff. **Block if any target returns
HIGH/CRITICAL** until reviewer signs off.

After all changes are applied:

```
gitnexus_detect_changes()
```

Verify only the symbols listed in this plan show up in the affected scope.
Any unexpected symbol = bug — investigate before committing.

If the index is stale, run `npx gitnexus analyze` first.

**Files touched (6 source + 2 config + 2 test = 10 files)**:

Source:
- `src/config.py` — new settings
- `src/services/chat_model_factory.py` — `self_hosted` branch
- `src/services/llm_service.py` — provider-specific graph cache + pre-stream fallback
- `src/services/llm_rate_limiter.py` — bypass for self-hosted

Config:
- `.env.example` — new env vars
- `docker-compose.yml` — pass new env vars to backend; backend depends on tutor-llm

Tests (new):
- `tests/services/test_chat_model_factory.py` — unit tests for `self_hosted` branch
- `tests/services/test_llm_rate_limiter.py` — bypass behavior

**Files NOT touched**: `src/agent.py`, `src/services/router.py` (router stays
on Gemini in v1), all API routers, LangGraph topology (nodes, edges, state).

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
    tutor_canary_ratio: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="When tutor_provider_override is set, fraction of traffic actually routed to it (hash-based on lecture_id)",
    )
    tutor_kill_switch: bool = Field(
        default=False,
        description="Global kill-switch: when true, force fallback provider regardless of override",
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
# Leave empty until rollout. Set to "self_hosted" to route tutor through vLLM.
TUTOR_PROVIDER_OVERRIDE=
TUTOR_FALLBACK_PROVIDER=google_genai
TUTOR_FALLBACK_MODEL=gemini-2.0-flash
# Shadow ratio: 0.0 = off, 0.1 = log self-hosted on 10% of requests for comparison
TUTOR_SHADOW_RATIO=0.0
# Canary ratio: fraction of traffic routed to override provider (1.0 = all)
TUTOR_CANARY_RATIO=1.0
# Kill switch: if true, force fallback provider regardless of override
TUTOR_KILL_SWITCH=false
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
  TUTOR_CANARY_RATIO: ${TUTOR_CANARY_RATIO:-1.0}
  TUTOR_KILL_SWITCH: ${TUTOR_KILL_SWITCH:-false}
```

For the `backend` service, use a healthcheck-aware dependency so backend
waits for vLLM to be ready (not just started):

```yaml
backend:
  # ... existing config ...
  depends_on:
    db:
      condition: service_healthy
    redis:
      condition: service_healthy
    tutor-llm:
      condition: service_healthy
      required: false   # backend can start even if tutor-llm is down (uses fallback)
```

⚠️ Compose `condition: service_healthy` requires Compose v2.20+. Verify
with `docker compose version`. If older, omit the `tutor-llm` dependency
entirely — backend will rely on runtime fallback when vLLM is unreachable.

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

## Change 3 — `src/services/llm_service.py`

Three changes: provider-specific graph cache, provider selection function,
and pre-stream fallback wrapper. **No mid-stream graph rebuild.**

### 3a. Replace single compiled graph with provider-keyed cache

Remove the module-level `compiled_graph = graph_builder.compile()` and the
single `_get_llm_with_tools` function. Replace with:

```python
import hashlib

_GRAPH_CACHE: dict[str, object] = {}

def _build_llm_for(provider: str):
    """Build a tool-bound LLM for the given provider."""
    model_name = "tutor-v1" if provider == "self_hosted" else (
        settings.tutor_fallback_model if provider == settings.tutor_fallback_provider
        else DEFAULT_MODEL
    )
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
        # Local models without tool support — degrade gracefully (no sandbox)
        return llm


def _get_compiled_graph(provider: str):
    """Provider-specific compiled graph. Built once per provider, reused."""
    if provider in _GRAPH_CACHE:
        return _GRAPH_CACHE[provider]

    llm_with_tools = _build_llm_for(provider)

    def _call_model(state: AgentState):
        enforce_llm_rate_limit(model="tutor", model_provider=provider)
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    builder = StateGraph(AgentState)
    builder.add_node("agent", _call_model)
    builder.add_node("tools", tool_node)
    builder.add_node("give_up", give_up_node)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", should_continue, ["tools", "give_up", END])
    builder.add_edge("tools", "agent")
    builder.add_edge("give_up", END)

    compiled = builder.compile()
    _GRAPH_CACHE[provider] = compiled
    return compiled
```

Delete the old:
```python
@lru_cache(maxsize=1)
def _get_llm_with_tools(): ...

def call_model(state): ...   # replaced by closure inside _get_compiled_graph

compiled_graph = graph_builder.compile()  # replaced by per-provider cache
```

### 3b. Provider selection (called per request)

```python
def _select_provider(lecture_id: str | None = None) -> str:
    """Decide which provider to use for this request. Pure function."""
    if settings.tutor_kill_switch:
        return settings.tutor_fallback_provider

    override = settings.tutor_provider_override
    if not override:
        return settings.model_provider

    # Canary: only route a fraction of traffic to override
    ratio = settings.tutor_canary_ratio
    if ratio >= 1.0 or not lecture_id:
        return override

    h = int(hashlib.md5(lecture_id.encode()).hexdigest(), 16) / (2**128)
    return override if h < ratio else settings.model_provider
```

### 3c. Pre-stream fallback wrapper (no mid-stream switch)

⚠️ **Iterator semantics MUST be verified against the actual LangGraph
version in use.** The pseudo-code below uses `next(stream)` assuming a
sync iterator with eager probe. LangGraph 0.2+ may return:
- a sync iterator over `(chunk, metadata)` tuples (matches code below), OR
- an async iterator that requires `anext()`, OR
- a streaming iterator that defers the first network call until `__next__`
  (in which case `next()` does NOT probe the model — first failure
  surfaces only on actual generation)

Before writing the production wrapper:
1. Add a unit test `tests/services/test_stream_iterator_semantics.py` that
   inspects the type of `compiled_graph.stream(...)` and asserts whether
   `next()` triggers model invocation
2. Choose between sync/async path based on test result
3. If the iterator is "deferred" (next() does not probe): switch to
   explicit pre-flight HTTP `GET /v1/models` ping on `self_hosted_base_url`
   instead of relying on `next()` to detect the failure

Reference implementation (sync, eager-probe path):

```python
def _stream_with_fallback(inputs, lecture_id: str | None):
    """Stream from primary; on pre-stream failure, retry with fallback.
    NEVER switches mid-stream — once a token is emitted, primary owns the response.
    """
    primary = _select_provider(lecture_id)
    fallback = settings.tutor_fallback_provider

    # Pre-flight ping for self_hosted (cheap; ~50ms via tunnel)
    if primary == "self_hosted":
        if not _self_hosted_alive(timeout_s=2.0):
            qa_logger.warning("Self-hosted unreachable; routing to fallback")
            primary = fallback

    # Probe-and-stream pattern: compile graph; first iter() may raise before yielding
    try:
        graph = _get_compiled_graph(primary)
        stream = graph.stream(inputs, stream_mode="messages")
        first = next(stream)   # may raise — caught here
    except StopIteration:
        return  # empty stream is OK
    except Exception as e:
        # Pre-first-token failure — safe to fall back
        if primary == fallback or primary != "self_hosted":
            raise   # fallback path itself failed, or primary wasn't self_hosted
        qa_logger.error(
            f"Self-hosted failed pre-stream: {e}. Falling back to {fallback}"
        )
        graph = _get_compiled_graph(fallback)
        yield from graph.stream(inputs, stream_mode="messages")
        return

    # First chunk succeeded; commit to this provider for the rest of the stream
    yield first
    try:
        yield from stream
    except Exception as mid_err:
        # Mid-stream failure — log and emit error event, do NOT silently switch
        qa_logger.error(f"{primary} failed mid-stream: {mid_err}")
        # Emit a structured error chunk that the caller can render as "[stream error]"
        from langchain_core.messages import AIMessage
        yield (AIMessage(content="\n\n[stream interrupted — please retry]"), None)


def _self_hosted_alive(timeout_s: float = 2.0) -> bool:
    """Cheap reachability check; cached for 5s to avoid hammering on bursts."""
    import time, requests
    cache = getattr(_self_hosted_alive, "_cache", (0.0, False))
    if time.time() - cache[0] < 5.0:
        return cache[1]
    try:
        r = requests.get(
            f"{settings.self_hosted_base_url}/models",
            timeout=timeout_s,
            headers=_self_hosted_headers(),  # CF-Access if configured
        )
        ok = r.status_code == 200
    except Exception:
        ok = False
    _self_hosted_alive._cache = (time.time(), ok)
    return ok
```

Required tests:
- `test_pre_flight_alive_caches` — second call within 5s does not hit network
- `test_pre_flight_failure_routes_to_fallback` — when alive returns False
- `test_no_mid_stream_switch` — when first token succeeds, mid-stream
  exception is logged, NOT silently retried on fallback
- `test_fallback_path_runs_on_pre_stream_failure` — first call raises,
  second graph compiled with fallback provider yields tokens

### 3d. Wire it into the streaming generator

In `get_context_and_stream_langgraph`, replace:

```python
for chunk, metadata in compiled_graph.stream(inputs, stream_mode="messages"):
```

with:

```python
for chunk, metadata in _stream_with_fallback(inputs, lecture_id):
```

### 3e. Vision routing for self-hosted

Self-hosted Qwen2.5-VL handles `image_base64` natively — no special
handling needed because the LangChain `{"type":"image_url","image_url":{"url":"data:image/..."}}`
format already matches what vLLM expects (Qwen vision tokens encoded
inside the same chat message).

**No changes** required to the `content_list` building logic at lines
358–363.

### 3f. Shadow-mode logging — OFFLINE REPLAY (revised)

Inline shadow (calling `graph.stream()` from the request path) risks
blocking the main response or starving the GPU even with `create_task`.
**V1 uses offline replay instead**: the request handler logs only the
input + primary answer; a separate batch worker replays sampled inputs
through self-hosted out-of-band.

Inline change in `get_context_and_stream_langgraph`: after
`_save_qa_history`, also append a one-line shadow-eligible record to a
dedicated rotating log when `tutor_shadow_ratio > 0` AND
`tutor_provider_override != "self_hosted"`:

```python
def _log_shadow_eligible(inputs_meta, primary_answer: str, lecture_id: str, question: str):
    """Append to shadow eligibility log. NO inference here."""
    if settings.tutor_shadow_ratio <= 0:
        return
    import random
    if random.random() >= settings.tutor_shadow_ratio:
        return
    shadow_jsonl_logger.info(json.dumps({
        "ts": time.time(),
        "lecture": lecture_id,
        "q": question[:2000],
        "primary_provider": settings.model_provider,
        "primary_a": primary_answer[:2000],
        "inputs_meta_hash": _hash_inputs(inputs_meta),
        # Note: we re-build full inputs offline from lecture_id + at_seconds + question
    }, ensure_ascii=False))
```

The `shadow_jsonl_logger` writes to `logs/shadow_eligible.jsonl` with
log rotation (50MB / 7 days).

**Offline replay worker** at `fine-tune-chatbot/scripts/eval/shadow_replay.py`:
- Reads `logs/shadow_eligible.jsonl`
- For each row, rebuilds `inputs` from `lecture_id + at_seconds + question`
  via the existing context fetchers
- Runs `_get_compiled_graph("self_hosted")` to generate shadow answer
- Writes paired log to `eval/runs/shadow/<date>.jsonl`
- Triggered hourly via cron / systemd timer; not in the request path

This decouples observability from request latency entirely. If shadow
worker fails or falls behind, primary serving is unaffected.

## Change 4 — Rate limiter (bypass external quota + add local capacity guard)

`src/services/llm_rate_limiter.py` currently throttles for Gemini API quota.
For self-hosted, there's no external quota — but local GPU still has
finite VRAM and `--max-num-seqs` cap. **Bypassing the quota limiter
without adding a local capacity guard risks OOM under spike load.**

### 4a. Bypass external quota for self-hosted

```python
def enforce_llm_rate_limit(model: str, model_provider: str) -> None:
    if model_provider == "self_hosted":
        return  # no external quota to respect; local capacity guard runs separately
    # ... existing logic ...
```

(Verify exact function signature when applying — do not break existing code.)

### 4b. Add local capacity guard (NEW)

Add a backend-level semaphore that caps concurrent requests to the
self-hosted endpoint. Match `vllm --max-num-seqs N` minus 1 (leave
headroom for retries / shadow / fallback probes).

`src/services/llm_capacity_guard.py` (new file):

```python
"""Local capacity guard for self-hosted vLLM endpoint.

vLLM has its own queue, but backend should backpressure earlier so that
a queue overflow returns a fast 503 to clients instead of a 30s timeout.
"""
from __future__ import annotations
import asyncio
from src.config import settings

# vLLM container is configured with --max-num-seqs N; backend caps at N-1
_LOCAL_MAX_INFLIGHT = max(1, settings.self_hosted_max_inflight - 1)
_self_hosted_sem = asyncio.Semaphore(_LOCAL_MAX_INFLIGHT)


async def acquire_self_hosted_slot(timeout_s: float = 2.0) -> bool:
    """Acquire a self-hosted inference slot. Returns False if timeout."""
    try:
        await asyncio.wait_for(_self_hosted_sem.acquire(), timeout=timeout_s)
        return True
    except asyncio.TimeoutError:
        return False


def release_self_hosted_slot() -> None:
    _self_hosted_sem.release()
```

Add `self_hosted_max_inflight: int = 4` to `Settings` (matches default
`--max-num-seqs 4`).

Wire it in `_stream_with_fallback` BEFORE attempting the primary stream:

```python
def _stream_with_fallback(inputs, lecture_id):
    primary = _select_provider(lecture_id)
    if primary == "self_hosted":
        if not run_async(acquire_self_hosted_slot(timeout_s=2.0)):
            # Backpressure: route this request straight to fallback
            qa_logger.warning("Self-hosted at capacity; routing to fallback")
            primary = settings.tutor_fallback_provider
        else:
            try:
                yield from _stream_primary_with_fallback(primary, inputs, lecture_id)
            finally:
                release_self_hosted_slot()
            return
    yield from _stream_primary_with_fallback(primary, inputs, lecture_id)
```

(Pseudo-code; adapt to FastAPI's async streaming generator pattern; if
the call site is sync, use `anyio` or a sync semaphore.)

Alert on sustained semaphore exhaustion: log when `acquire_self_hosted_slot`
returns False; if rate > 5% over 5 min, ops should investigate
(typically: spike traffic, slow generation, or misconfigured `max-num-seqs`).

## Change 5 — Tests

### `tests/services/test_chat_model_factory.py` (new)

```python
import pytest
from unittest.mock import patch
from src.services.chat_model_factory import build_chat_model_kwargs

def test_self_hosted_returns_openai_compatible(monkeypatch):
    monkeypatch.setattr("src.config.settings.self_hosted_base_url", "http://x:8000/v1")
    monkeypatch.setattr("src.config.settings.self_hosted_api_key", "k")
    kw = build_chat_model_kwargs(model="tutor-v1", temperature=0.2,
                                  model_provider="self_hosted")
    assert kw["model_provider"] == "openai"
    assert kw["base_url"] == "http://x:8000/v1"
    assert kw["api_key"] == "k"
    assert kw["model"] == "tutor-v1"

def test_existing_providers_unchanged(monkeypatch):
    monkeypatch.setattr("src.config.settings.gemini_api_key", "g_key")
    kw = build_chat_model_kwargs(model="gemini-2.0-flash", temperature=0.2,
                                  model_provider="google_genai")
    assert kw["model_provider"] == "google_genai"
    assert "base_url" not in kw
    assert kw["api_key"] == "g_key"
```

### `tests/services/test_llm_rate_limiter.py` (new or extend existing)

```python
def test_self_hosted_bypasses_rate_limit(monkeypatch):
    from src.services.llm_rate_limiter import enforce_llm_rate_limit
    # Should not raise even if no quota remains for any provider
    enforce_llm_rate_limit(model="tutor-v1", model_provider="self_hosted")
```

### `tests/services/test_llm_service_provider.py` (new)

```python
def test_select_provider_kill_switch(monkeypatch):
    from src.services.llm_service import _select_provider
    monkeypatch.setattr("src.config.settings.tutor_kill_switch", True)
    monkeypatch.setattr("src.config.settings.tutor_fallback_provider", "google_genai")
    assert _select_provider("any") == "google_genai"

def test_select_provider_canary_ratio(monkeypatch):
    from src.services.llm_service import _select_provider
    monkeypatch.setattr("src.config.settings.tutor_kill_switch", False)
    monkeypatch.setattr("src.config.settings.tutor_provider_override", "self_hosted")
    monkeypatch.setattr("src.config.settings.model_provider", "google_genai")
    monkeypatch.setattr("src.config.settings.tutor_canary_ratio", 0.0)
    assert _select_provider("lecture-1") == "google_genai"   # 0% canary

    monkeypatch.setattr("src.config.settings.tutor_canary_ratio", 1.0)
    assert _select_provider("lecture-1") == "self_hosted"   # 100% canary
```

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

- [ ] **Preflight GitNexus impact analysis** completed for all 6 target
      symbols; no HIGH/CRITICAL surprises
- [ ] All file changes applied (count = files touched in this plan):
  - `src/config.py`
  - `src/services/chat_model_factory.py`
  - `src/services/llm_service.py`
  - `src/services/llm_rate_limiter.py`
  - `src/services/llm_capacity_guard.py` (new)
  - `.env.example`
  - `docker-compose.yml`
  - `tests/services/test_chat_model_factory.py` (new)
  - `tests/services/test_llm_rate_limiter.py` (new or extended)
  - `tests/services/test_llm_service_provider.py` (new)
  - `tests/services/test_stream_iterator_semantics.py` (new)
  - `tests/services/test_llm_capacity_guard.py` (new)
- [ ] **Patch is based on current source** (not pseudo-code from this plan):
      each diff inspected against live `src/` files at apply time, with
      symbol names verified via grep + GitNexus
- [ ] Existing test suite green (`pytest tests/`)
- [ ] New tests green (provider selection, fallback pre-first-token,
      capacity guard, iterator semantics, no mid-stream switch)
- [ ] **`gitnexus_detect_changes()`** post-edit: only the symbols above
      show up in affected scope; investigate any extras
- [ ] With `TUTOR_PROVIDER_OVERRIDE=self_hosted`: real tutor question
      end-to-end works (text + image + tool-call paths all verified)
- [ ] Fallback verified by killing tutor-llm container during a request
- [ ] Capacity guard verified: synthetic load above
      `self_hosted_max_inflight - 1` returns fast fallback, not timeout
