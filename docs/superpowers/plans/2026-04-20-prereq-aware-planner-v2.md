# Prerequisite-Aware Planner v2.1 Implementation Plan

> **Historical plan:** This document is preserved for implementation history only. Planner production logic now reads canonical learning units, KP maps, prerequisite edges, and `learner_mastery_kp`; use the current handoff docs as authority.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current topic-level learning-path generator with a deterministic unit-level planner that supports forward/review/bridge frontiers, lower-confidence-bound mastery, skip auditing, and planner rationale output.

**Architecture:** Keep the existing FastAPI + SQLAlchemy backend, but move planner logic onto the KG-oriented branch of the codebase instead of extending the legacy `recommendation_engine.py` heuristics. Add persistent learner-goal and planner-audit state, add a unit-to-KC mapping layer, implement the v2.1 planner in two passes (minimal core first, advanced frontier behavior second), then expose it through a versioned or flagged rollout so v1 and v2 can be compared safely.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Pydantic v2, PostgreSQL, Alembic, Next.js 14 App Router, React 18, Vitest, pytest, Playwright

---

## File Structure

### Files to Modify

- `src/models/learning.py`
  Add planner-side persistence: posterior parameters on mastery rows, `WaivedUnit`, `PlannerRun`, and any planner audit enums.
- `src/models/course.py`
  Add unit-to-KC coverage mapping so the planner can score `LearningUnit` items against prerequisite KCs instead of only `Topic` rows.
- `src/repositories/mastery_repo.py`
  Expose planner-ready reads for `mu`, `sigma`, and KC-grain mastery lookups.
- `src/services/auth_service.py`
  Persist goal/profile fields from onboarding instead of leaving them only in browser session state.
- `src/routers/learning_path.py`
  Point path generation to the new planner service and version or flag the response contract.
- `src/schemas/learning_path.py`
  Replace the legacy topic-path response with `recommended_path`, `skippable_units`, `filtered_out`, and warnings.
- `src/kg/providers.py`
  Stop depending on the drifted `user_mastery` / `user_responses` tables for planner-critical reads.
- `src/config.py`
  Add a rollout switch such as `use_planner_v2` if query-param versioning alone is not enough.
- `frontend/app/onboarding/page.tsx`
  Capture planner-relevant goal selections explicitly and stop relying on session-only data for core planner inputs.
- `frontend/lib/api.ts`
  Update learning-path request/response types and add skip-confirm APIs if implemented in the same slice.
- `frontend/types/index.ts`
  Match the new planner contract.

### Files to Create

- `src/repositories/planner_repo.py`
  Planner-specific read model: goal profile, unit pool, completed/waived units, unit-KC coverage, prerequisite closures, recent progress.
- `src/services/planner_v2.py`
  Core deterministic planner implementation.
- `src/services/goal_embedding_service.py`
  Compute and cache the goal centroid embedding from selected course summaries / topic descriptions.
- `src/schemas/planner.py`
  Internal planner DTOs to keep `planner_v2.py` small and testable.
- `tests/services/test_planner_v2.py`
  Unit tests for frontier generation, scoring, budget enforcement, and fallback behavior.
- `tests/repositories/test_planner_repo.py`
  Read-model tests for completed/waived/unit-KC loading.
- `tests/contract/test_learning_path_planner_api.py`
  Contract tests for the new API shape.
- `frontend/tests/routes/learning/planner-path.test.tsx`
  UI contract tests for rendering recommended, skippable, and warning states.
- `alembic/versions/20260420_planner_v2_foundation.py`
  Migration for planner state tables and columns.

### Files to Inspect During Implementation

- `src/services/recommendation_engine.py`
  Legacy topic planner to retire or thin down after the new planner takes over.
- `src/kg/service.py`
  Existing deterministic KG service that should absorb or call the new planner logic.
- `src/models/user.py`
  Existing onboarding/user fields; decide whether to extend `users` or keep goal state in a dedicated planner table.
- `src/models/course.py`
  Existing `LearningUnit` and `LearningProgressRecord` models reused for completed-unit semantics.
- `frontend/app/(protected)/dashboard/page.tsx`
  Likely consumer of learning-path output.
- `frontend/app/(protected)/courses/[courseSlug]/learn/[unitSlug]/page.tsx`
  Future place for bridge warnings or re-plan entry points.

## Phase Plan

### Task 1a: Add Posterior Fields And Waived-Unit Persistence

**Files:**
- Modify: `src/models/learning.py`
- Modify: `src/repositories/mastery_repo.py`
- Create: `alembic/versions/20260420_planner_v2_foundation.py`
- Test: `tests/repositories/test_mastery_repo.py`
- Test: `tests/repositories/test_user_repo.py`

- [ ] **Step 1: Write the failing repository tests**

```python
async def test_bulk_get_for_user_returns_posterior_fields(session, seeded_user, seeded_topic):
    repo = MasteryRepository(session)
    await repo.upsert(
        user_id=seeded_user.id,
        topic_id=seeded_topic.id,
        kc_id=None,
        mastery_probability=0.61,
        posterior_mean=0.35,
        posterior_std=0.22,
        evidence_count=4,
    )

    result = await repo.bulk_get_for_user(seeded_user.id, [seeded_topic.id])
    assert result[seeded_topic.id].posterior_mean == 0.35
    assert result[seeded_topic.id].posterior_std == 0.22
```

```python
async def test_save_waived_unit_keeps_audit_separate_from_completed(repo, seeded_user, seeded_unit):
    await repo.save_waived_unit(seeded_user.id, seeded_unit.id, ["item_21"], 0.82)
    waived = await repo.list_waived_units(seeded_user.id)
    assert seeded_unit.id in {row.learning_unit_id for row in waived}
```

- [ ] **Step 2: Run the targeted tests to verify the schema is missing**

Run: `pytest tests/repositories/test_mastery_repo.py -k "posterior or waived" -v`
Expected: FAIL with missing column / unexpected keyword argument / missing table errors.

- [ ] **Step 3: Add the minimal schema foundation**

```python
class WaivedUnit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "waived_units"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    learning_unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("learning_units.id", ondelete="CASCADE"), nullable=False)
    evidence_items: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    mastery_lcb_at_waive: Mapped[float] = mapped_column(Float, nullable=False)
```

- [ ] **Step 4: Add the migration and repository reads**

Run: `pytest tests/repositories/test_mastery_repo.py tests/repositories/test_user_repo.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/models/learning.py src/repositories/mastery_repo.py alembic/versions/20260420_planner_v2_foundation.py tests/repositories/test_mastery_repo.py tests/repositories/test_user_repo.py
git commit -m "feat: add planner posterior and waived unit persistence"
```

### Task 1b: Add Unit-KC Mapping And Canonical Planner Read Foundations

**Files:**
- Modify: `src/models/course.py`
- Modify: `src/kg/providers.py`
- Create: `src/repositories/planner_repo.py`
- Test: `tests/repositories/test_planner_repo.py`
- Test: `tests/kg/test_service_path.py`
- Test: `tests/kg/test_service_recsys.py`

- [ ] **Step 1: Write the failing planner repository and source-of-truth tests**

```python
async def test_load_planner_context_returns_completed_waived_and_unit_kcs(repo, seeded_context):
    ctx = await repo.load_planner_context(user_id=seeded_context.user_id, horizon=10)
    assert seeded_context.completed_unit_id in ctx.completed_units
    assert seeded_context.waived_unit_id in ctx.waived_units
    assert ctx.unit_kc_map[seeded_context.target_unit_id][0].coverage_weight == 1.0
```

```python
async def test_db_mastery_provider_reads_canonical_mastery_scores(provider, user_id):
    topic_mastery = await provider.get_topic_mastery(user_id)
    assert isinstance(topic_mastery, dict)
```

- [ ] **Step 2: Run the repository tests**

Run: `pytest tests/repositories/test_planner_repo.py tests/kg/test_service_path.py tests/kg/test_service_recsys.py -v`
Expected: FAIL because `PlannerRepository`, `learning_unit_kc_map`, and canonical planner reads do not exist.

- [ ] **Step 3: Add the unit-KC mapping and read model foundation**

```python
class LearningUnitKCMap(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "learning_unit_kc_map"

    learning_unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("learning_units.id", ondelete="CASCADE"), nullable=False)
    kc_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("knowledge_components.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="main")
    coverage_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
```

```python
@dataclass(frozen=True)
class PlannerContext:
    user_id: uuid.UUID
    goal_track_weights: dict[str, float]
    goal_embedding: list[float]
    completed_units: set[uuid.UUID]
    waived_units: set[uuid.UUID]
    unit_kc_map: dict[uuid.UUID, list[UnitKCRef]]
    recent_units: list[uuid.UUID]
```

- [ ] **Step 4: Make canonical source-of-truth explicit**

```python
async def get_topic_mastery(self, user_id: uuid.UUID) -> dict[str, float]:
    # Read from mastery_scores / interactions-derived state only.
    # Do not query user_mastery here.
    ...
```

Run: `pytest tests/repositories/test_planner_repo.py tests/kg/test_service_path.py tests/kg/test_service_recsys.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/models/course.py src/kg/providers.py src/repositories/planner_repo.py tests/repositories/test_planner_repo.py tests/kg/test_service_path.py tests/kg/test_service_recsys.py
git commit -m "feat: add planner read model and canonical unit kc mapping"
```

### Task 2: Persist Goal Profile And Remove Session-Only Planner Inputs

**Files:**
- Modify: `src/models/user.py`
- Modify: `src/services/auth_service.py`
- Modify: `src/schemas/auth.py`
- Create: `src/services/goal_embedding_service.py`
- Modify: `frontend/app/onboarding/page.tsx`
- Test: `tests/test_user_skill_overview.py`
- Test: `tests/contract/test_course_start_api.py`

- [ ] **Step 1: Write the failing onboarding persistence tests**

```python
async def test_update_onboarding_persists_goal_track_and_selected_modules(db, user):
    body = OnboardingRequest(
        known_topic_ids=[],
        desired_module_ids=[],
        available_hours_per_week=6,
        target_deadline=date(2026, 6, 1),
        preferred_method=PreferredMethod.video,
        goal_track="ml",
        goal_track_weights={"ml": 1.0, "cv": 0.0, "nlp": 0.0, "genai": 0.0},
    )

    updated = await update_onboarding(db, user, body)
    assert updated.goal_track == "ml"
    assert updated.goal_track_weights["ml"] == 1.0
```

- [ ] **Step 2: Run the onboarding tests**

Run: `pytest tests/test_user_skill_overview.py tests/contract/test_course_start_api.py -k onboarding -v`
Expected: FAIL because the request and model do not expose planner goal fields.

- [ ] **Step 3: Extend the onboarding contract and persistence**

```python
class OnboardingRequest(BaseModel):
    known_topic_ids: list[uuid.UUID] = Field(default_factory=list)
    desired_module_ids: list[uuid.UUID] = Field(default_factory=list)
    available_hours_per_week: float = Field(gt=0, le=168)
    target_deadline: date
    preferred_method: PreferredMethod
    goal_track: str | None = None
    goal_track_weights: dict[str, float] = Field(default_factory=dict)
```

```python
user.goal_track = data.goal_track
user.goal_track_weights = data.goal_track_weights
user.selected_module_ids = [str(item) for item in data.desired_module_ids]
```

- [ ] **Step 4: Add goal centroid computation as a separate service**

```python
async def compute_goal_embedding_centroid(selected_course_summaries: list[str]) -> list[float]:
    if not selected_course_summaries:
        return [0.0] * 768
    try:
        return _average_vectors(embed_many(selected_course_summaries))
    except Exception:
        return [0.0] * 768
```

Planner rule for this step:
- `goal_onehot` is the real blocker for planner core.
- `goal_embedding` may fall back to a zero vector or cached centroid in the first rollout.
- Do not block planner core on production-grade embedding quality.

Run: `pytest tests/test_user_skill_overview.py tests/contract/test_course_start_api.py -k onboarding -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/models/user.py src/services/auth_service.py src/schemas/auth.py src/services/goal_embedding_service.py frontend/app/onboarding/page.tsx tests/test_user_skill_overview.py tests/contract/test_course_start_api.py
git commit -m "feat: persist planner goal profile from onboarding"
```

### Task 3: Implement Planner Core v2.1 Minimal Slice

**Files:**
- Create: `src/schemas/planner.py`
- Create: `src/services/planner_v2.py`
- Modify: `src/kg/service.py`
- Test: `tests/services/test_planner_v2.py`
- Test: `tests/kg/test_service_recsys.py`

- [ ] **Step 1: Write the failing minimal planner behavior tests**

```python
async def test_plan_sends_high_mastery_units_to_skippable(service, planner_context):
    result = await service.plan(planner_context, horizon=10)
    assert result.skippable_units[0].unit_id == planner_context.skip_candidate_id

async def test_forward_frontier_filters_hard_prereq_violations(service, planner_context):
    result = await service.plan(planner_context, horizon=10)
    assert result.filtered_out[0].reason == "prereq_violation_hard"
    assert all(item.frontier_type == "forward" for item in result.recommended_path)
```

- [ ] **Step 2: Run the new service tests**

Run: `pytest tests/services/test_planner_v2.py tests/kg/test_service_recsys.py -v`
Expected: FAIL because `planner_v2.py` and the new result schema do not exist.

- [ ] **Step 3: Implement only the minimal core**

```python
def mastery_lcb(mu: float, sigma: float, lambda_lcb: float = 1.0) -> float:
    z = (mu - lambda_lcb * sigma) / math.sqrt(1.0 + sigma * sigma)
    return float(NormalDist().cdf(z))
```

```python
async def plan(self, ctx: PlannerContext, horizon: int = 10) -> PlannerResult:
    forward = build_forward_frontier(ctx, horizon * 3)
    feasible_forward, filtered_out = check_hard_constraints(forward, ctx)
    scored = score_forward_frontier(ctx, feasible_forward)
    return assemble_result(ctx, scored, filtered_out, horizon)
```

- [ ] **Step 4: Reuse KG service as the orchestration boundary**

```python
async def rank_next(...):
    planner = PlannerV2(self.mastery, self.repo)
    result = await planner.plan(...)
    return [candidate.to_ranked_candidate() for candidate in result.recommended_path]
```

Run: `pytest tests/services/test_planner_v2.py tests/kg/test_service_recsys.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/schemas/planner.py src/services/planner_v2.py src/kg/service.py tests/services/test_planner_v2.py tests/kg/test_service_recsys.py
git commit -m "feat: implement planner v2 minimal core"
```

### Task 4: Implement Review, Bridge, MMR, And Budget Enforcement

**Files:**
- Modify: `src/services/planner_v2.py`
- Modify: `src/kg/service.py`
- Test: `tests/services/test_planner_v2.py`
- Test: `tests/services/test_planner_metrics.py`

- [ ] **Step 1: Write the failing advanced planner tests**

```python
async def test_plan_uses_bridge_when_forward_frontier_is_empty(service, planner_context):
    result = await service.plan(planner_context, horizon=10)
    assert result.recommended_path[0].frontier_type == "bridge"

async def test_frontier_budget_caps_review_and_bridge(service, planner_context):
    result = await service.plan(planner_context, horizon=10)
    assert len([x for x in result.recommended_path if x.frontier_type == "review"]) <= 2
```

- [ ] **Step 2: Run the advanced planner tests**

Run: `pytest tests/services/test_planner_v2.py tests/services/test_planner_metrics.py -k "bridge or frontier_budget or mmr" -v`
Expected: FAIL because review frontier, bridge frontier, MMR, and budget enforcement are not implemented.

- [ ] **Step 3: Add advanced frontier behaviors incrementally**

```python
review = build_review_frontier(ctx)
bridge = build_bridge_frontier(ctx, filtered_out) if not feasible_forward else []
reranked = mmr_rerank_scoped(scored_by_frontier, beta=0.7)
path = enforce_frontier_budget(reranked, horizon=horizon, max_review=2, max_bridge_consecutive=2)
```

- [ ] **Step 4: Verify bridge fallback and scoped rerank**

Run: `pytest tests/services/test_planner_v2.py tests/services/test_planner_metrics.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/services/planner_v2.py src/kg/service.py tests/services/test_planner_v2.py tests/services/test_planner_metrics.py
git commit -m "feat: add advanced planner frontier behaviors"
```

### Task 5: Roll Out The New Learning-Path API Behind A Version Or Flag

**Files:**
- Modify: `src/schemas/learning_path.py`
- Modify: `src/routers/learning_path.py`
- Modify: `src/services/recommendation_engine.py`
- Modify: `src/config.py`
- Test: `tests/contract/test_learning_path_planner_api.py`

- [ ] **Step 1: Write the failing versioned API contract tests**

```python
async def test_generate_learning_path_v2_returns_tripartite_payload(client, auth_headers):
    response = await client.post("/api/learning-path/generate?v=2", json={"desired_module_ids": []}, headers=auth_headers)
    assert response.status_code == 201
    payload = response.json()
    assert "recommended_path" in payload
    assert "skippable_units" in payload
    assert "filtered_out" in payload

async def test_generate_learning_path_v1_still_returns_legacy_shape(client, auth_headers):
    response = await client.post("/api/learning-path/generate", json={"desired_module_ids": []}, headers=auth_headers)
    assert response.status_code == 201
```

- [ ] **Step 2: Run the contract test**

Run: `pytest tests/contract/test_learning_path_planner_api.py -v`
Expected: FAIL because the router does not support versioned rollout yet.

- [ ] **Step 3: Replace the response schema with the planner contract**

```python
class PlannerPathItem(BaseModel):
    rank: int
    unit_id: uuid.UUID
    decision_type: Literal["learn", "skim", "review"]
    frontier_type: Literal["forward", "review", "bridge"]
    priority_score: float
    confidence: Literal["low", "medium", "high"]
    rationale_json: dict[str, Any]
```

```python
class GeneratePathResponse(BaseModel):
    recommended_path: list[PlannerPathItem] = Field(default_factory=list)
    skippable_units: list[PlannerSkipItem] = Field(default_factory=list)
    filtered_out: list[PlannerFilteredItem] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
```

- [ ] **Step 4: Add rollout control instead of a hard swap**

```python
@learning_path_router.post("/generate")
async def api_generate_learning_path(..., v: int | None = Query(default=None)):
    if v == 2 or settings.use_planner_v2:
        return await generate_learning_path_v2(...)
    return await generate_learning_path_v1(...)
```

Run: `pytest tests/contract/test_learning_path_planner_api.py tests/kg/test_router_kg.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/schemas/learning_path.py src/routers/learning_path.py src/services/recommendation_engine.py src/config.py tests/contract/test_learning_path_planner_api.py
git commit -m "feat: add versioned rollout for planner v2 api"
```

### Task 6: Integrate Re-Plan Triggers And Skip Auditing

**Files:**
- Modify: `src/services/assessment_service.py`
- Modify: `src/services/quiz_service.py`
- Modify: `src/models/learning.py`
- Modify: `src/repositories/planner_repo.py`
- Test: `tests/test_assessment_question_selector_integration.py`
- Test: `tests/services/test_question_selector.py`

- [ ] **Step 1: Write the failing integration tests**

```python
async def test_quiz_completion_can_trigger_replan_when_mastery_changes(app_client, seeded_user):
    response = await complete_quiz_and_fetch_result(...)
    assert response["learning_path_updated"] is True
```

```python
async def test_confirm_skip_creates_waived_unit_not_completed_unit(repo, seeded_user, seeded_unit):
    await repo.save_waived_unit(seeded_user.id, seeded_unit.id, ["item_21"], 0.82)
    assert seeded_unit.id in await repo._load_waived_units(seeded_user.id)
    assert seeded_unit.id not in await repo._load_completed_units(seeded_user.id)
```

- [ ] **Step 2: Run the affected integration tests**

Run: `pytest tests/test_assessment_question_selector_integration.py tests/services/test_question_selector.py -v`
Expected: FAIL because re-plan triggers and skip audit persistence are missing.

- [ ] **Step 3: Add planner callbacks and skip persistence**

```python
await planner_repo.save_waived_unit(
    user_id=user_id,
    learning_unit_id=unit_id,
    evidence_items=evidence_items,
    mastery_lcb=mastery_lcb_value,
)
```

```python
if mastery_changed_significantly:
    planner_result = await planner_service.plan_for_user(user.id, desired_module_ids)
```

- [ ] **Step 4: Verify planner state changes do not mutate completed-unit semantics**

Run: `pytest tests/test_assessment_question_selector_integration.py tests/services/test_question_selector.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/services/assessment_service.py src/services/quiz_service.py src/models/learning.py src/repositories/planner_repo.py tests/test_assessment_question_selector_integration.py tests/services/test_question_selector.py
git commit -m "feat: integrate planner replans and waived-unit auditing"
```

### Task 7: Adapt The Frontend To The New Planner Output

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/types/index.ts`
- Create: `frontend/tests/routes/learning/planner-path.test.tsx`
- Modify: `frontend/app/(protected)/dashboard/page.tsx`
- Modify: `frontend/components/course/CourseOverviewInteractive.tsx`

- [ ] **Step 1: Write the failing frontend contract test**

```tsx
it("renders recommended path, skippable units, and bridge warnings", async () => {
  render(<DashboardPlannerPanel data={mockPlannerResponse} />);
  expect(screen.getByText("Recommended path")).toBeInTheDocument();
  expect(screen.getByText("Skippable units")).toBeInTheDocument();
  expect(screen.getByText(/foundation module/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the frontend test**

Run: `npm --prefix frontend test -- planner-path.test.tsx`
Expected: FAIL because the client types and UI assume the old `items[]` contract.

- [ ] **Step 3: Update the shared frontend types**

```ts
export interface PlannerPathItem {
  rank: number;
  unit_id: string;
  decision_type: "learn" | "skim" | "review";
  frontier_type: "forward" | "review" | "bridge";
  priority_score: number;
  confidence: "low" | "medium" | "high";
  rationale_json: Record<string, unknown>;
}
```

- [ ] **Step 4: Render the new planner sections without blocking the current course flow**

Run: `npm --prefix frontend test -- planner-path.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/api.ts frontend/types/index.ts frontend/tests/routes/learning/planner-path.test.tsx frontend/app/(protected)/dashboard/page.tsx frontend/components/course/CourseOverviewInteractive.tsx
git commit -m "feat: render planner v2 path states in frontend"
```

### Task 8: Add Evaluation, Churn Metrics, And Guardrail Tests

**Files:**
- Modify: `src/services/planner_v2.py`
- Create: `tests/services/test_planner_metrics.py`
- Create: `tests/kg/test_planner_churn.py`
- Modify: `specs/001-course-first-refactor/quickstart.md`

- [ ] **Step 1: Write the failing metric tests**

```python
def test_overlap_at_k_matches_expected_value():
    assert overlap_at_k(["a", "b", "c"], ["b", "c", "d"], 3) == 2 / 3

def test_bridge_budget_caps_bridge_steps():
    result = enforce_frontier_budget(...)
    assert len([x for x in result.path if x.frontier_type == "bridge"]) <= 2
```

- [ ] **Step 2: Run the metric suite**

Run: `pytest tests/services/test_planner_metrics.py tests/kg/test_planner_churn.py -v`
Expected: FAIL because the metric helpers and bridge budget assertions are not implemented.

- [ ] **Step 3: Implement the metrics next to the planner, not in the router**

```python
def overlap_at_k(previous: list[str], current: list[str], k: int) -> float:
    prev = set(previous[:k])
    curr = set(current[:k])
    return len(prev & curr) / max(1, k)
```

- [ ] **Step 4: Record validation commands in quickstart**

Run: `pytest tests/services/test_planner_metrics.py tests/kg/test_planner_churn.py tests/services/test_planner_v2.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/services/planner_v2.py tests/services/test_planner_metrics.py tests/kg/test_planner_churn.py specs/001-course-first-refactor/quickstart.md
git commit -m "test: add planner v2 guardrail and churn coverage"
```

## Dependency Order

1. Task 1a must land before everything else because the planner needs posterior state and waived-unit semantics first.
2. Task 1b depends on Task 1a and explicitly resolves the canonical source-of-truth drift before planner code spreads further.
3. Task 2 should land before Task 3, but `goal_embedding` quality is not a blocker as long as the fallback path exists.
4. Task 3 unlocks Task 4.
5. Task 4 unlocks Task 5 and Task 8.
6. Task 5 should land before Task 7 so the frontend can target the rollout-safe API contract.
7. Task 6 can start after Task 5, but should merge before final rollout so replans and waive semantics are consistent.
8. Task 8 should be the last backend-focused slice before broad validation.

## Recommended Execution Order

### Phase A: Foundation
- Task 1a
- Task 1b
- Task 2

### Phase B: Planner Core
- Task 3
- Task 4

### Phase C: Rollout
- Task 5

### Phase D: Integration
- Task 6
- Task 7

### Phase E: Hardening
- Task 8

## Risks To Watch During Execution

- `src/kg/providers.py` currently reads from `user_mastery` and `user_responses`, while the rest of the app uses `mastery_scores`, `interactions`, and `sessions`. This is no longer just a note; Task 1b must fix the source-of-truth drift before planner rollout.
- `src/services/recommendation_engine.py` and `src/kg/service.py` overlap conceptually. Do not maintain two independent planners after Task 5; keep one real engine and one thin compatibility layer at most.
- The repo currently mixes topic-first and course-unit-first flows. Do not convert the planner to `unit_id` output without also adding explicit unit-KC coverage data.
- Goal embeddings are easy to overbuild. Keep the first slice deterministic and cacheable; do not introduce online LLM calls into runtime planning, and do not let embedding quality block Task 3.

## Spec Coverage Check

- Stage 0 frontier generation: covered by Tasks 3 and 4.
- Hard/soft constraints and `mastery_lcb`: covered by Tasks 1a, 1b, 3, and 4.
- `waived_units` separate from `completed_units`: covered by Tasks 1a and 6.
- New tripartite API output: covered by Task 5.
- Goal centroid embedding: covered by Task 2.
- Re-plan, bridge guard, churn metrics: covered by Tasks 6 and 8.
- UI support for `skippable_units` and warnings: covered by Task 7.

Plan complete and saved to `docs/superpowers/plans/2026-04-20-prereq-aware-planner-v2.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
