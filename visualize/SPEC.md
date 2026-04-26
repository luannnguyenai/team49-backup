# Visualize: Learning Path Roadmap UI — Specification

**Created:** 2026-04-25  
**Revised:** 2026-04-25 after codebase review  
**Skill template:** `gsd-spec-phase`  
**Ambiguity score:** 0.12 (gate: ≤ 0.20) ✓  
**Requirements:** 7 locked

## Goal

Người học mở `/learn` và thấy lộ trình cá nhân hóa của mình ở **2 view khả thi với backend hiện tại**: (a) **Graph** — đồ thị topic/subtopic lấy từ `section_title` và `learning_unit_title`; và (b) **Timeline** — cards group theo `week_number` từ backend, fallback rõ ràng về Week 1 nếu backend chưa phân bổ tuần. Click node/card mở drawer, xem chi tiết, bắt đầu học, và cập nhật trạng thái.

## Background

**Hiện trạng đã verify trong codebase:**

- Backend đã có `POST /api/learning-path/generate`, `GET /api/learning-path`, `GET /api/learning-path/timeline`, `PUT /api/learning-path/{path_id}/status`.
- `PathItemResponse` hiện là flat list: `id`, `learning_unit_id`, `learning_unit_title`, `section_title`, `action`, `estimated_hours`, `order_index`, `week_number`, `status`, `canonical_unit_id`.
- `PathItemResponse` **không có** `description`, `section_id`, `prereq_unit_ids`, `mastery_score`.
- `recommendation_engine.py` currently sets `week_number=None` on generated items; timeline service groups `None` into Week 1.
- Frontend `/learn` page currently renders a placeholder only.
- Frontend has no graph library installed.
- Frontend can fetch learning unit content by id through `learningUnitApi.contentById(id)`.
- Frontend user/auth state does not expose `goal_preferences`, so a client-side replan body cannot be constructed reliably.

**Scope correction from review:**

The original plan included Replan and prerequisite chips. Those are removed from Phase 1 because they require backend data not currently exposed. Phase 1 stays UI-focused and compatible with existing endpoints.

---

## Requirements

### R1. Graph view — topic/subtopic render
**Statement:** `/learn` renders a graph where Topic nodes represent sections and Subtopic nodes represent learning units.

- **Current:** `/learn` is a placeholder.
- **Target:** `<RoadmapCanvas>` renders section Topic nodes and learning-unit Subtopic nodes from `GET /api/learning-path`.
- **Acceptance:**
  - Given 3 section titles and 15 learning units, graph renders 3 Topic nodes and 15 Subtopic nodes.
  - Topic nodes and Subtopic nodes have distinct styles.
  - Edges connect units in global `order_index` order.
  - Graph supports pan, zoom, controls, and fit-view.
  - If no path exists, an empty state is shown with a clear route to onboarding or assessment flow; it must not call an API with missing body data.

### R2. Timeline view — backend-week aware
**Statement:** User can switch to Timeline view and see learning units grouped by week from backend timeline data.

- **Current:** `GET /api/learning-path/timeline` exists, but generated `week_number` values may all be `NULL`, causing a Week 1 fallback.
- **Target:** `<TimelineBoard>` renders columns from `GET /api/learning-path/timeline`; if all items are Week 1, the UI still renders honestly as Week 1 rather than pretending multi-week allocation exists.
- **Acceptance:**
  - Timeline renders 1+ week columns based on API response.
  - Skipped units excluded by backend do not appear in timeline.
  - Each column header displays week number and total hours.
  - Click card opens the same drawer as graph view.
  - A note or tooltip explains when all units are currently grouped in Week 1 because weekly allocation is not yet generated.

### R3. View toggle persistence
**Statement:** User can toggle Graph / Timeline; selected view persists across reload.

- **Current:** No toggle.
- **Target:** URL `?view=graph|timeline` has first precedence, then LocalStorage `learn:view`, then device default.
- **Acceptance:**
  - Desktop first visit defaults to Graph.
  - Mobile first visit defaults to Timeline.
  - Reload keeps chosen view.
  - `/learn?view=graph` always opens Graph.
  - `/learn?view=timeline` always opens Timeline.

### R4. Drawer detail — lazy content fetch
**Statement:** Click a Subtopic node or Timeline card opens a right drawer with learning-unit details and status actions.

- **Current:** No drawer; `PathItemResponse` lacks description.
- **Target:** Drawer uses path item fields immediately, then lazily fetches detailed content via `GET /api/learning-units/{id}/content` when opened.
- **Acceptance:**
  - Drawer opens for a learning unit and shows title, section, estimated hours, week, status, and CTA `Bắt đầu học` → `/learn/{learningUnitId}`.
  - If content fetch succeeds, drawer shows description/markdown summary available from content API.
  - If content fetch fails, drawer still remains usable with path item data and shows a non-blocking error message.
  - Status pills call `PUT /api/learning-path/{path_id}/status`.
  - Escape key and overlay click close the drawer.
  - Clicking a Topic node opens a section summary drawer/list, not status pills.

### R5. Status visualization and optimistic update
**Statement:** Subtopic nodes and Timeline cards reflect current path status.

- **Current:** No visual states.
- **Target:** Status mapping:
  - `pending` → default style
  - `in_progress` → emphasized border + in-progress icon
  - `completed` → check icon + reduced opacity + strikethrough
  - `skipped` → reduced opacity + skipped icon + strikethrough
- **Acceptance:**
  - Updating status changes node/card visual immediately.
  - If API fails, visual state reverts and error is shown.
  - Reload reflects backend status.

### R6. Recommended-next highlight — simple global order
**Statement:** The next recommended learning unit is the first non-skipped pending unit in global `order_index` order.

- **Current:** No recommendation highlight.
- **Target:** Compute on frontend from existing path items; do not infer prerequisite completion because backend does not expose prerequisites.
- **Acceptance:**
  - Given items sorted by `order_index`, the first item with `status='pending'` and `action !== 'skip'` is highlighted.
  - Completing highlighted item moves highlight to the next eligible item.
  - At most one item is highlighted.
  - If no pending eligible item exists, no highlight is shown.

### R7. Loading, empty, and error states
**Statement:** `/learn` handles loading, empty, and error states without dead ends.

- **Current:** Placeholder only.
- **Target:** Loading skeletons, retryable errors, and a clear empty-state CTA.
- **Acceptance:**
  - Initial load shows skeleton matching active view.
  - `GET /api/learning-path` error shows Vietnamese error message and Retry button.
  - Empty path shows "Chưa có lộ trình" and a CTA to onboarding/assessment/course-start flow, not a broken generate call.
  - Status update error reverts optimistic UI.

---

## Boundaries

### In scope
- Graph view with `reactflow` and `dagre`.
- Timeline view from existing `GET /api/learning-path/timeline`.
- View toggle with URL + LocalStorage persistence.
- Custom Topic/Subtopic node components.
- Drawer with lazy content fetch using existing learning unit content API.
- Status update via existing `PUT /api/learning-path/{path_id}/status`.
- Recommended-next frontend computation using global order.
- Loading skeletons, empty state, and retryable errors.
- Unit tests for presenters and status logic.
- One E2E happy path for drawer + status update.

### Out of scope for Phase 1
- Replan/regenerate button — frontend currently cannot access `goal_preferences`; a body-less backend endpoint should be designed first.
- True prerequisite chips or DAG edges — backend does not expose `prereq_unit_ids`.
- Multi-week allocation logic — backend currently groups `NULL` week numbers into Week 1; a separate backend phase should populate `week_number`.
- Mastery heatmap — `mastery_score` is not in `PathItemResponse`.
- Public progress sharing.
- Admin/editor roadmap builder.
- RoughJS hand-drawn clone.
- Full focus trap implementation beyond Escape/overlay/focus-first/restoring focus.
- Feature-flag percentage rollout/Sentry rollout infrastructure.

---

## Constraints

1. Use current stack:
