# Admin Dashboard + Observability — Localhost guide

End-to-end observability stack for A20-App-049 (FastAPI + Next.js).

- **Custom admin UI** at `http://localhost:3000/admin` — built into the existing Next.js frontend (route `frontend/app/admin/`). Inherits landing-page design tokens (cyan/indigo/teal, glass cards).
- **LangFuse Cloud** — LLM tracing (traces, costs, tokens, latency).
- **Grafana** — `http://localhost:3001` — pre-provisioned dashboards: API Traffic · System Health · User Activity.
- **Prometheus** — `http://localhost:9090` — scrapes FastAPI `/metrics`, postgres_exporter, redis_exporter.
- **Loki + Promtail** — `http://localhost:3100` — tails `logs/access.jsonl` and `logs/qa_history.jsonl`.

> Phase 1–15 implemented across `src/`, `frontend/`, and this folder. See `remaining tasks/admin dashboard/plan.md` for phase-by-phase build log.

---

## ⚡ Quickstart (recommended)

`start.sh` ở repo root đã được tích hợp **observability stack + admin user check**.
Một lệnh khởi tất cả: app stack (db, redis, backend, frontend) + monitoring stack (Prometheus, Grafana, Loki, Promtail, postgres_exporter, redis_exporter).

```bash
# Lần đầu (hoặc sau khi đổi pyproject.toml / package.json) → rebuild image
bash start.sh --rebuild

# Lần kế (image đã có) → chỉ start
bash start.sh

# Bỏ qua observability nếu chỉ cần app
bash start.sh --no-observability

# Production build (không hot reload)
bash start.sh --prod
```

Sau khi xong, mở:

| Service     | URL                          | Notes                                       |
| ----------- | ---------------------------- | ------------------------------------------- |
| Frontend    | http://localhost:3000        |                                             |
| Admin UI    | http://localhost:3000/admin  | Cần login bằng user `role=admin`            |
| Backend API | http://localhost:8000        | `/docs`, `/health`, `/metrics`              |
| Grafana     | http://localhost:3001        | admin/admin · 3 dashboards auto-provisioned |
| Prometheus  | http://localhost:9090        |                                             |
| Loki        | http://localhost:3100        | Truy cập qua Grafana → Explore              |
| LangFuse    | https://cloud.langfuse.com   | Cần `LANGFUSE_*_KEY` trong `.env`           |

**Promote 1 user thành admin (lần đầu, sau khi đăng ký account):**

```bash
docker compose exec backend uv run python admin-dashboard/scripts/seed_admin.py --email <your_email>
```

**Stop tất cả:**

```bash
docker compose stop && docker compose -f admin-dashboard/docker-compose.observability.yml stop
```

> Phần dưới là hướng dẫn manual / debug nếu không dùng `start.sh`.

---

## 1. Prerequisites

- Docker Desktop / Docker Engine.
- Python 3.12, Node.js 18+ (matching repo root).
- App stack already running: `docker compose up -d db redis`.
- Backend deps managed bởi `uv` qua `pyproject.toml` (Docker tự install). Local dev: `uv sync`.
- Frontend deps: `cd frontend && npm install`.

## 2. Apply DB migration & promote first admin

```bash
# from repo root
python -m alembic upgrade head

# Replace with your registered email
python admin-dashboard/scripts/seed_admin.py --email you@example.com

# Confirm
python admin-dashboard/scripts/seed_admin.py --list
```

## 3. (Optional) Hook up LangFuse Cloud

1. Create a project at <https://cloud.langfuse.com> → Settings → API Keys.
2. Edit `.env`:
   ```env
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_HOST=https://cloud.langfuse.com
   ```
3. Restart backend.
4. Trigger any LLM endpoint — trace appears in LangFuse.
   _LangFuse is fail-safe: leaving keys blank disables tracing without breaking calls._

## 4. Start the observability stack

```bash
docker compose -f admin-dashboard/docker-compose.observability.yml up -d
```

Wait ~10s, then verify:

| URL                               | Expect                                         |
| --------------------------------- | ---------------------------------------------- |
| <http://localhost:9090/targets>   | `prometheus`, `postgres`, `redis` UP. `fastapi` UP after backend boots. |
| <http://localhost:3001>           | Grafana login `admin / admin`. Anonymous viewer enabled for embeds.    |
| <http://localhost:3001/dashboards>| 3 dashboards under "A20 Admin" folder.         |
| <http://localhost:3100/ready>     | Loki ready.                                    |

## 5. Boot backend + frontend

```bash
# terminal A
python -m uvicorn src.api.app:app --port 8000

# terminal B
cd frontend && npm run dev
```

Endpoints:

- Backend metrics: <http://localhost:8000/metrics>
- Backend health: <http://localhost:8000/health>
- Admin UI: <http://localhost:3000/admin> (login as the admin user from step 2)

## 6. Smoke check

```bash
# Generate a few requests so dashboards have data
for i in 1 2 3 4 5; do curl -s http://localhost:8000/openapi.json > /dev/null; done

# Confirm Prometheus saw them
curl -s "http://localhost:9090/api/v1/query?query=http_requests_total{job=\"fastapi\"}"

# Confirm Loki ingested access logs
curl -s -G "http://localhost:3100/loki/api/v1/labels"
```

In the admin UI, you should see:

- **/admin** — 8 KPI cards + signups area chart + LLM bar chart.
- **/admin/users** — paginated table + 30d signups chart.
- **/admin/llm** — KPI rollup + LangFuse iframe + recent events.
- **/admin/traffic** — Prometheus KPI rollup + Grafana iframe.
- **/admin/system** — CPU/RAM/DB/Redis KPIs + service status badges + live CPU/RAM line chart.
- **/admin/logs** — auto-refreshing tail of `qa_history.jsonl`.

## 7. Layout overview

```
admin-dashboard/
├── README.md                            (this file)
├── docker-compose.observability.yml     Prometheus + Grafana + Loki + Promtail + exporters
├── prometheus/prometheus.yml            scrape config
├── loki/loki-config.yml                 Loki single-binary
├── promtail/promtail-config.yml         tails ../logs/*.jsonl → Loki
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/datasources.yml  Prometheus + Loki + Postgres datasources
│   │   └── dashboards/dashboards.yml    auto-import folder
│   └── dashboards/
│       ├── api-traffic.json
│       ├── system-health.json
│       └── user-activity.json
└── scripts/
    └── seed_admin.py                    promote/demote/list admins

src/
├── core/observability.py                LangFuse handler (fail-safe singleton)
├── middleware/
│   ├── prometheus.py                    /metrics endpoint setup
│   └── request_logger.py                JSON access log → logs/access.jsonl
├── routers/admin.py                     /api/admin/* endpoints
└── dependencies/auth.py                 require_admin dep

frontend/
├── app/admin/
│   ├── layout.tsx                       admin guard + topbar + sidebar
│   ├── page.tsx                         overview (KPI grid + charts)
│   ├── users/page.tsx
│   ├── llm/page.tsx
│   ├── traffic/page.tsx
│   ├── system/page.tsx
│   └── logs/page.tsx
├── components/admin/                    KpiCard · ChartCard · StatusBadge · AdminTopbar · AdminSidebar
└── lib/admin-api.ts                     typed wrappers around /api/admin/*

logs/
├── access.jsonl                         created by request_logger middleware
└── qa_history.jsonl                     created by llm_service.py (existing)
```

## 8. Stop everything

```bash
# Nếu start bằng start.sh (cả 2 stack)
docker compose stop && docker compose -f admin-dashboard/docker-compose.observability.yml stop

# Hoặc chỉ tắt observability:
docker compose -f admin-dashboard/docker-compose.observability.yml down

# Xoá hoàn toàn (giữ data volume):
docker compose down && docker compose -f admin-dashboard/docker-compose.observability.yml down
```

App stack (`db`, `redis`, `backend`, `frontend`) và observability stack chạy độc lập với nhau — có thể stop từng cái.

## 9. Khi nào cần rebuild image?

| Thay đổi | Hành động |
| --- | --- |
| `pyproject.toml` / `uv.lock` (backend deps) | `bash start.sh --rebuild` |
| `frontend/package.json` / `package-lock.json` | `bash start.sh` (auto-detect) hoặc `--rebuild` để chắc chắn |
| File `src/**/*.py` | Không cần — uvicorn `--reload` (dev mode) |
| File `frontend/**/*.tsx` | Không cần — Next.js HMR (dev mode) |
| `admin-dashboard/grafana/**` (dashboards, datasources) | `docker compose -f admin-dashboard/docker-compose.observability.yml restart grafana` |
| `admin-dashboard/prometheus/prometheus.yml` | `docker compose -f admin-dashboard/docker-compose.observability.yml restart prometheus` |
| `admin-dashboard/promtail/promtail-config.yml` | `docker compose -f admin-dashboard/docker-compose.observability.yml restart promtail` |
| `admin-dashboard/docker-compose.observability.yml` | `docker compose -f admin-dashboard/docker-compose.observability.yml up -d` (recreate) |

## 10. Troubleshooting

| Symptom                                          | Fix                                                                       |
| ------------------------------------------------ | ------------------------------------------------------------------------- |
| `fastapi` target shows `down` in Prometheus      | Start `uvicorn src.api.app:app --port 8000` on the host.                  |
| Grafana iframe blank in `/admin/traffic`         | Open `http://localhost:3001` once and accept the anonymous viewer cookie. |
| `/admin` redirects you to `/tutor`               | Your account is `role=user`. Run `seed_admin.py --email <e>`.             |
| Postgres datasource health "ERROR" in Grafana    | Ensure `al_db` exposes 5433 on host (already true in `docker-compose.yml`). |
| LangFuse traces never appear                     | Check backend logs for "LangFuse v3 callback handler initialised". Verify `LANGFUSE_*` env vars.|
| `logs/access.jsonl` empty                        | The middleware skips `/health` and `/metrics`. Hit any other endpoint.    |

## 11. Out of scope (future work)

- Production deploy (Railway env, secrets, public URLs).
- Alertmanager / PagerDuty / Slack alerting.
- OpenTelemetry distributed tracing.
- Audit log table separate from Loki.
- Authentication on Grafana (currently anonymous viewer for local embed).
