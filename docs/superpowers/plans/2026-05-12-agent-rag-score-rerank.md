# Agent RAG Score Rerank Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, generic score-based rerank stage for Agent RAG unit retrieval.

**Architecture:** Keep `AgentUnitSearchService` as the retrieval entry point, but replace the simple `title * 3 + body` scoring with a focused reranker helper that combines phrase, compact/acronym, title coverage, body coverage, and generic penalties. Do not hard-code course topics such as Mask R-CNN, CNN, RCNN, or Kim CNN.

**Tech Stack:** Python 3.12, FastAPI service layer, pytest async tests.

---

### Task 1: Cover Rerank Behavior

**Files:**
- Modify: `tests/services/test_agent_search_service.py`

- [ ] **Step 1: Add failing tests**

Add tests proving:
- `Mask RCNN` ranks `Instance segmentation with Mask R-CNN` above the broader `R-CNN family`.
- `Kim CNN` ranks `Kim CNN for sentence classification` above generic/deep CNN units.
- Broad `RCNN` keeps the base R-CNN family competitive and does not collapse to unrelated CNN foundations.

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/services/test_agent_search_service.py -q`

Expected: at least one new assertion fails because current scoring is too simple or lacks rerank trace/version.

- [ ] **Step 3: Commit tests**

Run:

```bash
git add tests/services/test_agent_search_service.py
git commit -m "test: cover agent unit rerank scoring"
```

### Task 2: Implement Generic Reranker

**Files:**
- Modify: `src/services/agent_search_service.py`

- [ ] **Step 1: Add scoring helpers**

Implement helpers in the same file for now:
- `_normalized_terms`
- `_coverage`
- `_compact_match`
- `_score_unit_candidate`

The scorer must emit numeric scores without domain-specific topic names.

- [ ] **Step 2: Wire scorer into search**

Use the scorer in `AgentUnitSearchService.search()` and update `ranking_version` to a new value such as `unit_title_rerank_v1`.

- [ ] **Step 3: Run focused tests**

Run: `uv run pytest tests/services/test_agent_search_service.py -q`

Expected: all search-service tests pass.

- [ ] **Step 4: Commit implementation**

Run:

```bash
git add src/services/agent_search_service.py
git commit -m "feat: rerank agent unit search results"
```

### Task 3: Regression Test Agent Flow

**Files:**
- No source edits expected.

- [ ] **Step 1: Run backend regression tests**

Run:

```bash
uv run pytest tests/services/test_agent_search_service.py tests/services/test_agent_graph_service.py tests/services/test_agent_tool_nodes_prerequisite_path.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Runtime smoke if backend is running**

Call `/api/agent/chat` for:
- `Mask RCNN`
- `Kim CNN`
- `RCNN`

Expected: targeted queries select the targeted unit, broad `RCNN` stays in the R-CNN family, and prerequisite graph action still appears for Mask R-CNN when available.
