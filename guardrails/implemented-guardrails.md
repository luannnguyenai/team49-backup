# Implemented Guardrails

Date: 2026-05-08

## Scope

These are the guardrails currently implemented in the codebase for user-facing AI chat surfaces:

- `assistant`
- `tutor`

This document describes what is actually installed now, not the full target design from the plan.

## Summary

The current implementation adds a shared backend PII guardrail layer and wires it into the main chat boundaries.

Implemented now:

- shared backend guardrail core
- deterministic redaction placeholders
- blocking policy for selected high-risk identifiers
- assistant input sanitization
- assistant output sanitization
- assistant title-generation sanitization
- tutor input sanitization
- tutor streamed output sanitization
- tutor QA log sanitization
- tutor QA persistence sanitization

Not fully implemented yet:

- dedicated frontend advisory UX for guardrail metadata
- full observability hardening for every trace and log sink
- direct `guardrails-ai` package integration in the active dependency graph

## Backend Guardrail Core

Implemented in:

- `src/services/guardrails/__init__.py`
- `src/services/guardrails/types.py`
- `src/services/guardrails/pii_policy.py`
- `src/services/guardrails/guardrails_adapter.py`
- `src/services/guardrails/pii_guardrail.py`

### Guardrail service

Primary service:

- `PIIGuardrailService`

Supported entrypoints:

- `sanitize_input(text)`
- `sanitize_output(text)`

### Current failure behavior

- input scan failure: fail open
  - request is allowed through unchanged
  - result includes `error_code`
- output scan failure: fail closed
  - output is blocked
  - sanitized output becomes empty
  - result includes `block_reason` and `error_code`

## Current PII Policy

### Redacted entities

- `EMAIL_ADDRESS` -> `[REDACTED_EMAIL]`
- `PHONE_NUMBER` -> `[REDACTED_PHONE]`
- `PERSON` -> `[REDACTED_PERSON]`
- `LOCATION` -> `[REDACTED_LOCATION]`

### Blocked entities

- `US_SSN` -> `pii_blocked_us_ssn`
- `CREDIT_CARD` -> `pii_blocked_credit_card`
- `US_BANK_NUMBER` -> `pii_blocked_bank_number`
- `US_PASSPORT` -> `pii_blocked_passport`

### Notes

- placeholders are deterministic and stable for tests
- redaction is normalized in project code, not delegated directly to a third-party response format

## Assistant Guardrails

Implemented in:

- `src/services/agent_graph_service.py`
- `src/services/agent_response_composer.py`
- `src/schemas/agent.py`
- `src/routers/agent.py`

### Input guardrails

Assistant user messages are sanitized before AI graph execution.

Implemented behavior:

- raw `request.message` is sanitized before graph invocation
- sanitized text is what enters downstream assistant logic
- if input policy returns `should_block=True`, assistant returns a safe blocked response

### Output guardrails

Assistant response markdown is sanitized before final response return.

Implemented behavior:

- `response.answer.markdown` is sanitized before return to the client
- response metadata records whether input or output redaction occurred

### Response metadata

Assistant response schema now supports:

- `guardrail.inputRedacted`
- `guardrail.outputRedacted`
- `guardrail.blocked`
- `guardrail.blockReason`
- `guardrail.errorCode`

Defined in:

- `src/schemas/agent.py`

### Title generation guardrail

Conversation title generation now uses sanitized content.

Implemented behavior:

- user message is sanitized before title generation
- assistant markdown is sanitized before title generation

This prevents title-generation prompts from receiving raw PII content.

## Tutor Guardrails

Implemented in:

- `src/services/llm_service.py`

### Input guardrails

Tutor question text is sanitized at the start of the tutor streaming flow.

Implemented behavior:

- raw `user_question` is sanitized before use
- sanitized question is used in:
  - routing
  - prompt construction
  - Langfuse span input
  - QA logging
  - QA persistence

If tutor input policy returns `should_block=True`:

- tutor returns a streamed blocked event immediately
- blocked event includes a guardrail payload

### Output guardrails

Tutor output is sanitized before it is streamed to the client.

Implemented behavior:

- SIMPLE path direct answers are sanitized before stream
- COMPLEX path streamed chunks are sanitized before emit
- fallback AI messages are sanitized before emit

### Persistence and logging guardrails

Tutor persistence and logging now use sanitized text.

Implemented behavior:

- `_log_qa(...)` receives sanitized question and answer
- `_save_qa_history(...)` receives sanitized question and answer

This reduces raw PII exposure in:

- `logs/qa_history.log`
- `logs/qa_history.jsonl`
- `QAHistory`

### Runtime observation

Live runtime testing showed:

- tutor did not echo back email or phone when prompted to bypass redaction
- tutor did not confirm SSN content when prompted to repeat it

Observed nuance:

- the tutor runtime currently behaves safely for tested SSN prompts, but does not always short-circuit into an immediate blocked event in the same way the backend core policy model suggests

This should be treated as a remaining behavior gap to tighten later.

## Dependency Status

### What is implemented now

The current backend adapter is active and working without requiring `guardrails-ai` to be installed in the live dependency graph.

### Why direct `guardrails-ai` is not enabled yet

A real dependency conflict was confirmed:

- `guardrails-ai==0.6.7` requires `openai<2.0.0`
- this repository currently uses `openai>=2.31.0`

Result:

- `guardrails-ai` was not added as an active project dependency
- the internal adapter remains the stable integration boundary
- direct package integration should happen only after a compatible version is verified

## Tests Added

### Guardrail core tests

Implemented in:

- `tests/services/test_pii_guardrail.py`

Covered behaviors:

- no-PII pass-through
- email redaction
- phone redaction
- block behavior for SSN
- adapter failure fallback
- bypass-style prompt still redacts PII

### Assistant integration-oriented tests

Implemented in:

- `tests/services/test_agent_response_composer.py`
- `tests/services/test_agent_graph_service.py`
- `tests/test_agent_router_guardrails.py`

Covered behaviors:

- response metadata propagation
- assistant input/output sanitization in chat flow
- title-generation sanitization

### Tutor integration-oriented tests

Implemented in:

- `tests/services/test_llm_service_guardrails.py`

Covered behaviors:

- tutor SIMPLE route output redaction
- tutor logging sanitization
- tutor persistence sanitization

## Verification Run

Verified with:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_agent_router_guardrails.py tests/services/test_pii_guardrail.py tests/services/test_agent_response_composer.py tests/services/test_agent_graph_service.py tests/services/test_llm_service_guardrails.py -q
```

Observed result at implementation time:

- `75 passed`

App import smoke test also passed:

```powershell
.\.venv\Scripts\python.exe -c "import src.api.app; print('app import ok')"
```

## Remaining Gaps

- frontend does not yet present dedicated guardrail notices to users
- tutor block behavior should be tightened so high-risk entities short-circuit more consistently at runtime
- full trace and observability sinks still need a dedicated audit pass
- direct `guardrails-ai` package integration remains pending dependency compatibility
