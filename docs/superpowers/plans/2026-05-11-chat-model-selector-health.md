# Chat Model Selector And Health Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a user-facing chat model selector to `/agent` and in-context AI Tutor, while keeping routing on the existing routing model and adding admin health checks for the default model and local Qwen 3.5 4B model.

**Architecture:** Introduce a small backend chat-model registry that owns safe model IDs, provider kwargs, labels, and health checks. Frontend chat surfaces send only `chatModelId`; backend validates it and uses the selected model only for response-generation paths, not the existing routing model. Admin reads the registry health endpoint and renders status cards on the existing LLM monitoring page.

**Tech Stack:** FastAPI, Pydantic, LangChain `init_chat_model`, httpx, Next.js 14 App Router, React 18, Vitest, pytest.

---

## Scope Boundaries

Only touch these areas:

- Backend model selection and health:
  - `src/config.py`
  - `src/services/chat_model_factory.py`
  - `src/services/model_registry.py`
  - `src/services/agent_router_factory.py`
  - `src/services/agent_graph_service.py`
  - `src/services/agentic_rag_pipeline.py`
  - `src/services/llm_service.py`
  - `src/api/app.py`
  - `src/routers/agent.py`
  - `src/routers/admin.py`
  - backend tests listed in tasks below
- Frontend two chat surfaces and admin LLM page:
  - `frontend/features/agent/api.ts`
  - `frontend/features/agent/components/AgentChatPage.tsx`
  - `frontend/components/learn/InContextTutor.tsx`
  - `frontend/lib/chat-model-options.ts`
  - `frontend/lib/admin-api.ts`
  - `frontend/app/admin/llm/page.tsx`
  - frontend tests listed in tasks below

Do not change course catalog, assessment, onboarding, recommendation, auth, or database schema.

## Model IDs

- `default`: current configured chat model from `settings.default_model` and `settings.model_provider`.
- `qwen35_4b`: OpenAI-compatible local model:
  - display label: `Qwen 3.5 4B`
  - model name: `qwen 3.5 4B`
  - base URL: `https://vllm.a20-app-049.io.vn/v1`
  - API key fallback: `EMPTY` for OpenAI-compatible local providers.

## Task 1: Backend Model Registry

**Files:**
- Create: `src/services/model_registry.py`
- Modify: `src/config.py`
- Modify: `src/services/chat_model_factory.py`
- Test: `tests/services/test_model_registry.py`
- Test: `tests/test_chat_model_factory.py`

- [ ] **Step 1: Write failing registry tests**

Add tests that prove:

```python
def test_chat_model_registry_exposes_default_and_qwen_options():
    options = list_chat_model_options()
    ids = [option.id for option in options]
    assert ids == ["default", "qwen35_4b"]
    assert options[1].base_url == "https://vllm.a20-app-049.io.vn/v1"
    assert options[1].model == "qwen 3.5 4B"
```

```python
def test_build_kwargs_for_qwen_uses_openai_compatible_base_url(monkeypatch):
    kwargs = build_chat_model_kwargs_for_option("qwen35_4b", temperature=0.2)
    assert kwargs["model_provider"] == "openai"
    assert kwargs["model"] == "qwen 3.5 4B"
    assert kwargs["base_url"] == "https://vllm.a20-app-049.io.vn/v1"
    assert kwargs["api_key"] == "EMPTY"
    assert "reasoning" not in kwargs
```

Extend `tests/test_chat_model_factory.py` with:

```python
def test_openai_compatible_extra_api_key_satisfies_known_provider_requirement():
    with patch("src.services.chat_model_factory.settings.model_provider", "openai"), patch(
        "src.services.chat_model_factory.settings.openai_api_key",
        "",
    ):
        kwargs = build_chat_model_kwargs(
            model="qwen 3.5 4B",
            temperature=0.2,
            extra_kwargs={
                "base_url": "https://vllm.a20-app-049.io.vn/v1",
                "api_key": "EMPTY",
            },
        )
    assert kwargs["api_key"] == "EMPTY"
    assert kwargs["base_url"] == "https://vllm.a20-app-049.io.vn/v1"
```

- [ ] **Step 2: Run red tests**

Run:

```bash
uv run pytest tests/services/test_model_registry.py tests/test_chat_model_factory.py -q
```

Expected: fail because `src.services.model_registry` does not exist and `build_chat_model_kwargs` still requires `OPENAI_API_KEY` before honoring `extra_kwargs["api_key"]`.

- [ ] **Step 3: Implement registry and factory support**

Implement `ChatModelOption` with these fields:

```python
id: str
label: str
provider: str
model: str
base_url: str | None
api_key: str | None
is_default: bool
```

Add functions:

```python
list_chat_model_options() -> list[ChatModelOption]
get_chat_model_option(model_id: str | None) -> ChatModelOption
build_chat_model_kwargs_for_option(model_id: str | None, *, temperature: float, max_tokens: int | None = None) -> dict
```

Update `build_chat_model_kwargs` so `extra_kwargs["api_key"]` satisfies known OpenAI provider credentials for OpenAI-compatible local endpoints.

- [ ] **Step 4: Green tests**

Run the same pytest command. Expected: pass.

**DoD Checklist:**
- [ ] Unknown model IDs raise `ValueError`.
- [ ] Qwen option never depends on `OPENAI_API_KEY`.
- [ ] Default option keeps existing settings behavior.
- [ ] No frontend-visible secret is added.

## Task 2: Request Contracts Pass `chatModelId`

**Files:**
- Modify: `src/schemas/agent.py`
- Modify: `src/api/app.py`
- Test: `tests/test_agent_schema_contract.py`
- Test: `tests/test_lecture_routes.py`
- Test: `frontend/tests/features/agent/api.test.ts`
- Test: `frontend/tests/unit/tutor/in-context-tutor.test.tsx`

- [ ] **Step 1: Write failing contract tests**

Add backend tests:

```python
def test_chat_request_accepts_chat_model_id_alias():
    request = AgentChatRequest(message="Explain CNNs", chatModelId="qwen35_4b")
    assert request.chat_model_id == "qwen35_4b"
    assert request.model_dump(by_alias=True)["chatModelId"] == "qwen35_4b"
```

Add lecture route assertion:

```python
mock_stream.assert_called_once_with(
    "cs231n-lecture-1",
    12.0,
    "Explain this part",
    image_base64=None,
    context_binding_id="ctx_unit_lecture_01",
    user_id=None,
    chat_model_id="qwen35_4b",
)
```

Add frontend API tests that `agentApi.chat({ chatModelId: "qwen35_4b" })` posts `chatModelId`, and tutor fetch body includes `chatModelId`.

- [ ] **Step 2: Run red tests**

Run:

```bash
uv run pytest tests/test_agent_schema_contract.py tests/test_lecture_routes.py -q
npm test -- --run tests/features/agent/api.test.ts tests/unit/tutor/in-context-tutor.test.tsx
```

Expected: fail because `chatModelId` is not accepted or forwarded yet.

- [ ] **Step 3: Implement request fields**

Add `chat_model_id` to `AgentChatRequest` with alias `chatModelId`, default `default`, and validation through model registry. Add the same field to `AskRequest` with alias `chatModelId`.

Update frontend API types to accept optional `chatModelId`.

- [ ] **Step 4: Green tests**

Run the same commands. Expected: pass.

**DoD Checklist:**
- [ ] Existing clients without `chatModelId` still default to `default`.
- [ ] `chatModelId` uses camelCase over the frontend/backend API boundary.
- [ ] Invalid IDs fail validation before model invocation.

## Task 3: `/agent` Uses Selected Model For Response Generation Only

**Files:**
- Modify: `src/services/agent_router_factory.py`
- Modify: `src/services/agent_graph_service.py`
- Modify: `src/services/agentic_rag_pipeline.py`
- Modify: `src/routers/agent.py`
- Test: `tests/services/test_agent_router_factory.py`
- Test: `tests/services/test_agent_graph_service.py`

- [ ] **Step 1: Write failing tests**

Add a factory test proving:

```python
router = build_production_agent_response_router(
    chat_model_id="qwen35_4b",
    init_model=lambda **kwargs: FakeChatModel(),
)
assert captured_kwargs["model"] == "qwen 3.5 4B"
assert captured_kwargs["base_url"] == "https://vllm.a20-app-049.io.vn/v1"
```

Add graph service test with separate routers:

```python
service = AgentGraphService(..., router=RoutingRouter(), response_router=ResponseRouter())
```

The routing router records `route()` usage; response router records `compose_grounded_answer()` usage. Expected behavior:

- `route()` comes from routing router.
- final answer composition comes from response router.

- [ ] **Step 2: Run red tests**

Run:

```bash
uv run pytest tests/services/test_agent_router_factory.py tests/services/test_agent_graph_service.py -q
```

Expected: fail because there is no response router path yet.

- [ ] **Step 3: Implement response router separation**

Add `build_production_agent_response_router(chat_model_id=...)` that uses `build_chat_model_kwargs_for_option`.

Update `AgentGraphService`:

- Keep `self.router` for route, slot, policy, tool planning.
- Add `self.response_router = response_router or router`.
- Use `response_router` in assistant-help and grounded-answer composition.
- Pass `response_router` to external research synthesis.
- Update `AgenticRAGPipeline` to use routing router for `rag_think`, `rag_act`, `rag_observe`, and response router for `rag_respond`.

Update `src/routers/agent.py` to pass `response_router=build_production_agent_response_router(chat_model_id=body.chat_model_id)`.

- [ ] **Step 4: Green tests**

Run the same pytest command. Expected: pass.

**DoD Checklist:**
- [ ] `build_production_agent_router()` remains unchanged for routing model.
- [ ] Selected model affects response generation only.
- [ ] `web_papers` synthesis uses the selected response model.
- [ ] Existing deterministic-router tests keep working.

## Task 4: AI Tutor Uses Selected Model For Tutor Answer Generation

**Files:**
- Modify: `src/services/llm_service.py`
- Modify: `src/api/app.py`
- Test: `tests/services/test_llm_service_guardrails.py`
- Test: `tests/test_lecture_routes.py`

- [ ] **Step 1: Write failing tutor model selection tests**

Add a service-level test that patches `_get_llm_with_tools` and asserts the selected `chat_model_id` reaches the graph state for complex tutor flow.

Add route-level test that `AskRequest(chatModelId="qwen35_4b")` forwards `chat_model_id="qwen35_4b"` to `get_context_and_stream_langgraph`.

- [ ] **Step 2: Run red tests**

Run:

```bash
uv run pytest tests/test_lecture_routes.py tests/services/test_llm_service_guardrails.py -q
```

Expected: fail because tutor service has no `chat_model_id` parameter.

- [ ] **Step 3: Implement tutor model override**

Change `_get_llm_with_tools()` to `_get_llm_with_tools(chat_model_id: str)` with small LRU cache. Build kwargs through `build_chat_model_kwargs_for_option`.

Add `chat_model_id` to `AgentState` and graph inputs. In `call_model`, enforce rate limit using the selected option's provider/model and invoke `_get_llm_with_tools(chat_model_id)`.

If selected model is not `default` and router returns `SIMPLE`, route through the complex answer path so the selected chat model produces the final user answer.

- [ ] **Step 4: Green tests**

Run the same pytest command. Expected: pass.

**DoD Checklist:**
- [ ] Smart router still uses `FAST_MODEL`.
- [ ] Tutor final generation uses selected model.
- [ ] Default selection keeps existing simple-route behavior.
- [ ] Qwen selection does not require OpenAI cloud key.

## Task 5: Admin Model Health Endpoint

**Files:**
- Modify: `src/services/model_registry.py`
- Modify: `src/routers/admin.py`
- Test: `tests/services/test_model_registry.py`
- Test: `tests/test_admin_routes.py`

- [ ] **Step 1: Write failing health tests**

Add tests for:

```python
async def test_qwen_health_uses_openai_compatible_models_endpoint():
    result = await check_chat_model_health("qwen35_4b", client=fake_client)
    assert result["id"] == "qwen35_4b"
    assert result["status"] == "healthy"
    assert result["base_url"] == "https://vllm.a20-app-049.io.vn/v1"
```

Add admin route test:

```python
result = await model_health(_admin=object())
assert [item["id"] for item in result["models"]] == ["default", "qwen35_4b"]
```

- [ ] **Step 2: Run red tests**

Run:

```bash
uv run pytest tests/services/test_model_registry.py tests/test_admin_routes.py -q
```

Expected: fail because endpoint and health helper do not exist.

- [ ] **Step 3: Implement health helper and route**

Implement `check_chat_model_health(model_id, *, timeout_s=4.0, client=None)`:

- For OpenAI-compatible entries, call `{base_url}/models`.
- For default OpenAI without custom base URL, call `https://api.openai.com/v1/models` when an API key exists.
- Return `healthy`, `degraded`, or `down` with `latency_ms`, `checked_at`, and sanitized `error`.

Add:

```python
@admin_router.get("/model/health")
async def model_health(...)
```

- [ ] **Step 4: Green tests**

Run the same pytest command. Expected: pass.

**DoD Checklist:**
- [ ] Endpoint never returns API keys.
- [ ] Failed model health check does not fail the whole admin page.
- [ ] Health checks use short timeout.

## Task 6: Agent Chat Model Selector UI

**Files:**
- Create: `frontend/lib/chat-model-options.ts`
- Modify: `frontend/features/agent/api.ts`
- Modify: `frontend/features/agent/components/AgentChatPage.tsx`
- Test: `frontend/tests/features/agent/api.test.ts`
- Test: `frontend/tests/routes/agent/page.test.tsx`

- [ ] **Step 1: Write failing frontend tests**

Add route test:

```typescript
const qwenButton = await screen.findByRole("button", { name: /qwen 3.5 4b/i });
fireEvent.click(qwenButton);
fireEvent.change(input, { target: { value: "Explain CNNs" } });
fireEvent.click(screen.getByRole("button", { name: /send message/i }));
expect(agentApiMock.chat).toHaveBeenCalledWith(expect.objectContaining({
  chatModelId: "qwen35_4b",
}));
```

- [ ] **Step 2: Run red tests**

Run:

```bash
npm test -- --run tests/features/agent/api.test.ts tests/routes/agent/page.test.tsx
```

Expected: fail because selector and payload do not exist.

- [ ] **Step 3: Implement selector**

Create shared options:

```typescript
export type ChatModelId = "default" | "qwen35_4b";
export const CHAT_MODEL_OPTIONS = [
  { id: "default", label: "Default" },
  { id: "qwen35_4b", label: "Qwen 3.5 4B" },
] as const;
```

Add model selector buttons to `Composer` near tool-mode buttons. Persist to `localStorage` key `agent.chatModelId`. Pass selected `chatModelId` into `agentApi.chat`.

- [ ] **Step 4: Green tests**

Run the same npm test command. Expected: pass.

**DoD Checklist:**
- [ ] Selector is visible in `/agent` composer.
- [ ] Selection survives page reload through localStorage.
- [ ] Disabled state follows existing composer disabled state.
- [ ] Default payload remains valid.

## Task 7: In-Context Tutor Model Selector UI

**Files:**
- Modify: `frontend/components/learn/InContextTutor.tsx`
- Reuse: `frontend/lib/chat-model-options.ts`
- Test: `frontend/tests/unit/tutor/in-context-tutor.test.tsx`
- Test: `frontend/tests/routes/learning/unit.test.tsx`

- [ ] **Step 1: Write failing tutor UI tests**

Add a test that selects Qwen in the tutor panel and asserts the fetch body contains:

```json
{"chatModelId":"qwen35_4b"}
```

- [ ] **Step 2: Run red tests**

Run:

```bash
npm test -- --run tests/unit/tutor/in-context-tutor.test.tsx tests/routes/learning/unit.test.tsx
```

Expected: fail because tutor has no model selector.

- [ ] **Step 3: Implement selector**

Add compact model buttons to the tutor header. Persist to `localStorage` key `tutor.chatModelId`. Include selected `chatModelId` in `/api/lectures/ask` request body.

- [ ] **Step 4: Green tests**

Run the same npm test command. Expected: pass.

**DoD Checklist:**
- [ ] Selector is inside the tutor panel, not global navigation.
- [ ] It does not change lesson context, stored messages, or rating behavior.
- [ ] Fetch body includes `chatModelId`.

## Task 8: Admin Health UI

**Files:**
- Modify: `frontend/lib/admin-api.ts`
- Modify: `frontend/app/admin/llm/page.tsx`
- Test: `frontend/tests/routes/admin/llm.test.tsx`

- [ ] **Step 1: Write failing admin UI test**

Extend the mocked admin API with `modelHealth`, returning:

```typescript
{
  models: [
    { id: "default", label: "Default", provider: "openai", model: "gpt-5.4-mini", status: "healthy", latency_ms: 120 },
    { id: "qwen35_4b", label: "Qwen 3.5 4B", provider: "openai", model: "qwen 3.5 4B", status: "healthy", latency_ms: 80 },
  ],
}
```

Assert the page renders `Model health`, `Qwen 3.5 4B`, and `healthy`.

- [ ] **Step 2: Run red test**

Run:

```bash
npm test -- --run tests/routes/admin/llm.test.tsx
```

Expected: fail because admin UI does not call or render model health.

- [ ] **Step 3: Implement admin UI**

Add `ModelHealth` types and `adminApi.modelHealth()`. Load it with the existing LLM page calls. Render a compact status panel above volume KPIs.

- [ ] **Step 4: Green test**

Run the same npm test command. Expected: pass.

**DoD Checklist:**
- [ ] Admin page handles partial health errors.
- [ ] Health panel has clear status and latency.
- [ ] No API keys or secrets render in UI.

## Task 9: Final Verification

**Files:**
- No new source files beyond tasks above.

- [ ] **Step 1: Run targeted backend tests**

```bash
uv run pytest tests/services/test_model_registry.py tests/test_chat_model_factory.py tests/test_agent_schema_contract.py tests/test_lecture_routes.py tests/services/test_agent_router_factory.py tests/services/test_agent_graph_service.py tests/services/test_llm_service_guardrails.py tests/test_admin_routes.py -q
```

- [ ] **Step 2: Run targeted frontend tests**

```bash
npm test -- --run tests/features/agent/api.test.ts tests/routes/agent/page.test.tsx tests/unit/tutor/in-context-tutor.test.tsx tests/routes/learning/unit.test.tsx tests/routes/admin/llm.test.tsx
```

- [ ] **Step 3: Run type/build verification**

```bash
npm run type-check
npm run build
```

- [ ] **Step 4: Inspect diff**

```bash
git diff --stat
git diff -- src/services/model_registry.py src/services/chat_model_factory.py src/schemas/agent.py src/api/app.py src/routers/agent.py src/routers/admin.py frontend/features/agent/api.ts frontend/features/agent/components/AgentChatPage.tsx frontend/components/learn/InContextTutor.tsx frontend/app/admin/llm/page.tsx
```

**DoD Checklist:**
- [ ] All targeted tests pass or failures are documented with exact reason.
- [ ] Type check/build pass or failures are documented with exact reason.
- [ ] Diff stays inside scoped files.
- [ ] `/agent` and AI Tutor both expose model selection.
- [ ] Admin LLM page displays health for `default` and `qwen35_4b`.
