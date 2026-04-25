# Inline Video Quiz Learning Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the desktop learning shell so lecture playback supports production-grade inline review quizzes, chapter/checkpoint progress markers, resizable side panels, and durable watch/quiz history without introducing a parallel runtime stack.

**Architecture:** Reuse the existing canonical quiz, session, interaction, history, and planner-session-state infrastructure instead of inventing a second quiz system. Extend the current quiz start flow to support `inline_video` checkpoints, persist watch/checkpoint progress in `PlannerSessionState.current_progress`, and render a desktop-only learning shell composed of a custom progress rail, resizable/hidable side panels, and an inline quiz overlay that resumes in place.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Pydantic v2, PostgreSQL JSON fields already in use, Next.js 14 App Router, React 18, TypeScript 5, Vitest, pytest.

---

## Implementation Surface

**Backend surfaces**
- `src/schemas/quiz.py`
- `src/routers/quiz.py`
- `src/services/quiz_service.py`
- `src/schemas/history.py`
- `src/services/history_service.py`
- `src/schemas/learning_session.py`
- `src/routers/learning_session.py`
- `src/services/learning_session_service.py`
- `src/repositories/planner_audit_repo.py`

**Frontend surfaces**
- `frontend/lib/api.ts`
- `frontend/types/index.ts`
- `frontend/components/learn/LearningUnitShell.tsx`
- `frontend/components/learn/InContextTutor.tsx`
- `frontend/components/learn/VideoProgressRail.tsx` (new)
- `frontend/components/learn/InlineVideoQuizOverlay.tsx` (new)
- `frontend/components/learn/ResizablePanel.tsx` (new)
- `frontend/components/learn/useDesktopPanelState.ts` (new)
- `frontend/app/(protected)/history/page.tsx`

**Test surfaces**
- `tests/services/test_inline_video_quiz_service.py` (new)
- `tests/contract/test_inline_video_quiz_routes.py` (new)
- `tests/services/test_learning_session_service.py`
- `tests/services/test_history_service_inline_quiz.py` (new)
- `frontend/tests/routes/learning/unit.test.tsx`
- `frontend/tests/unit/tutor/in-context-tutor.test.tsx`
- `frontend/tests/unit/content/video-progress-rail.test.tsx` (new)
- `frontend/tests/unit/content/inline-video-quiz-overlay.test.tsx` (new)
- `frontend/tests/routes/history/inline-quiz-history.test.tsx` (new)

## Shared Decisions

- Use the existing `sessions` and `interactions` tables for inline quiz attempts.
- Encode checkpoint semantics in existing fields:
  - `session_type = "quiz"`
  - `canonical_phase = "inline_midpoint_quiz"` or `"inline_end_quiz"`
  - `PlannerSessionState.current_progress.inline_quiz`
- Do **not** add a new table or migration for this feature.
- Midpoint checkpoint shows `3` questions after `>= 50%` watched.
- End checkpoint shows `5` questions after `>= 90%` watched.
- End checkpoint does not auto-open if the midpoint quiz is still in progress.
- Inline quiz overlay is desktop-only and lives above the video frame.
- Standalone `/quiz/[learningUnitId]` flow remains intact and continues to use `mini_quiz`.

Example planner session progress shape to preserve across tasks:

```json
{
  "learning_unit_id": "6b536e6d-8120-42a3-b11e-d0c9291f97a8",
  "video_progress_s": 812.4,
  "video_finished": false,
  "watch_percent": 0.53,
  "inline_quiz": {
    "midpoint": {
      "shown": true,
      "active_session_id": "f8b1d12e-8c8f-4766-a61e-4298d0a8b5fb",
      "completed_session_id": null,
      "excluded_item_ids": ["cs231n_l1_q12", "cs231n_l1_q09"]
    },
    "end": {
      "shown": false,
      "active_session_id": null,
      "completed_session_id": null,
      "excluded_item_ids": []
    }
  }
}
```

### Task 1: Extend runtime contract for inline quiz checkpoints

**Files:**
- Modify: `src/schemas/quiz.py`
- Modify: `src/routers/quiz.py`
- Modify: `src/schemas/learning_session.py`
- Modify: `src/routers/learning_session.py`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/types/index.ts`
- Test: `tests/contract/test_inline_video_quiz_routes.py`

- [ ] **Step 1: Write the failing backend contract test for inline quiz start**

Create `tests/contract/test_inline_video_quiz_routes.py` with a route test asserting `/api/quiz/start` accepts the extended request body:

```python
async def test_quiz_start_route_accepts_inline_checkpoint_payload(client, monkeypatch):
    expected = QuizStartResponse(
        session_id=uuid4(),
        learning_unit_id=uuid4(),
        total_questions=3,
        questions=[],
    )
    monkeypatch.setattr("src.routers.quiz.start_quiz", AsyncMock(return_value=expected))

    response = await client.post(
        "/api/quiz/start",
        json={
            "learning_unit_id": str(expected.learning_unit_id),
            "count": 3,
            "source": "inline_video",
            "checkpoint": "midpoint",
            "exclude_item_ids": ["item_a", "item_b"],
        },
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 201
```

- [ ] **Step 2: Run the route test to verify it fails**

Run: `uv run pytest tests/contract/test_inline_video_quiz_routes.py -q`

Expected: FAIL because `QuizStartRequest` does not yet accept `count`, `source`, `checkpoint`, or `exclude_item_ids`.

- [ ] **Step 3: Extend `QuizStartRequest` and response metadata**

Update `src/schemas/quiz.py` to support inline starts without breaking the standalone flow:

```python
class QuizStartRequest(BaseModel):
    learning_unit_id: uuid.UUID = Field(
        validation_alias=AliasChoices("learning_unit_id", "topic_id")
    )
    count: int | None = Field(default=None, ge=1, le=10)
    source: str = Field(default="standalone")
    checkpoint: str | None = Field(default=None)
    exclude_item_ids: list[str] = Field(default_factory=list, max_length=20)
```

Add lightweight response metadata for frontend branching:

```python
class QuizStartResponse(BaseModel):
    session_id: uuid.UUID
    learning_unit_id: uuid.UUID
    total_questions: int
    questions: list[QuestionForQuiz]
    source: str = "standalone"
    checkpoint: str | None = None
```

- [ ] **Step 4: Thread the new request fields through the quiz router**

Update `src/routers/quiz.py` so the start route passes all fields:

```python
return await start_quiz(
    db,
    user.id,
    body.learning_unit_id,
    count=body.count,
    source=body.source,
    checkpoint=body.checkpoint,
    exclude_item_ids=body.exclude_item_ids,
)
```

- [ ] **Step 5: Extend learning-session request/response shapes for inline quiz state**

Update `src/schemas/learning_session.py` to carry watched percent and inline quiz state:

```python
class LearningUnitProgressRequest(BaseModel):
    video_progress_s: float | None = Field(default=None, ge=0)
    video_finished: bool = False
    watch_percent: float | None = Field(default=None, ge=0, le=1)
    inline_quiz: dict | None = None
```

Keep `LearningUnitProgressResponse.current_progress` generic, but document that it now returns `watch_percent` and `inline_quiz`.

- [ ] **Step 6: Add typed frontend API helpers before touching UI**

Update `frontend/types/index.ts` and `frontend/lib/api.ts` with inline-quiz-aware shapes:

```ts
export interface InlineQuizStartPayload {
  learning_unit_id: string;
  count: number;
  source: "inline_video";
  checkpoint: "midpoint" | "end";
  exclude_item_ids: string[];
}
```

```ts
export const canonicalQuizApi = {
  start: (payload: string | InlineQuizStartPayload) =>
    api
      .post<QuizStartResponse>(
        "/api/quiz/start",
        typeof payload === "string" ? { learning_unit_id: payload } : payload,
      )
      .then((r) => r.data),
};
```

- [ ] **Step 7: Run the contract test to verify it passes**

Run: `uv run pytest tests/contract/test_inline_video_quiz_routes.py -q`

Expected: PASS

- [ ] **Step 8: Commit the contract layer**

```bash
git add src/schemas/quiz.py src/routers/quiz.py src/schemas/learning_session.py src/routers/learning_session.py frontend/lib/api.ts frontend/types/index.ts tests/contract/test_inline_video_quiz_routes.py
git commit -m "feat: add inline quiz start contract"
```

### Task 2: Implement inline quiz selection, resume, and persisted watch state

**Files:**
- Modify: `src/services/quiz_service.py`
- Modify: `src/services/learning_session_service.py`
- Modify: `src/repositories/planner_audit_repo.py`
- Test: `tests/services/test_inline_video_quiz_service.py`
- Test: `tests/services/test_learning_session_service.py`

- [ ] **Step 1: Write the failing service tests for midpoint/end starts and resume**

Create `tests/services/test_inline_video_quiz_service.py` with at least these cases:

```python
async def test_start_inline_midpoint_quiz_uses_requested_count(monkeypatch):
    response = await start_quiz(
        db,
        user_id,
        learning_unit_id,
        count=3,
        source="inline_video",
        checkpoint="midpoint",
        exclude_item_ids=[],
    )
    assert response.total_questions == 3
    assert response.checkpoint == "midpoint"

async def test_start_inline_end_quiz_excludes_previously_used_items(monkeypatch):
    response = await start_quiz(
        db,
        user_id,
        learning_unit_id,
        count=5,
        source="inline_video",
        checkpoint="end",
        exclude_item_ids=["item_1", "item_2"],
    )
    returned_ids = [question.item_id for question in response.questions]
    assert "item_1" not in returned_ids
    assert "item_2" not in returned_ids

async def test_start_inline_quiz_reuses_active_session_for_same_checkpoint(monkeypatch):
    first = await start_quiz(db, user_id, learning_unit_id, count=3, source="inline_video", checkpoint="midpoint")
    second = await start_quiz(db, user_id, learning_unit_id, count=3, source="inline_video", checkpoint="midpoint")
    assert second.session_id == first.session_id

async def test_end_checkpoint_does_not_open_while_midpoint_is_in_progress(monkeypatch):
    await start_quiz(db, user_id, learning_unit_id, count=3, source="inline_video", checkpoint="midpoint")
    with pytest.raises(ConflictError):
        await start_quiz(db, user_id, learning_unit_id, count=5, source="inline_video", checkpoint="end")
```

Extend `tests/services/test_learning_session_service.py` with a progress-state test:

```python
async def test_update_learning_unit_progress_persists_watch_percent_and_inline_quiz_state():
    result = await update_learning_unit_progress(
        db,
        user_id=user_id,
        learning_unit_id=learning_unit_id,
        video_progress_s=600.0,
        video_finished=False,
        watch_percent=0.5,
        inline_quiz={"midpoint": {"shown": True, "active_session_id": "quiz-1"}},
    )
    assert result.current_progress["watch_percent"] == 0.5
    assert result.current_progress["inline_quiz"]["midpoint"]["active_session_id"] == "quiz-1"
```

- [ ] **Step 2: Run the service tests to verify they fail**

Run: `uv run pytest tests/services/test_inline_video_quiz_service.py tests/services/test_learning_session_service.py -q`

Expected: FAIL because the services only support the standalone quiz flow and the old progress payload.

- [ ] **Step 3: Extend `start_quiz` to accept inline metadata**

Update the public signature in `src/services/quiz_service.py`:

```python
async def start_quiz(
    db: AsyncSession,
    user_id: uuid.UUID,
    learning_unit_id: uuid.UUID,
    *,
    count: int | None = None,
    source: str = "standalone",
    checkpoint: str | None = None,
    exclude_item_ids: list[str] | None = None,
) -> QuizStartResponse:
    if source == "standalone":
        return await _start_canonical_quiz(db, user_id, learning_unit_id)
    return await _start_inline_quiz(
        db,
        user_id,
        learning_unit_id,
        count=count,
        checkpoint=checkpoint,
        exclude_item_ids=exclude_item_ids or [],
    )
```

Use these rules:
- standalone: keep current `mini_quiz` behavior with `10` questions
- inline midpoint: `3` questions, `canonical_phase = "inline_midpoint_quiz"`
- inline end: `5` questions, `canonical_phase = "inline_end_quiz"`

- [ ] **Step 4: Persist active/completed checkpoint state in planner session progress**

In `src/services/learning_session_service.py`, merge instead of overwrite:

```python
progress = {
    "learning_unit_id": str(learning_unit_id),
    "video_progress_s": video_progress_s,
    "video_finished": video_finished,
    "watch_percent": watch_percent,
    "inline_quiz": inline_quiz or existing_inline_quiz,
}
```

Add a small helper in the same file:

```python
def _merge_inline_quiz_progress(existing: dict | None, incoming: dict | None) -> dict:
    base = dict(existing or {})
    update = dict(incoming or {})
    for checkpoint in ("midpoint", "end"):
        if checkpoint in update:
            base[checkpoint] = {**base.get(checkpoint, {}), **update[checkpoint]}
    return base
```

- [ ] **Step 5: Reuse active quiz sessions for the same checkpoint**

Inside `src/services/quiz_service.py`, read `PlannerSessionState.current_progress.inline_quiz` and short-circuit:

```python
if source == "inline_video" and checkpoint_state.get("active_session_id"):
    existing = await _get_quiz_session(db, user_id, UUID(checkpoint_state["active_session_id"]))
    if existing.completed_at is None:
        return await _build_existing_quiz_start_response(db, existing)
```

- [ ] **Step 6: Track excluded item ids and prevent duplicate checkpoint pools**

When inline quiz starts, store:

```python
checkpoint_state = {
    "shown": True,
    "active_session_id": str(session.id),
    "completed_session_id": None,
    "excluded_item_ids": item_ids_for_started_session,
}
```

Use `exclude_item_ids` plus previous checkpoint exclusions when selecting end-quiz questions.

- [ ] **Step 7: Mark checkpoint completion during quiz finalize**

Inside `_complete_canonical_quiz`, if `session.canonical_phase` is inline:

```python
checkpoint = "midpoint" if session.canonical_phase == "inline_midpoint_quiz" else "end"
```

Update planner progress:
- clear `active_session_id`
- set `completed_session_id`
- keep `excluded_item_ids`
- set `current_stage = "post_quiz"`

- [ ] **Step 8: Run the service tests to verify they pass**

Run: `uv run pytest tests/services/test_inline_video_quiz_service.py tests/services/test_learning_session_service.py -q`

Expected: PASS

- [ ] **Step 9: Commit the runtime state layer**

```bash
git add src/services/quiz_service.py src/services/learning_session_service.py tests/services/test_inline_video_quiz_service.py tests/services/test_learning_session_service.py
git commit -m "feat: persist inline quiz checkpoint state"
```

### Task 3: Extend history and review surfaces for inline quiz attempts

**Files:**
- Modify: `src/schemas/history.py`
- Modify: `src/services/history_service.py`
- Modify: `frontend/app/(protected)/history/page.tsx`
- Modify: `frontend/types/index.ts`
- Test: `tests/services/test_history_service_inline_quiz.py`
- Test: `frontend/tests/routes/history/inline-quiz-history.test.tsx`

- [ ] **Step 1: Write the failing history tests**

Create `tests/services/test_history_service_inline_quiz.py`:

```python
async def test_history_item_exposes_inline_quiz_checkpoint_metadata():
    response = await get_history(db, user_id, session_type=SessionType.quiz)
    assert response.items[0].source == "inline_video"
    assert response.items[0].checkpoint == "midpoint"

async def test_session_detail_keeps_inline_quiz_questions_reviewable():
    detail = await get_session_detail(db, user_id, session_id)
    assert detail.source == "inline_video"
    assert detail.checkpoint == "midpoint"
    assert len(detail.questions) == 3
```

Create `frontend/tests/routes/history/inline-quiz-history.test.tsx`:

```tsx
it("renders inline midpoint quiz badges and learning unit labels", async () => {
  expect(screen.getByText("Mid-video quiz")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/services/test_history_service_inline_quiz.py -q`

Run: `npm test -- --run tests/routes/history/inline-quiz-history.test.tsx`

Expected: FAIL because history items do not expose checkpoint/source metadata and the page cannot render the new labels.

- [ ] **Step 3: Extend history schemas with source/checkpoint fields**

Update `src/schemas/history.py`:

```python
class HistoryItem(BaseModel):
    session_id: uuid.UUID
    session_type: SessionType
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: int | None
    subject: str
    learning_unit_id: uuid.UUID | None
    section_id: uuid.UUID | None
    score_percent: float | None
    correct_count: int
    total_questions: int
    source: str | None = None
    checkpoint: str | None = None
```

Also extend `SessionDetailResponse` if the frontend needs to label the reviewed session:

```python
class SessionDetailResponse(BaseModel):
    session_id: uuid.UUID
    session_type: SessionType
    bloom_breakdown: dict[str, str]
    weak_kcs: list[str]
    misconceptions: list[str]
    questions: list[QuestionInteractionDetail]
    source: str | None = None
    checkpoint: str | None = None
```

- [ ] **Step 4: Derive inline quiz metadata in the history service**

In `src/services/history_service.py`, parse `sess.canonical_phase`:

```python
def _session_checkpoint(sess: Session) -> tuple[str | None, str | None]:
    if sess.canonical_phase == "inline_midpoint_quiz":
        return ("inline_video", "midpoint")
    if sess.canonical_phase == "inline_end_quiz":
        return ("inline_video", "end")
    return (None, None)
```

Thread the result into both list and detail responses.

- [ ] **Step 5: Update the history page to show inline quiz labels and direct review**

In `frontend/app/(protected)/history/page.tsx`, add UI rules:

```ts
const CHECKPOINT_LABELS = {
  midpoint: "Mid-video quiz",
  end: "End-of-video quiz",
} as const;
```

Render a small badge next to quiz rows when `item.source === "inline_video"`.

- [ ] **Step 6: Add direct review affordance from history**

Support a query-param-driven auto-expand:

```ts
const targetSessionId = searchParams.get("session_id");
const [expandedSessionId, setExpandedSessionId] = useState<string | null>(targetSessionId);
```

If present, auto-open that row so a completed inline quiz can be reviewed immediately from the learning page.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `uv run pytest tests/services/test_history_service_inline_quiz.py -q`

Run: `npm test -- --run tests/routes/history/inline-quiz-history.test.tsx`

Expected: PASS

- [ ] **Step 8: Commit the history layer**

```bash
git add src/schemas/history.py src/services/history_service.py frontend/app/(protected)/history/page.tsx frontend/types/index.ts tests/services/test_history_service_inline_quiz.py frontend/tests/routes/history/inline-quiz-history.test.tsx
git commit -m "feat: expose inline quiz history metadata"
```

### Task 4: Build the desktop shell primitives for progress rail and resizable panels

**Files:**
- Create: `frontend/components/learn/VideoProgressRail.tsx`
- Create: `frontend/components/learn/ResizablePanel.tsx`
- Create: `frontend/components/learn/useDesktopPanelState.ts`
- Modify: `frontend/components/learn/LearningUnitShell.tsx`
- Test: `frontend/tests/unit/content/video-progress-rail.test.tsx`
- Test: `frontend/tests/routes/learning/unit.test.tsx`

- [ ] **Step 1: Write the failing frontend tests for rail markers and panel persistence**

Create `frontend/tests/unit/content/video-progress-rail.test.tsx`:

```tsx
it("renders chapter markers and midpoint/end checkpoint dots on the rail", () => {
  expect(screen.getByLabelText("Midpoint quiz checkpoint")).toBeInTheDocument();
});

it("calls onSeek when a chapter marker is clicked", async () => {
  await user.click(screen.getByRole("button", { name: /chapter 2/i }));
  expect(onSeek).toHaveBeenCalledWith(300);
});
```

Extend `frontend/tests/routes/learning/unit.test.tsx` with assertions for:
- key ideas above timestamps
- rail markers
- left/tutor panel hide buttons

- [ ] **Step 2: Run the frontend tests to verify they fail**

Run: `npm test -- --run tests/unit/content/video-progress-rail.test.tsx tests/routes/learning/unit.test.tsx`

Expected: FAIL because the shell still uses a plain video section without a custom rail or persistent panel state.

- [ ] **Step 3: Add a reusable desktop panel state hook**

Create `frontend/components/learn/useDesktopPanelState.ts`:

```ts
export function useDesktopPanelState(key: string, initialWidth: number) {
  const [width, setWidth] = useState(initialWidth);
  const [hidden, setHidden] = useState(false);
  return { width, hidden, setWidth, hide: () => setHidden(true), show: () => setHidden(false) };
}
```

Persist to `localStorage` keys such as:
- `al_learning_left_panel`
- `al_learning_tutor_panel`

- [ ] **Step 4: Add a resizable panel shell**

Create `frontend/components/learn/ResizablePanel.tsx` with:

```tsx
export default function ResizablePanel({
  side,
  width,
  minWidth,
  maxWidth,
  hidden,
  onResize,
  onToggleHidden,
  children,
}: Props) {
  return (
    <aside style={{ width, minWidth, maxWidth }}>
      <button type="button" onClick={onToggleHidden}>Toggle</button>
      {hidden ? null : children}
      <div role="separator" aria-orientation="vertical" data-side={side} />
    </aside>
  );
}
```

Requirements:
- mouse drag only on desktop
- enforce min/max width
- show a narrow reopen tab when hidden

- [ ] **Step 5: Add the custom video progress rail**

Create `frontend/components/learn/VideoProgressRail.tsx` with props:

```tsx
type RailMarker = {
  id: string;
  type: "chapter" | "quiz";
  label: string;
  time: number;
  state?: "locked" | "available" | "completed";
};
```

Render:
- watched progress fill
- chapter dots
- midpoint/end quiz dots
- hover label
- seek handler on click

- [ ] **Step 6: Recompose `LearningUnitShell` around the new primitives**

Update `frontend/components/learn/LearningUnitShell.tsx`:
- move `Key ideas at this moment` above `Timestamps`
- render `VideoProgressRail` below the video
- wrap left sidebar and tutor in `ResizablePanel`
- keep tutor always open by default, but user-hideable

Target order:

```tsx
video
VideoProgressRail
KeyIdeasCard
TimestampList
```

- [ ] **Step 7: Run the frontend tests to verify they pass**

Run: `npm test -- --run tests/unit/content/video-progress-rail.test.tsx tests/routes/learning/unit.test.tsx`

Expected: PASS

- [ ] **Step 8: Commit the desktop shell primitives**

```bash
git add frontend/components/learn/VideoProgressRail.tsx frontend/components/learn/ResizablePanel.tsx frontend/components/learn/useDesktopPanelState.ts frontend/components/learn/LearningUnitShell.tsx frontend/tests/unit/content/video-progress-rail.test.tsx frontend/tests/routes/learning/unit.test.tsx
git commit -m "feat: add desktop learning shell controls"
```

### Task 5: Implement the inline quiz overlay and shell integration

**Files:**
- Create: `frontend/components/learn/InlineVideoQuizOverlay.tsx`
- Modify: `frontend/components/learn/LearningUnitShell.tsx`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/types/index.ts`
- Test: `frontend/tests/unit/content/inline-video-quiz-overlay.test.tsx`
- Test: `frontend/tests/routes/learning/unit.test.tsx`

- [ ] **Step 1: Write the failing overlay tests**

Create `frontend/tests/unit/content/inline-video-quiz-overlay.test.tsx`:

```tsx
it("starts the midpoint overlay at 50 percent watched", async () => {
  expect(await screen.findByText("Quick review")).toBeInTheDocument();
});

it("resumes an in-progress inline quiz instead of starting a new one", async () => {
  expect(startQuiz).toHaveBeenCalledTimes(1);
});

it("does not show the end quiz while midpoint is still active", async () => {
  expect(screen.queryByText("Final review")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run the overlay tests to verify they fail**

Run: `npm test -- --run tests/unit/content/inline-video-quiz-overlay.test.tsx tests/routes/learning/unit.test.tsx`

Expected: FAIL because no overlay exists and `LearningUnitShell` does not track checkpoint triggers.

- [ ] **Step 3: Build a focused inline quiz overlay component**

Create `frontend/components/learn/InlineVideoQuizOverlay.tsx` with this contract:

```tsx
type InlineVideoQuizOverlayProps = {
  checkpoint: "midpoint" | "end";
  session: QuizStartResponse | null;
  onStart: () => Promise<void>;
  onDismiss: () => void;
  onAnswer: (questionId: string, answer: SelectedAnswer) => Promise<void>;
  onComplete: () => Promise<void>;
};
```

The overlay must support:
- start CTA
- one-question-at-a-time answering
- completion summary
- resume banner if a quiz session already exists

- [ ] **Step 4: Add checkpoint trigger logic in `LearningUnitShell`**

Add watched-progress guards:

```ts
const shouldOfferMidpointQuiz = watchPercent >= 0.5 && !inlineQuiz.midpoint.completed_session_id;
const shouldOfferEndQuiz = watchPercent >= 0.9 && midpointResolved && !inlineQuiz.end.completed_session_id;
```

When starting inline quiz:

```ts
await canonicalQuizApi.start({
  learning_unit_id: unit.id,
  count: checkpoint === "midpoint" ? 3 : 5,
  source: "inline_video",
  checkpoint,
  exclude_item_ids,
});
```

- [ ] **Step 5: Persist watch/checkpoint state while the user watches**

Use the learning session API from `LearningUnitShell` on throttled intervals and on key transitions:

```ts
await learningSessionApi.updateProgress(unit.id, {
  video_progress_s: currentTime,
  video_finished: watchPercent >= 0.95,
  watch_percent: watchPercent,
  inline_quiz,
});
```

- [ ] **Step 6: Add direct review affordance after quiz completion**

After complete:
- keep summary in overlay
- show `Review this attempt`
- link to `/history?session_id=<quizSessionId>`

- [ ] **Step 7: Run the overlay and route tests to verify they pass**

Run: `npm test -- --run tests/unit/content/inline-video-quiz-overlay.test.tsx tests/routes/learning/unit.test.tsx`

Expected: PASS

- [ ] **Step 8: Commit the inline overlay**

```bash
git add frontend/components/learn/InlineVideoQuizOverlay.tsx frontend/components/learn/LearningUnitShell.tsx frontend/lib/api.ts frontend/types/index.ts frontend/tests/unit/content/inline-video-quiz-overlay.test.tsx frontend/tests/routes/learning/unit.test.tsx
git commit -m "feat: add inline video quiz overlay"
```

### Task 6: Production hardening, end-to-end checks, and operator flags

**Files:**
- Modify: `src/services/quiz_service.py`
- Modify: `frontend/components/learn/LearningUnitShell.tsx`
- Modify: `frontend/lib/api.ts`
- Create: `frontend/tests/e2e/learning-inline-quiz.spec.ts`
- Modify: `frontend/tests/unit/tutor/in-context-tutor.test.tsx`

- [ ] **Step 1: Add the failing hardening tests**

Add at least these cases:

```tsx
it("keeps tutor suggestions usable after the tutor panel is hidden and restored", async () => {
  render(<LearningUnitShell data={fixture} courseSlug="cs231n" />);
  await user.click(screen.getByRole("button", { name: /hide ai tutor/i }));
  await user.click(screen.getByRole("button", { name: /show ai tutor/i }));
  expect(screen.getByText("Giải thích ý chính của đoạn này dễ hiểu hơn")).toBeInTheDocument();
})
```

Add e2e coverage in `frontend/tests/e2e/learning-inline-quiz.spec.ts`:

```ts
test("user reaches midpoint quiz, completes it, finishes end quiz, and reviews history", async ({ page }) => {
  // seek, trigger overlay, answer quiz, navigate to history review
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm test -- --run tests/unit/tutor/in-context-tutor.test.tsx`

Expected: FAIL if panel restoration or overlay coexistence breaks tutor state.

- [ ] **Step 3: Add feature-flag gates without forking the architecture**

Use a backend setting and frontend public env:

```python
inline_video_quiz_enabled: bool = True
```

```ts
const inlineVideoQuizEnabled = process.env.NEXT_PUBLIC_INLINE_VIDEO_QUIZ_ENABLED !== "false";
```

Rules:
- backend rejects inline start when disabled
- frontend hides quiz markers and overlay when disabled

- [ ] **Step 4: Add throttling and duplicate-trigger guards**

Hardening rules in `LearningUnitShell`:
- do not call progress update more than once per few seconds during watch
- do not reopen midpoint after dismiss in the same watch session
- do not start a second inline session while one is in progress

- [ ] **Step 5: Run the targeted verification suite**

Run:

```bash
uv run pytest tests/contract/test_inline_video_quiz_routes.py tests/services/test_inline_video_quiz_service.py tests/services/test_learning_session_service.py tests/services/test_history_service_inline_quiz.py -q
npm test -- --run tests/routes/learning/unit.test.tsx tests/unit/content/video-progress-rail.test.tsx tests/unit/content/inline-video-quiz-overlay.test.tsx tests/routes/history/inline-quiz-history.test.tsx tests/unit/tutor/in-context-tutor.test.tsx
```

Expected:
- backend tests all PASS
- frontend tests all PASS

- [ ] **Step 6: Run the reseed and smoke-check flow**

Run:

```bash
uv run python scripts/seed.py
```

Then manually verify:
- open the first video-backed lecture from `/courses/cs231n`
- open the first video-backed lecture from `/courses/cs224n`
- midpoint overlay at 50%
- end overlay at 90%+
- `/history?session_id=<completed-inline-quiz-session-id>`

- [ ] **Step 7: Commit the hardened feature**

```bash
git add src/services/quiz_service.py frontend/components/learn/LearningUnitShell.tsx frontend/lib/api.ts frontend/tests/e2e/learning-inline-quiz.spec.ts frontend/tests/unit/tutor/in-context-tutor.test.tsx
git commit -m "feat: ship inline video quiz learning shell"
```

## Coverage Review

- `YouTube-like progress rail with dots`: Task 4
- `Resizable + hide/show left sidebar and AI Tutor`: Task 4
- `Key ideas before timestamps`: Task 4
- `3-question midpoint quiz`: Tasks 1, 2, 5
- `5-question end quiz`: Tasks 1, 2, 5
- `Quiz questions from question_bank for current lecture`: Task 2
- `Persist user unit session state`: Tasks 1, 2, 5
- `Persist quiz attempts in history and allow review`: Task 3
- `Production feature flag and duplicate-trigger hardening`: Task 6

## Notes For Implementation

- Do not add a new persistence table unless a later review proves the current `current_progress` JSON cannot express the required state.
- Do not replace the existing standalone quiz page; inline quiz is an additive path.
- Keep all new UI desktop-only. Mobile/tablet can remain on the current experience.
- Prefer small helpers over further inflating `LearningUnitShell.tsx`. If logic exceeds the file’s readability threshold, split the quiz trigger state into a helper hook before adding more JSX.
