# How It Works — Visualize Learning Path

**Feature:** Visual learning path at `/learn`  
**Scope:** Phase 1 MVP  
**Goal:** Show the learner's personalized path as both a graph roadmap and a weekly timeline, using the backend APIs that already exist.

---

## 1. User-facing behavior

When a learner opens:

```txt
/learn
```

They see:

1. A page header: `Lộ trình của bạn`.
2. A view toggle:
   - `Đồ thị` — graph roadmap view.
   - `Tuần` — timeline/week view.
3. Their learning path data loaded from the backend.
4. A right-side drawer when they click a topic/unit.

The UI does **not** regenerate the learning path in Phase 1. It only visualizes and updates status for the current path.

---

## 2. Main frontend entry point

The app route is:

```txt
frontend/app/learn/page.tsx
```

It renders:

```tsx
<LearningPathShell />
```

`LearningPathShell` is the main feature container:

```txt
frontend/features/learning-path/components/LearningPathShell.tsx
```

Responsibilities:

- Load current path data.
- Load timeline data.
- Manage Graph vs Timeline view.
- Show loading/error/empty states.
- Render the drawer once globally.

---

## 3. Data sources

The frontend uses existing backend endpoints only.

### Current path

```http
GET /api/learning-path
```

Frontend wrapper:

```txt
frontend/features/learning-path/api.ts
```

Returns shape:

```ts
interface LearningPathResponse {
  total_units: number;
  completed_units: number;
  in_progress_units: number;
  items: PathItemResponse[];
}
```

Each `PathItemResponse` represents one learning unit row in the path:

```ts
interface PathItemResponse {
  id: string;
  learning_unit_id: string;
  learning_unit_title: string;
  section_title: string | null;
  action: "skip" | "quick_review" | "standard_learn" | "deep_practice" | "remediate";
  estimated_hours: number | null;
  order_index: number;
  week_number: number | null;
  status: "pending" | "in_progress" | "completed" | "skipped";
  canonical_unit_id: string | null;
}
```

### Timeline data

```http
GET /api/learning-path/timeline
```

Returns:

```ts
interface TimelineResponse {
  total_weeks: number;
  items: WeekEntry[];
}

interface WeekEntry {
  week: number;
  learning_units: PathItemResponse[];
  total_hours: number;
}
```

Important Phase 1 behavior:

- Backend currently may set `week_number = null` for generated items.
- Timeline service groups `null` into Week 1.
- The UI shows this truthfully instead of pretending a multi-week plan exists.

### Unit content for drawer

The path response does not include long description/markdown. So the drawer lazy-loads detail only when opened:

```http
GET /api/learning-units/{learningUnitId}/content
```

Frontend wrapper already exists in:

```txt
frontend/lib/api.ts → learningUnitApi.contentById(id)
```

---

## 4. State management

State lives in:

```txt
frontend/features/learning-path/store.ts
```

Store responsibilities:

- `items` — current path units.
- `summary` — total/completed/in-progress counts.
- `timeline` — backend timeline response.
- `loading` / `error`.
- `selectedItemId` — selected learning unit drawer.
- `selectedSectionKey` — selected section/topic drawer.
- `updatingStatusById` — per-unit optimistic update state.

Main actions:

```ts
loadPath()
selectItem(id)
selectSection(sectionKey)
closeDrawer()
updateStatus(pathId, status)
```

---

## 5. Graph view

Component:

```txt
frontend/features/learning-path/components/RoadmapCanvas.tsx
```

Libraries:

- `reactflow` — interactive graph canvas.
- `@dagrejs/dagre` — auto-layout.

Graph generation logic:

```txt
frontend/features/learning-path/presenters.ts
```

Function:

```ts
pathToFlow(items): { nodes, edges, sectionSummaries }
```

### Node mapping

| Backend data | Graph node |
|---|---|
| `section_title` | Topic node |
| `PathItemResponse` | Subtopic node |

### Edge mapping

Phase 1 uses simple sequential edges:

```txt
unit(order_index N) → unit(order_index N + 1)
```

This is intentional because backend does not yet expose prerequisite DAG data.

### Topic node

File:

```txt
frontend/features/learning-path/components/nodes/TopicNode.tsx
```

Shows:

- Section title.
- Number of learning units.

Click behavior:

- Opens section summary drawer.

### Subtopic node

File:

```txt
frontend/features/learning-path/components/nodes/SubtopicNode.tsx
```

Shows:

- Learning unit title.
- Estimated hours.
- Status badge/icon.
- `Tiếp theo` badge when recommended.

Click behavior:

- Opens unit detail drawer.

---

## 6. Timeline view

Component:

```txt
frontend/features/learning-path/components/TimelineBoard.tsx
```

Behavior:

- Uses backend timeline if available.
- Falls back to frontend `groupByWeek(items)` if timeline request fails.
- Renders horizontal week columns.
- Each card is a learning unit.

Card component:

```txt
frontend/features/learning-path/components/cards/LearningUnitCard.tsx
```

Timeline grouping rule:

```ts
week = item.week_number ?? 1
```

Skipped units are hidden from timeline when `action === "skip"`.

If every item has `week_number === null`, the UI displays a note:

```txt
Lộ trình hiện đang được gom vào Tuần 1; phân bổ nhiều tuần sẽ được bổ sung sau.
```

---

## 7. View toggle

Component:

```txt
frontend/features/learning-path/components/ViewToggle.tsx
```

Available views:

```ts
"graph" | "timeline"
```

Precedence:

1. URL query param:

```txt
/learn?view=graph
/learn?view=timeline
```

2. LocalStorage:

```txt
learn:view
```

3. Device default:

| Device | Default |
|---|---|
| Desktop | Graph |
| Mobile | Timeline |

---

## 8. Drawer behavior

Component:

```txt
frontend/features/learning-path/components/LearningUnitDrawer.tsx
```

There are two drawer modes.

### Section drawer

Triggered by clicking a Topic node.

Shows:

- Section title.
- Number of units.
- List of units in that section.

Clicking a listed unit switches to unit drawer.

### Unit drawer

Triggered by clicking:

- Subtopic node in graph.
- Unit card in timeline.

Shows immediately from `PathItemResponse`:

- Unit title.
- Section title.
- Week number fallback.
- Estimated hours.
- Status controls.
- Previous/Next navigation by global `order_index`.
- CTA:

```txt
Bắt đầu học → /learn/{learningUnitId}
```

Then lazy-loads content:

```ts
learningUnitApi.contentById(learning_unit_id)
```

If content fetch fails, drawer still works and shows a non-blocking error.

Close behavior:

- Escape key.
- Overlay click.
- Close button.

---

## 9. Status updates

Status options:

```ts
pending | in_progress | completed | skipped
```

When user clicks a status pill:

```http
PUT /api/learning-path/{path_id}/status
```

Request body:

```json
{ "status": "completed" }
```

Frontend behavior:

1. Optimistically update local UI.
2. Call backend.
3. If backend succeeds: keep state.
4. If backend fails: revert to previous state and show error.

Backend may reject `skipped` depending on skip policy. That is expected; UI reverts.

---

## 10. Recommended-next logic

Function:

```txt
frontend/features/learning-path/presenters.ts → computeRecommendedNext(items)
```

Phase 1 rule:

```txt
First item sorted by order_index where:
  status === "pending"
  and action !== "skip"
```

Only one item can be highlighted.

Why not prerequisites?

Because backend does not yet expose:

```txt
prereq_unit_ids
```

So Phase 1 does not infer hidden prerequisite logic.

---

## 11. Empty, loading, and error states

### Loading

`LearningPathShell` shows:

- Graph skeleton for graph view.
- Timeline skeleton for timeline view.

### Empty path

Component:

```txt
frontend/features/learning-path/components/EmptyState.tsx
```

Behavior:

- Does not call generate directly.
- If user is not onboarded: link to `/onboarding`.
- Else: link to `/dashboard` to choose a course.

Reason:

Frontend currently cannot safely construct `desired_section_ids` for `POST /api/learning-path/generate`.

### Error

Shows Vietnamese message and Retry button.

---

## 12. Dependency install requirements

Frontend dependencies required:

```json
"reactflow": "^11.11.4",
"@dagrejs/dagre": "^3.0.0"
```

They must exist
