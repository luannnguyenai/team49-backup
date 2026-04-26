# Visualize — Learning Path Roadmap UI

Plan folder for the **graph + weekly timeline** visualization of the personalized learning path, inspired by [roadmap.sh/ai-data-scientist](https://roadmap.sh/ai-data-scientist).

This folder has been revised after plan review. The current scope is **Phase 1 MVP**: build the roadmap UI against the backend that exists today, without requiring new graph/prerequisite/replan endpoints.

## Files

| File | Purpose | Skill template |
|---|---|---|
| `RESEARCH.md` | Deep analysis of roadmap.sh — components, rendering, UX patterns, data shape | n/a |
| `SPEC.md` | Locked requirements (WHAT + WHY) with falsifiable acceptance criteria | `gsd-spec-phase` |
| `PLAN.md` | Implementation plan (HOW) — files to create, tasks, gates, rollout | `gsd-plan-phase` |

## Workflow

1. **Read RESEARCH.md** to understand the source-of-inspiration's component decomposition.
2. **Read SPEC.md** to lock scope — every requirement is testable.
3. **Read PLAN.md** to execute — each task has owner file paths, verification, and dependency order.

## Locked decisions (from chat)

| Question | Decision |
|---|---|
| Default visual style | Graph (topic/subtopic) — **không cần** sketch hand-drawn 1:1 |
| Views supported | **Cả hai**: Graph (default desktop) + Timeline (default mobile + alt view) |
| Roadmap source | Auto-generated từ `recommendation_engine.py` (không có editor admin) |
| Library | `reactflow` + `dagre` (auto-layout) — chọn vì cân bằng tốc độ + tính năng |
| Replan | **Out of Phase 1** — backend currently lacks a body-less regenerate endpoint and frontend cannot read `goal_preferences` |
| Prerequisites | **Out of Phase 1** — backend response has no `prereq_unit_ids`; use previous/next navigation only |
| Timeline weeks | Phase 1 renders backend `week_number`; if backend returns all `NULL`, UI transparently shows Week 1 |

## Status

- [x] Research roadmap.sh
- [x] Lock SPEC requirements
- [x] Draft implementation PLAN
- [x] Review and correct PLAN against current codebase
- [ ] Approve PLAN → spawn execute phase
- [ ] Build & verify
