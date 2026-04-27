# Final Quiz Completion Without Video Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a lesson stay completed as soon as the user finishes the final review quiz, expose that completion as a green tick in the lecture list, and surface per-course learning progress percent in the catalog without requiring `video_finished` to be true.

**Architecture:** Keep `LearningProgressRecord` as the source of truth for lesson completion and treat inline-quiz completion metadata in `PlannerSessionState.current_progress` as resume/runtime state. Update the progress sync path so later video progress writes cannot downgrade a completed lesson, then project that canonical completion state into two read models: user-aware course unit lists for lecture ticks and user-aware course catalog rows with computed progress percent.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async ORM, Pydantic v2, Vitest, React 18, Next.js 14 App Router

---

## File Structure

- Modify: `src/services/learning_session_service.py`
  - Preserve completed lesson status when a final inline quiz has already been completed.
  - Derive `current_stage="post_quiz"` from final quiz completion alone instead of `video_finished && completed_end_quiz`.
- Modify: `src/services/quiz_service.py`
  - Keep the final-quiz completion rule explicit and documented in code.
  - Ensure quiz progress sync writes remain consistent with the new precedence model.
- Modify: `src/services/course_catalog_service.py`
  - Compute per-course progress percent for authenticated users from `learning_progress_records`.
- Modify: `src/services/learning_unit_service.py`
  - Attach user-specific completion flags to course unit list rows used by `LearningUnitShell`.
- Modify: `src/schemas/course.py`
  - Extend catalog and unit-list contracts with progress/completion read fields.
- Modify: `src/routers/courses.py`
  - Make `/api/courses/{slug}/units` optionally user-aware and keep `/api/courses` aligned with the new progress field.
- Modify: `tests/services/test_learning_session_service.py`
  - Add regression coverage for “completed final quiz + later video sync must not reopen lesson”.
- Modify: `tests/services/test_inline_video_quiz_service.py`
  - Tighten service expectations around completion semantics and post-quiz state.
- Modify: `tests/services/test_course_db_read_path.py`
  - Add service-level coverage for catalog progress enrichment.
- Modify: `tests/contract/test_course_catalog_api.py`
  - Cover the new catalog progress field.
- Modify: `frontend/tests/routes/learning/unit.test.tsx`
  - Add UI-facing regression coverage for lecture completion ticks and post-quiz semantics.
- Modify: `frontend/tests/routes/course/catalog.test.tsx`
  - Cover rendering of per-course progress percent on catalog cards.
- Modify: `frontend/components/learn/LearningUnitShell.tsx`
  - Render a green completion tick in the lecture list when a unit is completed.
- Modify: `frontend/components/course/CourseCatalog.tsx`
  - Render a progress label/meter from the new catalog field.
- Modify: `frontend/types/index.ts`
  - Extend client types for course progress percent and lecture completion flags.

### Task 1: Lock Down Backend Completion Semantics With Failing Tests

**Files:**
- Modify: `tests/services/test_learning_session_service.py`
- Modify: `tests/services/test_inline_video_quiz_service.py`
- Verify: `src/services/learning_session_service.py`
- Verify: `src/services/quiz_service.py`

- [ ] **Step 1: Add a regression test that a completed final inline quiz keeps the lesson completed even when later progress sync reports `video_finished=False`**

```python
@pytest.mark.asyncio
async def test_update_learning_unit_progress_preserves_completed_status_after_end_quiz(monkeypatch):
    user_id = uuid4()
    unit_id = uuid4()
    course_id = uuid4()
    existing_progress = {
        "learning_unit_id": str(unit_id),
        "inline_quiz": {
            "end": {
                "shown": True,
                "active_session_id": None,
                "completed_session_id": str(uuid4()),
            }
        },
    }

    class FakeCanonicalContentRepository:
        def __init__(self, db):
            assert db == "db-session"

        async def get_learning_units_by_ids(self, unit_ids):
            return {unit_id: SimpleNamespace(id=unit_id, course_id=course_id)}

    class FakeLearningProgressRepository:
        payload = None

        def __init__(self, db):
            assert db == "db-session"

        async def upsert(self, **payload):
            FakeLearningProgressRepository.payload = payload
            return SimpleNamespace(**payload)

    class FakePlannerAuditRepository:
        payload = None

        def __init__(self, db):
            assert db == "db-session"

        async def get_session_state(self, actual_user_id, session_id):
            return SimpleNamespace(current_progress=existing_progress)

        async def upsert_session_state(self, **payload):
            FakePlannerAuditRepository.payload = payload
            return SimpleNamespace(**payload)

    monkeypatch.setattr(
        learning_session_service,
        "CanonicalContentRepository",
        FakeCanonicalContentRepository,
    )
    monkeypatch.setattr(
        learning_session_service,
        "LearningProgressRepository",
        FakeLearningProgressRepository,
    )
    monkeypatch.setattr(
        learning_session_service,
        "PlannerAuditRepository",
        FakePlannerAuditRepository,
    )

    result = await learning_session_service.update_learning_unit_progress(
        "db-session",
        user_id=user_id,
        learning_unit_id=unit_id,
        video_progress_s=420.0,
        video_finished=False,
        watch_percent=0.71,
    )

    assert result.current_stage == "post_quiz"
    assert FakeLearningProgressRepository.payload["status"] == LearningProgressStatus.completed
    assert FakeLearningProgressRepository.payload["completed_at"] is not None
```

- [ ] **Step 2: Add a narrower quiz-service regression test that final inline quiz completion is the only inline checkpoint that updates the learning path**

```python
def test_should_complete_learning_unit_only_for_standalone_or_end_checkpoint():
    assert quiz_service._should_complete_learning_unit(
        SimpleNamespace(canonical_phase="inline_midpoint_quiz")
    ) is False
    assert quiz_service._should_complete_learning_unit(
        SimpleNamespace(canonical_phase="inline_end_quiz")
    ) is True
    assert quiz_service._should_complete_learning_unit(
        SimpleNamespace(canonical_phase="mini_quiz")
    ) is True
```

- [ ] **Step 3: Run the targeted backend tests and confirm they fail for the current implementation**

Run: `uv run pytest tests/services/test_learning_session_service.py tests/services/test_inline_video_quiz_service.py -q`

Expected: FAIL because `update_learning_unit_progress()` still writes `LearningProgressStatus.in_progress` and returns `current_stage == "watching"` when `video_finished=False` even after the final quiz has been completed.

- [ ] **Step 4: Commit the failing-test checkpoint**

```bash
git add tests/services/test_learning_session_service.py tests/services/test_inline_video_quiz_service.py
git commit -m "test: capture final quiz completion without video gate"
```

### Task 2: Make Final Quiz Completion the Source of Truth in Backend State

**Files:**
- Modify: `src/services/learning_session_service.py`
- Modify: `src/services/quiz_service.py`
- Verify: `src/repositories/learning_progress_repo.py`

- [ ] **Step 1: Introduce a helper in `learning_session_service.py` that detects whether the final inline quiz has already been completed**

```python
def _has_completed_final_inline_quiz(inline_quiz: dict | None) -> bool:
    if not isinstance(inline_quiz, dict):
        return False
    end_state = inline_quiz.get("end")
    return isinstance(end_state, dict) and bool(end_state.get("completed_session_id"))
```

- [ ] **Step 2: Update `update_learning_unit_progress()` so completed final quiz wins over `video_finished`**

```python
completed_final_quiz = _has_completed_final_inline_quiz(merged_inline_quiz)
current_stage = "watching"
progress_status = LearningProgressStatus.in_progress
completed_at = None

if completed_final_quiz:
    current_stage = "post_quiz"
    progress_status = LearningProgressStatus.completed
    completed_at = now
elif _has_active_inline_quiz(merged_inline_quiz):
    current_stage = "quiz_in_progress"

await LearningProgressRepository(db).upsert(
    user_id=user_id,
    course_id=unit.course_id,
    learning_unit_id=unit.id,
    status=progress_status,
    last_position_seconds=video_progress_s,
    last_opened_at=now,
    completed_at=completed_at,
)
```

- [ ] **Step 3: Preserve the explicit business rule in `quiz_service.py` and document it near `_should_complete_learning_unit()`**

```python
def _should_complete_learning_unit(session: Session) -> bool:
    """A lesson completes after standalone quiz completion or the final inline quiz.

    Video watch progress is resume/analytics state only and must not gate completion.
    """
    checkpoint = _quiz_checkpoint_for_session(session)
    if checkpoint is None:
        return True
    return checkpoint == "end"
```

- [ ] **Step 4: Keep quiz progress sync consistent with the new rule by continuing to emit `current_stage="post_quiz"` immediately after final quiz completion**

```python
await _sync_quiz_progress_state(
    db,
    user_id=user_id,
    learning_unit_id=unit.id,
    session_id=session.id,
    item_ids=item_ids,
    answered_item_ids=item_ids,
    current_stage="post_quiz" if should_complete_learning_unit else "watching",
    source=_quiz_source_for_session(session),
    checkpoint=_quiz_checkpoint_for_session(session),
    quiz_phase=session.canonical_phase or "mini_quiz",
    extra_progress={
        "score_percent": quiz_score_percent,
        "completed_at": now.isoformat(),
    },
)
```

- [ ] **Step 5: Run the targeted backend tests and confirm they pass**

Run: `uv run pytest tests/services/test_learning_session_service.py tests/services/test_inline_video_quiz_service.py -q`

Expected: PASS with the new regression showing `LearningProgressStatus.completed` survives later watch-progress updates.

- [ ] **Step 6: Commit the backend semantic change**

```bash
git add src/services/learning_session_service.py src/services/quiz_service.py tests/services/test_learning_session_service.py tests/services/test_inline_video_quiz_service.py
git commit -m "fix: preserve lesson completion after final quiz"
```

### Task 3: Expose Completion State to Catalog and Lecture List Read Models

**Files:**
- Modify: `src/services/course_catalog_service.py`
- Modify: `src/services/learning_unit_service.py`
- Modify: `src/schemas/course.py`
- Modify: `src/routers/courses.py`
- Modify: `tests/services/test_course_db_read_path.py`
- Modify: `tests/contract/test_course_catalog_api.py`

- [ ] **Step 1: Add a service-level test for catalog progress percent derived from completed units**

```python
async def test_list_course_catalog_includes_progress_percent_for_authenticated_user():
    rows = [
        {
            "id": "course_cs231n",
            "slug": "cs231n",
            "title": "CS231n",
            "short_description": "Vision",
            "status": "ready",
            "cover_image_url": None,
            "hero_badge": None,
        }
    ]
```

- [ ] **Step 2: Add a contract-level test that the catalog exposes `progress_percent`**

```python
async def test_get_courses_includes_progress_percent_field(self):
    response = await self.client.get("/api/courses")
    self.assertEqual(response.status_code, 200)
    self.assertIn("progress_percent", response.json()["items"][0])
```

- [ ] **Step 3: Extend `CourseCatalogItem` and the catalog serializer with a nullable progress field**

```python
class CourseCatalogItem(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    slug: str
    title: str
    short_description: str
    status: str
    cover_image_url: str | None = None
    hero_badge: str | None = None
    is_recommended: bool = False
    progress_percent: int | None = None
```

- [ ] **Step 4: Compute progress percent from completed units per course for authenticated users**

```python
progress_percent = round((completed_units / total_units) * 100) if total_units else 0
```

- [ ] **Step 5: Extend the course-units route to expose per-unit completion for lecture ticks**

```python
return {
    "units": [
        {
            "slug": u["slug"],
            "title": u["title"],
            "status": u["status"],
            "unit_type": u["unit_type"],
            "order_index": u["order_index"],
            "lecture_label": u.get("lecture_label"),
            "is_completed": u.get("is_completed", False),
        }
        for u in units
    ]
}
```

- [ ] **Step 6: Run the read-model and contract tests**

Run: `uv run pytest tests/contract/test_course_catalog_api.py tests/services/test_course_db_read_path.py -q`

Expected: PASS with the new catalog progress field and user-aware lecture completion data.

- [ ] **Step 7: Commit the API/read-model changes**

```bash
git add src/services/course_catalog_service.py src/services/learning_unit_service.py src/schemas/course.py src/routers/courses.py tests/contract/test_course_catalog_api.py tests/services/test_course_db_read_path.py
git commit -m "feat: expose completion progress in catalog and lecture lists"
```

### Task 4: Render Lecture Ticks and Catalog Progress in the Frontend

**Files:**
- Modify: `frontend/components/learn/LearningUnitShell.tsx`
- Modify: `frontend/components/course/CourseCatalog.tsx`
- Modify: `frontend/types/index.ts`
- Modify: `frontend/tests/routes/learning/unit.test.tsx`
- Modify: `frontend/tests/routes/course/catalog.test.tsx`
- Verify: `frontend/app/quiz/[learningUnitId]/results/page.tsx`

- [ ] **Step 1: Add client types for `is_completed` on unit list items and `progress_percent` on catalog items**

```ts
export interface CourseUnitListItem {
  slug: string;
  title: string;
  status: CourseStatus;
  unit_type: string;
  order_index: number;
  lecture_label?: string | null;
  is_completed?: boolean;
}

export interface CourseCatalogItem {
  id: string;
  slug: string;
  title: string;
  short_description: string;
  status: CourseStatus;
  cover_image_url: string | null;
  hero_badge: string | null;
  is_recommended: boolean;
  progress_percent?: number | null;
}
```

- [ ] **Step 2: Add a route test that the lecture list shows a green completion tick for a completed unit**

```tsx
expect(screen.getByLabelText("Lecture 01 completed")).toBeInTheDocument();
```

- [ ] **Step 3: Add a catalog test that course cards render progress percent**

```tsx
expect(screen.getByText("40% hoàn thành")).toBeInTheDocument();
```

- [ ] **Step 4: Render a green completion icon in `LearningUnitShell` lecture rows when `lecture.is_completed` is true**

```tsx
{lecture.is_completed ? (
  <span aria-label={`${lecture.lecture_label} completed`} className="text-emerald-500">
    <CheckCircle2 className="h-4 w-4" />
  </span>
) : null}
```

- [ ] **Step 5: Render the course progress percent in `CourseCatalog` only when the backend provides it**

```tsx
{typeof course.progress_percent === "number" ? (
  <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
    {course.progress_percent}% hoàn thành
  </p>
) : null}
```

- [ ] **Step 6: Run the focused frontend test files**

Run: `npm test -- --run frontend/tests/routes/learning/unit.test.tsx frontend/tests/routes/course/catalog.test.tsx`

Expected: PASS and confirm the UI shows lecture completion ticks, course progress percent, and post-quiz review affordances independently of `video_finished`.

- [ ] **Step 7: Commit the frontend rendering changes**

```bash
git add frontend/components/learn/LearningUnitShell.tsx frontend/components/course/CourseCatalog.tsx frontend/types/index.ts frontend/tests/routes/learning/unit.test.tsx frontend/tests/routes/course/catalog.test.tsx
git commit -m "feat(frontend): show lesson ticks and catalog progress"
```

### Task 5: Cross-Surface Verification and Handoff

**Files:**
- Modify if needed: `docs/superpowers/plans/2026-04-26-final-quiz-completion-without-video-gate.md`

- [ ] **Step 1: Run the full focused backend verification set**

Run: `uv run pytest tests/services/test_learning_session_service.py tests/services/test_inline_video_quiz_service.py tests/contract/test_course_catalog_api.py tests/services/test_course_db_read_path.py -q`

Expected: PASS

- [ ] **Step 2: Run the full focused frontend verification set**

Run: `npm test -- --run frontend/tests/routes/learning/unit.test.tsx frontend/tests/routes/course/catalog.test.tsx frontend/tests/routes/history/inline-quiz-history.test.tsx`

Expected: PASS

- [ ] **Step 3: Manually verify the business rule checklist in code review**

```text
Checklist:
- Completing a standalone quiz still marks the lesson complete.
- Completing an inline midpoint quiz does not complete the lesson.
- Completing an inline end quiz marks the lesson complete immediately.
- A later PUT /api/learning-session/learning-units/{id}/progress call cannot downgrade that lesson back to in_progress.
- /api/courses/{slug}/units exposes is_completed so lecture rows can show a green tick.
- /api/courses exposes per-course progress_percent for authenticated users.
- Review/history links still come from completed quiz session ids.
```

- [ ] **Step 4: Create the final integration commit**

```bash
git add src/services/learning_session_service.py src/services/quiz_service.py src/services/course_catalog_service.py src/services/learning_unit_service.py src/schemas/course.py src/routers/courses.py tests/services/test_learning_session_service.py tests/services/test_inline_video_quiz_service.py tests/services/test_course_db_read_path.py tests/contract/test_course_catalog_api.py frontend/components/learn/LearningUnitShell.tsx frontend/components/course/CourseCatalog.tsx frontend/types/index.ts frontend/tests/routes/learning/unit.test.tsx frontend/tests/routes/course/catalog.test.tsx
git commit -m "fix: complete lessons after final quiz and surface progress"
```

- [ ] **Step 5: Handoff note for reviewers**

```text
Reviewer notes:
- No DB migration is required; this is a semantic fix plus read-model enrichment.
- The canonical source of truth for completion remains learning_progress_records.status.
- planner_session_state.current_progress remains resume/runtime state and should not be treated as authoritative for reopening completed lessons.
- Course catalog progress percent is a read-model projection from completed units, not a separately persisted counter.
- This plan intentionally does not change quiz unlock thresholds; it only removes video-finished as a completion gate.
```
