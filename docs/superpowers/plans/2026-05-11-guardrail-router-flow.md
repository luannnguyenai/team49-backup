# Guardrail Router Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one shared 0.8B guardrail router gate for Tutor and Agent, with Cloudflare Tunnel vLLM first, OpenAI/Gemini fallback second, and explicit error on total router failure.

**Architecture:** Create a focused guardrail router service that validates a stable JSON decision schema and exposes sync and async entry points. Tutor calls the sync gate before the existing Tutor task routing, while Agent calls the async gate before `StructuredAgentRouter`. Later responder model replacement stays configuration-driven through provider/base-url/model settings rather than hardcoded API calls.

**Tech Stack:** Python 3.12, Pydantic, httpx, LangChain chat model factory, FastAPI service layer tests with pytest.

---

### Task 1: Guardrail Router Service

**Files:**
- Create: `src/services/guardrail_router.py`
- Test: `tests/services/test_guardrail_router.py`

- [x] **Step 1: Write failing tests**
  - Test OpenAI-compatible tunnel success.
  - Test tunnel failure falls back to model provider.
  - Test invalid/failed tunnel and failed model provider raises `GuardrailRouterUnavailableError`.

- [ ] **Step 2: Implement minimal service**
  - Add decision and scope models.
  - Add schema validation.
  - Add sync and async OpenAI-compatible HTTP calls.
  - Add fallback provider call using existing chat model factory.

### Task 2: Tutor Gate

**Files:**
- Modify: `src/services/llm_service.py`
- Test: `tests/services/test_tutor_guardrail_router.py`

- [ ] **Step 1: Write failing tests**
  - Verify a non-allow guardrail decision returns an English block/clarify/redirect event before the legacy Tutor router.
  - Verify disabled guardrail preserves existing Tutor routing.

- [ ] **Step 2: Implement minimal Tutor integration**
  - Build a `GuardrailScopePacket` from lecture title, current chapter, lecture outline, and lecture scope metadata.
  - Call the guardrail gate before `route_question()`.
  - Return English user-facing messages for `SAFETY_REFUSE`, `SOFT_REFUSE_REDIRECT`, and `ASK_CLARIFY`.

### Task 3: Agent Gate

**Files:**
- Modify: `src/services/agent_graph_service.py`
- Modify: `src/routers/agent.py`
- Test: `tests/services/test_agent_graph_service.py`

- [ ] **Step 1: Write failing tests**
  - Verify a non-allow guardrail decision returns an English `AgentChatResponse` without invoking `StructuredAgentRouter`.
  - Verify a guardrail service outage raises `AgentRouterUnavailableError` with `GUARDRAIL_ROUTER_UNAVAILABLE`.

- [ ] **Step 2: Implement minimal Agent integration**
  - Inject guardrail router service into `AgentGraphService`.
  - Run it after PII input sanitation and before graph-run creation.
  - Map router unavailable errors to the existing agent unavailable response path.

### Task 4: Configuration

**Files:**
- Modify: `src/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing tests**
  - Verify guardrail router config defaults are disabled and English-named.

- [ ] **Step 2: Implement config fields**
  - Add Cloudflare/vLLM base URL, model, API key, Cloudflare Access headers, timeout, fallback provider, and fallback model fields.
  - Keep all URLs configurable through environment variables.

### Task 5: Verification

**Files:**
- Run targeted tests.

- [ ] **Step 1: Run guardrail service tests**
- [ ] **Step 2: Run Tutor integration tests**
- [ ] **Step 3: Run Agent integration tests**
- [ ] **Step 4: Run config tests**
