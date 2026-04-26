# Cross-Track Onboarding Build Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Replace the current course-first onboarding with a `primary track + supporting track + goal + self-level` flow, drive assessment selection through a blueprint layer instead of frontend-expanded unit lists, and generate a cross-track multi-course / multi-unit learning path after assessment.

**Architecture:** Keep the current canonical runtime tables and question selection path, but insert three new layers on top of them: `onboarding profile v2`, `assessment blueprint resolution`, and `path assembly from readiness signals`. Do not rip out `selected_course_ids` in one shot. During rollout, keep writing a backward-compatible seed course list into `goal_preferences.selected_course_ids` while new services read richer v2 profile data from JSON fields.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Pydantic v2, PostgreSQL JSON fields, Next.js 14 App Router, React 18, TypeScript 5, Zustand, Axios, pytest, Vitest.

---

## Why This Matches The Current Codebase

- The current onboarding page in `frontend/app/onboarding/page.tsx` is the only place that creates assessment scope. Today it expands `selected_course_ids` into large `canonicalUnitIds` via `frontend/lib/canonical-assessment-session.ts`.
- The current backend already has a stable canonical assessment runtime in `src/services/assessment_service.py`, `src/services/canonical_question_selector.py`, and `src/repositories/canonical_question_repo.py`.
- The current planner in `src/services/recommendation_engine.py` is still course-first because it reads `goal_preferences.selected_course_ids`.
- `GoalPreference` in `src/models/learning.py` already has JSON fields. That lets us ship v2 profile data without a mandatory schema migration in phase 1.
- `course_entry_service.py` gates on `user.is_onboarded` plus “has at least one assessment session”. That means we should not block the rollout on a new user-state model unless product explicitly wants it.

## Shared Decisions

- Keep `/api/assessment/start` as the main entry point, but add a new blueprint-driven request shape instead of requiring frontend-supplied `canonical_unit_ids`.
- Keep the existing canonical question bank and selector. Blueprint logic chooses pools; selector still chooses items.
- Do not make assessment adaptive in phase 1. Phase 1 is deterministic blueprint resolution plus weighted question mix.
- Do not delete course-first fields in phase 1. Write compatibility data until planner v2 is complete.
- Treat `is_onboarded` pragmatically:
  - set it once pre-assessment intent is captured
  - do not block learning on post-assessment constraints
  - if schedule/method is missing, planner falls back to defaults and UI can prompt later
- Store v2 onboarding profile in `goal_preferences.goal_weights_json` and `goal_preferences.notes` first. Add typed DB columns only if the JSON contract becomes unstable.

## Implementation Surface

**Backend surfaces**
- `src/schemas/auth.py`
- `src/routers/users.py` or the existing router that serves `PUT /api/users/me/onboarding`
- `src/services/auth_service.py`
- `src/repositories/goal_preference_repo.py`
- `src/schemas/assessment.py`
- `src/routers/assessment.py`
- `src/services/assessment_service.py`
- `src/services/canonical_question_selector.py`
- `src/repositories/canonical_question_repo.py`
- `src/schemas/learning_path.py`
- `src/routers/learning_path.py`
- `src/services/recommendation_engine.py`
- `src/services/course_entry_service.py`
- `src/models/learning.py` only if later phases need typed persistence
- New: `src/schemas/onboarding_v2.py` or extend `src/schemas/auth.py`
- New: `src/services/assessment_blueprint_service.py`
- New: `src/services/learning_path_profile_service.py`
- New: `src/services/track_taxonomy_service.py`

**Frontend surfaces**
- `frontend/app/onboarding/page.tsx`
- `frontend/components/onboarding/StepKnownUnits.tsx`
- `frontend/components/onboarding/StepDesiredSections.tsx`
- `frontend/components/onboarding/StepTimeSchedule.tsx`
- `frontend/components/onboarding/StepLearningMethod.tsx`
- `frontend/lib/onboarding-schema.ts`
- `frontend/lib/api.ts`
- `frontend/lib/canonical-assessment-session.ts`
- `frontend/app/assessment/page.tsx`
- `frontend/app/assessment/results/page.tsx`
- `frontend/types/index.ts`
- `frontend/stores/authStore.ts`
- New: `frontend/components/onboarding/StepPrimaryTrack.tsx`
- New: `frontend/components/onboarding/StepSupportingTrack.tsx`
- New: `frontend/components/onboarding/StepGoalSelection.tsx`
- New: `frontend/components/onboarding/StepSelfLevel.tsx`
- New: `frontend/app/onboarding/constraints/page.tsx` if constraints are split into a separate page

**Config / content surfaces**
- New: `data/bootstrap/tracks.json`
- New: `data/bootstrap/learning_goals.json`
- New: `data/bootstrap/assessment_blueprints.json`

**Test surfaces**
- `tests/services/test_auth_service_cutover.py`
- `tests/services/test_assessment_canonical_cutover.py`
- `tests/services/test_assessment_canonical_mastery_cutover.py`
- `tests/repositories/test_goal_preference_repo.py`
- `tests/services/test_recommendation_engine.py` or a new dedicated file
- New: `tests/services/test_assessment_blueprint_service.py`
- New: `tests/contract/test_onboarding_v2_routes.py`
- New: `tests/contract/test_assessment_blueprint_routes.py`
- New: `tests/contract/test_learning_path_v2_routes.py`
- `frontend/tests/routes/onboarding/*.test.tsx`
- `frontend/tests/routes/assessment/*.test.tsx`

## Target V2 Contracts

### Onboarding intent payload

Use a new request shape instead of overloading course-first meanings:

```ts
type OnboardingIntentPayload = {
  primary_track_slug: string;
  supporting_track_slug?: string | null;
  learning_goal_slug: string;
  self_level_band: "beginner" | "intermediate" | "advanced" | "not_sure";
};
```

### Onboarding constraints payload

```ts
type OnboardingConstraintsPayload = {
  available_hours_per_week: number;
  target_deadline?: string | null;
  preferred_method?: "reading" | "video" | null;
  pace_preference?: "balanced" | "accelerated" | "steady";
};
```

### Assessment start payload

Frontend should stop sending expanded unit lists by default:

```ts
type AssessmentStartPayloadV2 = {
  primary_track_slug: string;
  supporting_track_slug?: string | null;
  learning_goal_slug: string;
  self_level_band: "beginner" | "intermediate" | "advanced" | "not_sure";
  phase?: "placement";
};
```

### Assessment result additions

Keep `overall_score_percent`, but add readiness signals needed by the planner:

```ts
type AssessmentResultSummaryV2 = {
  primary_track_score: number;
  supporting_track_score?: number | null;
  foundation_readiness: "low" | "medium" | "high";
  bridge_readiness: "low" | "medium" | "high";
  recommended_entry_band: "foundation" | "bridge" | "core" | "advanced";
  weak_kp_ids: string[];
};
```

## Phase 1: Introduce V2 Onboarding Profile Without Breaking Existing Flow

**Purpose:** Capture the new product intent and keep writing compatibility data for the current planner.

**Files**
- Modify: `src/schemas/auth.py`
- Modify: `src/services/auth_service.py`
- Modify: `src/repositories/goal_preference_repo.py`
- Modify: `frontend/types/index.ts`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/stores/authStore.ts`
- Create or extend: `tests/contract/test_onboarding_v2_routes.py`
- Extend: `tests/services/test_auth_service_cutover.py`

**Functions to add or change**
- `src/schemas/auth.py`
  - add `OnboardingIntentRequest`
  - add `OnboardingConstraintsRequest`
  - keep `OnboardingRequest` as legacy compatibility wrapper during rollout
- `src/services/auth_service.py`
  - add `update_onboarding_intent(db, user, data) -> User`
  - add `update_onboarding_constraints(db, user, data) -> User`
  - add `_build_goal_preference_v2_snapshot(...) -> dict`
  - add `_derive_compat_selected_course_ids(primary_track_slug, supporting_track_slug) -> list[str]`
- `src/repositories/goal_preference_repo.py`
  - keep `upsert_for_user`
  - add `get_profile_snapshot_for_user(user_id) -> dict | None` helper if repeated parsing becomes noisy
- `frontend/lib/api.ts`
  - add `authApi.onboardingIntent(...)`
  - add `authApi.onboardingConstraints(...)`
- `frontend/types/index.ts`
  - add `OnboardingIntentPayload`
  - add `OnboardingConstraintsPayload`

**Notes**
- Write v2 profile into `goal_preferences.goal_weights_json` and `goal_preferences.notes`.
- Continue populating `goal_preferences.selected_course_ids` with a derived seed list so `recommendation_engine.py` does not break before phase 4.
- Keep `user.available_hours_per_week`, `target_deadline`, and `preferred_method` nullable.

## Phase 2: Replace Course-First Onboarding UI With Track-First Intent Capture

**Purpose:** Change the user-facing flow without yet changing planner logic.

**Files**
- Modify: `frontend/app/onboarding/page.tsx`
- Modify: `frontend/lib/onboarding-schema.ts`
- Modify: `frontend/lib/canonical-assessment-session.ts`
- Create: `frontend/components/onboarding/StepPrimaryTrack.tsx`
- Create: `frontend/components/onboarding/StepSupportingTrack.tsx`
- Create: `frontend/components/onboarding/StepGoalSelection.tsx`
- Create: `frontend/components/onboarding/StepSelfLevel.tsx`
- Create: `data/bootstrap/tracks.json`
- Create: `data/bootstrap/learning_goals.json`

**Functions to add or change**
- `frontend/lib/onboarding-schema.ts`
  - replace `selected_course_ids` requirement with `primary_track_slug`, `learning_goal_slug`, `self_level_band`
  - make `supporting_track_slug` optional and disallow equality with `primary_track_slug`
- `frontend/app/onboarding/page.tsx`
  - replace current steps array
  - submit `authApi.onboardingIntent(...)`
  - store pending assessment intent instead of `canonicalUnitIds`
- `frontend/lib/canonical-assessment-session.ts`
  - replace `buildCanonicalAssessmentContext(...)` with `buildPendingAssessmentIntent(...)`
  - replace local-storage shape `{ canonicalUnitIds, unitNameMap }` with `{ primary_track_slug, supporting_track_slug, learning_goal_slug, self_level_band }`

**Notes**
- Delete the UX meaning of `known topics` in onboarding. That information is now inferred through self-level + assessment.
- Do not ask for schedule in this page anymore.
- Keep a compatibility reader in `readPendingCanonicalAssessment()` for one release so stale browser storage does not white-screen the assessment page.

## Phase 3: Add Blueprint Resolution Layer On Top Of The Existing Canonical Question Bank

**Purpose:** Move assessment scoping server-side and stop exploding course choices into 100+ unit IDs in the browser.

**Files**
- Create: `src/services/assessment_blueprint_service.py`
- Create: `src/services/track_taxonomy_service.py`
- Modify: `src/schemas/assessment.py`
- Modify: `src/services/assessment_service.py`
- Create: `data/bootstrap/assessment_blueprints.json`
- Create: `tests/services/test_assessment_blueprint_service.py`
- Create: `tests/contract/test_assessment_blueprint_routes.py`

**Functions to add or change**
- `src/services/track_taxonomy_service.py`
  - `load_track_taxonomy() -> TrackTaxonomy`
  - `resolve_track_seed_courses(primary_track_slug, supporting_track_slug) -> list[str]`
  - `resolve_blueprint_units(blueprint) -> AssessmentUnitPool`
- `src/services/assessment_blueprint_service.py`
  - `load_assessment_blueprints() -> list[AssessmentBlueprint]`
  - `resolve_assessment_blueprint(primary_track_slug, supporting_track_slug, learning_goal_slug, self_level_band, phase="placement") -> AssessmentBlueprint`
  - `expand_blueprint_scope(db, blueprint) -> ExpandedAssessmentScope`
  - `build_question_mix(scope, blueprint) -> BlueprintQuestionRequest`
- `src/schemas/assessment.py`
  - extend `AssessmentStartRequest` with v2 onboarding fields
  - keep `canonical_unit_ids` as deprecated fallback
- `src/services/assessment_service.py`
  - add `_resolve_assessment_start_scope(db, request) -> ExpandedAssessmentScope`
  - keep `_resolve_canonical_unit_ids()` only for legacy callers

**Notes**
- Blueprint JSON should reference canonical units or KP pools, not frontend course cards.
- Fallback order for blueprint resolution:
  - exact match
  - same primary + goal, drop supporting track
  - same primary only
  - hard default for primary track
- This phase is where the current `139 items` validation failure disappears, because the backend now controls pool size before selection.

## Phase 4: Refactor Assessment Runtime To Emit Readiness Signals, Not Just Per-Unit Scores

**Purpose:** Keep the canonical selector, but change the session start and result contracts so the planner can consume them.

**Files**
- Modify: `src/services/assessment_service.py`
- Modify: `src/repositories/canonical_question_repo.py`
- Modify: `src/services/canonical_question_selector.py`
- Modify: `src/schemas/assessment.py`
- Modify: `frontend/app/assessment/page.tsx`
- Modify: `frontend/types/index.ts`
- Extend: `tests/services/test_assessment_canonical_cutover.py`
- Extend: `tests/services/test_assessment_canonical_mastery_cutover.py`

**Functions to add or change**
- `src/services/assessment_service.py`
  - `start_assessment(...)` should accept v2 scope and call blueprint resolver
  - add `_select_questions_for_blueprint_scope(db, scope, blueprint) -> list[QuestionBankItem]`
  - add `_build_assessment_summary_v2(...) -> dict`
  - extend `_build_canonical_assessment_response(...)` to include:
    - `primary_track_score`
    - `supporting_track_score`
    - `foundation_readiness`
    - `bridge_readiness`
    - `recommended_entry_band`
- `src/repositories/canonical_question_repo.py`
  - add optional filters for `difficulty_bucket`, `exclude_item_ids`, and scoped unit/KP pools if selector cannot already express them cleanly
- `src/services/canonical_question_selector.py`
  - accept blueprint-driven mix instructions instead of only raw `canonical_unit_ids`
- `frontend/app/assessment/page.tsx`
  - call `canonicalAssessmentApi.start()` with pending intent payload
  - stop expecting a local `unitNameMap` built in onboarding

**Notes**
- Do not remove `learning_unit_results`; keep them for results UI and backward compatibility.
- Readiness fields should be computed from grouped canonical unit / KP outcomes, not from self-reported level.
- Persist blueprint metadata into session fields or planner audit state if later phases need explainability.

## Phase 5: Build Planner V2 That Uses Profile + Assessment Results Instead Of `selected_course_ids`

**Purpose:** Make the system actually recommend a multi-course, cross-track learning path for the user rather than replaying preselected courses.

**Files**
- Modify: `src/schemas/learning_path.py`
- Modify: `src/routers/learning_path.py`
- Modify: `src/services/recommendation_engine.py`
- Create: `src/services/learning_path_profile_service.py`
- Extend: `tests/repositories/test_goal_preference_repo.py`
- Create: `tests/services/test_learning_path_profile_service.py`
- Create or extend: `tests/services/test_recommendation_engine_v2.py`
- Create: `tests/contract/test_learning_path_v2_routes.py`

**Functions to add or change**
- `src/services/learning_path_profile_service.py`
  - `load_learning_path_profile(db, user_id) -> LearningPathProfile`
  - `load_latest_assessment_readiness(db, user_id) -> AssessmentReadinessSnapshot`
  - `derive_path_constraints(user, profile) -> PathConstraintSnapshot`
- `src/services/recommendation_engine.py`
  - keep `generate_learning_path(...)` as public entry point
  - add `_generate_cross_track_learning_path(db, user, request) -> GeneratePathResponse`
  - add `_build_primary_spine_units(profile, content_repo) -> list[LearningUnit]`
  - add `_build_bridge_units(profile, readiness, content_repo) -> list[LearningUnit]`
  - add `_apply_readiness_actions(units, readiness) -> list[PathCandidate]`
  - add `_apply_constraints_and_schedule(candidates, constraints) -> list[PathItemResponse]`
  - add `_build_path_explanations(profile, readiness, items) -> list[str]`
- `src/schemas/learning_path.py`
  - make `GeneratePathRequest` optional or add `assessment_session_id`
  - extend responses with path explanation and profile metadata if needed by frontend

**Notes**
- `primary_track` defines the main spine.
- `supporting_track` only authorizes bridge units and supporting courses.
- `learning_goal` changes ranking weights:
  - `foundation` should bias foundational units
  - `build-project` should bias applied bridge units earlier
  - `research` should bias depth and theory later in the path
- Until planner v2 is fully verified, keep a feature flag or fallback path that still uses compatibility `selected_course_ids`.

## Phase 6: Add Post-Assessment Constraints Capture And Recommendation UI

**Purpose:** Complete the intended product flow: intent -> assessment -> constraints -> learning path.

**Files**
- Create: `frontend/app/onboarding/constraints/page.tsx`
- Modify: `frontend/app/assessment/results/page.tsx`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/types/index.ts`
- Modify: `frontend/app/(protected)/dashboard/page.tsx` or the route that first shows the generated path
- Create or extend frontend tests around assessment results and dashboard path display

**Functions to add or change**
- `frontend/app/assessment/results/page.tsx`
  - add CTA logic:
    - if constraints missing -> go to `/onboarding/constraints`
    - else -> generate path
- `frontend/app/onboarding/constraints/page.tsx`
  - submit `authApi.onboardingConstraints(...)`
- `frontend/lib/api.ts`
  - add `learningPathApi.generate(...)` wrapper if one does not already exist
- `frontend/types/index.ts`
  - add `AssessmentResultSummaryV2`
  - add path explanation types if planner returns them

**Notes**
- This is where the user finally sees why the path contains both primary and supporting track content.
- Path UI should explicitly label:
  - `core`
  - `bridge`
  - `skip`
  - `deep practice`
- Show a short explanation sentence tied to the assessment result instead of a generic recommendation banner.

## Phase 7: Cleanup, Cutover, And Legacy Removal

**Purpose:** Remove the temporary compatibility logic once v2 is stable.

**Files**
- Revisit all earlier surfaces
- Add migration only if typed persistence is still needed

**Cleanup items**
- remove legacy onboarding step components no longer used
- remove `selected_course_ids` from frontend onboarding types
- deprecate frontend code that expands assessment unit lists in the browser
- remove planner fallback to compatibility course seeds
- if stable, move v2 profile fields from JSON blobs to typed DB columns and write an Alembic migration

## Verification Plan By Phase

- **Phase 1**
  - `uv run pytest tests/services/test_auth_service_cutover.py tests/contract/test_onboarding_v2_routes.py -q`
- **Phase 2**
  - `npm test -- --run tests/routes/onboarding`
- **Phase 3**
  - `uv run pytest tests/services/test_assessment_blueprint_service.py tests/contract/test_assessment_blueprint_routes.py -q`
- **Phase 4**
  - `uv run pytest tests/services/test_assessment_canonical_cutover.py tests/services/test_assessment_canonical_mastery_cutover.py -q`
- **Phase 5**
  - `uv run pytest tests/services/test_recommendation_engine_v2.py tests/contract/test_learning_path_v2_routes.py -q`
- **Phase 6**
  - `npm test -- --run tests/routes/assessment tests/routes/dashboard`

## Recommended Build Order

1. Phase 1 first. Without v2 profile persistence, every later step will rely on temporary local state.
2. Phase 2 next. Change the UI only after the backend can accept the new intent.
3. Phase 3 and Phase 4 together. They remove the current “frontend builds huge unit list” failure mode.
4. Phase 5 next. This is the real value layer; until it exists, cross-track onboarding is just a nicer form.
5. Phase 6 after planner v2 is stable. Constraints are only useful once the path can consume them.
6. Phase 7 last, after one release cycle or after feature-flag validation.

## Main Risks

- If track taxonomy is weak, blueprint resolution will feel arbitrary. Fix taxonomy at the unit/KP layer before overfitting selectors.
- If planner v2 keeps reading only `selected_course_ids`, the new onboarding will look smarter than it really is.
- If `is_onboarded` semantics are changed too aggressively, `/courses/[slug]/start` can regress. Keep the current gate semantics until the new flow is fully exercised.
- If readiness output stays too coarse, cross-track path generation will be hard to explain and harder to trust.

## Definition Of Done

- User no longer chooses courses before assessment.
- `/api/assessment/start` can start from `primary track + supporting track + goal + self-level` without frontend-expanded unit lists.
- Assessment results include planner-usable readiness signals.
- Learning path generation uses v2 onboarding profile plus assessment output, not only `selected_course_ids`.
- Generated path can include primary-track spine units and supporting-track bridge units with explicit rationale.
