# Path Agent RAG Plan

Date: 2026-04-29
Status: Review draft
Scope: Path-level AI Agent for general course/path Q&A, unit search, assessment handoff, and replan handoff.

## 1. Executive Summary

The product should add a separate Path Agent instead of expanding the existing Lecture AI Tutor.

The existing Lecture AI Tutor should remain scoped to the current lecture/player so it can answer timestamp-grounded questions without drifting into unrelated course advice. The new Path Agent should handle broader questions across the selected learning path, such as "what should I learn next?", "where is receptive field taught?", "can I skip CNN?", "what part of DL is required for NLP?", and "test me on the units I probably know."

For V1, this does not require vector embeddings. The current canonical schema already has enough structured content to support high-quality hierarchical retrieval:

- `units`: unit title, lecture, course, summary, key points, content type, salience, transcript path, clip reference, quiz flags.
- `unit_kp_map` + `concepts_kp`: concept/KP labels, descriptions, structural roles, coverage.
- `question_bank`: assessment questions mapped to unit/KP.
- `learner_mastery_kp`: user mastery state.
- `placement_assessment_results`: placement decisions by unit.
- `planner_session_state` and learning path rows: current path/replan state.

Recommended V1 retrieval architecture:

```text
User message
-> AgentContextResolver
-> IntentRouter
-> UnitSearchService using BM25/full-text + structured boosts
-> UnitContextService expands top units with KP/transcript/timestamps
-> Agent response + optional action: open player, start assessment, request replan
```

Embedding can be added later as a hybrid fallback over unit-level search documents, not as the first retrieval layer.

## 2. Product Goals

### 2.1 Goals

- Let users ask broad questions about their current path or courses without leaving `/learn`.
- Let the Agent find the most relevant unit(s), not just answer from raw transcript text.
- Let the Agent explain why a unit is recommended, skipped, review-only, or needs assessment.
- Let the Agent start assessment for selected units when the user asks to verify knowledge.
- Let the Agent request replan only after evidence exists from assessment/player interactions.
- Keep every answer traceable to course, lecture, unit, KP, and optionally timestamp.

### 2.2 Non-goals for V1

- Do not replace the existing lecture-scoped AI Tutor.
- Do not use LLM-generated mastery as authoritative truth.
- Do not use vector embeddings as the primary retrieval path.
- Do not allow the Agent to write planner/mastery state directly without validated backend actions.
- Do not make the Agent browse arbitrary external web sources.
- Do not search full transcripts before narrowing to candidate units.

## 3. Design Principle

The core searchable object is the canonical learning unit.

The unit is the correct join point because it connects all major runtime systems:

| Capability | Unit connection |
| --- | --- |
| Player navigation | Unit maps to lecture and timestamp/clip data. |
| Planner | Learning path rows are unit-based. |
| Assessment | `question_bank.unit_id` maps questions to units. |
| Mastery | `unit_kp_map` maps units to KPs; KP mastery is user state. |
| RAG answer | Unit has summary, key points, transcript path, and evidence timestamps. |
| Runtime navigation | Unit must be joined to product `learning_units` and `courses` to produce `learn_href`. |

The Agent should not search "documents" in the abstract. It should search units first, then expand to transcript snippets or video evidence only when needed.

Important distinction:

- `units.unit_id` is the canonical retrieval key.
- The UI/player usually needs product runtime navigation fields: `learning_units.id`, `learning_units.slug`, `courses.slug`, `course_slug`, `unit_slug`, or a prebuilt `learn_href`.
- Every search result that can become a user action must include both canonical identity and runtime navigation identity. A result with only `canonical_unit_id` is not actionable enough.

## 4. User Question Simulation

These are expected user questions and the retrieval/action behavior the system should support.

The product direction is English-first, so acceptance examples and test cases should use English queries. Vietnamese can still be supported later through query translation, but it should not drive V1 retrieval acceptance.

| User question | Expected scope | Retrieval target | Action |
| --- | --- | --- | --- |
| "Where is receptive field taught?" | current path or current course | Units whose title/KP/key_points mention receptive field | Return lecture/unit + open player action |
| "How are CNNs different from Vision Transformers?" | current path/course | Top CNN units + ViT units | Answer with cited units; optionally suggest comparison quiz |
| "What should I learn next?" | current path | Learning path rows + mastery/progress | Return next unit/lecture and reason |
| "I already know CNNs. Can I skip them?" | current path | CNN units + quiz availability + mastery | Start assessment instead of trusting self-report |
| "Which DL parts are required for NLP?" | selected NLP path | Path requirement service over KP/prerequisite graph | Return required DL units and gap reason |
| "Where am I weak?" | current user | learner mastery + placement results + recent interactions | Summarize weak KPs/units and suggest assessment/review |
| "Open the stride section in the CNN lecture." | current path/course | Unit search -> runtime navigation -> timestamp | Navigate player to unit/timestamp |
| "Give me a quick quiz on backprop." | current path/course | Units/KPs for backprop + question bank | Start assessment/quiz |
| "Why does the planner want me to learn this unit?" | selected unit | path item reason_codes + prerequisite gaps + mastery | Explain planner rationale |
| "I came back after a month. What should I review?" | current user | stale mastery + review service + progress | Suggest review units |

## 5. Retrieval Architecture

### 5.1 AgentContextResolver

This service builds a structured context object before the LLM reasons about the query.

```ts
type AgentLearningContext = {
  userId: string;
  currentRoute: string;
  currentPathKey: "computer_vision" | "nlp" | null;
  selectedCourseIds: string[];
  currentCourseId?: string;
  currentLectureId?: string;
  currentUnitId?: string;
  currentPlayerTimestampSec?: number;
  activeLearningPathItemId?: string;
  recentAssessmentSessionId?: string;
};
```

Sources:

- Frontend route: `/learn`, `/courses/:courseSlug/learn/:unitSlug`, `/assessment/results`.
- User profile/onboarding: selected goal/path.
- Learning path state: generated path rows.
- Player state: current course, lecture, unit, timestamp.
- Backend: progress/mastery/session state.

### 5.2 IntentRouter

The Agent should classify the user message into one or more intents.

```ts
type AgentIntent =
  | "explain_concept"
  | "find_content"
  | "navigate_to_unit"
  | "ask_what_next"
  | "assess_knowledge"
  | "request_replan"
  | "explain_planner_decision"
  | "summarize_progress"
  | "general_course_question";
```

Examples:

- "Where is receptive field taught?" -> `find_content`
- "Explain receptive field." -> `explain_concept`
- "Test me on CNNs." -> `assess_knowledge`
- "Why do I need to learn this unit?" -> `explain_planner_decision`

### 5.3 QueryNormalizer

Search quality should not rely on raw user wording. Before UnitSearchService runs, normalize common domain aliases and abbreviations.

Examples:

| Raw phrase | Normalized terms |
| --- | --- |
| `ViT` | `vision transformer`, `transformer`, `image transformer` |
| `CNN` | `convnet`, `convolutional neural network`, `convolution` |
| `RF` in a CV query | `receptive field` |
| `word vectors` | `embeddings`, `word embeddings`, `dense vectors` |
| `RAG` | `retrieval augmented generation`, `retrieval`, `augmentation` |
| `backprop` | `backpropagation`, `gradient`, `chain rule` |

The normalizer must be traceable. Every expanded query should return the expansion in retrieval trace:

```json
{
  "raw_query": "Where is RF covered?",
  "normalized_query": "where is receptive field covered",
  "expansions": [
    {"from": "RF", "to": ["receptive field"], "reason": "cv_domain_alias"}
  ]
}
```

### 5.4 UnitSearchService

V1 should use database full-text/BM25-style search over a unit-centered search document.

Search document fields:

```text
unit_id
course_id
lecture_id
lecture_title
unit_name
summary
key_points_text
kp_names
kp_descriptions
content_type
salience_score
duration_min
has_quiz_items
is_worth_learning
section_flags
transcript_path
video_clip_ref
learning_unit_id
course_slug
unit_slug
learn_href
```

Initial implementation options:

- PostgreSQL `tsvector` + `ts_rank_cd`.
- Optional trigram similarity for title/unit fuzzy matching.
- Later: Typesense/OpenSearch/ParadeDB if BM25 quality or performance becomes a bottleneck.

Final score should combine text score with product-specific boosts:

```text
final_score =
  text_rank
  + scope_boost
  + current_path_boost
  + current_course_boost
  + salience_boost
  + quiz_available_boost
  + mastery_gap_boost
  + progress_next_boost
  - hidden_or_logistics_penalty
```

Recommended V1 boost rules:

| Signal | Boost |
| --- | --- |
| Unit in current selected path | Strong positive |
| Unit in current course/player | Strong positive |
| Unit has `has_quiz_items=true` for assessment intent | Positive |
| Unit has weak/stale mastery | Positive for review/replan intent |
| Unit is completed/mastered | Negative for "what next", positive for "review known topic" |
| `content_type=administrative` | Negative except logistics queries |
| `section_flags` includes intro/logistics/career | Negative for assessment |
| `salience_score=high` or critical KP | Positive |

### 5.5 PathRequirementService

Cross-path prerequisite and gap questions should not be answered by BM25 alone.

Questions such as "Which DL parts are required for NLP?" require graph/planner reasoning:

```text
selected path -> target course/KPs -> prerequisite_edges -> unit_kp_map -> user mastery -> required units/gaps
```

Inputs:

```ts
type PathRequirementRequest = {
  targetPathKey: "computer_vision" | "nlp";
  targetCourseIds: string[];
  sourceCourseIds?: string[];
  includeMastery?: boolean;
};
```

Output:

```ts
type PathRequirementResponse = {
  requiredUnits: Array<{
    canonical_unit_id: string;
    learning_unit_id?: string;
    course_id: string;
    course_slug?: string;
    unit_slug?: string;
    learn_href?: string;
    unit_name: string;
    required_kp_ids: string[];
    prerequisite_for: string[];
    mastery_lcb?: number;
    status: "required" | "already_mastered" | "needs_review" | "unassessed";
    reasons: string[];
  }>;
  trace: {
    target_path: string;
    prerequisite_depth: number;
    graph_edges_considered: number;
    ranking_version: string;
  };
};
```

This service should be used for path requirement, prerequisite gap, and "why do I need this DL unit for NLP/CV?" questions. UnitSearchService can still help explain a specific concept after the requirement service selects the relevant units.

### 5.6 RuntimeNavigationResolver

Search output must be actionable. RuntimeNavigationResolver joins canonical units to product navigation data.

Required output fields for any "open player" action:

```ts
type RuntimeNavigationTarget = {
  canonical_unit_id: string;
  learning_unit_id: string | null;
  course_id: string;
  course_slug: string | null;
  unit_slug: string | null;
  learn_href: string | null;
  lecture_id: string | null;
  start_sec?: number;
  end_sec?: number;
};
```

Resolution strategy:

1. Prefer existing learning path item fields if the unit is already in the current path: `learning_unit_id`, `course_slug`, `unit_slug`, `learn_href`.
2. Otherwise join canonical `units.unit_id` to product `learning_units.canonical_unit_id`, then join `courses`.
3. If no runtime row exists, return `learn_href=null` and mark the result as non-actionable; the Agent can still answer from canonical context but should not show an "Open player" button.

### 5.7 UnitContextService

After UnitSearchService returns top candidates, UnitContextService expands only those units.

Returned context:

```ts
type UnitContext = {
  unit_id: string;
  course_id: string;
  lecture_id: string | null;
  lecture_title: string | null;
  unit_name: string;
  summary: string | null;
  key_points: Array<{
    text: string;
    evidence_type?: string;
    timestamp_s?: number;
  }>;
  kp_links: Array<{
    kp_id: string;
    name: string;
    planner_role?: string;
    coverage_level?: string;
    coverage_weight?: number;
  }>;
  quiz_count: number;
  transcript_path: string | null;
  video_clip_ref: unknown | null;
};
```

### 5.8 TranscriptSnippetService

Transcript should be searched only after top units are selected.

Input:

```ts
{
  unit_id: string;
  query: string;
  max_snippets: number;
}
```

Output:

```ts
{
  unit_id: string;
  snippets: Array<{
    text: string;
    start_sec?: number;
    end_sec?: number;
    source: "transcript" | "key_point" | "summary";
  }>;
}
```

V1 can use timestamped `key_points` first. Transcript parsing can be added incrementally.

## 6. Sample Data For Reviewer

The following examples are from the local canonical DB and show why unit-centered retrieval is enough for V1.

### 6.1 Sample Unit: Receptive Field

Query:

```text
"receptive field in CNNs"
```

Candidate unit:

```text
course_id: CS231n
lecture_title: Lecture 5: Image Classification with CNNs
unit_id: local::lecture_5_image_classification_with_cnns::seg6
unit_name: Receptive fields, stride, and convolution formulas
content_type: core_theory
salience_score: medium
duration_min: 7
transcript_path: data/courses/CS231n/transcripts/cs231n-2025-lecture05-image-classification-with-cnns_transcript.txt
```

Summary:

```text
The instructor defines the effective receptive field as the region of the original image that can influence one downstream activation...
```

Key points:

```text
- The effective receptive field is the part of the original image that can influence one later activation. timestamp_s=3220
- With stacked stride-1 convolutions, receptive field size grows as depth increases.
- Stride skips filter placements, downsamples feature maps, and increases receptive-field growth rate.
- Convolution output size depends on input size, kernel size, padding, and stride.
```

Quiz availability:

```text
q1: What is an effective receptive field in a convolutional network?
    difficulty: easy
    primary_kp_id: kp_receptive_fields_and_strided_downsampling

q2: Why can stride help a convolutional network aggregate global image information faster?
    difficulty: medium
    primary_kp_id: kp_receptive_fields_and_strided_downsampling

q3: For an input volume 3x32x32, ten 5x5 filters, stride 1, and padding 2, what is the output shape?
    difficulty: medium
    primary_kp_id: kp_convolution_hyperparameters_and_tensor_shapes
```

Expected Agent response:

```text
Receptive field is covered in CS231n Lecture 5, unit "Receptive fields, stride, and convolution formulas".
The strongest timestamp evidence is around 3220s. I can open the player at that unit or start a short quiz on this topic.
```

### 6.2 Sample Unit: CNN Basics

Query:

```text
"what are CNNs and why do they matter"
```

Candidate:

```text
course_id: CS231n
lecture_title: Lecture 5: Image Classification with CNNs
unit_id: local::lecture_5_image_classification_with_cnns::seg3
unit_name: What convolutional networks are and why they matter
content_type: core_theory
salience_score: medium
duration_min: 8
quiz_count: 3
```

Key points:

```text
- A CNN usually interleaves convolution, pooling, and nonlinear layers, then uses fully connected layers for final prediction.
- AlexNet in 2012 scaled CNNs with more data and GPU compute and helped trigger the vision deep-learning boom.
- Transformers later outperformed CNNs on many vision tasks, but CNNs still matter for intuition, history, and hybrid systems.
```

Expected Agent behavior:

- If user asks explanation: answer from summary/key_points.
- If user asks where to learn: return the unit and player link.
- If user claims they know CNN: start placement/verification questions for linked units instead of marking mastery directly.

### 6.3 Sample NLP Unit: Word Vectors

Query:

```text
"word vectors and embeddings in NLP"
```

Candidate:

```text
course_id: CS224n
lecture_title: Lecture 1 - Intro and Word Vectors
unit_id: local::lecture01-wordvecs::seg3
unit_name: Meaning representations: denotation, one-hot vectors, and dense embeddings
content_type: core_theory
salience_score: medium
duration_min: 13
```

Key points:

```text
- Denotational semantics treats meaning as the pairing between a symbol and what it denotes.
- One-hot vectors are localist representations where words like hotel and motel are orthogonal.
- Distributional semantics says a word's meaning can be inferred from contexts.
- Word vectors are dense embeddings whose dot products capture similarity and semantic neighborhoods.
```

Expected Agent behavior:

- If user is on NLP path, this unit should rank high.
- If user is on CV path, it should rank lower unless the query explicitly asks NLP/embedding.

## 7. Retrieval Trace Examples

### 7.1 Find Content

User:

```text
"Where is receptive field covered?"
```

Trace:

```json
{
  "intent": "find_content",
  "scope": "current_path",
  "selected_path": "computer_vision",
  "candidate_courses": ["CS230", "CS231n"],
  "query_normalization": {
    "raw_query": "Where is receptive field covered?",
    "normalized_query": "where is receptive field covered",
    "expansions": []
  },
  "query_terms": ["receptive", "field"],
  "top_units": [
    {
      "unit_id": "local::lecture_5_image_classification_with_cnns::seg6",
      "learning_unit_id": "runtime-learning-unit-id-if-available",
      "course_id": "CS231n",
      "course_slug": "cs231n",
      "unit_slug": "lecture-05-seg6",
      "learn_href": "/courses/cs231n/learn/lecture-05-seg6#t=3220",
      "lecture_title": "Lecture 5: Image Classification with CNNs",
      "unit_name": "Receptive fields, stride, and convolution formulas",
      "reasons": ["unit_title_match", "key_point_match", "quiz_available", "current_path_match"]
    },
    {
      "unit_id": "local::lecture_1_introduction::seg3",
      "course_id": "CS231n",
      "lecture_title": "Lecture 1: Introduction",
      "unit_name": "Neuroscience and early computer vision foundations",
      "reasons": ["key_point_match: local receptive fields"]
    }
  ],
  "selected_action": "offer_open_player_at_timestamp"
}
```

### 7.2 Assessment Handoff

User:

```text
"I already know CNNs. Test me quickly so I can skip what I know."
```

Trace:

```json
{
  "intent": "assess_knowledge",
  "scope": "current_path",
  "selected_path": "computer_vision",
  "search_terms": ["cnn", "convolutional network"],
  "candidate_units": [
    "local::lecture_5_image_classification_with_cnns::seg3",
    "local::lecture_5_image_classification_with_cnns::seg4",
    "local::lecture_5_image_classification_with_cnns::seg5",
    "local::lecture_5_image_classification_with_cnns::seg6"
  ],
  "eligible_quiz_units": [
    {
      "unit_id": "local::lecture_5_image_classification_with_cnns::seg6",
      "quiz_count": 3
    }
  ],
  "selected_action": "start_assessment",
  "note": "Self-report does not update mastery. Assessment evidence is required before skip/replan."
}
```

### 7.3 Planner Explanation

User:

```text
"Why does the planner want me to learn this unit?"
```

Trace:

```json
{
  "intent": "explain_planner_decision",
  "scope": "current_unit",
  "inputs": [
    "learning_path_item.reason_codes",
    "learning_path_item.prerequisite_gap_kp_ids",
    "learner_mastery_kp for linked KPs",
    "unit_kp_map coverage"
  ],
  "answer_policy": "Explain evidence, not speculation. If no evidence exists, say it is unassessed and offer placement-lite."
}
```

## 8. API / Tool Contract

These endpoints can be implemented as internal services first and exposed as HTTP only if needed by the frontend.

### 8.1 `GET /api/agent/context`

Returns current learning context.

```ts
type AgentContextResponse = AgentLearningContext & {
  pathLabel: string | null;
  currentPathSummary: {
    totalUnits: number;
    completedUnits: number;
    inProgressUnits: number;
    nextUnitId?: string;
  } | null;
};
```

### 8.2 `POST /api/agent/search-units`

Request:

```ts
type UnitSearchRequest = {
  query: string;
  scope?: "current_unit" | "current_lecture" | "current_course" | "current_path" | "global_catalog";
  courseIds?: string[];
  limit?: number;
  includeHidden?: boolean;
  intent?: AgentIntent;
};
```

Response:

```ts
type UnitSearchResponse = {
  results: Array<{
    canonical_unit_id: string;
    learning_unit_id: string | null;
    course_id: string;
    course_slug: string | null;
    lecture_id: string | null;
    lecture_title: string | null;
    unit_slug: string | null;
    learn_href: string | null;
    start_sec?: number;
    end_sec?: number;
    unit_name: string;
    summary: string | null;
    score: number;
    reasons: string[];
    has_quiz_items: boolean;
    content_type: string | null;
    salience_score: string | null;
    actionable: boolean;
  }>;
  trace: {
    trace_id: string;
    resolved_scope: string;
    normalized_query: string;
    query_expansions: Array<{ from: string; to: string[]; reason: string }>;
    applied_filters: string[];
    ranking_version: string;
    runtime_navigation_resolution: "path_item" | "product_learning_unit" | "missing";
  };
};
```

### 8.3 `GET /api/agent/unit-context/{unit_id}`

Returns unit context, KP links, quiz count, and timestamp evidence.

### 8.4 `POST /api/agent/transcript-snippets`

Narrow transcript retrieval for already-selected units.

### 8.5 `POST /api/agent/actions/start-assessment`

Starts assessment for selected canonical unit IDs and returns the existing assessment session payload.

### 8.6 `POST /api/agent/actions/request-replan`

Does not directly mutate planner state until backend validates evidence ownership and impact. It should accept explicit evidence, current plan identity, affected KPs, and support dry-run first:

```ts
type ReplanRequest = {
  currentPlanId: string;
  plannerSessionId: string;
  reason: "assessment_completed" | "mastery_stale" | "user_goal_changed" | "manual_review";
  dryRun: boolean;
  evidence: {
    assessmentSessionId?: string;
    completedSessionOwnedByUser: boolean;
    phase?: "placement" | "mini_quiz" | "skip_verification" | "bridge_check" | "final_quiz" | "review";
    sourceCanonicalUnitIds: string[];
    affectedKpIds: string[];
    masteryDeltas: Array<{
      kp_id: string;
      before_lcb?: number;
      after_lcb?: number;
      before_mean?: number;
      after_mean?: number;
    }>;
  };
};
```

Response:

```ts
type ReplanResponse = {
  dryRun: boolean;
  accepted: boolean;
  rejectedReason?: string;
  impact: {
    unitsAdded: number;
    unitsRemoved: number;
    unitsChangedAction: number;
    estimatedHoursBefore: number;
    estimatedHoursAfter: number;
  };
  warnings: string[];
  nextPlanId?: string;
};
```

Validation rules:

- `assessmentSessionId` must belong to the current user.
- `phase` must be an evidence-producing phase.
- `affectedKpIds` must be linked to the source units or assessment items.
- `currentPlanId`/`plannerSessionId` must match the active path state.
- If `dryRun=true`, no planner mutation occurs; return impact only.

## 9. Data Model Additions

### 9.1 Search Document View

Recommended materialized view:

```sql
CREATE MATERIALIZED VIEW unit_search_documents AS
WITH quiz_counts AS (
  SELECT
    qb.unit_id,
    COUNT(DISTINCT qb.item_id) FILTER (
      WHERE COALESCE(qb.qa_gate_passed, true) = true
    ) AS quiz_count,
    COUNT(DISTINCT qb.item_id) FILTER (
      WHERE COALESCE(qb.qa_gate_passed, true) = true
        AND COALESCE(ipm.phase, '') IN (
          'placement',
          'mini_quiz',
          'skip_verification',
          'bridge_check',
          'final_quiz',
          'review'
        )
    ) AS usable_quiz_count
  FROM question_bank qb
  LEFT JOIN item_phase_map ipm ON ipm.item_id = qb.item_id
  GROUP BY qb.unit_id
),
kp_text AS (
  SELECT
    m.unit_id,
    string_agg(DISTINCT k.name, ' ') AS kp_names,
    string_agg(DISTINCT COALESCE(k.description, ''), ' ') AS kp_descriptions
  FROM unit_kp_map m
  JOIN concepts_kp k ON k.kp_id = m.kp_id
  GROUP BY m.unit_id
)
SELECT
  u.unit_id,
  u.course_id,
  u.lecture_id,
  u.lecture_title,
  u.unit_name,
  u.summary,
  u.key_points,
  u.section_flags,
  u.content_type,
  u.salience_score,
  u.duration_min,
  u.transcript_path,
  u.video_clip_ref,
  COALESCE(q.usable_quiz_count, 0) > 0 AS has_quiz_items,
  COALESCE(q.quiz_count, 0) AS quiz_count,
  COALESCE(q.usable_quiz_count, 0) AS usable_quiz_count,
  u.is_worth_learning,
  kt.kp_names,
  kt.kp_descriptions,
  to_tsvector(
    'english',
    concat_ws(
      ' ',
      u.course_id,
      u.lecture_title,
      u.unit_name,
      u.summary,
      u.key_points::text,
      u.section_flags::text,
      kt.kp_names,
      kt.kp_descriptions
    )
  ) AS search_vector
FROM units u
LEFT JOIN kp_text kt ON kt.unit_id = u.unit_id
LEFT JOIN quiz_counts q ON q.unit_id = u.unit_id
WHERE coalesce(u.active, true) = true
```

Notes:

- Use a normal SQL view first if materialized refresh is premature.
- Add trigram index later for fuzzy title search.
- Keep vector embedding columns unused in V1.
- `units.has_quiz_items` can be used as a cached hint, but the retrieval view should derive quiz availability from `question_bank` + `item_phase_map` + `qa_gate_passed` so stale backfills do not mislead assessment intent.
- Add runtime navigation fields either in this view or in `RuntimeNavigationResolver`; do not return only canonical IDs to the frontend.

### 9.2 Retrieval Trace

Retrieval trace is not optional. It is the main debugging surface for Agent/RAG behavior and should exist from Phase 1 as structured response metadata. Persistence can be behind a feature flag, but every search response must include a trace object.

Minimum per-response trace:

```ts
type RetrievalTrace = {
  trace_id: string;
  user_id: string;
  message_id?: string;
  intent: AgentIntent;
  raw_query: string;
  normalized_query: string;
  query_expansions: Array<{ from: string; to: string[]; reason: string }>;
  scope: string;
  selected_path?: string;
  candidate_courses: string[];
  applied_filters: string[];
  ranking_version: string;
  runtime_navigation_resolution: Array<{
    canonical_unit_id: string;
    source: "path_item" | "product_learning_unit" | "missing";
    learn_href: string | null;
  }>;
  selected_unit_ids: string[];
};
```

Optional persistence table:

```text
agent_retrieval_trace
- id
- user_id
- session_id
- message_id
- intent
- scope
- query
- selected_unit_ids
- applied_filters
- query_expansions
- runtime_navigation_resolution
- ranking_version
- created_at
```

This lets reviewers debug whether Agent behavior is deterministic, grounded, and actionable.

## 10. Agent Guardrails

### 10.1 Mastery Rules

- Self-report can create assessment candidates, not mastery.
- LLM confidence can recommend what to test, not what to skip.
- Skip/replan decisions require:
  - assessment evidence,
  - player quiz evidence,
  - or existing `learner_mastery_kp` with sufficient confidence.

### 10.2 Scope Rules

- Lecture AI Tutor answers only within current lecture/player.
- Path Agent can search across selected path.
- Global search must be explicit or triggered by broad user phrasing.
- Agent answers should cite units/lectures; if no source is found, say so.

### 10.3 Action Rules

- Agent can offer actions.
- Backend tools perform actions.
- No direct DB mutation by LLM.
- Replan should be a backend-controlled action with evidence IDs.

## 11. Embedding Decision

V1 should not require vector embeddings.

Use BM25/full-text first because:

- The corpus is highly structured by course, lecture, unit, KP.
- Unit summaries and key points are already high-quality retrieval text.
- Many product questions require planner/mastery state, not semantic search.
- BM25 is easier to inspect and explain to reviewers.
- Embeddings over raw transcript would add cost/noise before the search target is narrowed.

Embedding should be added in V2 as hybrid search when:

- Users ask vague semantic questions that keyword search misses.
- Course count grows beyond the current small curated set.
- The same concept appears under very different wording across courses.
- Path-level Q&A needs cross-course synthesis more often.

If V2 adds embedding, embed this first:

```text
unit_name + lecture_title + summary + key_points + KP names + KP descriptions
```

Do not embed full transcripts first. Transcript chunks should remain a second-stage evidence source.

## 12. Rollout Plan

### Phase 1: Search Foundation

- Create `unit_search_documents` view/service.
- Implement `UnitSearchService`.
- Implement `QueryNormalizer` with explicit synonym/domain alias expansion.
- Implement `RuntimeNavigationResolver` so every actionable search result can produce `learn_href`.
- Return structured retrieval trace in every search response from day one.
- Add optional trace persistence behind a feature flag.
- Add unit tests for scoped search:
  - CV path query returns CS231n CNN units.
  - NLP path query returns CS224n word vector units.
  - Administrative/logistics units are downranked for assessment.
  - `has_quiz_items` boosts assessment intent.
  - Synonym queries such as `ViT`, `convnet`, `RF`, and `word vectors` expand and rank expected units.
  - Search results include runtime navigation fields or are marked non-actionable.

### Phase 2: Agent Context And Tools

- Implement `AgentContextResolver`.
- Implement `PathRequirementService` for prerequisite/gap questions that should not use BM25 alone.
- Implement service-level tools:
  - `search_units`
  - `get_path_requirements`
  - `get_unit_context`
  - `get_transcript_snippets`
  - `start_assessment`
  - `request_replan`
- Validate replan dry-run inputs: plan/session ownership, assessment ownership, phase, affected KPs, and mastery deltas.
- Add retrieval/action trace output for every tool call.

### Phase 3: Chat UI

- Add Path Agent entry point in `/learn`.
- Keep Lecture AI Tutor separate in player.
- Show cited units in Agent answers.
- Provide action buttons:
  - Open unit
  - Start quiz/assessment
  - Review path impact
  - Request replan

### Phase 4: Assessment/Replan Loop

- Let Agent propose units for assessment based on query/profile.
- User confirms.
- Assessment updates mastery.
- Replan reads updated evidence.
- Agent summarizes what changed.

### Phase 5: Hybrid Retrieval

- Add embeddings over `unit_search_documents` if BM25 misses become common.
- Use hybrid ranking:

```text
final_score = bm25_score + semantic_score + structured_boosts
```

## 13. Testing Plan

### 13.1 Unit Tests

- Search query `"receptive field"` returns `local::lecture_5_image_classification_with_cnns::seg6`.
- Search query `"word vector embedding"` returns CS224n word vector unit on NLP path.
- Search query `"RF in CNNs"` expands `RF` to `receptive field` and returns the same CS231n unit with trace.
- Search query `"ViT"` expands to `vision transformer` and does not rely on exact title text only.
- Assessment intent excludes administrative units unless explicitly requested.
- Course/path scope changes ranking.
- Query with no result returns a safe fallback and does not hallucinate.
- Search results include runtime navigation data or `actionable=false`.
- Path requirement query for NLP returns required CS230/DL units via prerequisite/KP graph, not BM25-only.

### 13.2 Integration Tests

- `/api/agent/search-units` returns trace with scope, filters, ranking version.
- `/api/agent/unit-context/{unit_id}` includes KP links and quiz count.
- `/api/agent/search-units` returns `learn_href` for units joined to product runtime data.
- `/api/agent/path-requirements` returns prerequisite/gap trace and required units for selected path.
- Assessment handoff starts session only for eligible units.
- Replan dry-run returns impact without mutation.
- Replan mutation rejects missing/foreign/incomplete evidence.

### 13.3 UX Tests

- User can ask "where is X taught?" and open the player at the unit.
- User can ask "test me on X" and land in assessment.
- User can ask "why this unit?" and see planner reasons.
- User can ask "which DL parts are required for NLP?" and receive graph-based requirements, not generic search results.
- Lecture Tutor and Path Agent do not conflict in scope.

## 14. Reviewer Checklist

Reviewers should validate:

- Is unit-centered retrieval the right abstraction for current schema?
- Are BM25/full-text and structured boosts enough for V1?
- Are self-report, LLM inference, assessment evidence, and mastery state separated clearly?
- Are Agent actions safely mediated by backend tools?
- Are transcript/video evidence only loaded after candidate units are selected?
- Is the Path Agent clearly separated from Lecture AI Tutor?
- Are retrieval traces available from Phase 1 and sufficient for debugging bad answers?
- Does each actionable search result include runtime navigation fields such as `learn_href`, `course_slug`, `unit_slug`, or `learning_unit_id`?
- Are cross-path prerequisite/gap questions handled by graph services instead of BM25-only search?
- Does query normalization cover common domain aliases such as `ViT`, `CNN`, `convnet`, `RF`, and `word vectors`?
- Does replan require validated evidence ownership, phase, affected KPs, mastery deltas, and dry-run impact before mutation?
- Are hidden/admin/logistics units handled correctly for assessment and search?

## 15. Open Questions

1. Should `unit_search_documents` be a SQL view first or a materialized view from day one?
2. Should Path Agent live in `/learn` only, or also be accessible from dashboard?
3. Should global catalog search be allowed by default or require explicit user wording?
4. Should the Agent expose "confidence" to users, or only show citations and actions?
5. Should transcript snippets be implemented from raw transcript text now, or should V1 rely on timestamped key points first?

## 16. Recommended Decision

Implement V1 as deterministic hierarchical retrieval:

```text
context -> intent -> unit search -> unit context -> optional transcript -> answer/action
```

Do not add embeddings yet. Add retrieval trace logging early so reviewers can inspect why the Agent selected each unit. Use assessment/player evidence as the only source of mastery changes. Keep the existing Lecture AI Tutor lecture-scoped and introduce a separate Path Agent for path/course-level questions.
