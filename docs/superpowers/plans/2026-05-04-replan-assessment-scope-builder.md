# Replan Assessment Scope Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable `/replan` flow that lets learners describe knowledge they already have, review the matched current-path units and knowledge points, then hand off to the existing `/assessment` flow. `/replan` only builds the assessment scope. Existing `/assessment`, `/assessment/results`, and `/learn` own testing, result display, and path updates.

**Architecture:** Agent and Learn surface direct links/cards into `/replan`. `/replan` collects a knowledge claim, uses an LLM keyword planner to avoid brittle normalization, searches current-path units, suggests prerequisite units from the prerequisite graph, filters already skipped/mastered units, renders an editable scope review, then starts the existing assessment resource. Backend assessment submit continues to persist results used by `/learn`.

**Tech Stack:** Next.js 14 App Router, React 18, TypeScript 5, Zustand/sessionStorage assessment handoff, FastAPI, SQLAlchemy, Pydantic, existing assessment service, existing recommendation engine, existing canonical question/KP/prerequisite data.

---

## Product Decisions

- `/replan` is a scope builder only; it does not render quiz questions, results, or a custom replan proposal page.
- `/assessment` remains the owner for taking the test and viewing results.
- `/learn` remains the owner for showing the updated learning path after assessment results are persisted.
- No hard cap, no default cap, and no recommended question cap in `/replan`.
- Candidate units are selected by default; learners untick units they do not want to test.
- Question count is calculated from selected units and selected difficulty filters.
- Estimated time uses `10 seconds/question` because most questions are theory-heavy.
- Unit review cards must show Unit Title + Knowledge Points + question availability, not only question totals.
- Already skipped/mastered units are excluded by default. If the user describes only already handled units, show a notification and ask them to describe something else.
- Prerequisite units are suggestions, not automatic additions. User must accept the popup to add them.
- No explicit Cancel button. If the learner leaves, goes back, or closes the tab, no extra flow is needed.

---

## Existing Code To Reuse

- Reuse `/assessment` page for rendering and submitting questions.
- Reuse `/assessment/results` for result display and the existing route back to `/learn`.
- Reuse `writePendingCanonicalAssessment` handoff pattern where practical.
- Reuse canonical question selection and result persistence in `src/services/assessment_service.py`.
- Reuse placement decisions consumed by `src/services/recommendation_engine.py`.
- Reuse onboarding visual language: full-page wizard shell, progress bar, card layout, textarea pattern, and shortlist confirmation style.

Current assessment decision behavior:

```text
score_pct >= 70 -> skip
score_pct >= 50 -> review
score_pct < 50  -> relearn
```

The current decision logic is score-only. It does not require separate hard/application correctness for skip.

---

## Planned Files

- Create: `frontend/app/replan/page.tsx`
  - New `/replan` page and wizard shell.
- Create: `frontend/components/replan/ReplanKnowledgeClaimStep.tsx`
  - Step 1 textarea and guardrail messaging.
- Create: `frontend/components/replan/ReplanScopeReviewStep.tsx`
  - Unit cards/table with title, KPs, question counts, checkbox, and difficulty dropdown.
- Create: `frontend/components/replan/PrerequisiteSuggestionDialog.tsx`
  - Popup to include or skip prerequisite suggestions.
- Create: `frontend/lib/replan-assessment-context.ts`
  - Handoff helpers extending the assessment context with replan metadata if needed.
- Create: `frontend/lib/replan-api.ts`
  - Typed client for analysis and assessment-start endpoints if backend endpoints are added.
- Create: `frontend/tests/unit/replan/*`
  - Unit tests for guardrails, scope review totals, prerequisite popup, and storage/API handoff.
- Modify: `frontend/lib/canonical-assessment-session.ts`
  - Add optional metadata only if `/replan` uses sessionStorage handoff.
- Modify: `frontend/app/assessment/page.tsx`
  - Only if needed to read expanded handoff metadata. Do not fork assessment UX.
- Modify: `src/routers/*`
  - Add replan endpoints if implementing backend analysis in this pass.
- Create: `src/services/replan_keyword_planner.py`
  - LLM keyword planner; avoids brittle mechanical normalization.
- Create: `src/services/replan_unit_discovery.py`
  - Current-path candidate search and LLM unit selection.
- Create: `src/services/replan_prerequisite_suggestions.py`
  - Prerequisite graph suggestions, filtered by current path and already handled state.
- Create: `src/services/replan_question_scope.py`
  - Question/KP counts per selected unit and difficulty filter.
- Test: `tests/services/test_replan_keyword_planner.py`
- Test: `tests/services/test_replan_unit_discovery.py`
- Test: `tests/services/test_replan_prerequisite_suggestions.py`
- Test: `tests/services/test_replan_question_scope.py`

---

## Task 1: Entry Points

**Files:**
- Modify: `frontend/features/agent/components/AgentChatPage.tsx`
- Modify: Learn page/component that owns the existing learning path header/action area
- Create/modify tests under `frontend/tests/`

- [ ] **Step 1: Add Agent action card/link**

When user asks Agent to optimize learning based on known knowledge, render a lightweight card:

```text
I can help you optimize your plan by verifying what you already know.

[Optimize plan] -> /replan?source=agent&returnTo=/agent
[Change path]   -> existing change-path flow or /learn change-path entry
```

Agent must not run the replan wizard in chat and must not mutate planner state.

- [ ] **Step 2: Add Learn entry button**

Add an `Optimize plan` button near the learning path controls.

```text
Optimize plan -> /replan?source=learn&returnTo=/learn
```

- [ ] **Step 3: Tests**

Verify:

- Agent card links to `/replan`.
- Learn button links to `/replan`.
- No chat-side wizard UI is introduced.

---

## Task 2: Replan Wizard Shell

**Files:**
- Create: `frontend/app/replan/page.tsx`
- Create shared replan components as needed

- [ ] **Step 1: Build page shell**

Use onboarding's visual style:

- centered max-width card
- header icon
- progress indicator
- step title/subtitle
- slide/fade transitions if simple

Do not import onboarding domain components directly if it creates mode-specific branching. Prefer a replan-specific component using the same style.

- [ ] **Step 2: Keep scope small**

The page supports only:

```text
describe claim -> analyze -> prerequisite popup -> review scope -> start assessment
```

Do not add:

- custom result page
- custom apply page
- cancel flow
- tab-close/back cancellation logic

---

## Task 3: Step 1 Guardrails

**Files:**
- Create: `frontend/components/replan/ReplanKnowledgeClaimStep.tsx`
- Backend validation can live in the analyze endpoint if implemented
- Test: `frontend/tests/unit/replan/ReplanKnowledgeClaimStep.test.tsx`

- [ ] **Step 1: Render textarea with explicit safety copy**

Copy:

```text
Mô tả cụ thể những phần bạn đã nắm để hệ thống tạo bài kiểm tra xác nhận.
Mô tả này không tự động bỏ qua bài học. Kết quả assessment mới được dùng để cập nhật lộ trình.
```

Placeholder:

```text
Ví dụ:
- Tôi đã nắm CNN, convolution, pooling.
- Tôi biết Faster R-CNN nhưng chưa chắc YOLO.
- Tôi hiểu object detection cơ bản, muốn kiểm tra để bỏ bớt phần nền tảng.
```

- [ ] **Step 2: Reject empty/too short claims**

Reject empty or too-short inputs with:

```text
Hãy mô tả cụ thể concept hoặc unit bạn đã biết, ví dụ: "CNN, R-CNN, Faster R-CNN".
```

- [ ] **Step 3: Guard against skip-all commands**

Detect and block/re-ask for claims like:

```text
tôi biết hết
skip all
bỏ hết
cho qua toàn bộ
tối ưu hết mức
bỏ tất cả phần dễ
tôi muốn bỏ nguyên path
```

Message:

```text
Mình không thể tạo bài kiểm tra để bỏ toàn bộ lộ trình từ một mô tả quá chung.
Hãy nêu cụ thể những concept hoặc unit bạn đã biết.
```

- [ ] **Step 4: Allow broad but usable claims**

Do not block claims like:

```text
Tôi biết object detection cơ bản.
Tôi đã học computer vision ở trường.
Tôi biết machine learning fundamentals.
```

Mark them as broad and warn in the review step:

```text
Mô tả của bạn khá rộng. Hãy kiểm tra kỹ danh sách unit được chọn trước khi bắt đầu assessment.
```

- [ ] **Step 5: Tests**

Verify empty, skip-all, broad, and specific claims behave correctly.

---

## Task 4: LLM Keyword Planner

**Files:**
- Create: `src/services/replan_keyword_planner.py`
- Test: `tests/services/test_replan_keyword_planner.py`

- [ ] **Step 1: Add structured keyword-plan contract**

Output shape:

```json
{
  "primaryKeywords": [
    {
      "text": "Faster R-CNN",
      "reason": "User explicitly claims Faster RCNN knowledge.",
      "mustKeepPhrase": true
    }
  ],
  "secondaryKeywords": [],
  "negativeOrUncertainKeywords": [
    {
      "text": "YOLO",
      "reason": "User says they are not confident."
    }
  ],
  "searchQueries": [
    "Faster R-CNN",
    "\"Faster R-CNN\" object detection",
    "Faster RCNN"
  ],
  "doNotExpandTo": [
    "CNN",
    "R-CNN"
  ],
  "specificity": "specific",
  "guardrailFlags": []
}
```

- [ ] **Step 2: Avoid mechanical normalization**

Do not make rule-based normalization the source of truth.

Required behavior:

```text
User: "I know Faster RCNN"
Search: "Faster R-CNN", "Faster RCNN"
Do not expand to: "R-CNN", "CNN" unless LLM explicitly includes those as separate assessment targets.
```

- [ ] **Step 3: Tests**

Add cases:

- `Faster RCNN` does not degrade into generic `RCNN`/`CNN`.
- `YOLO chưa chắc` is captured as negative/uncertain, not selected as known knowledge.
- Broad claims are marked broad, not blocked.

---

## Task 5: Current-Path Unit Discovery

**Files:**
- Create: `src/services/replan_unit_discovery.py`
- Test: `tests/services/test_replan_unit_discovery.py`

- [ ] **Step 1: Load current path units only**

Candidate units must come from the learner's current active path. No global/out-of-path unit can be selected.

Each candidate should include:

```json
{
  "canonicalUnitId": "unit_faster_rcnn",
  "title": "Faster R-CNN",
  "summary": "...",
  "pathOrder": 12,
  "questionCounts": {
    "easy": 3,
    "medium": 4,
    "hard": 2,
    "application": 1
  }
}
```

- [ ] **Step 2: Search with LLM-planned queries**

Use BM25/lexical retrieval over:

- title
- description
- summary
- key points
- transcript snippets if already available in existing search services

Respect `doNotExpandTo`.

- [ ] **Step 3: LLM unit selection from candidates**

The LLM selects from current-path candidates only:

```json
{
  "selectedUnits": [
    {
      "canonicalUnitId": "unit_faster_rcnn",
      "selection": "include",
      "reason": "Exact conceptual match to the user's Faster RCNN claim."
    }
  ],
  "excludedUnits": [
    {
      "canonicalUnitId": "unit_rcnn",
      "reason": "Related but not the explicit target."
    }
  ],
  "maybeUnits": []
}
```

- [ ] **Step 4: Backend validation**

Drop and log any selected unit that:

- is not in current path
- has no assessment questions
- only appears because of forbidden expansion

---

## Task 6: Prerequisite Suggestion Popup

**Files:**
- Create: `src/services/replan_prerequisite_suggestions.py`
- Create: `frontend/components/replan/PrerequisiteSuggestionDialog.tsx`
- Test: `tests/services/test_replan_prerequisite_suggestions.py`
- Test: `frontend/tests/unit/replan/PrerequisiteSuggestionDialog.test.tsx`

- [ ] **Step 1: Query prerequisite graph**

Given selected units, suggest prerequisite units from the graph:

```text
Faster R-CNN -> Fast R-CNN -> R-CNN -> CNN foundations
```

Filter suggestions:

- current path only
- not already skipped/mastered
- has question bank items
- no duplicates

- [ ] **Step 2: Limit suggestion explosion**

Use bounded selection:

```text
max_depth: 2 by default
max_suggestions: 5
```

Rank by:

- prerequisite depth
- path-order proximity
- question availability
- foundation relevance

- [ ] **Step 3: Popup behavior**

Show when suggestions exist:

```text
Mình tìm thấy một vài phần nền tảng liên quan.

"Faster R-CNN" thường dựa trên các phần trước đó trong lộ trình.
Một số phần này chưa được ghi nhận là bạn đã nắm rõ.

Bạn có muốn thêm chúng vào bài kiểm tra xác nhận không?
```

Buttons:

```text
[Thêm vào bài kiểm tra]
[Bỏ qua]
```

- [ ] **Step 4: Never auto-add**

Prerequisites are suggestions only.

```text
Include -> add to review scope
Skip    -> keep only user-described units
```

---

## Task 7: Skipped/Mastered Filtering

**Files:**
- Add to backend replan services
- Add UI note/toast in `/replan`
- Test backend and frontend cases

- [ ] **Step 1: Determine already handled state**

A unit is already handled if it is already skipped/mastered according to existing learner state used by `/learn`.

Use existing placement/mastery/path state rather than creating a second definition.

- [ ] **Step 2: Exclude already handled units by default**

If a selected or suggested unit is already handled, do not include it in the assessment scope by default.

- [ ] **Step 3: Notify when claim hits already handled units**

Only already handled units:

```text
Faster R-CNN đã được ghi nhận là bạn nắm rõ rồi, nên không cần test lại.
```

Mixed handled and new:

```text
Faster R-CNN đã được ghi nhận là mastered/skipped nên được bỏ khỏi assessment.
Mình vẫn tìm thấy YOLOv8 là phần mới có thể kiểm tra.
```

- [ ] **Step 4: Tests**

Verify:

- old-only claim shows notification and no assessment scope
- mixed claim filters old units and keeps new units
- prerequisite suggestions also respect filtering

---

## Task 8: Review Scope UI With Unit Title And Knowledge Points

**Files:**
- Create: `frontend/components/replan/ReplanScopeReviewStep.tsx`
- Create: `src/services/replan_question_scope.py`
- Test: `frontend/tests/unit/replan/ReplanScopeReviewStep.test.tsx`
- Test: `tests/services/test_replan_question_scope.py`

- [ ] **Step 1: Backend provides KP display data**

For each review unit, include:

```json
{
  "canonicalUnitId": "unit_faster_rcnn",
  "title": "Faster R-CNN",
  "source": "matched_from_description",
  "knowledgePoints": [
    "Region Proposal Network",
    "Anchor boxes",
    "Two-stage detection",
    "RoI pooling / feature extraction"
  ],
  "questionCounts": {
    "easy": 3,
    "medium": 4,
    "hard": 2,
    "application": 1
  }
}
```

KP source priority:

1. question-linked KPs for candidate questions
2. `UnitKPMap` + `ConceptKP`
3. `CanonicalUnit.key_points`

- [ ] **Step 2: Render unit title and KP list**

Each unit card must show:

```text
[x] Faster R-CNN                         [All v]

Knowledge Points:
- Region Proposal Network
- Anchor boxes
- Two-stage detection
- RoI pooling / feature extraction

Easy 3 · Medium 4 · Hard 2 · Application 1
Source: Matched from your description
```

- [ ] **Step 3: Render prerequisite source labels**

Prerequisite units should explain why they are present:

```text
Source: Suggested prerequisite for Faster R-CNN
```

- [ ] **Step 4: Difficulty dropdown**

Support per-unit filter:

```text
Easy only
Easy + Medium
Easy + Medium + Hard
All
```

`All` means:

```text
Easy + Medium + Hard + Application
```

- [ ] **Step 5: Default selection behavior**

All eligible candidate units are selected initially.

No default question cap is applied.

- [ ] **Step 6: Realtime totals**

Calculate:

```text
selected_questions = sum(selected unit counts allowed by each unit's difficulty filter)
estimated_time = selected_questions * 10 seconds
```

Render:

```text
Total selected questions: 42
Estimated time: ~7 minutes
```

---

## Task 9: Assessment Handoff

**Files:**
- Modify: `frontend/lib/canonical-assessment-session.ts` if using sessionStorage
- Modify: `frontend/app/replan/page.tsx`
- Modify or add backend endpoint only if exact difficulty filtering cannot be represented by existing assessment start

- [ ] **Step 1: Build assessment scope**

On `Start assessment`, hand off selected units and difficulty filters.

Payload concept:

```json
{
  "selectedUnits": [
    {
      "canonicalUnitId": "unit_faster_rcnn",
      "difficultyFilter": "all"
    },
    {
      "canonicalUnitId": "unit_rcnn",
      "difficultyFilter": "easy_medium_hard"
    }
  ],
  "questionTotal": 19,
  "estimatedSeconds": 190,
  "scope": "current_path_only"
}
```

- [ ] **Step 2: Reuse `/assessment`**

After scope is prepared:

```text
router.push("/assessment")
```

or:

```text
router.push("/assessment?next=/learn")
```

Do not add a replan-specific result route.

- [ ] **Step 3: Support exact filters if needed**

Current assessment start supports canonical units and depth. It may not support exact per-unit difficulty filters. If exact filtering is required, add a focused backend bridge:

```text
POST /api/replan/assessment/start
```

This endpoint should use existing assessment resources but honor selected unit/difficulty scope.

---

## Task 10: Backend Path Update Reuse

**Files:**
- Inspect/modify `src/services/assessment_service.py`
- Inspect/modify `src/services/recommendation_engine.py`
- Tests under `tests/`

- [ ] **Step 1: Verify assessment results update path inputs**

Current assessment submit persists per-unit placement decisions:

```text
score_pct >= 70 -> skip
score_pct >= 50 -> review
score_pct < 50  -> relearn
```

Confirm `/learn` already uses these decisions to render:

```text
skip   -> skip/hide unit
review -> quick_review
relearn -> keep in learning path
```

- [ ] **Step 2: Avoid duplicate replan result logic**

Do not create:

- `/replan/{id}/result`
- custom Apply Replan button
- custom proposal page

Assessment result and Learn own this.

- [ ] **Step 3: Add recompute hook only if needed**

If `/learn` does not reflect new assessment decisions after returning from results, add the minimum backend/frontend refresh needed so `/learn` fetches latest recommendation/path data.

---

## Task 11: Tests And Verification

**Frontend tests:**

- [ ] Guardrail blocks skip-all and empty claims.
- [ ] Broad but usable claims continue with warning.
- [ ] Review scope renders Unit Title + Knowledge Points.
- [ ] All eligible units are selected initially.
- [ ] Unticking a unit updates total questions.
- [ ] Difficulty dropdown updates total questions.
- [ ] Prerequisite popup adds units only after user accepts.
- [ ] Already handled units are excluded and noted.
- [ ] Start assessment hands off selected scope to existing `/assessment`.

**Backend tests:**

- [ ] LLM keyword plan does not expand `Faster RCNN` into `R-CNN`/`CNN` unless explicitly selected.
- [ ] Current-path discovery excludes out-of-path units.
- [ ] Prerequisite suggestions are current-path only and filtered by handled state.
- [ ] Question scope includes KP names and counts by difficulty.
- [ ] Assessment results still drive `/learn` through existing placement decision logic.

**Manual verification:**

- [ ] From Agent, click Optimize Plan and land on `/replan`.
- [ ] From `/learn`, click Optimize Plan and land on `/replan`.
- [ ] Enter `Tôi biết Faster RCNN`.
- [ ] Confirm `Faster R-CNN` is selected without accidental `CNN`/`R-CNN` expansion.
- [ ] Accept prerequisite suggestions and confirm added units show source labels.
- [ ] Confirm each unit card shows Knowledge Points.
- [ ] Adjust difficulty dropdown and verify question total/time changes.
- [ ] Start assessment and complete it in `/assessment`.
- [ ] On `/assessment/results`, click existing route to `/learn`.
- [ ] Confirm `/learn` reflects updated skip/review/relearn decisions.

---

## Non-Goals

- No custom `/replan` result page.
- No custom `/replan` apply/confirm page.
- No explicit Cancel button.
- No browser-tab-close interruption workflow.
- No global question cap.
- No default/recommended question cap.
- No chat-embedded Planner Mode wizard.
- No out-of-path unit selection.
- No automatic prerequisite inclusion without user confirmation.

---

## Open Implementation Notes

- Exact per-unit difficulty filtering may require a small backend bridge because existing assessment start primarily accepts unit ids and depth.
- Existing assessment decision logic is score-only. If later product wants "skip requires hard/application correctness", that should be a separate decision-rule change.
- KP display should be based on actual candidate question KPs where possible, because the review UI must explain what the assessment will test.
- If using sessionStorage handoff, keep metadata additive and backwards-compatible with onboarding.
