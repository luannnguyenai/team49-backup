# Onboarding Agent Assessment Routing Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix beginner fresh-start routing, local agent timeout, onboarding loading clarity, and assessment AI feedback rendering without changing the intended rule that beginners do not take the onboarding assessment.

**Architecture:** Keep beginner and experienced onboarding as separate flows. The backend course gate must recognize `goal_preferences.placement_status='skipped'` as valid beginner access, while assessment-only routes remain assessment-backed. Agent timeout is fixed by moving LangGraph checkpointer setup out of the per-request chat path, matching AWS configuration.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic, Next.js 14 App Router, React 18, Zustand, Vitest, pytest.

---

## Root Cause Summary

1. Beginner fresh-start users are correctly marked as `placement_status='skipped'`, but `src/services/course_entry_service.py` only checks for a completed assessment session before allowing `/courses/{slug}/learn/{unitSlug}` access. This redirects beginners into `/assessment`, where sessionStorage has no pending assessment units, producing "No learning units were found for this assessment."

2. Local `/agent` hangs because `src/services/agent_checkpointer_factory.py` runs `AsyncPostgresSaver.setup()` inside each first chat request when `AGENT_GRAPH_CHECKPOINTER_SETUP=true`. AWS fixed this by setting `AGENT_GRAPH_CHECKPOINTER_SETUP=false` after checkpoint tables existed.

3. Assessment AI feedback fails silently. Backend catches all summary generation/parser failures and returns `available=false`; frontend then hides the summary block. The existing test `test_parse_assessment_ai_summary_accepts_single_quoted_model_payload` already fails because the parser only uses `json.loads`.

4. Onboarding Finish can feel laggy because `isLoading` from `useAuthStore` is not wired into the Finish button. There is no disabled/loading state during `PUT /api/users/me/onboarding` and route transition.

5. Some navigation targets are stale or inconsistent: protected Sidebar still exposes `Courses -> /`, but authenticated `/` redirects to `/agent`; legacy quiz/module-test CTAs use `/learn/{learningUnitId}` while the current course player uses `/courses/{courseSlug}/learn/{unitSlug}` when `learn_href` exists.

## File Structure

- Modify `src/services/course_entry_service.py`: allow skipped-placement beginners through the same course gate used by course start and direct learning access.
- Create or modify `tests/services/test_course_entry_service.py`: lock beginner skipped access and experienced assessment-required behavior.
- Modify `.env.example` and `docker-compose.yml`: document/apply the AWS agent checkpointer setup fix for local runtime.
- Modify `tests/services/test_agent_checkpointer_factory.py`: assert setup is skipped when configured false.
- Modify `src/services/assessment_service.py`: parse common LLM JSON variants and return useful unavailable metadata.
- Modify `frontend/app/assessment/results/page.tsx`: render an explicit unavailable state instead of hiding AI feedback failures.
- Modify `frontend/tests/routes/assessment/results/page.test.tsx`: cover successful and unavailable summary states.
- Modify `frontend/app/onboarding/page.tsx` and `frontend/components/onboarding/StepAssessmentDepth.tsx`: add pending/disabled state on Finish.
- Modify `frontend/components/layout/Sidebar.tsx`: match TopNav by removing or rerouting the authenticated Courses nav item.
- Modify `frontend/lib/canonical-learning-runtime.ts` only if legacy quiz/module-test redirects need course-aware hrefs in a later task.

---

### Task 1: Fix Beginner Fresh-Start Course Gate

**Files:**
- Modify: `src/services/course_entry_service.py`
- Create or modify: `tests/services/test_course_entry_service.py`

- [ ] **Step 1: Write failing tests for skipped placement access**

Add these tests:

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.services import course_entry_service


@pytest.mark.asyncio
async def test_start_learning_allows_beginner_skipped_without_completed_assessment(monkeypatch):
    user = SimpleNamespace(id=uuid4(), is_onboarded=True)
    monkeypatch.setattr(
        course_entry_service,
        "_get_course_gate_snapshot_from_db",
        AsyncMock(return_value={"slug": "cs231n", "status": "ready"}),
    )
    monkeypatch.setattr(course_entry_service, "_check_skill_test_completed", AsyncMock(return_value=False))
    monkeypatch.setattr(course_entry_service, "_check_placement_skipped", AsyncMock(return_value=True))
    monkeypatch.setattr(course_entry_service, "_get_first_unit_slug_from_db", AsyncMock(return_value="lecture-1"))

    decision = await course_entry_service.get_start_learning_decision("cs231n", user=user)

    assert decision.reason == "learning_ready"
    assert decision.target == "/courses/cs231n/learn/lecture-1"


@pytest.mark.asyncio
async def test_start_learning_still_requires_assessment_when_not_skipped(monkeypatch):
    user = SimpleNamespace(id=uuid4(), is_onboarded=True)
    monkeypatch.setattr(
        course_entry_service,
        "_get_course_gate_snapshot_from_db",
        AsyncMock(return_value={"slug": "cs231n", "status": "ready"}),
    )
    monkeypatch.setattr(course_entry_service, "_check_skill_test_completed", AsyncMock(return_value=False))
    monkeypatch.setattr(course_entry_service, "_check_placement_skipped", AsyncMock(return_value=False))

    decision = await course_entry_service.get_start_learning_decision("cs231n", user=user)

    assert decision.reason == "skill_test_required"
    assert decision.target == "/assessment?next=/courses/cs231n/start"
```

- [ ] **Step 2: Run tests and confirm they fail**

Run:

```bash
uv run pytest tests/services/test_course_entry_service.py -q
```

Expected: fails because `_check_placement_skipped` does not exist.

- [ ] **Step 3: Implement skipped-placement helper and gate**

In `src/services/course_entry_service.py`, add:

```python
async def _check_placement_skipped(user_id: uuid.UUID) -> bool:
    try:
        from src.database import async_session_factory
        from src.models.learning import GoalPreference

        async with async_session_factory() as db:
            result = await db.execute(
                select(GoalPreference.placement_status)
                .where(GoalPreference.user_id == user_id)
                .limit(1)
            )
            return result.scalar_one_or_none() == "skipped"
    except Exception:
        return False
```

Then replace both skill-test checks with:

```python
has_completed_skill_test = await _check_skill_test_completed(user.id)
placement_skipped = await _check_placement_skipped(user.id)
if not has_completed_skill_test and not placement_skipped:
    return StartLearningDecisionResponse(
        decision="redirect",
        target=f"/assessment?next=/courses/{course_slug}/start",
        reason="skill_test_required",
    )
```

For `assert_learning_access`, use the same condition and keep the forbidden message only when both are false:

```python
has_completed_skill_test = await _check_skill_test_completed(user.id)
placement_skipped = await _check_placement_skipped(user.id)
if not has_completed_skill_test and not placement_skipped:
    raise ForbiddenError("Please complete the skill assessment before accessing this learning content.")
```

- [ ] **Step 4: Verify**

Run:

```bash
uv run pytest tests/services/test_course_entry_service.py -q
uv run pytest tests/contract/test_course_start_api.py -q
```

Expected: all pass.

---

### Task 2: Port AWS Agent Timeout Fix to Local Runtime

**Files:**
- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Modify: `tests/services/test_agent_checkpointer_factory.py`

- [ ] **Step 1: Add test coverage for setup skip**

Add:

```python
@pytest.mark.asyncio
async def test_postgres_backend_skips_setup_when_disabled(monkeypatch):
    import src.services.agent_checkpointer_factory as factory

    class FakeSaver:
        setup_called = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def setup(self):
            self.setup_called = True

    class FakeAsyncPostgresSaver:
        @staticmethod
        def from_conn_string(_uri):
            return FakeSaver()

    monkeypatch.setitem(
        __import__("sys").modules,
        "langgraph.checkpoint.postgres.aio",
        SimpleNamespace(AsyncPostgresSaver=FakeAsyncPostgresSaver),
    )
    settings = SimpleNamespace(
        agent_graph_checkpointer_backend="postgres",
        agent_graph_checkpointer_setup=False,
        database_url="postgresql+asyncpg://user:pass@localhost:5432/app",
    )

    async with factory.build_agent_graph_checkpointer(app_settings=settings) as checkpointer:
        assert checkpointer is not None
        assert checkpointer.setup_called is False
```

- [ ] **Step 2: Configure local env like AWS**

Add to `.env.example`:

```env
# LangGraph checkpointer setup is a one-time schema operation.
# Keep false during normal runtime; run setup separately only for fresh DB bootstrap.
AGENT_GRAPH_CHECKPOINTER_BACKEND=postgres
AGENT_GRAPH_CHECKPOINTER_SETUP=false
```

Add to `docker-compose.yml` backend env:

```yaml
  AGENT_GRAPH_CHECKPOINTER_BACKEND: ${AGENT_GRAPH_CHECKPOINTER_BACKEND:-postgres}
  AGENT_GRAPH_CHECKPOINTER_SETUP: ${AGENT_GRAPH_CHECKPOINTER_SETUP:-false}
```

- [ ] **Step 3: Verify**

Run:

```bash
uv run pytest tests/services/test_agent_checkpointer_factory.py -q
```

Expected: all pass.

---

### Task 3: Fix Assessment AI Summary Parser and UI State

**Files:**
- Modify: `src/services/assessment_service.py`
- Modify: `tests/services/test_assessment_ai_summary.py`
- Modify: `frontend/app/assessment/results/page.tsx`
- Modify: `frontend/tests/routes/assessment/results/page.test.tsx`

- [ ] **Step 1: Confirm current backend failure**

Run:

```bash
uv run pytest tests/services/test_assessment_ai_summary.py -q
```

Expected before fix: `test_parse_assessment_ai_summary_accepts_single_quoted_model_payload` fails with `available=False`.

- [ ] **Step 2: Make parser tolerant without executing model text**

In `src/services/assessment_service.py`, import `ast`, then update parser:

```python
def _parse_json_like_payload(text: str) -> dict | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        try:
            payload = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            return None
    return payload if isinstance(payload, dict) else None
```

Use it inside `_parse_assessment_ai_summary`:

```python
payload = _parse_json_like_payload(text)
if payload is None:
    return AssessmentAISummaryResponse(
        available=False,
        model_used=DEFAULT_MODEL,
        provider=settings.model_provider,
    )
```

- [ ] **Step 3: Add frontend visible unavailable state**

In `frontend/app/assessment/results/page.tsx`, keep unavailable summary in state:

```tsx
.then((summary) => {
  setAiSummary(summary);
})
```

Render below loading:

```tsx
{aiSummary && !aiSummary.available && (
  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
    AI feedback is temporarily unavailable. Your scored placement results below are still saved.
  </div>
)}
```

- [ ] **Step 4: Add frontend tests**

Add one test for a rendered summary and one for unavailable state:

```tsx
it("renders AI summary when available", async () => {
  vi.mocked(assessmentApi.summary).mockResolvedValue({
    available: true,
    summary: "Review activation functions before moving on.",
    highlights: ["1 unit needs review"],
    next_step: "Start with the weakest unit.",
    model_used: "gpt-5.4-mini",
    provider: "openai",
  });

  render(<AssessmentResultsPage />);

  expect(await screen.findByText("AI summary")).toBeInTheDocument();
  expect(screen.getByText("Review activation functions before moving on.")).toBeInTheDocument();
});

it("shows an unavailable AI feedback state instead of silently hiding it", async () => {
  vi.mocked(assessmentApi.summary).mockResolvedValue({
    available: false,
    summary: null,
    highlights: [],
    next_step: null,
    model_used: "gpt-5.4-mini",
    provider: "openai",
  });

  render(<AssessmentResultsPage />);

  expect(await screen.findByText(/AI feedback is temporarily unavailable/i)).toBeInTheDocument();
});
```

- [ ] **Step 5: Verify**

Run:

```bash
uv run pytest tests/services/test_assessment_ai_summary.py -q
npm test -- --run tests/routes/assessment/results/page.test.tsx
```

Expected: all pass.

---

### Task 4: Make Onboarding Finish Non-Ambiguous During Lag

**Files:**
- Modify: `frontend/app/onboarding/page.tsx`
- Modify: `frontend/components/onboarding/StepAssessmentDepth.tsx`
- Modify: `frontend/tests/unit/onboarding/StepAssessmentDepth.test.tsx`

- [ ] **Step 1: Extend assessment-depth props**

Change props:

```tsx
interface Props {
  onBack: () => void;
  onNext: () => void;
  nextLabel?: string;
  nextLoading?: boolean;
}
```

Use it:

```tsx
export default function StepAssessmentDepth({ onBack, onNext, nextLabel = "Continue", nextLoading = false }: Props) {
```

Disable Back and Finish while loading:

```tsx
<button type="button" onClick={onBack} disabled={nextLoading} ...>
```

```tsx
<button type="button" onClick={onNext} disabled={nextLoading} ...>
  {nextLoading ? "Saving..." : nextLabel}
</button>
```

- [ ] **Step 2: Wire auth loading into onboarding**

In `frontend/app/onboarding/page.tsx`, pass:

```tsx
<StepAssessmentDepth
  onBack={() => navigate(3)}
  onNext={() => {
    handleSubmit(submitOnboarding)();
  }}
  nextLabel="Finish"
  nextLoading={isLoading}
/>
```

- [ ] **Step 3: Add test**

Add:

```tsx
it("disables finish while onboarding is saving", () => {
  render(<StepAssessmentDepth onBack={vi.fn()} onNext={vi.fn()} nextLabel="Finish" nextLoading />);
  expect(screen.getByRole("button", { name: "Saving..." })).toBeDisabled();
});
```

- [ ] **Step 4: Verify**

Run:

```bash
npm test -- --run tests/unit/onboarding/StepAssessmentDepth.test.tsx
```

Expected: pass.

---

### Task 5: Fix Protected Sidebar Courses Redirect

**Files:**
- Modify: `frontend/components/layout/Sidebar.tsx`
- Modify: `frontend/tests/unit/layout/sidebar-logout.test.tsx` or create `frontend/tests/unit/layout/sidebar-navigation.test.tsx`

- [ ] **Step 1: Add test that protected sidebar does not link Courses to authenticated root**

Add:

```tsx
it("does not render the public Courses root link in the protected sidebar", () => {
  render(<Sidebar mobileOpen={false} onMobileClose={vi.fn()} />);
  expect(screen.queryByRole("link", { name: /courses/i })).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Filter Courses in Sidebar like TopNav**

In `Sidebar.tsx`:

```tsx
const visibleNavItems = NAV_ITEMS.filter((navItem) => navItem.label !== "Courses");
```

Then map `visibleNavItems` instead of `NAV_ITEMS`.

- [ ] **Step 3: Verify**

Run:

```bash
npm test -- --run tests/unit/layout/sidebar-logout.test.tsx
```

Expected: pass.

---

### Task 6: Audit Legacy Learn Links After Core Fixes

**Files:**
- Inspect: `frontend/lib/canonical-learning-runtime.ts`
- Inspect: `frontend/app/module-test/[sectionId]/results/page.tsx`
- Inspect: `frontend/app/quiz/[learningUnitId]/results/page.tsx`
- Modify only if product wants every learner entry to use the course player route.

- [ ] **Step 1: Document current legacy links**

Current links:

```tsx
buildQuizRuntimeRef(...).learnHref = `/learn/${learningUnitId}`
router.push(`/learn/${rt.learning_unit_id}`)
```

These go to the legacy canonical content page, not the course player.

- [ ] **Step 2: Decide whether legacy content routes remain supported**

If legacy `/learn/{id}` is still supported for quiz/module-test review, leave unchanged. If every route must use the course player, extend quiz/module-test result payloads to include `learn_href` or `course_slug + unit_slug`.

- [ ] **Step 3: Add tests for whichever decision is chosen**

For legacy support:

```tsx
expect(screen.getByRole("button", { name: /review/i })).toBeInTheDocument();
```

For course-player support:

```tsx
expect(navigationMock.router.push).toHaveBeenCalledWith("/courses/cs230/learn/lecture-1");
```

---

## Final Verification

- [ ] Run backend targeted tests:

```bash
uv run pytest tests/services/test_course_entry_service.py tests/contract/test_course_start_api.py tests/services/test_assessment_ai_summary.py tests/services/test_agent_checkpointer_factory.py -q
```

- [ ] Run frontend targeted tests:

```bash
npm test -- --run tests/routes/assessment/results/page.test.tsx tests/unit/onboarding/StepAssessmentDepth.test.tsx tests/unit/layout/sidebar-logout.test.tsx
```

- [ ] Manual browser checks:

```text
1. Register or login as a new user.
2. Select "You are new to AI".
3. Confirm onboarding finishes to /learn without assessment.
4. Generate/open a plan unit.
5. Verify /courses/{slug}/learn/{unitSlug} opens and does not redirect to /assessment.
6. Complete an experienced assessment and verify AI summary or visible unavailable state.
7. Open /agent locally and verify first answer returns without client timeout.
```

