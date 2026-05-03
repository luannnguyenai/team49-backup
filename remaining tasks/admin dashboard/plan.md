# Admin Dashboard + Observability — Phased Plan

> File này sẽ được copy thành `admin-dashboard/plan.md` ngay sau khi user approve plan mode.

## Context

Project A20-App-049 (FastAPI + Next.js, localhost-first). Mục tiêu: build admin dashboard monitor users/traffic/LLM/system health, đồng bộ style với landing page.

**Quyết định kiến trúc:**
- Admin UI = route `/admin` trong frontend Next.js hiện tại — kế thừa design tokens landing (cyan/indigo/teal, glass cards, radial gradient bg).
- LangFuse **Cloud** free tier cho LLM tracing.
- Grafana stack self-host qua docker-compose (Prometheus + Grafana + Loki + Promtail).
- Charts: Recharts.
- Deploy production để sau.

---

## Nguyên tắc phân phase

- **Mỗi phase = 1 task duy nhất**, có thể test độc lập, không phụ thuộc phase chưa làm.
- **Isolate**: phase này không sửa file phase khác; nếu phải sửa, chỉ thêm dòng mới (không refactor).
- **Verify** mỗi phase trước khi chuyển sang phase kế.
- Có thể skip / hoãn / đổi thứ tự bất kỳ phase nào (trừ Phase 1 — foundation).
- Mỗi phase commit riêng biệt.

---

## Phase 1 — Foundation: User role + admin guard ✅ DONE (2026-05-02)

**Task duy nhất:** Thêm cột `role` vào bảng users + dependency `require_admin()` ở backend + script seed admin.

**Scope:**
- Alembic migration: `ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user' NOT NULL`.
- `src/models/user.py`: thêm field `role`.
- `src/core/security.py`: thêm `require_admin` FastAPI dependency.
- `admin-dashboard/scripts/seed_admin.py`: CLI promote user theo email.

**Files:**
- NEW: `alembic/versions/xxxx_add_user_role.py`
- MODIFY: `src/models/user.py`, `src/core/security.py`
- NEW: `admin-dashboard/scripts/seed_admin.py`

**Verify:**
1. `alembic upgrade head` chạy không lỗi.
2. `psql ... \d users` → cột `role` tồn tại.
3. `python admin-dashboard/scripts/seed_admin.py --email <e>` → user đó có role='admin'.
4. Test endpoint giả tưởng dùng `Depends(require_admin)`: non-admin → 403, admin → 200.

**Isolation:** Không động backend logic khác. Không động frontend.

---

## Phase 2 — Backend: Prometheus metrics endpoint ✅ DONE (2026-05-02)

**Task duy nhất:** Expose `/metrics` từ FastAPI cho Prometheus scrape.

**Scope:**
- Install `prometheus-fastapi-instrumentator`.
- `src/middleware/prometheus.py`: setup Instrumentator.
- `src/main.py`: mount instrumentator + expose `/metrics`.

**Files:**
- NEW: `src/middleware/prometheus.py`
- MODIFY: `src/main.py` (chỉ thêm 2-3 dòng init)
- MODIFY: `requirements.txt`

**Verify:**
1. Restart backend.
2. `curl http://localhost:8000/metrics` → trả về Prometheus text format với `http_requests_total`, `http_request_duration_seconds`.
3. Gọi vài request thật → counter tăng.

**Isolation:** Không sửa router/service nào.

---

## Phase 3 — Backend: Structured access log ✅ DONE (2026-05-02)

**Task duy nhất:** Middleware ghi JSON access log vào `logs/access.jsonl`.

**Scope:**
- Install `python-json-logger`.
- `src/middleware/request_logger.py`: middleware log mỗi request (`{ts, method, path, status, latency_ms, user_id, request_id}`).
- `src/main.py`: mount middleware.

**Files:**
- NEW: `src/middleware/request_logger.py`
- MODIFY: `src/main.py` (1 dòng add_middleware)
- MODIFY: `requirements.txt`

**Verify:**
1. Gọi 5 request → `tail -f logs/access.jsonl` thấy 5 JSON lines hợp lệ.
2. Field `latency_ms` > 0, `user_id` đúng cho request đã auth.

**Isolation:** Độc lập với Phase 2.

---

## Phase 4 — Backend: LangFuse LLM tracing ✅ DONE (2026-05-02 — wired, fail-safe; trace verify cần user nhập LangFuse keys vào .env)

**Task duy nhất:** Inject LangFuse callback vào tất cả LLM call.

**Scope:**
- Install `langfuse`.
- ENV: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`.
- `src/core/observability.py`: export singleton `langfuse_handler`.
- `src/services/llm_service.py`: pass `config={"callbacks": [langfuse_handler], "metadata": {...}}` vào mỗi `.invoke()` / `.ainvoke()`.

**Files:**
- NEW: `src/core/observability.py`
- MODIFY: `src/services/llm_service.py` (chỉ wrap callback, không đổi logic)
- MODIFY: `.env.example`, `requirements.txt`

**Verify:**
1. Tạo project ở cloud.langfuse.com, lấy keys.
2. Gọi 1 endpoint LLM (vd `/api/quiz/generate`).
3. LangFuse Cloud dashboard → trace mới với metadata `user_id`, `route`.
4. Cost/token/latency hiển thị đúng.

**Isolation:** Chỉ sửa llm_service. Nếu LangFuse down, app vẫn chạy (callback fail-safe).

---

## Phase 5 — Observability stack: docker-compose ✅ DONE (2026-05-02)

**Task duy nhất:** Dựng Prometheus + Grafana + Loki + Promtail chạy local.

**Scope:**
- `admin-dashboard/docker-compose.observability.yml`: 4 services + 2 exporters (postgres_exporter, redis_exporter).
- Configs:
  - `prometheus/prometheus.yml`: scrape `host.docker.internal:8000/metrics`, exporters.
  - `loki/loki-config.yml`: default config.
  - `promtail/promtail-config.yml`: tail `../logs/*.jsonl` → Loki labels `{app, file}`.
  - `grafana/provisioning/datasources.yml`: Prometheus + Loki + Postgres.

**Files:** Toàn bộ trong `admin-dashboard/` (chưa có dashboards JSON — phase sau).

**Verify:**
1. `docker compose -f admin-dashboard/docker-compose.observability.yml up -d`.
2. `http://localhost:9090/targets` → tất cả UP.
3. `http://localhost:3001` (Grafana, admin/admin) → 3 datasources connected.
4. Grafana Explore: query `{app="A20-App-049"}` Loki → thấy logs từ Phase 3.
5. Query Prometheus `http_requests_total` → có data từ Phase 2.

**Isolation:** Stack chạy độc lập. Stop bất kỳ lúc nào không ảnh hưởng app.

**Phụ thuộc:** Phase 2 (cho metrics), Phase 3 (cho logs) — nhưng có thể dựng trước, data sẽ rỗng đến khi 2/3 xong.

---

## Phase 6 — Grafana dashboards ✅ DONE (2026-05-02)

**Task duy nhất:** Tạo 3 dashboard JSON auto-provisioned.

**Scope:**
- `admin-dashboard/grafana/dashboards/api-traffic.json`: req/s, latency p50/p95/p99, status code distribution.
- `admin-dashboard/grafana/dashboards/system-health.json`: CPU/RAM (node_exporter optional), Postgres connections, Redis hit rate.
- `admin-dashboard/grafana/dashboards/user-activity.json`: DAU/MAU bằng Postgres datasource SQL.
- `admin-dashboard/grafana/provisioning/dashboards.yml`: auto-load.

**Files:** Chỉ trong `admin-dashboard/grafana/`.

**Verify:**
1. Restart Grafana container.
2. 3 dashboards xuất hiện trong Grafana UI.
3. Mỗi dashboard hiển thị data thật sau khi gọi vài request.

**Isolation:** Phase 6 không sửa code app.

**Phụ thuộc:** Phase 5.

---

## Phase 7 — Backend: Admin API endpoints ✅ DONE (2026-05-02)

**Task duy nhất:** Tạo `/api/admin/*` router.

**Scope (`src/routers/admin.py`)** — tất cả `Depends(require_admin)`:
- `GET /api/admin/stats/overview` → `{total_users, dau, mau, signups_7d, llm_calls_24h, avg_latency_ms, error_rate, system_uptime_pct}`.
- `GET /api/admin/users?page=&size=&q=` → paginated list.
- `GET /api/admin/signups/timeseries?days=30` → array `[{date, count}]`.
- `GET /api/admin/llm/recent?limit=50` → tail `logs/qa_history.jsonl`.
- `GET /api/admin/llm/stats?hours=24` → `{calls_per_hour, top_users, errors}`.
- `GET /api/admin/system/health` → `{cpu_pct, ram_pct, db_connections, redis_hit_rate, services: [...]}` (đọc qua psutil + DB query + Prometheus query).
- `GET /api/admin/traffic/summary` → query Prometheus HTTP API.

**Files:**
- NEW: `src/routers/admin.py`
- MODIFY: `src/main.py` (1 dòng include_router)

**Verify:**
1. Login admin user → call mỗi endpoint qua curl/HTTPie với JWT → 200 + JSON đúng schema.
2. Login non-admin → 403.

**Isolation:** Không sửa logic existing.

**Phụ thuộc:** Phase 1 (require_admin).

---

## Phase 8 — Frontend: Admin shell + design system primitives ✅ DONE (2026-05-02)

**Task duy nhất:** Tạo layout admin (topbar + sidebar + guard) + 5 component primitives đồng bộ landing style.

**Scope:**
- `frontend/app/admin/layout.tsx`: server-side role check; redirect nếu không admin. Layout gồm topbar + sidebar.
- `frontend/middleware.ts`: thêm guard `/admin/*` (redirect nếu không có JWT).
- `frontend/components/admin/`:
  - `AdminTopbar.tsx`: logo + breadcrumb + user menu + dark/light toggle.
  - `AdminSidebar.tsx`: nav Overview / Users / LLM / Traffic / System / Logs.
  - `KpiCard.tsx`: glass card `rounded-[28px] bg-white/70 backdrop-blur`, gradient accent border `from-indigo-600 via-cyan-500 to-teal-400`, value `text-4xl font-bold`, label uppercase, slot sparkline.
  - `ChartCard.tsx`: wrapper Recharts (ResponsiveContainer + AreaChart/LineChart/BarChart) trong glass card.
  - `StatusBadge.tsx`: Healthy(emerald) / Degraded(amber) / Down(rose).
- Install `recharts`.
- `frontend/app/admin/page.tsx`: placeholder "Welcome admin" (data wiring ở phase sau).

**Files:** Toàn bộ NEW trong `frontend/app/admin/` + `frontend/components/admin/`.

**Verify:**
1. Login admin → `http://localhost:3000/admin` → topbar + sidebar render đúng style landing (cyan brand, glass cards, Inter font).
2. Non-admin user → redirect `/`.
3. Dark/light toggle hoạt động.
4. Storybook-like check: import `KpiCard` với mock data → render đúng (visual sanity check).

**Isolation:** Không sửa landing page hoặc component cũ.

---

## Phase 9 — Frontend: Overview page (KPI + charts) ✅ DONE (2026-05-02)

**Task duy nhất:** Implement `/admin` overview với 8 KPI + 2 charts.

**Scope:**
- `frontend/app/admin/page.tsx`:
  - Grid 4×2 KPI cards: Total Users · DAU · MAU · Signups 7d · LLM Calls 24h · LLM Avg Latency · Error Rate · System Uptime. Mỗi card có sparkline 24h (Recharts mini line).
  - 2 chart panels: Signup trend 30 ngày (AreaChart), LLM calls/hour 24h (BarChart).
  - Fetch `/api/admin/stats/overview` + `/api/admin/signups/timeseries`.
  - Loading + error states (skeleton glass cards).

**Files:** MODIFY `frontend/app/admin/page.tsx`.

**Verify:**
1. Mở `/admin` → 8 KPI hiển thị số đúng (so với DB query thủ công).
2. 2 chart render data thật.
3. Style đồng bộ landing (cyan accent, glass).

**Phụ thuộc:** Phase 7, Phase 8.

---

## Phase 10 — Frontend: Users page ✅ DONE (2026-05-02)

**Task duy nhất:** Table users + search + pagination + signup growth chart.

**Scope:**
- `frontend/app/admin/users/page.tsx`: table glass-style, search input, pagination, AreaChart growth.
- Fetch `/api/admin/users`, `/api/admin/signups/timeseries`.

**Files:** NEW `frontend/app/admin/users/page.tsx`.

**Verify:** Search, pagination, chart đều work.

**Isolation:** Tách biệt phase 9.

---

## Phase 11 — Frontend: LLM page + LangFuse embed ✅ DONE (2026-05-02)

**Task duy nhất:** Trang `/admin/llm`.

**Scope:**
- `frontend/app/admin/llm/page.tsx`:
  - 4 KPI: Total calls 24h · Avg latency · Token usage · Est cost USD.
  - LineChart calls/hour, BarChart top 5 users, list recent errors.
  - Iframe LangFuse Cloud (rounded-[28px] glass wrapper) + button "Open LangFuse →".
- Fetch `/api/admin/llm/stats`, `/api/admin/llm/recent`.

**Files:** NEW `frontend/app/admin/llm/page.tsx`.

**Verify:** Số liệu khớp LangFuse Cloud, iframe load đúng.

---

## Phase 12 — Frontend: Traffic page + Grafana embed ✅ DONE (2026-05-02)

**Task duy nhất:** Trang `/admin/traffic`.

**Scope:**
- `frontend/app/admin/traffic/page.tsx`:
  - KPI: Req/s, p50/p95/p99 latency, 4xx rate, 5xx rate.
  - Iframe Grafana `http://localhost:3001/d/api-traffic?theme=light&kiosk` trong glass wrapper.
- Fetch `/api/admin/traffic/summary`.

**Files:** NEW `frontend/app/admin/traffic/page.tsx`.

**Verify:** KPI khớp Prometheus, iframe Grafana render.

**Phụ thuộc:** Phase 6.

---

## Phase 13 — Frontend: System health page ✅ DONE (2026-05-02)

**Task duy nhất:** Trang `/admin/system`.

**Scope:**
- `frontend/app/admin/system/page.tsx`:
  - KPI: CPU% · RAM% · DB connections · Redis hit rate · Disk usage · Service uptime.
  - LineChart CPU/RAM 1h, gauge DB connections, Redis ops/sec.
  - Service status grid: FastAPI / Postgres / Redis với `StatusBadge`.
- Fetch `/api/admin/system/health`. Auto-refresh 10s.

**Files:** NEW `frontend/app/admin/system/page.tsx`.

**Verify:** Tất cả số liệu thật, badge đổi màu khi service down.

---

## Phase 14 — Frontend: Logs page ✅ DONE (2026-05-02)

**Task duy nhất:** Tail viewer `qa_history.jsonl` + access log.

**Scope:**
- `frontend/app/admin/logs/page.tsx`: tail 100 dòng, filter user/route/level, monospace font, auto-refresh 5s.
- Fetch `/api/admin/llm/recent` + thêm endpoint `/api/admin/access/recent` nếu cần.

**Files:** NEW `frontend/app/admin/logs/page.tsx`.

**Verify:** Logs render real-time, filter work.

---

## Phase 15 — Polish + docs ✅ DONE (2026-05-02)

**Task duy nhất:** README setup + smoke test end-to-end.

**Scope:**
- `admin-dashboard/README.md`: hướng dẫn setup từng bước (env, docker compose, seed admin, mở các URL).
- Smoke test script: gọi 10 request mix → verify LangFuse có 10 traces, Grafana có spike, `/admin` counter tăng đồng thời.

**Verify:** New dev follow README → toàn bộ stack chạy < 15 phút.

---

## Critical Files Tổng Hợp

| File | Phase | Change |
|---|---|---|
| `alembic/versions/xxxx_add_user_role.py` | 1 | NEW |
| `src/models/user.py` | 1 | + role column |
| `src/core/security.py` | 1 | + require_admin |
| `admin-dashboard/scripts/seed_admin.py` | 1 | NEW |
| `src/middleware/prometheus.py` | 2 | NEW |
| `src/main.py` | 2,3,7 | mount middlewares + router |
| `src/middleware/request_logger.py` | 3 | NEW |
| `src/core/observability.py` | 4 | NEW |
| `src/services/llm_service.py` | 4 | + LangFuse callback |
| `admin-dashboard/docker-compose.observability.yml` | 5 | NEW |
| `admin-dashboard/{prometheus,loki,promtail,grafana}/...` | 5,6 | NEW configs + dashboards |
| `src/routers/admin.py` | 7 | NEW |
| `frontend/middleware.ts` | 8 | guard /admin/* |
| `frontend/app/admin/layout.tsx` + `page.tsx` | 8,9 | NEW |
| `frontend/components/admin/*` | 8 | NEW primitives |
| `frontend/app/admin/{users,llm,traffic,system,logs}/page.tsx` | 10-14 | NEW |
| `admin-dashboard/README.md` | 15 | NEW |

## Files to Reuse

- `src/middleware/rate_limit.py` — template middleware.
- `src/core/security.py::get_current_user`.
- `frontend/components/landing/*` — pattern glass card + radial gradient.
- `frontend/components/RadarChart.tsx` — nếu cần radar.
- `tailwind.config.ts` — brand tokens, không sửa.
- `logs/qa_history.jsonl` — LLM logs source.

## Out of Scope

- Deploy production / Railway env.
- Alerting (Slack/PagerDuty).
- OpenTelemetry distributed tracing.
- Audit log table riêng (Loki đủ).
- Auth cho Grafana (anonymous local).
