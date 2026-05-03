# DeepTutor-Style Agentic RAG Design

## Purpose

Refactor `/agent` RAG behavior to follow DeepTutor's proven agentic chat shape:
`thinking -> acting -> observing -> responding`.

The goal is a more natural tutor experience where the model uses visible thread
context, selects tools through structured tool calls, retrieves grounded course
evidence, and answers without hallucinating. Planner Mode, replan, and repath
remain separate product work.

## Non-Negotiable Rules

- No production hard-coded domain keyword maps, synonym maps, topic locks, or
  canned topic responses without explicit approval.
- Concrete topic names in tests or golden eval fixtures are allowed only as
  review cases; they must not become runtime routing logic.
- LLM may propose search queries, but application tools enforce scope, policy,
  citations, and evidence sufficiency.
- The assistant answers naturally in the user's language or mixed-language
  style. UI copy can be English; chat output must not be forced to English.
- Hidden thinking, tool orchestration, metadata keys, and prompts are never
  shown to the user.

## Architecture

Add a focused Agentic RAG pipeline inspired by DeepTutor's `AgenticChatPipeline`,
adapted to this codebase:

```text
AgentGraphService
  -> route/policy/canonicalization
  -> AgenticRAGPipeline
       -> thinking
       -> acting
       -> execute_tools
       -> observing
       -> responding
  -> compose AgentChatResponse
```

The pipeline is not a new retrieval engine. It wraps existing course/path/unit
services and lets the model decide which allowed RAG tool to use.

## Pipeline Stages

### Thinking

The model receives:

- current user message
- visible recent thread messages
- route context
- current path scope
- pending clarification state, if present
- available tool descriptions

It produces an internal structured memo:

- user goal
- active topic, if any
- missing information
- evidence need
- proposed tool plan

This output is internal only and is stored in transient state/trace, not rendered
as chat memory.

### Acting

The model chooses one or more allowed tool calls. For this PR, keep the action
set small and RAG-focused:

- `search_current_path_units(query)`
- `get_unit_summary(unit_id)`
- `ask_clarification(question)`
- `offer_scope_expansion(topic)`
- `search_allowed_other_paths(query)` after approval only

Tool call arguments must be grounded in the user message, visible thread
context, route context, or previous tool observations. The app rejects unsupported
tools and invalid scope transitions.

### Execute Tools

The app executes tool calls through adapters over existing services:

- current path search uses title-first unit retrieval
- expanded path search requires pending scope-expansion approval
- summary/detail tools return typed citations and actions
- clarification tools create pending clarification state when needed

Tool execution is deterministic and policy-controlled. It may return `grounded`,
`partial`, `too_many_results`, `scope_expansion_required`, or `no_source`.

### Observing

The model reads tool results and produces an internal evidence judgment:

- `grounded`: enough direct source evidence exists
- `partial`: source exists but does not fully answer the user's requested aspect
- `no_source`: no direct source exists
- `needs_clarification`: the entity or scope remains ambiguous

The app validates this judgment against citations. If citations are empty for a
grounded-required result, the final answer must be no-source or clarification.

### Responding

The model writes the final user-facing answer using only validated observations
and accepted citations. It should:

- answer directly when evidence is grounded
- say source limits naturally when evidence is partial
- ask a concise clarification when required
- preserve source citations/actions for UI rendering
- avoid trailing unvalidated "would you like..." suggestions after successful
  retrieval

## Tool Contract

The RAG pipeline uses local tool abstractions rather than generic free-form
function names:

```python
class AgenticRAGToolCall(BaseModel):
    tool: Literal[
        "search_current_path_units",
        "get_unit_summary",
        "ask_clarification",
        "offer_scope_expansion",
        "search_allowed_other_paths",
    ]
    arguments: dict[str, Any]
    rationale: str
```

```python
class AgenticRAGObservation(BaseModel):
    tool: str
    success: bool
    evidence_status: Literal[
        "grounded",
        "partial",
        "too_many_results",
        "scope_expansion_required",
        "no_source",
        "needs_clarification",
    ]
    result: ToolResult
```

## Memory Semantics

Only visible chat turns and compacted thread summary are passed into the model.
Internal thinking/observing output is not written back as user-visible memory.

Follow-up behavior must use thread context:

- "còn gì nữa không" after YOLO means YOLO follow-up
- "loss function đi" after YOLO means YOLO loss-function follow-up
- "thế còn CNN" after YOLO is a new CNN topic and must not reuse YOLO citation
- "thử lại" after a failed request retries the original visible failed request

## Hallucination Controls

- No citation means no grounded answer.
- Partial citation means source-limited answer, not invented external detail.
- Generic results cannot be treated as evidence for a specific active topic.
- Current-path search runs before expanded search unless the user explicitly
  requested another path or approved expansion.
- Too many results should create pending retrieval refinement or top-results
  approval, not dump a long list.

## Planner Mode Boundary

If the user asks to replan, repath, or start assessment, the RAG pipeline may
return a structured action to open Planner Mode later. It must not mutate planner
state from chat text.

## Testing

Use existing and new tests around:

- golden eval dataset invariants
- stage output schema
- tool selection without domain keyword maps
- current-path-first search
- scope expansion approval
- visible thread memory follow-ups
- evidence gap source-limited answers
- new topic does not reuse old citation
- no hidden thinking in final answer

## Rollout

This can ship behind the existing `/agent` route for RAG intents only. Non-RAG
action flows keep their current behavior until Planner Mode work begins.
