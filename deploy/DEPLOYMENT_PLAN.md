# Deployment Plan — Railway (Demo, 1–2 tuần)

## Mục tiêu

Deploy nhanh để chạy demo 1–2 tuần. Không cần production-grade.

- Public frontend (Next.js)
- Public backend API (FastAPI)
- PostgreSQL + pgvector
- Redis
- Tất cả trên **một** platform: Railway

## Tại sao Railway

- Hỗ trợ deploy thẳng từ `docker-compose.yml` / Dockerfile của repo, không cần viết lại.
- Có sẵn plugin **Postgres (kèm `pgvector`)** và **Redis** — không cần host ngoài.
- Không cold-start (khác Render Free).
- $5 trial credit + Hobby plan đủ cho demo nhỏ 1–2 tuần.
- Tự cấp HTTPS + domain `*.up.railway.app`, không cần Caddy/Nginx/Let's Encrypt.
- Một dashboard quản lý 4 service.

## Kiến trúc demo

```text
Internet
  -> https://<frontend>.up.railway.app   (Next.js service)
  -> https://<backend>.up.railway.app    (FastAPI service)
       -> Postgres plugin (pgvector)
       -> Redis plugin
```

## Service breakdown trên Railway

Tạo **1 project** chứa 4 service:

| Service | Nguồn | Ghi chú |
|---|---|---|
| `backend` | Repo, root build context = `/`, Dockerfile = `Dockerfile` | Expose port `8000` |
| `frontend` | Repo, root build context = `frontend/`, Dockerfile = `frontend/Dockerfile` | Expose port `3000` |
| `postgres` | Railway plugin **Postgres** | Bật extension `pgvector` (xem dưới) |
| `redis` | Railway plugin **Redis** | Mặc định đủ |

## Bước deploy

### 1. Chuẩn bị repo

- Push branch `deploy-plan` lên GitHub.
- Đảm bảo `Dockerfile` (backend) và `frontend/Dockerfile` build được standalone (không phụ thuộc compose).

### 2. Tạo Railway project

1. railway.app → **New Project** → **Deploy from GitHub repo** → chọn repo này.
2. Railway tự detect Dockerfile. Đặt tên service: `backend`.
3. **+ New** → **Database** → **Add PostgreSQL**.
4. **+ New** → **Database** → **Add Redis**.
5. **+ New** → **GitHub Repo** (cùng repo) → đặt tên `frontend`. Vào **Settings → Build → Root Directory** = `frontend`.

### 3. Bật pgvector trên Postgres plugin

Vào service Postgres → tab **Data** (hoặc connect bằng `psql` qua `DATABASE_PUBLIC_URL`):

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Verify:
```sql
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

### 4. Set environment variables

Xem chi tiết trong `ENVIRONMENT_MATRIX.md`. Tóm tắt:

**Service `backend`:**
- `DATABASE_URL` = `${{Postgres.DATABASE_URL}}` nhưng đổi prefix thành `postgresql+asyncpg://` (Railway cấp `postgresql://`)
- `REDIS_URL` = `${{Redis.REDIS_URL}}`
- `SECRET_KEY` = random 64 hex (`openssl rand -hex 32`)
- `CORS_ORIGINS` = `["https://<frontend-domain>.up.railway.app"]`
- `MODEL_PROVIDER`, `OPENAI_API_KEY` (hoặc provider khác)
- `DEBUG=false`, `LOG_LEVEL=INFO`
- `PORT=8000` (Railway tự inject `PORT`, đảm bảo backend bind `0.0.0.0:$PORT`)

**Service `frontend`:**
- `NEXT_PUBLIC_API_URL` = `https://<backend-domain>.up.railway.app`
- `NODE_ENV=production`
- `PORT=3000`

> Railway dùng cú pháp `${{ServiceName.VAR}}` để reference biến giữa service.

### 5. Generate public domain

Mỗi service `backend`, `frontend` → **Settings → Networking → Generate Domain**.

Sau đó cập nhật lại:
- `CORS_ORIGINS` (backend) với domain thật của frontend
- `NEXT_PUBLIC_API_URL` (frontend) với domain thật của backend
- Frontend phải **rebuild** sau khi đổi `NEXT_PUBLIC_API_URL` (Railway tự rebuild khi env đổi).

### 6. Chạy migration + seed dữ liệu

Trên service `backend`, mở **Shell** (hoặc cài `railway` CLI và chạy `railway run`):

```bash
uv run alembic upgrade head
uv run python -m src.scripts.pipeline.import_canonical_artifacts_to_db
uv run python -m src.scripts.pipeline.import_product_shell_to_db
uv run python -m src.scripts.pipeline.check_canonical_runtime_parity
```

### 7. Smoke test

- `https://<backend>/health` → 200
- `https://<frontend>/api/health` → 200
- Frontend home load được
- Login/register flow OK
- 1 course page load được
- 1 quiz session start + submit được

## Course assets (`data/courses/`)

Demo: build asset thẳng vào image backend (đã có trong repo, sẽ được COPY bởi Dockerfile).

Nếu asset quá lớn (>500MB) làm image phình:
- Tạm thời commit chỉ asset của 1–2 course demo
- Long-term: chuyển object storage (out of scope cho demo)

## Chi phí ước tính

- $5 trial credit Railway → đủ ~2–3 tuần với demo traffic thấp.
- Sau đó Hobby plan $5/tháng + usage (~$5–10/tháng cho stack này).
- LLM cost (OpenAI/Anthropic) tách riêng, không qua Railway.

## Rollback

- Railway giữ history deployment. Mỗi service → tab **Deployments** → chọn bản cũ → **Redeploy**.
- DB migration: trước khi chạy migration mới, snapshot Postgres plugin (Railway có nút **Backup** trên paid plan; Hobby chưa có → dump thủ công nếu cần).

## Sau demo

Khi cần production thật → quay lại VM + Docker Compose + reverse proxy (xem git history của file này) hoặc nâng plan Railway.

## Out of scope cho demo

- TLS thủ công (Railway lo)
- Reverse proxy config (Railway lo)
- Backup runbook (snapshot Railway hoặc dump tay khi cần)
- CI/CD pipeline (Railway tự deploy mỗi `git push`)
- Observability stack riêng (dùng built-in logs/metrics của Railway)
- Rate limiting tầng proxy (FastAPI middleware là đủ cho demo)
