# Update Agent Branch Changes

Date: 2026-05-15

Branch: `update-agent`

Comparison scope: `main..update-agent`

This document describes the functional and technical changes introduced on this
branch. The branch focuses on making the AI Agent more context-aware inside the
learning experience, especially for current lesson questions, current-path
planning questions, and learner-specific quiz/progress analysis.

## Executive Summary

This branch changes the Agent from a mostly content-search assistant into a
more context-aware Agentic RAG flow. It now receives lightweight route context
from `/learn`, can choose between course-content retrieval and user-learning
context retrieval, and can answer learner-specific questions such as:

- "What am I currently learning?"
- "What should I study next?"
- "How long will this path take at my weekly cadence?"
- "Does this current unit have a quiz?"
- "Based on my quiz history, what should I improve?"
- "Summarize the current lecture/video I am watching."

The implementation intentionally avoids hard-coded user-query handling. Instead,
it extends the data contract and routing/tool prompts so the model can adapt to
semantic intent while staying constrained by backend-owned tools and allowlisted
data.

## Branch Delta

Compared with `main`, the branch changes 25 files:

- `frontend/components/learn/LearningUnitShell.tsx`
- `frontend/features/agent/components/AgentChatPage.tsx`
- `frontend/features/agent/route-context.ts`
- `frontend/tests/routes/agent/page.test.tsx`
- `frontend/tests/routes/learning/unit.test.tsx`
- `frontend/types/index.ts`
- `src/prompts/agent/agentic_rag.yaml`
- `src/repositories/canonical_content_repo.py`
- `src/routers/agent.py`
- `src/schemas/course.py`
- `src/services/agent_graph_service.py`
- `src/services/agent_structured_router.py`
- `src/services/agent_tool_nodes.py`
- `src/services/agent_user_learning_context_service.py`
- `src/services/agentic_rag_contracts.py`
- `src/services/agentic_rag_pipeline.py`
- `src/services/agentic_rag_tools.py`
- `src/services/guardrail_router.py`
- `src/services/learning_unit_service.py`
- `tests/services/test_agent_graph_service.py`
- `tests/services/test_agent_structured_router.py`
- `tests/services/test_agent_tool_nodes_prerequisite_path.py`
- `tests/services/test_agent_user_learning_context_service.py`
- `tests/services/test_agentic_rag_pipeline.py`
- `tests/services/test_guardrail_router.py`

High-level size:

- 2865 insertions
- 100 deletions

## User-Facing Behavior Changes

### Agent Understands Current Learning Context

When the learner is on `/learn`, the frontend stores a small route context
snapshot and the Agent page sends it with chat requests. The Agent can now infer
that "this video", "this lesson", "the current unit", or "path này" refers to
the learner's active learning context rather than asking broad clarification
questions.

Examples now supported:

- "tóm tắt video mình vừa xem"
- "video này có quiz không?"
- "xong đoạn này thì nên học gì tiếp?"
- "mình đang học path nào vậy?"
- "mình học 10 phút mỗi tuần thì bao lâu master path này?"

### Agent Can Analyze Existing Quiz History

The Agent can answer read-only diagnostic questions based on prior quiz attempts.
The backend computes aggregate learning analytics and passes only safe,
allowlisted fields to the LLM.

Examples now supported:

- "dựa trên lịch sử làm quiz của tôi thì tôi cần cải thiện những gì?"
- "nhìn các quiz gần đây, tôi hay sai phần nào nhất?"
- "trong những lần làm quiz trước, chủ đề nào tôi bị sai nhiều nhất?"
- "từ các câu quiz đã làm sai thì tôi cần cải thiện phần nào?"
- "mình vừa làm vài quiz, nhìn lịch sử thì nên ôn gì trước?"

The Agent should analyze existing attempts, not propose a new assessment, unless
the learner explicitly asks to take/start/generate a quiz.

### Agent Can Summarize Lecture-Level Context

The Agent can retrieve lecture-level context. If a lecture summary is not
available, it can fall back to ordered unit summaries from the same lecture so
the responder can synthesize a lecture summary without guessing.

## Frontend Changes

### Route Context Persistence

File: `frontend/features/agent/route-context.ts`

This new helper writes and reads a sanitized route context snapshot in
`localStorage`.

Stored fields:

- `route`
- `courseSlug`
- `unitSlug`
- `canonicalUnitId`
- `playerTimestampSec`
- `savedAt`

Important details:

- The snapshot TTL is 2 hours.
- String fields are trimmed and dropped if empty.
- Timestamp values must be finite non-negative numbers.
- Invalid JSON or expired snapshots are ignored.

Purpose:

- Preserve the last known learning context when the learner navigates from
  `/learn` to `/agent`.
- Allow the Agent to answer current-lesson/current-path references without
  requiring the learner to restate the course or unit.

### Learning Unit Shell Writes Context

File: `frontend/components/learn/LearningUnitShell.tsx`

The learning unit page now writes the active route context as the learner views
a unit. This includes course/unit slugs, canonical unit id, and player timestamp
when available.

### Agent Page Sends Context

File: `frontend/features/agent/components/AgentChatPage.tsx`

The Agent chat request now includes route context read from local storage. This
keeps the backend contract explicit: the model does not infer current page state
by itself; the frontend sends a normalized snapshot.

### Quiz Metadata in Frontend Types

File: `frontend/types/index.ts`

Learning unit types now include quiz availability metadata. This lets frontend
and Agent route context consistently expose whether a unit has quiz items.

## Backend API and Schema Changes

### Agent Router Wiring

File: `src/routers/agent.py`

The Agent route now injects `AgentUserLearningContextService` into
`AgentGraphService`, so Agentic RAG tools can read authenticated learner context.

Key constraint:

- The LLM never supplies a user id.
- The backend uses the authenticated request user.
- The service is read-only and scoped to allowed/current path course ids.

### Course and Learning Unit Quiz Metadata

Files:

- `src/schemas/course.py`
- `src/services/learning_unit_service.py`

Learning unit responses now carry whether quiz items exist for the unit. This is
used by current-unit answers such as "video này có quiz không?".

## Agentic RAG Architecture Changes

### Graph Routing

File: `src/services/agent_graph_service.py`

The graph now has a dedicated `agentic_rag` node for production routers that
support the DeepTutor-style stage contract:

1. `rag_think`
2. `rag_act`
3. `rag_observe`
4. `rag_respond`

The old RAG nodes remain as compatibility path for tests/bootstrap routers that
do not support the full stage contract.

The Agent chooses the Agentic RAG path when:

- policy allows the request;
- the effective intent is RAG-capable;
- slots are not ambiguous;
- the query has a raw topic, canonical unit id, or is a user-context intent.

User-context intents include progress/weak-area/next-step style questions. This
is what enables ReAct-style handling for personalized questions instead of a
plain LLM response.

### Streaming Path

The streaming path now routes through the same Agentic RAG flow when supported.
It emits status updates, then converts the final `ToolResult` into the streamed
Agent response.

This reduces drift between non-streaming and streaming behavior.

### Effective RAG Intent

The graph differentiates between the original route intent and the effective RAG
intent. For example, a user can ask a personalized progress question that does
not have a course topic, but still needs Agentic RAG because the relevant
evidence is user-learning context.

## RAG Tools

File: `src/services/agentic_rag_tools.py`

The tool registry now exposes these tools to the acting stage:

### `search_current_path_units`

Searches title-level units in the learner's current path. Used for content
discovery, concept lookup, and navigation.

### `get_unit_summary`

Retrieves normalized summary evidence for a selected learning unit.

### `get_lecture_context`

Retrieves lecture-level context. This is used when the learner asks for a full
lecture summary or surrounding lecture context.

Inputs:

- `canonical_unit_id`
- `query`

### `get_user_learning_context`

Retrieves read-only learning state for the authenticated learner.

Input:

- `context_kind`

Allowed context kinds:

- `current_unit_state`
- `progress_summary`
- `weak_areas`
- `study_time_estimate`
- `planner_reasoning_context`
- `quiz_history_analysis`
- `general`

Security rule:

- The backend injects the authenticated user id.
- The tool schema does not allow passing arbitrary user ids.
- The LLM cannot run arbitrary SQL.

### Clarification and Scope Expansion Tools

The registry still includes:

- `ask_clarification`
- `offer_scope_expansion`
- `search_allowed_other_paths`

Expanded search remains gated by explicit approval.

## User Learning Context Service

File: `src/services/agent_user_learning_context_service.py`

This new service is the main backend addition in the branch.

Purpose:

- Provide a safe, read-only snapshot of learner state to Agentic RAG.
- Scope database reads to the authenticated user and allowed/current path.
- Expose only aggregate or non-sensitive learning fields.
- Avoid letting the LLM query arbitrary tables or personal data.

### Snapshot Fields

The snapshot includes:

- `context_kind`
- `available_fields`
- `current_learning_state`
- `progress_summary`
- `path_workload_summary`
- `path_position`
- `recent_progress`
- `weak_knowledge_points`
- `recent_assessments`
- `quiz_history_analysis`
- `recent_placement_results`
- `waived_units`

### Current Learning State

Reads from planner session state and route context to expose:

- current unit
- current stage
- video progress seconds
- watch percent
- last activity

The route context can override the stale planner current unit when the learner
is actively viewing a unit in `/learn`.

### Path Workload Summary

Computes:

- total units
- completed/skipped units
- remaining units
- total estimated minutes
- remaining estimated minutes/hours
- missing estimate count

This supports questions like:

- "If I study 10 minutes per week, how long will this path take?"

### Path Position

Computes:

- current index in path
- previous unit
- current unit
- next unit
- next unfinished unit

This supports questions like:

- "What should I study next?"
- "After this video, where do I go?"

### Weak Knowledge Points

Reads learner mastery by KP and returns the weakest observed concepts, ordered
by mastery and evidence count.

### Quiz History Analysis

This is the key personalization feature added in the branch.

Data sources:

- `Interaction`
- `Session`
- `QuestionBankItem`
- `ConceptKP`
- `CanonicalUnit`

Window:

- last 300 interactions
- last 12 sessions

Returned fields:

- `total_answered`
- `correct_count`
- `accuracy_percent`
- `weakest_quiz_kps`
- `weakest_quiz_units`
- `recent_session_scores`
- `trend`
- `data_window`

Ranking behavior:

- Buckets are grouped by KP and by unit.
- Only buckets with at least one incorrect answer are returned.
- Ranking favors higher incorrect count, then lower accuracy.

Privacy and leakage controls:

- The payload does not expose question text.
- The payload does not expose answer keys.
- The payload does not expose selected answers.
- The payload does not expose arbitrary user profile fields.

This lets the Agent answer "what should I improve?" without revealing the quiz
bank or answer content.

### Trend Calculation

Recent session scores are split into recent and previous windows. The service
returns:

- `improving`
- `declining`
- `stable`
- `insufficient_data`

The threshold is 5 percentage points.

## Lecture Context Retrieval

File: `src/repositories/canonical_content_repo.py`

The canonical content repository now supports lecture-level retrieval. This is
used by `get_lecture_context`.

Behavior:

- Resolve context from a canonical unit id when available.
- Fetch surrounding units in the same lecture.
- Use ordered unit summaries if lecture-level summary is missing.

This improves current-lecture questions like:

- "tóm tắt lecture này"
- "video mình vừa xem nói gì?"
- "đoạn này đang nói supervised learning kiểu gì?"

## Prompt and Router Changes

File: `src/prompts/agent/agentic_rag.yaml`

The prompt changes are contract-level guidance, not exact message hard-coding.

### Route Stage

The route prompt now explicitly treats these as context-grounded requests:

- current lesson references
- current path references
- time/cadence estimates
- quiz history diagnostics
- prior quiz mistakes
- progress and weak-area summaries

Important distinction:

- Existing quiz history analysis routes to `summarize_progress`.
- Starting/generating a new quiz routes to `assess_knowledge`.

This fixes the failure mode where "tôi hay sai phần nào trong quiz?" was
mistaken for a request to start a new assessment.

### Thinking Stage

The thinking prompt now tells the model to plan for the learner-context tool
when the request needs:

- progress
- weak areas
- quiz history
- error-pattern analysis
- current learning state
- study-time estimates
- planner reasoning

### Acting Stage

The acting prompt exposes:

- `get_lecture_context`
- `get_user_learning_context`

The model is instructed to select a single tool call and to derive arguments
only from user message, thread context, route context, slots, or observations.

### Responding Stage

The responding prompt now includes specific instructions for:

- using `path_workload_summary` for time estimates;
- using `path_position.next_unfinished_unit` for next-step questions;
- using current-unit `has_quiz_items` for quiz availability;
- using `quiz_history_analysis` for quiz-history improvement questions;
- not revealing question text or answer keys;
- not ending with unsolicited follow-up offers.

## Agentic RAG Contracts and Pipeline

Files:

- `src/services/agentic_rag_contracts.py`
- `src/services/agentic_rag_pipeline.py`

### Structured Final Answer Contract

The final response schema clarifies that `answer_markdown` must be the final
answer only. It should not include hidden thoughts, tool orchestration, or
optional follow-up offers.

### Tool Result Preservation

The pipeline now treats database/tool observations as authoritative for
citations, actions, trace, and non-evidence tool status.

Why this matters:

- The observer model can judge evidence quality.
- The observer model must not mutate tool-returned result payloads.
- Learner-context tools often have no citations because they are not course
  document retrieval. That should not automatically become `no_source`.

This fixes cases where valid learner-context answers were downgraded to
`no_source`.

### Hidden Stage Text Cleanup

The pipeline strips accidental "Hidden thought" or "Final:" prefixes from final
answers. This is a safety cleanup for structured LLM output, not a query-specific
answer rewrite.

## Tool Nodes

File: `src/services/agent_tool_nodes.py`

The tool node layer now exposes:

- `user_learning_context`
- `lecture_context`

### `user_learning_context`

Calls `AgentUserLearningContextService.snapshot()` with:

- authenticated `user_id`
- allowed course ids
- current path course ids
- route context
- requested context kind

It returns a `ToolResult` with learner context in metadata. This metadata is used
by the Agentic RAG responder.

### `lecture_context`

Calls canonical content repository lecture-context methods and returns
course-content evidence for lecture summary/explanation workflows.

## Guardrail Router Change

File: `src/services/guardrail_router.py`

The guardrail parser now normalizes model output aliases.

Handled examples:

- `safety_label: ON_TOPIC` is recovered as `SAFE` when the action is not
  `SAFETY_REFUSE`.
- `attack_type: aux` is normalized to `none`.

Reason:

During browser testing, the guardrail fallback model returned a valid-looking
JSON object with schema drift:

```json
{
  "safety_label": "ON_TOPIC",
  "topic_label": "ON_TOPIC",
  "action": "ALLOW_LESSON_ANSWER",
  "attack_type": "aux"
}
```

Before this branch, that caused `GUARDRAIL_ROUTER_UNAVAILABLE` and blocked
otherwise valid Agent responses.

This fix is generic schema normalization, not a special case for any specific
user query.

## Data Safety Model

The learner-context design uses several constraints:

1. The LLM cannot pass a user id.
2. The authenticated backend user id scopes all learner-context queries.
3. Course scope uses allowed/current path course ids.
4. The service returns allowlisted fields only.
5. Quiz history is aggregate only.
6. Raw question text and answer keys are not exposed.
7. Expanded path search remains gated by explicit approval.

## Main Runtime Flows

### Current Lesson Summary

1. Learner opens `/learn/:course/:unit`.
2. `LearningUnitShell` writes route context.
3. Learner opens Agent and asks "tóm tắt video mình vừa xem".
4. `AgentChatPage` includes route context in chat request.
5. Router resolves deictic phrase to current lesson.
6. Agentic RAG acting stage selects `get_lecture_context`.
7. Repository fetches lecture/unit summaries.
8. Responder answers from validated lecture context.

### Quiz History Improvement

1. Learner asks "dựa trên lịch sử làm quiz của tôi thì tôi cần cải thiện gì?"
2. Router classifies as `summarize_progress`, not `assess_knowledge`.
3. Agentic RAG acting stage selects `get_user_learning_context`.
4. Tool node calls `AgentUserLearningContextService.snapshot()`.
5. Service computes `quiz_history_analysis`.
6. Responder uses weakest KPs/units, recent scores, and trend.
7. Answer states data-window limitations naturally.

### Next Step Recommendation

1. Learner asks "xong đoạn này thì học gì tiếp?"
2. Route context identifies current unit.
3. User context snapshot includes `path_position`.
4. Responder uses `next_unfinished_unit` first, then `next_unit` as fallback.
5. The Agent avoids inventing a next lesson when path order is unavailable.

### Time-to-Mastery Estimate

1. Learner asks with cadence, e.g. "10 phút mỗi tuần".
2. Router keeps `summarize_progress`.
3. User context snapshot includes `path_workload_summary`.
4. Responder converts cadence to minutes/week.
5. Responder divides `remaining_estimated_minutes` by cadence and states that
   it estimates content time unless mastery evidence exists.

## Tests Added or Updated

### Frontend Route Context

Files:

- `frontend/tests/routes/agent/page.test.tsx`
- `frontend/tests/routes/learning/unit.test.tsx`

Coverage:

- learning unit shell writes route context;
- agent page includes route context in requests;
- context survives navigation between `/learn` and Agent;
- context supports current unit and quiz metadata behavior.

### User Learning Context Service

File: `tests/services/test_agent_user_learning_context_service.py`

Coverage:

- path position payload exposes previous/current/next/next-unfinished units;
- quiz history payload ranks error buckets;
- quiz history payload does not leak question text or answer keys.

### Structured Router

File: `tests/services/test_agent_structured_router.py`

Coverage:

- route context is first-class grounding;
- current course/path identity is not confused with path switching;
- current-path references are resolved as current path;
- time-estimate requests route to progress summary;
- quiz-history error analysis routes to progress summary;
- prior quiz mistakes do not trigger new assessment flow;
- prompt-injection guardrails remain in place.

### Agentic RAG Pipeline

File: `tests/services/test_agentic_rag_pipeline.py`

Coverage:

- tool registry exposes policy metadata;
- learner-context tool schema includes `quiz_history_analysis`;
- lecture context tool is available;
- observer cannot replace authoritative tool results;
- learner-context evidence status is preserved;
- structured stream response is used;
- hidden thought / citation-marker cleanup works;
- prompt disallows unsolicited follow-up offers.

### Agent Tool Nodes

File: `tests/services/test_agent_tool_nodes_prerequisite_path.py`

Coverage:

- agent tool nodes correctly handle context behavior around prerequisite/path
  flows and newer tool contracts.

### Agent Graph

File: `tests/services/test_agent_graph_service.py`

Coverage:

- production router path uses Agentic RAG when supported;
- user-context intents route through RAG;
- current route context affects RAG behavior;
- stream path preserves Agentic RAG behavior;
- pending clarifications and action flows remain compatible.

### Guardrail Router

File: `tests/services/test_guardrail_router.py`

Coverage:

- fallback schema aliases are normalized;
- `ON_TOPIC` in `safety_label` no longer crashes the guardrail parser;
- `aux` attack type normalizes to `none`;
- existing fallback/cooldown behavior remains covered.

## Browser-Use Verification Captured During Implementation

The branch was tested against the running local app with the demo account:

- `Demo.Full@vinuni.edu.vn`

Representative query results:

### Quiz History

Query:

- `dựa trên lịch sử làm quiz của tôi thì tôi cần cải thiện những gì?`

Observed:

- answered from quiz history;
- identified weak topics;
- included trend;
- no new-assessment action.

Latency:

- about 15.0s

### Quiz Error Pattern

Query:

- `nhìn các quiz gần đây, tôi hay sai phần nào nhất?`

Initial issue:

- routed as assessment proposal.

Fix:

- strengthened intent contract so prior quiz mistakes route to
  `summarize_progress`.

Observed after fix:

- answered from quiz history;
- no assessment action.

Latency:

- about 20.8s

### Prior Quiz Missed Topics

Query:

- `trong những lần làm quiz trước, chủ đề nào tôi bị sai nhiều nhất?`

Observed after final fix:

- confidence `partial`;
- no fallback;
- answered from available quiz-history window.

Latency:

- about 18.8s

### Review Recommendation

Query:

- `mình vừa làm vài quiz, nhìn lịch sử thì nên ôn gì trước?`

Observed:

- ranked review areas from quiz history;
- no unsolicited trailing offer.

Latency:

- about 16.7s

## Verification Commands Used During Implementation

Backend targeted suite:

```bash
uv run pytest tests/services/test_agent_user_learning_context_service.py tests/services/test_guardrail_router.py tests/services/test_agentic_rag_pipeline.py tests/services/test_agent_structured_router.py tests/services/test_agent_graph_service.py tests/services/test_agent_tool_nodes_prerequisite_path.py -q
```

Observed result during implementation:

- `178 passed`

Frontend targeted tests:

```bash
npm test -- tests/routes/agent/page.test.tsx tests/routes/learning/unit.test.tsx
```

Observed result during implementation:

- `61 passed`

Type check:

```bash
npm run type-check
```

Observed before the later main merge:

- failed because `tests/routes/admin/logs.test.tsx` imported missing
  `@/app/admin/logs/page`.

Note:

- The current branch head includes a later merge from `main` that adds
  `frontend/app/admin/logs/page.tsx`. If documenting final merge readiness, rerun
  type-check from the latest head.

## Known Limitations

### Latency

The Agentic RAG path is higher quality but slower than a direct response. Browser
tests commonly observed roughly 15-21 seconds for personalized quiz-history
queries. The flow performs multiple LLM stages plus backend tool reads.

Possible follow-ups:

- cache learner-context snapshots per request/session;
- reduce observing/responding calls for non-evidence learner-context requests;
- add fast-path structured responders for pure aggregate summaries.

### Quiz History Window

Quiz history currently uses:

- 300 latest interactions;
- 12 latest sessions.

This is intentional to keep context bounded. The Agent should state data-window
limits when relevant.

### Aggregation Granularity

The service ranks by primary KP and unit. It does not yet aggregate by:

- prerequisite chain;
- concept hierarchy;
- spaced repetition schedule;
- topic clusters beyond primary KP.

### Evidence Citations

Learner-context answers often have no course-content citations because the
source is user progress data rather than document retrieval. The pipeline now
preserves `partial` instead of incorrectly downgrading these answers to
`no_source`.

### Prompt Compliance

The responder prompt now instructs the model not to add unsolicited follow-up
offers. This is a contract-level fix. It does not use phrase-stripping or
hard-coded removal of specific Vietnamese/English sentences.

## Operational Notes

### No Database Migration

The branch reads existing tables:

- `learning_progress_records`
- `learning_units`
- `course_sections`
- `courses`
- `planner_session_state`
- `learner_mastery_kp`
- `sessions`
- `interactions`
- `question_bank`
- `concepts_kp`
- `units`
- placement and waived-unit tables

No schema migration is introduced by this branch.

### Permissions

The user-learning context tool should remain backend-scoped. Do not add tool
arguments that allow the model to pass:

- user id;
- arbitrary SQL;
- table names;
- raw filter expressions;
- personal profile fields.

### Privacy

Do not expand quiz-history payloads to include:

- question text;
- choices;
- answer index;
- selected answer;
- explanation text;
- raw per-question content.

If deeper diagnostics are needed, add aggregate fields or backend-authored
recommendations rather than exposing raw question bank content to the LLM.

## Commit Map

Functional commits in this branch:

- `c4a2e85c` Persist learning route context in unit shell
- `d5fe8af5` Pass route context from agent page
- `8a5f5003` Add agent route context helper
- `a98bc02e` Test agent route context behavior
- `6212fa4d` Test learning route context persistence
- `7142fde6` Expose unit quiz metadata in frontend types
- `69432fe9` Improve agentic RAG quiz history guidance
- `c6f33cf1` Add lecture context retrieval support
- `0af2eeab` Wire user learning context into agent router
- `8501b91f` Expose quiz metadata on course schema
- `5377dadd` Route progress requests through agentic RAG
- `8bf49653` Refine structured agent routing prompts
- `b864b25b` Add learner context and lecture tools
- `8cdc5853` Tighten agentic RAG response contracts
- `115573e9` Preserve learner context evidence status
- `4c0d96a0` Register learner and lecture RAG tools
- `8962a2ae` Add user learning context snapshots
- `48e82cc8` Normalize guardrail router aliases
- `62066b8a` Include quiz metadata in learning units
- `01a77988` Test agent graph learner context flows
- `78c989ec` Test structured routing improvements
- `ad58c876` Test agent tool node context behavior
- `d73c720e` Test user learning context snapshots
- `dc891020` Test agentic RAG context contracts
- `72993e3b` Test guardrail alias normalization

Merge commit:

- `41935def` Merge branch `main` into `update-agent`

## Recommended Review Checklist

Before merging, review:

- `src/services/agent_user_learning_context_service.py`
  - Ensure no sensitive fields are returned.
  - Ensure course/user scoping is correct.
- `src/prompts/agent/agentic_rag.yaml`
  - Ensure routing semantics are general, not query-specific.
- `src/services/agentic_rag_pipeline.py`
  - Ensure evidence-status preservation is appropriate for non-citation tools.
- `src/services/guardrail_router.py`
  - Ensure alias normalization is conservative enough.
- `frontend/features/agent/route-context.ts`
  - Ensure TTL and localStorage behavior match product expectations.

Recommended final verification:

```bash
uv run pytest tests/services/test_agent_user_learning_context_service.py tests/services/test_guardrail_router.py tests/services/test_agentic_rag_pipeline.py tests/services/test_agent_structured_router.py tests/services/test_agent_graph_service.py tests/services/test_agent_tool_nodes_prerequisite_path.py -q
```

```bash
cd frontend
npm test -- tests/routes/agent/page.test.tsx tests/routes/learning/unit.test.tsx
npm run type-check
```

