# Visualize: Learning Path Roadmap UI — Implementation Plan

**Created:** 2026-04-25  
**Revised:** 2026-04-25 after codebase review  
**Skill template:** `gsd-plan-phase`  
**Sources:** `SPEC.md` (7 requirements locked) + `RESEARCH.md`  
**Scope:** Phase 1 MVP — graph + timeline UI using existing backend endpoints only.

---

## 0. Execution Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | Use `reactflow` + `@dagrejs/dagre` | Fastest path to interactive graph + auto-layout. |
| D2 | No new backend endpoint in Phase 1 | Existing `GET /api/learning-path` and `/timeline` are enough for MVP. |
| D3 | Edges are sequential by global `order_index` | Backend does not expose real prerequisite edges yet. |
| D4 | Topic node = `section_title`; Subtopic node = `PathItemResponse` learning unit | Only section information currently available is `section_title`. |
| D5 | Topic keys are derived from first-seen section title + stable index | `section_id` is not exposed; avoid assuming titles are globally unique. |
| D6 | Timeline renders backend truth | If backend returns all Week 1, UI shows Week 1 and does not fake allocation. |
| D7 | Drawer lazy-fetches content via existing `learningUnitApi.contentById` | `PathItemResponse` lacks description. |
| D8 | Recommended-next = first pending non-skip item by global order | No `prereq_unit_ids`; do not infer prerequisites. |
| D9 | Replan is out of Phase 1 | Frontend cannot construct `desired_section_ids` from current user state. |
| D10 | Roadmap canvas is dynamically imported client-only | Protects SSR and route bundle size. |
| D11 | Use lightweight local toast/error components, no toast dependency | Avoid bundle creep. |

---

## 1. Target Architecture

```
frontend/
├── app/learn/page.tsx
├── features/learning-path/
│   ├── api.ts
│   ├── presenters.ts
│   ├── store.ts
│   ├── components/
│   │   ├── EmptyState.tsx
│   │   ├── LearningPathShell.tsx
│   │   ├── LearningUnitDrawer.tsx
│   │   ├── RoadmapCanvas.tsx
│   │   ├── TimelineBoard.tsx
│   │   ├── ViewToggle.tsx
│   │   ├── cards/
│   │   │   └── LearningUnitCard.tsx
│   │   └── nodes/
│   │       ├── SubtopicNode.tsx
│   │       └── TopicNode.tsx
│   └── lib/
│       ├── layout.ts
│       └── status.ts
└── tests/unit/learning-path/
    ├── presenters.test.ts
    └── status.test.ts
```

Notes:
- `LearningPathShell` owns client state, loads path, handles view selection, and renders Graph/Timeline.
- `RoadmapCanvas` must be dynamically loaded from `/learn/page.tsx` or inside shell with `next/dynamic({ ssr: false })`.
- Keep API wrappers close to existing `frontend/lib/api.ts` patterns.

---

## 2. Data Contracts

### Add frontend types
Add to `frontend/types/index.ts`:

```ts
export type PathAction = "skip" | "quick_review" | "standard_learn" | "deep_practice" | "remediate";
export type PathStatus = "pending" | "in_progress" | "completed" | "skipped";

export interface PathItemResponse {
  id: string;
  learning_unit_id: string;
  learning_unit_title: string;
  section_title: string | null;
  action: PathAction;
  estimated_hours: number | null;
  order_index: number;
  week_number: number | null;
  status: PathStatus;
  canonical_unit_id: string | null;
}

export interface LearningPathResponse {
  total_units: number;
  completed_units: number;
  in_progress_units: number;
  items: PathItemResponse[];
}

export interface WeekEntry {
  week: number;
  learning_units: PathItemResponse[];
  total_hours: number;
}

export interface TimelineResponse {
  total_weeks: number;
  items: WeekEntry[];
}
```

Do not add `description`, `section_id`, or `prereq_unit_ids` in Phase 1; they are not returned by backend.

---

## 3. Task Breakdown

### Wave 1 — Foundation

#### T1.1 Install dependencies
Command:

```bash
cd frontend && npm install reactflow @dagrejs/dagre
```

Verify:
- `frontend/package.json` has both dependencies.
- `npm run type-check` still starts cleanly after type work.

#### T1.2 Add learning path API wrapper
File: `frontend/features/learning-path/api.ts`

Functions:
- `getLearningPath(): Promise<LearningPathResponse>` → `GET /api/learning-path`
- `getTimeline(): Promise<TimelineResponse>` → `GET /api/learning-path/timeline`
- `updatePathStatus(pathId: string, status: PathStatus): Promise<UpdateStatusResponse>` → `PUT /api/learning-path/{path_id}/status`

Important:
- Do **not** implement `generatePath()` or `replan()` in Phase 1 UI.
- Use existing exported `api` from `frontend/lib/api.ts`.

Verify:
- TypeScript imports compile.

#### T1.3 Add frontend response types
File: `frontend/types/index.ts`

Add exact types from Section 2 plus:

```ts
export interface UpdateStatusResponse {
  id: string;
  learning_unit_id: string;
  status: PathStatus;
  updated_at: string;
}
```

Verify:
- `npm run type-check`.

#### T1.4 Add status helpers
File: `frontend/features/learning-path/lib/status.ts`

Functions:
- `getStatusLabel(status: PathStatus): string`
- `getStatusIconName(status: PathStatus): "circle" | "play" | "check" | "skip"`
- `getStatusClassName(status: PathStatus, isRecommended?: boolean): string`
- `isVisibleInTimeline(item: PathItemResponse): boolean` (`action !== "skip"`)

Verify:
- Unit test covers all 4 statuses.

---

### Wave 2 — Pure presenters

#### T2.1 `pathToFlow()`
File: `frontend/features/learning-path/presenters.ts`

Input: `PathItemResponse[]`.

Output:

```ts
type FlowModel = {
  nodes: Node[];
  edges: Edge[];
  sectionSummaries: SectionSummary[];
};
```

Rules:
- Sort items by `order_index` before processing.
- Build one Topic node per first-seen `section_title` bucket.
- Section key format: `section-${firstOrderIndex}-${slugifiedTitle}`.
- Build one Subtopic node per item with id `unit-${item.id}`.
- Add edge Topic → first Subtopic in that section.
- Add sequential edges between all unit nodes in global order.
- Do not create prerequisite edges.

Verify cases:
- Empty path.
- One section, one unit.
- One section, multiple units.
- Multiple sections.
- Duplicate section titles with separated first occurrence.
- Items unsorted input.

#### T2.2 `groupByWeek()`
Rules:
- Group items by `week_number ?? 1`.
- Exclude `action === "skip"`.
- Sort columns by week ascending.
- Sort units by `order_index`.
- Compute total hours.

Verify:
- Week 1 fallback when `week_number` is null.
- Skipped units excluded.
- Multiple weeks preserved when backend provides them.

#### T2.3 `computeRecommendedNext()`
Rules:
- Sort by `order_index`.
- Return first item with `status === "pending" && action !== "skip"`.
- Return `null` if none.

Verify:
- All pending → first item.
- Completed first item → second item.
- First item is skip → next non-skip pending.
- All completed → null.

#### T2.4 `autoLayout()`
File: `frontend/features/learning-path/lib/layout.ts`

Use dagre direction `TB`.

Verify:
- Returned nodes all have non-zero `position`.
- Layout function is deterministic for same input.

---

### Wave 3 — Store and state

#### T3.1 Add Zustand store
File: `frontend/features/learning-path/store.ts`

State:

```ts
{
  items: PathItemResponse[];
  timeline: TimelineResponse | null;
  loading: boolean;
  error: string | null;
  selectedItemId: string | null;
  selectedSectionKey: string | null;
  updatingStatusById: Record<string, boolean>;
}
```

Actions:
- `loadPath()` → fetch path and timeline in parallel.
- `selectItem(id)`.
- `selectSection(sectionKey)`.
- `closeDrawer()`.
- `updateStatus(pathId, status)` optimistic + revert.

No `replan()` action in Phase 1.

Verify:
- Unit test optimistic update and revert.

#### T3.2 Add view persistence hook
File can be `frontend/features/learning-path/components/ViewToggle.tsx` or separate hook.

Rules:
- Read URL first.
- Else LocalStorage.
- Else `window.matchMedia("(max-width: 767px)")` → timeline for mobile, graph for desktop.
- Write both URL and LocalStorage on toggle.

Verify:
- Manual and unit test if feasible.

---

### Wave 4 — UI components

#### T4.1 Nodes
Files:
- `TopicNode.tsx`
- `SubtopicNode.tsx`

Requirements:
- Topic = yellow-ish card, section title, count.
- Subtopic = purple-ish card, title, hours, status icon, recommended badge.
- `aria-label` on clickable nodes.

#### T4.2 `RoadmapCanvas`
File: `RoadmapCanvas.tsx`

Requirements:
- Client-only component with `ReactFlow`, `MiniMap`, `Controls`, `Background`.
- Uses `pathToFlow()`, `autoLayout()`, `computeRecommendedNext()`.
- Node click selects section or unit.
- Enable `onlyRenderVisibleElements` if available.

#### T4.3 `TimelineBoard`
File: `TimelineBoard.tsx`

Requirements:
- Prefer API `timeline` from store; fallback to `groupByWeek(items)` if timeline missing.
- Render horizontal scroll columns.
- If exactly one column and all source `week_number` are null, show note: "Lộ trình hiện đang được gom vào Tuần 1; phân bổ nhiều tuần sẽ được bổ sung sau."
- Card click selects unit.

#### T4.4 `LearningUnitCard`
File: `cards/LearningUnitCard.tsx`

Requirements:
- Status visual same as SubtopicNode.
- Shows section, hours, recommended badge.

#### T4.5 `LearningUnitDrawer`
File: `LearningUnitDrawer.tsx`

Requirements:
- If `selectedItemId` present: show unit detail.
- Lazy-fetch `learningUnitApi.contentById(learning_unit_id)` on open.
- If `selectedSectionKey` present: show section summary + units list.
- Unit drawer status pills: `pending`, `in_progress`, `completed`, `skipped`.
- Previous/Next buttons based on global `order_index` instead of prerequisite chips.
- Escape and overlay close.
- Focus close button on open and restore previous focus on close.

#### T4.6 `EmptyState`
File: `EmptyState.tsx`

Requirements:
- Do not call generate directly.
- CTA choices:
  - If user not onboarded: `/onboarding`.
  - Else `/dashboard` with copy: "Chọn khóa học để tạo lộ trình".

---

### Wave 5 — Page integration

#### T5.1 Replace `/learn` placeholder
File: `frontend/app/learn/page.tsx`

Requirements:
- Render a client `LearningPathShell` component.
- Header: title + `ViewToggle` only. No Replan button.
- Body: loading skeleton, error retry, empty state, graph/timeline.
- Drawer mounted once.

#### T5.2 Add skeletons/errors
Can live inside `LearningPathShell` initially.

Requirements:
- Graph skeleton: fake nodes.
- Timeline skeleton: fake columns.
- Error: Vietnamese message + Retry button.

---

### Wave 6 — Verification

#### T6.1 Unit tests
Files:
- `frontend/tests/unit/learning-path/presenters.test.ts`
- `frontend/tests/unit/learning-path/status.test.ts`

Run:

```bash
cd frontend && npm run test -- learning-path
```

#### T6.2 Typecheck

```bash
cd frontend && npm run type-check
```

#### T6.3 Build

```bash
cd frontend && npm run build
```

#### T6.4 E2E smoke
File: `frontend/tests/e2e/learning-path-roadmap.spec.ts`

Flow:
- Login/register seeded user with path.
- Go `/learn`.
- Assert graph or timeline renders.
- Click unit card/node.
- Drawer opens.
- Click completed status.
- Assert visual changed.

---

## 4. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Timeline only has Week 1 | Medium | UI explains backend has not allocated multiple weeks yet. |
| Duplicate section titles | Medium | Use first order index in section key; future backend should expose `section_id`. |
| ReactFlow SSR issues | High | Dynamic import with `ssr: false`. |
| Bundle growth | Medium | Dynamic import RoadmapCanvas from start. |
| Drawer content fetch fails | Low | Non-blocking error; keep status actions usable. |
| Skip status can be forbidden by backend policy | Medium | Revert optimistic update and show API error. |

---

## 5. Deferred Follow-up Phases

### Phase 2 — Backend weekly allocation
- Add `assign_week_numbers()` to `recommendation_engine.py`.
- Use user availability/deadline if available.
- Persist `week_number` in `recommended_path_json`.
- Timeline becomes truly multi-week.

### Phase 3 — Replan
- Add body-less endpoint `POST /api/learning-path/regenerate-current` or expose `goal_preferences` safely.
- Add `ReplanButton` with confirm dialog.

### Phase 4 — Real prerequisite DAG
- Add `prereq_unit_ids` or graph endpoint.
- Replace sequential edges with prerequisite edges.
- Add prerequisite chips in drawer.

### Phase 5 — Mastery heatmap
- Add `mastery_score` to path item or separate endpoint.
- Visual heatmap on nodes/cards.

---

## 6. Definition of Done

- [ ] All Phase 1 requirements in `SPEC.md` pass.
- [ ] No broken generate/replan call exists in UI.
- [ ] No UI assumes prereq data that backend does not expose.
- [ ] Timeline handles Week 1 fallback honestly.
- [ ] Unit tests and typecheck pass.
- [ ] Build passes.
- [ ] E2E happy path pass or documented blocker.

---

*Plan folder: `visualize/`*  
*Plan revised: 2026-04-25*  
*Next step: implement Wave 1.*
