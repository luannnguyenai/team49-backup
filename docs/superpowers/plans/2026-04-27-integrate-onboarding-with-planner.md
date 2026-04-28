# Integrate Onboarding With Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge `luan_updatet7` into `planner` and make onboarding feed exactly one concrete planner path: CV or NLP.

**Architecture:** Onboarding is the input provider. `/learn` remains the planner surface. The planner keeps its schema-v2 metadata and roadmap UI, while onboarding contributes `path_key`, self-report cluster priors, experience level, and placement evidence.

**Tech Stack:** Next.js App Router, React 18, Zustand, FastAPI, SQLAlchemy, Pydantic, PostgreSQL.

---

### Task 1: Merge Branches And Preserve Both Data Models

**Files:**
- Modify: `src/schemas/learning_path.py`
- Modify: `src/routers/learning_path.py`
- Modify: `src/services/recommendation_engine.py`
- Modify: `frontend/types/index.ts`
- Modify: `frontend/components/learn/LearningUnitShell.tsx`

- [ ] **Step 1: Checkout planner and start merge**

Run:

```bash
git switch planner
git merge --no-ff luan_updatet7
```

Expected: conflicts in `learning_path.py`, `recommendation_engine.py`, `learning_path.py router`, and maybe shared frontend files.

- [ ] **Step 2: Resolve `PathItemResponse` by keeping all fields**

In `src/schemas/learning_path.py`, `PathItemResponse` must include both planner fields and placement phase fields:

```python
canonical_unit_id: str | None = None
reason_codes: list[str] = Field(default_factory=list)
prerequisite_gap_kp_ids: list[str] = Field(default_factory=list)
segment_policy: str | None = None
content_type: str | None = None
salience_score: str | None = None
has_quiz_items: bool | None = None
is_worth_learning: bool | None = None
override_critical_kp: bool = False
phase_tag: str | None = None
is_locked: bool = False
rationale_log: str | None = None
```

- [ ] **Step 3: Resolve router by keeping planner helper**

In `src/routers/learning_path.py`, keep `_path_item_response(...)` and extend it to include phase fields:

```python
phase_tag=getattr(lp, "phase_tag", None),
is_locked=bool(getattr(lp, "is_locked", False)),
rationale_log=getattr(lp, "rationale_log", None),
```

- [ ] **Step 4: Resolve recommendation engine by composing decisions**

Keep planner schema-v2 metadata:

```python
reason_codes
prerequisite_gap_kp_ids
segment_policy
content_type
salience_score
has_quiz_items
is_worth_learning
override_critical_kp
```

Also keep placement phase:

```python
phase_tag
is_locked
rationale_log
```

When writing `recommended_path_json`, persist both groups.

- [ ] **Step 5: Verify merge compiles**

Run:

```bash
python -m py_compile src/schemas/learning_path.py src/routers/learning_path.py src/services/recommendation_engine.py
```

Expected: no syntax errors.

- [ ] **Step 6: Commit merge base**

```bash
git add src/schemas/learning_path.py src/routers/learning_path.py src/services/recommendation_engine.py frontend/types/index.ts frontend/components/learn/LearningUnitShell.tsx
git commit -m "merge: integrate onboarding branch into planner"
```

---

### Task 2: Replace Goal Selection With Two Planner Paths

**Files:**
- Modify: `frontend/components/onboarding/StepGoalSelection.tsx`
- Modify: `frontend/stores/onboardingStore.ts`
- Modify: `frontend/lib/onboarding-schema.ts`
- Modify: `frontend/types/index.ts`
- Modify: `src/config/goal_course_map.py`
- Modify: `src/schemas/onboarding.py`
- Modify: `src/schemas/auth.py`
- Modify: `src/services/onboarding_service.py`
- Test: `frontend/tests/unit/onboarding/StepGoalSelection.test.tsx`
- Test: `tests/test_onboarding_endpoints.py`

- [ ] **Step 1: Change UI copy and single-select behavior**

`StepGoalSelection` asks:

```tsx
<p>Hướng bạn muốn tập trung là gì?</p>
```

Cards:

```tsx
[
  { id: "dl_cv", label: "Computer Vision (CV)" },
  { id: "dl_nlp", label: "Natural Language Processing (NLP)" },
]
```

Clicking a card replaces the current selection, never appends.

- [ ] **Step 2: Change backend map**

`src/config/goal_course_map.py`:

```python
GOAL_COURSE_MAP = {
    "dl_cv": ["cs230", "cs231n"],
    "dl_nlp": ["cs230", "cs224n"],
}
```

Remove standalone `deep_learning`.

- [ ] **Step 3: Validate exactly one path**

In onboarding schemas, reject empty or multiple `goal_ids`:

```python
if len(v) != 1:
    raise ValueError("Select exactly one learning path.")
```

- [ ] **Step 4: Update tests**

Frontend test should assert 2 cards only, single-select replacement, and no multi-select.

Backend test should assert:

```python
_derive_course_ids(["dl_cv"]) == ["cs230", "cs231n"]
_derive_course_ids(["dl_nlp"]) == ["cs230", "cs224n"]
```

- [ ] **Step 5: Run focused tests**

```bash
cd frontend
npm test -- --run tests/unit/onboarding/StepGoalSelection.test.tsx
cd ..
UV_PROJECT_ENVIRONMENT=/tmp/a20-app-049-venv uv run --with pytest-asyncio pytest tests/test_onboarding_endpoints.py tests/test_onboarding_goal_ids.py -q
```

- [ ] **Step 6: Commit**

```bash
git add frontend/components/onboarding/StepGoalSelection.tsx frontend/stores/onboardingStore.ts frontend/lib/onboarding-schema.ts frontend/types/index.ts src/config/goal_course_map.py src/schemas/onboarding.py src/schemas/auth.py src/services/onboarding_service.py frontend/tests/unit/onboarding/StepGoalSelection.test.tsx tests/test_onboarding_endpoints.py tests/test_onboarding_goal_ids.py
git commit -m "feat: make onboarding select one planner path"
```

---

### Task 3: Replace Raw Unit Step 3 With Cluster Self-Assessment

**Files:**
- Create: `frontend/components/onboarding/pathClusters.ts`
- Modify: `frontend/components/onboarding/StepKnownTopicsFiltered.tsx`
- Modify: `frontend/stores/onboardingStore.ts`
- Modify: `frontend/app/onboarding/page.tsx`
- Modify: `src/services/onboarding_service.py`
- Test: `frontend/tests/unit/onboarding/StepKnownTopicsFiltered.test.tsx`

- [ ] **Step 1: Add cluster config**

Create cluster config with 8-12 CV/NLP clusters. Example:

```ts
export const PATH_CLUSTERS = {
  dl_cv: [
    { id: "dl_foundations", label: "Deep Learning Foundations", courseIds: ["cs230", "cs231n"], lectureOrders: [1, 2, 3, 4] },
    { id: "cnn_fundamentals", label: "CNN Fundamentals", courseIds: ["cs231n"], lectureOrders: [5, 6] },
    { id: "object_detection_segmentation", label: "Object Detection & Segmentation", courseIds: ["cs231n"], lectureOrders: [9] },
  ],
  dl_nlp: [
    { id: "dl_foundations", label: "Deep Learning Foundations", courseIds: ["cs230"], lectureOrders: [1, 2, 3, 4] },
    { id: "word_vectors", label: "Word Vectors", courseIds: ["cs224n"], lectureOrders: [1, 2] },
    { id: "attention_transformers", label: "Attention & Transformers", courseIds: ["cs224n"], lectureOrders: [7, 8, 9] },
  ],
} as const;
```

- [ ] **Step 2: Store cluster priors**

Add state:

```ts
clusterSelfRatings: Record<string, "unknown" | "some" | "confident">
setClusterSelfRating(clusterId, rating)
```

- [ ] **Step 3: Render cluster cards**

Each cluster card shows:

```tsx
label
Review button
3 rating buttons: Chưa học / Đã học qua / Tự tin
```

The Review drawer shows representative bullets and max 2-4 representative lectures, not raw units.

- [ ] **Step 4: Persist priors**

Send cluster ratings in onboarding notes via auth onboarding payload or `saveKnownTopics` replacement. Store as:

```json
{
  "path_key": "dl_cv",
  "cluster_self_ratings": {
    "cnn_fundamentals": "confident"
  }
}
```

- [ ] **Step 5: Run focused tests**

```bash
cd frontend
npm test -- --run tests/unit/onboarding/StepKnownTopicsFiltered.test.tsx
```

- [ ] **Step 6: Commit**

```bash
git add frontend/components/onboarding/pathClusters.ts frontend/components/onboarding/StepKnownTopicsFiltered.tsx frontend/stores/onboardingStore.ts frontend/app/onboarding/page.tsx src/services/onboarding_service.py frontend/tests/unit/onboarding/StepKnownTopicsFiltered.test.tsx
git commit -m "feat: replace onboarding unit checklist with path clusters"
```

---

### Task 4: Connect Onboarding To Planner Profile And /learn

**Files:**
- Modify: `frontend/app/onboarding/page.tsx`
- Modify: `frontend/features/learning-path/profile.ts`
- Modify: `frontend/features/learning-path/stores/learningPathStore.ts`
- Test: `frontend/tests/unit/learning-path/profile.test.ts`

- [ ] **Step 1: Add adapter from onboarding path**

In planner profile module:

```ts
export function pathKeyToLearningProfile(pathKey: "dl_cv" | "dl_nlp", weeklyHours?: number): LearningProfile {
  return withHashes({
    source: "onboarding",
    goal: pathKey,
    startCourseId: "CS230",
    selectedCourseIds: pathKey === "dl_cv" ? ["CS230", "CS231n"] : ["CS230", "CS224n"],
    weeklyHours: weeklyHours ?? null,
  });
}
```

- [ ] **Step 2: Set planner profile on onboarding submit**

Before redirect:

```ts
useLearningPathStore.getState().setProfile(pathKeyToLearningProfile(pathKey, data.available_hours_per_week));
router.push("/learn");
```

- [ ] **Step 3: Keep backend source of truth**

Frontend profile is UX state only. Backend still uses `goal_preferences.selected_course_ids` to generate path.

- [ ] **Step 4: Run planner tests**

```bash
cd frontend
npm test -- --run tests/unit/learning-path/profile.test.ts tests/unit/learning-path/roadmap-planner.test.tsx
npm run type-check
```

- [ ] **Step 5: Commit**

```bash
git add frontend/app/onboarding/page.tsx frontend/features/learning-path/profile.ts frontend/features/learning-path/stores/learningPathStore.ts frontend/tests/unit/learning-path/profile.test.ts
git commit -m "feat: hand off onboarding path to learn planner"
```

---

### Task 5: Final Verification

- [ ] **Step 1: Backend focused tests**

```bash
UV_PROJECT_ENVIRONMENT=/tmp/a20-app-049-venv uv run --with pytest-asyncio pytest tests/test_onboarding_endpoints.py tests/test_onboarding_goal_ids.py tests/services/test_recommendation_engine_canonical_cutover.py -q
```

- [ ] **Step 2: Frontend focused tests**

```bash
cd frontend
npm test -- --run tests/unit/onboarding/StepGoalSelection.test.tsx tests/unit/onboarding/StepKnownTopicsFiltered.test.tsx tests/unit/learning-path/profile.test.ts tests/unit/learning-path/roadmap-model.test.ts tests/unit/learning-path/roadmap-planner.test.tsx
npm run type-check
```

- [ ] **Step 3: Commit final fixes if needed**

```bash
git add <changed-files>
git commit -m "fix: stabilize onboarding planner integration"
```

---

## Self-Review

- The plan preserves `planner` roadmap UI and schema-v2 metadata.
- The plan preserves `luan_updatet7` onboarding, placement phase, and experience level concepts.
- Step 1 is reduced to exactly two path choices.
- Step 3 no longer renders hundreds of raw units.
- DL is mandatory foundation inside each path, not a standalone goal.
