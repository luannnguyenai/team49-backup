# Learn Path UX — Giảm "ngợp" cho `/learn`

## Vấn đề

Trang `/learn` hiện render `LearningPathShell` với 2 view (graph/timeline). View graph (`RoadmapPlanner`) dựng dọc toàn bộ courses → lectures → unit cards. Khi user có nhiều khóa và mỗi khóa 10+ lectures, người học nhìn vào 1 vách thông tin dài và không biết:

1. Bây giờ làm gì tiếp theo? — "Next up" chỉ là 1 badge nhỏ trên 1 card.
2. Tôi đang ở đâu trong toàn bộ hành trình? — Header chỉ có summary tổng.
3. Hôm nay học bao lâu? — Không có gợi ý phiên học cụ thể.
4. Sao card này quan trọng? — Hàng loạt reason badges gây nhiễu.
5. Lectures collapse hay expand? — Hiện tất cả collapse → phải click khám phá.

## Mục tiêu

Giảm visual noise, đặt **1 hành động rõ ràng** trước mặt user, cho họ một **bản đồ tổng quan ngắn** để định hướng. **Không** đổi data model, store, API, backend.

## Phases

Mỗi phase 1 task duy nhất, có thể merge độc lập:

| # | Phase | File chi tiết |
|---|-------|---------------|
| 0 | Extract shared course-display helpers | [phase-0-extract-course-display.md](./phase-0-extract-course-display.md) |
| 1 | Hero "Continue learning" card | [phase-1-continue-learning-hero.md](./phase-1-continue-learning-hero.md) |
| 2 | Journey strip — bird's-eye các course | [phase-2-journey-strip.md](./phase-2-journey-strip.md) |
| 3 | Smart default expand + slim done courses | [phase-3-smart-expand.md](./phase-3-smart-expand.md) |
| 4 | Giảm noise của reason badges | [phase-4-slim-reason-badges.md](./phase-4-slim-reason-badges.md) |

**Thứ tự bắt buộc:** Phase 0 trước Phase 2 (Phase 2 dùng helper từ Phase 0). Các phase khác độc lập, có thể chạy song song hoặc theo bất kỳ thứ tự nào sau Phase 0.

## Out of scope

- Không đổi `PathItemResponse`, `store.ts`, `roadmap-model.ts`, `presenters.ts`, `planner-reasons.ts`, `player-insights.ts`.
- Không đụng `TimelineBoard`, `PlannerHeader`, backend API, types.
- Không thêm view mới.
