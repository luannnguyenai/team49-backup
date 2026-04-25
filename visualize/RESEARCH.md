# RESEARCH — roadmap.sh Component & Pattern Analysis

**Source studied:** https://roadmap.sh/ai-data-scientist (and sibling roadmaps)
**Repo:** https://github.com/kamranahmedse/developer-roadmap (MIT)
**Date:** 2026-04-25

---

## 1. Visual & rendering architecture

### Stack roadmap.sh dùng
- **Astro + React** (SSG cho landing, hydrate React cho roadmap canvas).
- **Renderer:** custom canvas dựa trên [`renderer-roadmap`](https://github.com/kamranahmedse/developer-roadmap/tree/master/src/components) → vẽ SVG bằng [RoughJS](https://roughjs.com/) để có cảm giác sketch hand-drawn.
- **Data format:** mỗi roadmap = 1 file `*.json` (Excalidraw-compatible schema: `elements[]` + `appState`) + thư mục `content/` chứa N file `.md` (1 file per topic/subtopic, đặt tên theo `{slug}@{nodeId}.md`).
- **Layout:** **manual positioning** (mỗi node có `x, y` cố định trong JSON). Editor là một fork của Excalidraw → cho phép kéo-thả & xuất JSON.

### Hệ luỵ cho A20
A20 không thể auto-generate JSON với tọa độ tay → ta phải dùng **auto-layout** (dagre/elk). Đây là khác biệt lớn nhất so với roadmap.sh và là lý do chọn `reactflow` thay vì port renderer của họ.

---

## 2. Phân loại node (visual taxonomy)

| Node type | Style trên roadmap.sh | Hành vi click | Map sang A20 |
|---|---|---|---|
| **Topic** (vàng đậm, viền đen sketch, shadow nhẹ) | Concept bắt buộc | Mở drawer phải với content markdown + resources | `Section` (chương) |
| **Subtopic** (tím nhạt, nhỏ hơn, gắn quanh topic cha) | Concept con | Mở drawer phải | `LearningUnit` (bài học) |
| **Label** (text trần, không box, font lớn) | Section heading | Không clickable | Tiêu đề "Tuần 1", "Pillar A", v.v. |
| **Button/Link** (style như nút, viền đậm) | Link external | Mở tab mới | Resource / video link |
| **Todo group** (box dashed) | Nhóm tùy chọn | Toggle expand | (skip) |

**Quan sát:** ~80% diện tích roadmap là Topic + Subtopic. Label và Button là phụ trợ. → A20 chỉ cần build Topic + Subtopic + Label là đủ.

---

## 3. Connection (edges)

| Loại nối | Style | Ý nghĩa |
|---|---|---|
| Solid line | Đường liền sketch-style | Bắt buộc, học theo thứ tự |
| Dashed line | Đường đứt sketch | Tùy chọn / alternative path |
| Arrow head | Mũi tên ở đầu | Chiều đi (prerequisite → target) |

**Quan sát:** Hầu hết edge KHÔNG có nhãn. Branching là visual (rẽ nhánh dọc) chứ không cần label.

---

## 4. State & progress tracking

| State | Visual treatment |
|---|---|
| `pending` (default) | Màu nguyên gốc của node type |
| `done` | Strikethrough + opacity 60% + checkmark badge góc |
| `learning` (in-progress) | Border đậm + pulse animation viền vàng |
| `skipped` | Opacity 30% + strikethrough |
| `recommended` (next) | Glow / pulse / arrow chỉ vào |

**Persistence:** LocalStorage key `roadmap-progress-{roadmap_id}` cho guest, sync lên server cho user đã đăng nhập.

**Toggle pattern:** Click node → drawer mở → các nút "Done / Learning / Skip / Pending" → đóng drawer → node đổi màu ngay (optimistic update).

---

## 5. Drawer (right panel) — content shape

Khi click node, drawer trượt vào từ phải, chiếm ~40% màn hình:

```
┌─────────────────────────────────┐
│ [×]            Topic Title      │
│ ────────────────────────────    │
│ [Done] [Learning] [Skip] [Pin]  │  ← Status pills
│                                 │
│ ## Description                  │
│ Markdown content (1-3 đoạn)     │
│                                 │
│ ## Free Resources               │
│ • [link 1] (article, 5 min)    │
│ • [link 2] (video, 10 min)     │
│                                 │
│ ## Premium / Books              │
│ • [book] (paid)                 │
│                                 │
│ ## Visit AI Tutor →             │  ← (optional, mới)
└─────────────────────────────────┘
```

**Cho A20:** drawer sẽ chứa:
- Title + section name
- Status pills (pending/in_progress/completed/skipped) — gọi `PUT /api/learning-path/{path_id}/status`
- Mô tả LU (Phase 1: lazy-fetch từ `GET /api/learning-units/{id}/content`, vì `PathItemResponse` chưa có description)
- Estimated hours + week assignment
- Phase 1 navigation: bài trước / bài tiếp theo theo `order_index`; prerequisites thật cần backend expose `prereq_unit_ids`
- Nút primary: "Bắt đầu học" → `/learn/{learningUnitId}`

---

## 6. Layout patterns roadmap.sh hay dùng

1. **Vertical spine + side branches:** trục chính chạy dọc (top → bottom), các topic chính nằm trên trục, subtopic rẽ trái/phải. → **Áp dụng được cho A20.**
2. **Phase grouping:** nhóm node theo giai đoạn (Beginner / Intermediate / Advanced) bằng background panel mờ + Label header. → **Map sang A20:** group theo `week_number`.
3. **Optional cluster:** nhóm node optional vào 1 box dashed riêng. → A20 có thể dùng cho `action = skip` ở phase sau.

---

## 7. Khác biệt giữa roadmap.sh và yêu cầu A20

| Khía cạnh | roadmap.sh | A20 |
|---|---|---|
| Roadmap tạo | Manual (admin design trong editor) | **Auto** từ `recommendation_engine.py` |
| Tọa độ node | Fixed trong JSON | **Auto-layout** (dagre) |
| Per-user customization | Không (1 roadmap chung cho tất cả) | **Có** — mỗi user 1 path khác nhau |
| Mastery awareness | Không | **Future** — cần thêm `mastery_score`, chưa thuộc Phase 1 |
| AI replan | Không | **Future** — cần endpoint body-less hoặc expose `goal_preferences`, chưa thuộc Phase 1 |
| Editor | Có (Excalidraw fork) | **Không cần** ở Phase này |
| Sketch hand-drawn | Có (RoughJS) | **Không cần 1:1** — chỉ cần border-dashed gợi ý sketch |

---

## 8. Library evaluation

| Lib | Pros | Cons | Verdict |
|---|---|---|---|
| **reactflow** (xyflow) | Mature, MIT, 21k★, custom node types, built-in zoom/pan/minimap, React-native | Bundle ~80kb gz | ✅ **Chosen** |
| `roughjs` + custom SVG | True hand-drawn vibe | Phải tự build pan/zoom/edge routing → effort cao | ❌ Reject (không cần 1:1) |
| `react-archer` | Đơn giản, bind nodes bằng ref | Không hỗ trợ pan/zoom canvas | ❌ Quá nghèo tính năng |
| `mermaid` | Render từ text, đơn giản | Không tương tác (click node mở drawer khó) | ❌ Read-only quá |
| `dagre` | Auto-layout DAG | Không phải renderer | ✅ **Dùng kèm reactflow** cho layout |
| `tldraw` | Sketch + interactive | Bundle to (~500kb), overkill | ❌ |

---

## 9. Tham khảo các implementation tương tự

- **roadmap.sh own renderer** — `kamranahmedse/developer-roadmap/src/components/Roadmap.tsx`
- **react-flow examples** — https://reactflow.dev/examples (có example "Layouted Flow" dùng dagre)
- **Refactoring Guru roadmaps** — design pattern roadmap, đơn giản hơn, dùng SVG flat
- **Notion / Coda dependency graph** — node + drawer pattern tương tự

---

## 10. Takeaways cho A20

1. **Không clone hand-drawn** — vibe sketch chỉ cần đạt qua `border-2 border-dashed` + `shadow-[3px_3px_0_0_rgba(0,0,0,0.15)]`.
2. **Topic = Section, Subtopic = LearningUnit** — mapping tự nhiên.
3. **Edges Phase 1 sinh tự động** từ global `order_index` (sequential). Prereq/DAG thật là phase sau vì backend chưa expose `prereq_unit_ids`.
4. **Auto-layout dagre** với direction `TB` (top-to-bottom) cho graph view.
5. **Drawer pattern** giống roadmap.sh nhưng nội dung A20-specific (hours, status, previous/next, "Bắt đầu học" CTA).
6. **Timeline view** là alt view tận dụng sẵn `GET /api/learning-path/timeline` — render thành cột tuần, cards dọc trong mỗi cột. Phase 1 hiển thị đúng dữ liệu backend; nếu backend gom hết vào Week 1 thì UI không fake multi-week.
7. **Status sync** qua `PUT /api/learning-path/{path_id}/status` — optimistic update phía FE.
