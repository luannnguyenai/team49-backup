# DeepTutor-Style Agentic RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current fragmented RAG loop with a DeepTutor-style `thinking -> acting -> observing -> responding` Agentic RAG pipeline while preserving course/path policy and no-hallucination controls.

**Architecture:** Add a focused pipeline service under `src/services/agentic_rag_pipeline.py` plus contracts and tool adapters. `AgentGraphService` delegates RAG intents to that pipeline after route/policy/canonicalization, while non-RAG planner/action flows remain unchanged.

**Tech Stack:** Python 3.12, FastAPI service layer, Pydantic contracts, existing LangGraph graph, existing `StructuredAgentRouter`, existing unit search services, pytest.

---

## Files

- Create: `src/services/agentic_rag_contracts.py`
  - Pydantic stage contracts for thinking, tool calls, observations, and final response.
- Create: `src/services/agentic_rag_tools.py`
  - Tool adapter over existing `AgentToolNodes` and current-path/expanded-path rules.
- Create: `src/services/agentic_rag_pipeline.py`
  - DeepTutor-style pipeline orchestration.
- Modify: `src/services/agent_structured_router.py`
  - Add structured stage methods and prompts; remove old RAG-specific final/source-limited entrypoints once no longer used.
- Modify: `src/services/agent_graph_service.py`
  - Replace `rag_decide_tool/rag_execute_tool/rag_observe` branch with pipeline delegation.
- Modify: `src/services/agent_tool_nodes.py`
  - Keep retrieval behavior; remove user-facing canned text where pipeline should compose.
- Test: `tests/services/test_agentic_rag_pipeline.py`
- Test: `tests/services/test_agent_structured_router.py`
- Test: `tests/services/test_agent_graph_service.py`
- Test: `tests/services/test_agent_golden_eval_dataset.py`

---

## Task 1: Contracts

**Files:**
- Create: `src/services/agentic_rag_contracts.py`
- Test: `tests/services/test_agentic_rag_pipeline.py`

- [ ] **Step 1: Write failing contract tests**

Create `tests/services/test_agentic_rag_pipeline.py` with tests that validate:

```python
from src.services.agent_graph_contracts import ToolResult
from src.services.agentic_rag_contracts import (
    AgenticRAGObservation,
    AgenticRAGToolCall,
)


def test_agentic_rag_tool_call_rejects_unknown_tool():
    try:
        AgenticRAGToolCall(tool="search_web", arguments={}, rationale="bad")
    except Exception as exc:
        assert "search_web" in str(exc)
    else:
        raise AssertionError("unknown tools must be rejected")


def test_agentic_rag_observation_wraps_tool_result():
    result = ToolResult(kind="clarification", answer_markdown="Need more detail.")
    observation = AgenticRAGObservation(
        tool="ask_clarification",
        success=True,
        evidence_status="needs_clarification",
        result=result,
    )

    assert observation.result.answer_markdown == "Need more detail."
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
docker exec al_backend uv run pytest -q tests/services/test_agentic_rag_pipeline.py
```

Expected: fail because `src.services.agentic_rag_contracts` does not exist.

- [ ] **Step 3: Implement contracts**

Create `src/services/agentic_rag_contracts.py`:

```python
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.services.agent_graph_contracts import ToolResult


AgenticRAGToolName = Literal[
    "search_current_path_units",
    "get_unit_summary",
    "ask_clarification",
    "offer_scope_expansion",
    "search_allowed_other_paths",
]

AgenticRAGEvidenceStatus = Literal[
    "grounded",
    "partial",
    "too_many_results",
    "scope_expansion_required",
    "no_source",
    "needs_clarification",
]


class AgenticRAGThought(BaseModel):
    user_goal: str
    active_topic: str | None = None
    missing_information: list[str] = Field(default_factory=list)
    evidence_need: Literal["none", "retrieval", "clarification"] = "retrieval"
    tool_plan: list[str] = Field(default_factory=list)


class AgenticRAGToolCall(BaseModel):
    tool: AgenticRAGToolName
    arguments: dict[str, Any] = Field(default_factory=dict)
    rationale: str


class AgenticRAGObservation(BaseModel):
    tool: AgenticRAGToolName
    success: bool
    evidence_status: AgenticRAGEvidenceStatus
    result: ToolResult


class AgenticRAGFinal(BaseModel):
    answer_markdown: str
    evidence_status: AgenticRAGEvidenceStatus
    evidence_sufficient: bool = False
    clarification_question: str | None = None
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
docker exec al_backend uv run pytest -q tests/services/test_agentic_rag_pipeline.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/services/agentic_rag_contracts.py tests/services/test_agentic_rag_pipeline.py
git commit -m "feat: add agentic rag contracts"
```

---

## Task 2: Tool Adapter

**Files:**
- Create: `src/services/agentic_rag_tools.py`
- Modify: `tests/services/test_agentic_rag_pipeline.py`

- [ ] **Step 1: Add failing tool adapter tests**

Append tests for:

```python
import pytest

from src.services.agent_graph_contracts import AgentSlots, ToolResult
from src.services.agentic_rag_contracts import AgenticRAGToolCall
from src.services.agentic_rag_tools import AgenticRAGToolExecutor


class FakeToolNodes:
    def __init__(self):
        self.calls = []

    async def clarify(self, message, reason="ambiguous_target"):
        self.calls.append(("clarify", message, reason))
        return ToolResult(kind="clarification", answer_markdown=reason)

    async def find_content(self, message, intent, slots, allowed_course_ids):
        self.calls.append(("find_content", message, intent, slots, allowed_course_ids))
        return ToolResult(
            kind="find_content",
            answer_markdown=None,
            citations=[],
            metadata={"search_queries": slots.search_queries},
        )


@pytest.mark.asyncio
async def test_tool_executor_searches_current_path_with_llm_query():
    tools = FakeToolNodes()
    executor = AgenticRAGToolExecutor(tools)
    slots = AgentSlots(raw_topic="YOLO", search_queries=["YOLO"])

    observation = await executor.execute(
        AgenticRAGToolCall(
            tool="search_current_path_units",
            arguments={"query": "YOLO single-stage detector"},
            rationale="search topic",
        ),
        message="Tìm YOLO",
        intent="find_content",
        slots=slots,
        allowed_course_ids=["CS231N"],
    )

    assert observation.tool == "search_current_path_units"
    assert tools.calls[0][3].search_queries == ["YOLO single-stage detector"]


@pytest.mark.asyncio
async def test_tool_executor_blocks_expanded_search_without_approval():
    tools = FakeToolNodes()
    executor = AgenticRAGToolExecutor(tools)
    slots = AgentSlots(raw_topic="CNN", search_scope="current_path")

    observation = await executor.execute(
        AgenticRAGToolCall(
            tool="search_allowed_other_paths",
            arguments={"query": "CNN"},
            rationale="try broader search",
        ),
        message="find CNN",
        intent="find_content",
        slots=slots,
        allowed_course_ids=["CS224N", "CS231N"],
    )

    assert observation.evidence_status == "scope_expansion_required"
    assert observation.result.kind == "clarification"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
docker exec al_backend uv run pytest -q tests/services/test_agentic_rag_pipeline.py
```

Expected: fail because `agentic_rag_tools.py` does not exist.

- [ ] **Step 3: Implement tool adapter**

Create `src/services/agentic_rag_tools.py` with `AgenticRAGToolExecutor.execute()` that:

- maps `search_current_path_units` to `AgentToolNodes.find_content`
- maps `search_allowed_other_paths` only when `slots.search_scope == "expanded_paths"` or `slots.scope_expansion_approved`
- maps `ask_clarification` to `AgentToolNodes.clarify`
- maps `offer_scope_expansion` to a clarification result with `scope_expansion_offered=True`
- returns observations with status derived from `ToolResult.metadata`, citations, fallback, and warning.

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
docker exec al_backend uv run pytest -q tests/services/test_agentic_rag_pipeline.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/services/agentic_rag_tools.py tests/services/test_agentic_rag_pipeline.py
git commit -m "feat: add agentic rag tool adapter"
```

---

## Task 3: Structured Router Stage Methods

**Files:**
- Modify: `src/services/agent_structured_router.py`
- Modify: `tests/services/test_agent_structured_router.py`

- [ ] **Step 1: Add failing tests for stage methods**

Add tests asserting the router exposes:

- `rag_think(...)`
- `rag_act(...)`
- `rag_observe(...)`
- `rag_respond(...)`

The fake model should verify prompts include stage-specific instructions and do
not include domain keyword maps.

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
docker exec al_backend uv run pytest -q tests/services/test_agent_structured_router.py
```

Expected: fail because methods are missing.

- [ ] **Step 3: Implement router stage methods**

Add methods to `StructuredAgentRouter` using structured output from
`agentic_rag_contracts.py`. Prompts must:

- say output is internal for thinking/observing
- tell acting to choose only allowed tools
- tell responding to use only validated evidence
- preserve natural user language
- forbid invented course facts and unvalidated options
- avoid exact answer templates.

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
docker exec al_backend uv run pytest -q tests/services/test_agent_structured_router.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/services/agent_structured_router.py tests/services/test_agent_structured_router.py
git commit -m "feat: add agentic rag router stages"
```

---

## Task 4: Pipeline Core

**Files:**
- Create: `src/services/agentic_rag_pipeline.py`
- Modify: `tests/services/test_agentic_rag_pipeline.py`

- [ ] **Step 1: Add failing pipeline orchestration tests**

Test that:

- pipeline calls router stages in order
- tool result observations are passed to observe/respond
- final answer is returned as `ToolResult`
- no hidden thought text appears in final answer.

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
docker exec al_backend uv run pytest -q tests/services/test_agentic_rag_pipeline.py
```

Expected: fail because `AgenticRAGPipeline` does not exist.

- [ ] **Step 3: Implement pipeline**

Create `AgenticRAGPipeline.run(...)` that:

1. calls `router.rag_think`
2. calls `router.rag_act`
3. executes each tool call through `AgenticRAGToolExecutor`
4. calls `router.rag_observe`
5. validates citation/evidence constraints
6. calls `router.rag_respond`
7. returns a `ToolResult` with final markdown, citations, actions, warning,
   fallback, metadata, and trace.

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
docker exec al_backend uv run pytest -q tests/services/test_agentic_rag_pipeline.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/services/agentic_rag_pipeline.py tests/services/test_agentic_rag_pipeline.py
git commit -m "feat: add agentic rag pipeline"
```

---

## Task 5: Graph Integration

**Files:**
- Modify: `src/services/agent_graph_service.py`
- Modify: `tests/services/test_agent_graph_service.py`

- [ ] **Step 1: Add failing graph integration tests**

Add tests proving RAG intents delegate to `AgenticRAGPipeline` after policy, while
non-RAG intents still dispatch to existing action nodes.

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
docker exec al_backend uv run pytest -q tests/services/test_agent_graph_service.py
```

Expected: fail until graph integration exists.

- [ ] **Step 3: Integrate pipeline**

Modify `AgentGraphService`:

- instantiate `AgenticRAGToolExecutor` and `AgenticRAGPipeline`
- replace old `rag_decide_tool -> rag_execute_tool -> rag_observe` node chain with one `agentic_rag` node
- keep existing pending clarification persistence behavior
- keep run lifecycle/dedupe/lock behavior unchanged.

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
docker exec al_backend uv run pytest -q tests/services/test_agent_graph_service.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/services/agent_graph_service.py tests/services/test_agent_graph_service.py
git commit -m "feat: wire agentic rag pipeline into graph"
```

---

## Task 6: Remove Old RAG Seams

**Files:**
- Modify: `src/services/agent_structured_router.py`
- Modify: `src/services/agent_graph_service.py`
- Modify: `tests/services/test_agent_structured_router.py`
- Modify: `tests/services/test_agent_graph_service.py`

- [ ] **Step 1: Search old seams**

Run:

```bash
rg -n "plan_rag_tool|compose_react_final|compose_source_limited_answer|rag_decide_tool|rag_execute_tool|rag_observe" src tests
```

Expected: list old references.

- [ ] **Step 2: Remove unused old seams**

Delete old methods only after Task 5 tests pass and no production code depends on
them.

- [ ] **Step 3: Run agent test suite**

Run:

```bash
docker exec al_backend uv run pytest -q tests/services/test_agentic_rag_pipeline.py tests/services/test_agent_structured_router.py tests/services/test_agent_graph_service.py tests/services/test_agent_golden_eval_dataset.py
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add src/services/agent_structured_router.py src/services/agent_graph_service.py tests/services/test_agent_structured_router.py tests/services/test_agent_graph_service.py
git commit -m "refactor: remove legacy rag seams"
```

---

## Task 7: Verification

**Files:**
- No new files expected.

- [ ] **Step 1: Run focused tests**

```bash
docker exec al_backend uv run pytest -q tests/services/test_agentic_rag_pipeline.py tests/services/test_agent_structured_router.py tests/services/test_agent_graph_service.py tests/services/test_agent_golden_eval_dataset.py
```

Expected: pass.

- [ ] **Step 2: Run agent-wide service tests**

```bash
docker exec al_backend uv run pytest -q tests/services/test_agent_*.py
```

Expected: pass or only known live-router skips.

- [ ] **Step 3: Check formatting diff**

```bash
git diff --check
```

Expected: no output.

- [ ] **Step 4: Run GitNexus changed-scope check**

```bash
gitnexus detect-changes
```

Expected: changed symbols and flows match Agentic RAG scope.

---

## Self-Review

- Spec coverage: pipeline stages, tool contract, memory, hallucination controls,
  Planner Mode boundary, and testing are covered.
- Placeholder scan: no placeholder tasks are left.
- Type consistency: all new contract names use `AgenticRAG*`; graph integration
  references a single `agentic_rag` node.
