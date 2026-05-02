# Agent Golden Evals

This repository now has a reviewable golden evaluation dataset for the `/agent`
ReAct RAG flow:

- `tests/fixtures/agent/golden_eval_cases.json`
- `tests/services/test_agent_golden_eval_dataset.py`

The dataset is a product behavior contract. It is not a prompt file, not a
production keyword list, and not a synonym map. Do not copy fixture terms into
runtime routing, retrieval, or canned response branches.

## What It Covers

The current fixture includes Vietnamese and English cases for:

- initial content retrieval
- same-topic follow-up resolution
- source-limited answers when the available evidence is narrow
- contextual evidence gaps, such as a follow-up asking for details not present
  in the retrieved source
- switching to a new topic after an active context
- visible thread-memory recall
- current-path-first search and explicit scope expansion
- too-many-results refinement and top-result approval
- failed-request retry using the original user request
- lexical traps that must not route by raw keywords
- assessment and future Planner Mode boundaries

## Review Rules

When editing `golden_eval_cases.json`:

- keep each case behavior-oriented instead of exact-answer-oriented
- include both expected behavior and forbidden behavior
- keep Vietnamese and English coverage for important user journeys
- prefer policies like `must_not_reuse_active_yolo_citation` over fixed output
  text
- keep source/evidence expectations explicit
- do not add runtime-only implementation details to the fixture

The fixture may mention concrete topics such as YOLO, CNN, or U-Net because those
are human-reviewed eval examples. That does not permit production code to
hard-code those terms.

## Run

Use the deterministic dataset checks:

```bash
docker exec al_backend uv run pytest -q tests/services/test_agent_golden_eval_dataset.py
```

The existing live routing eval remains opt-in and separate:

```bash
RUN_AGENT_ROUTER_EVAL=1 docker exec al_backend uv run pytest -q tests/services/test_agent_routing_eval.py
```

The next step can be an opt-in live golden runner, for example
`RUN_AGENT_GOLDEN_EVAL=1`, that executes selected cases through the configured
production router/API and scores behavior against the same fixture.
