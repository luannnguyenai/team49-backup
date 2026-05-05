# Deployment Plan — Render + AWS Assets

## Requirement lock

User requirements:

- Deploy bằng **Render**, không dùng Railway.
- Sau deploy sẽ mua và gắn custom domain.
- Data/course/video assets đẩy lên **AWS S3** và stream qua **CloudFront**.
- Kế hoạch phải chia phase như cũ.
- **Mỗi phase chỉ làm 1 task**.
- Mỗi phase phải có **DoD checklist**.
- Mỗi phase phải ghi rõ **files sẽ touch**.
- Thay đổi phải **isolated**, tránh ảnh hưởng logic khác.

## Target architecture

```text
Browser
  ├─ Render frontend: Next.js
  │    temp:  https://<frontend>.onrender.com
  │    final: https://app.<domain> hoặc https://<domain>
  │
  ├─ Render backend: FastAPI
  │    temp:  https://<backend>.onrender.com
  │    final: https://api.<domain>
  │    deps:  Render PostgreSQL + pgvector, Render Redis/Key Value
  │
  └─ AWS CloudFront CDN
       final: https://cdn.<domain>
       origin: private S3 bucket
```

Critical rule: video/large assets phải stream trực tiếp `CloudFront -> Browser`. Backend không proxy video bytes từ S3 về user.

## Global rules

1. **One task per phase**: không gom infra + code + data + validation vào cùng phase.
2. **DoD gate**: phase sau chỉ bắt đầu khi DoD phase trước pass.
3. **Isolation**:
   - Không refactor unrelated auth, quiz, planner, recommendation, course ordering.
   - Không đổi DB schema nếu phase không yêu cầu.
   - Không đổi UI/UX nếu phase không yêu cầu.
   - Giữ local dev chạy được.
4. **Asset provider must be config-driven**:
   - `ASSET_STORAGE_PROVIDER=local`: giữ behavior local `/data/...` hiện tại.
   - `ASSET_STORAGE_PROVIDER=s3`: trả CloudFront URL.
5. **No secrets in git**: Render/AWS/DB/Redis/LLM keys chỉ set trong dashboard/secret manager.

## Phase overview

| Phase | Single task |
|---:|---|
| 0 | Lock deploy variables |
| 1 | Make backend Docker Render-compatible |
| 2 | Make frontend Docker Render-compatible |
| 3 | Create private S3 bucket |
| 4 | Upload course assets to S3 |
| 5 | Create CloudFront distribution |
| 5.1 | (Conditional) Set up CloudFront signed URL keys |
| 6 | Add asset delivery config |
| 7 | Add CloudFront asset URL service |
| 8 | Switch course asset URL generation behind config |
| 9 | Create Render PostgreSQL |
| 10 | Enable pgvector |
| 11 | Create Render Redis/Key Value |
| 12 | Deploy backend to Render |
| 13 | Run database migrations |
| 13.5 | Create `scripts/render_bootstrap.sh` wrapper |
| 14 | Run full bootstrap pipeline on Render |
| 14.1 | Verify S3 ↔ DB asset key parity |
| 15 | Deploy frontend to Render |
| 16 | Smoke test on Render temporary domains |
| 17 | Attach frontend/backend custom domains |
| 18 | Attach CDN custom domain |
| 19 | Final production-readiness check |
| 20 | Document rollback commands |

---

## Phase 0 — Lock deploy variables

### Task

Chốt biến triển khai trước khi sửa code hoặc tạo cloud resources.

### Files that will be touched

- `deploy/DEPLOYMENT_PLAN.md` only if decisions are recorded.

### Locked decisions

| Hạng mục | Giá trị |
|---|---|
| AWS region | `ap-southeast-1` (Singapore) |
| Render region | `Oregon` (free tier mặc định, chấp nhận cold start + Postgres free expire 90 ngày) |
| Backend service name | `backend` |
| Frontend service name | `frontend` |
| Postgres service name | `db` |
| Redis service name | `redis` |
| S3 bucket name | `a20-course-assets-prod` |
| Demo data | Upload toàn bộ 3 course `CS224n`, `CS230`, `CS231n` (~15GB) lên S3 |
| Custom domain | Mua ở **cuối** sau khi smoke test pass; Phase 17–18 mới gắn |
| Tạm thời dùng | `https://<service>.onrender.com` và `https://<distribution>.cloudfront.net` |

### Steps

1. Chọn AWS region (đã chốt).
2. Chọn Render region (đã chốt).
3. Chốt service names (đã chốt).
4. Hoãn quyết định domain layout đến trước Phase 17.
5. Chốt scope data demo (đã chốt).

### DoD checklist

- [ ] AWS region recorded.
- [ ] Render region recorded.
- [ ] Service names recorded.
- [ ] Domain layout recorded.
- [ ] Demo asset scope recorded.
- [ ] No code/cloud resource changed before decisions are complete.

### Isolation guard

Planning only. Không sửa Dockerfile, app code, DB, AWS, Render.

---

## Phase 1 — Make backend Docker Render-compatible

### Task

Cho backend container listen đúng Render runtime port.

### Why this is must-fix

Root `Dockerfile` hiện đang hard-code `--port 8000`. Render inject biến `PORT` runtime (thường `10000`) và health-check ở port đó. Nếu không sửa, deploy Render sẽ fail health check ngay lần đầu. Phase này **bắt buộc** thay đổi `Dockerfile`, không phải optional.

### Files that will be touched

- `Dockerfile` (must)
- `.dockerignore` only if build context includes unnecessary large assets.

### Steps

1. Update Uvicorn command để bind `0.0.0.0:${PORT:-8000}`. Yêu cầu shell expansion → dùng dạng `CMD ["sh", "-c", "uv run python -m uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]` hoặc tương đương.
2. Giữ app module `src.api.app:app`.
3. Không đổi dependency install nếu build chưa fail.
4. Không sửa API/business logic.

### DoD checklist

- [ ] Backend Dockerfile uses `$PORT` with fallback `8000` (verified by reading Dockerfile, không phải optional).
- [ ] `docker build -t a20-backend .` succeeds, or failure is documented as local tooling issue.
- [ ] Container starts with default port `8000` when `PORT` is not set.
- [ ] Container starts with overridden `PORT` (ví dụ `docker run -e PORT=10000 -p 10000:10000 ...`).
- [ ] `/health` returns 200 locally on the chosen port.
- [ ] No backend business logic files changed.

### Isolation guard

Only container startup is in scope. Không chạm auth, DB, course, quiz, LLM, planner, recommendation, asset logic.

---

## Phase 2 — Make frontend Docker Render-compatible

### Task

Cho frontend container compatible với Render runtime/build.

### Files that may be touched

- `frontend/Dockerfile`
- `frontend/next.config.mjs` only if standalone output is missing/broken.

### Steps

1. Ensure runner listens on Render expected port.
2. Preserve `NEXT_PUBLIC_API_URL` as build-time value.
3. Preserve `API_INTERNAL_URL` for server-side calls.
4. Không đổi pages/components.

### DoD checklist

- [ ] `docker build -t a20-frontend ./frontend` succeeds, or failure is documented as local tooling issue.
- [ ] Container starts with default port `3000`.
- [ ] Container starts with overridden `PORT` if Render requires it.
- [ ] `/api/health` returns 200 locally.
- [ ] `NEXT_PUBLIC_API_URL` can be supplied at build time.
- [ ] No UI/page/component logic changed.

### Isolation guard

Only frontend container/runtime is in scope. Không đổi UX, routing, auth flow, onboarding, course pages, quiz.

---

## Phase 3 — Create private S3 bucket

### Task

Tạo một private S3 bucket cho course/video assets.

### Files that will be touched

- None required in repo.

### Steps

1. Create bucket, example `a20-course-assets-prod`.
2. Set region from Phase 0.
3. Enable Block Public Access.
4. Decide whether to enable versioning.
5. Do not upload data in this phase.
6. Do not create CloudFront in this phase.

### DoD checklist

- [ ] S3 bucket exists.
- [ ] Bucket region matches Phase 0.
- [ ] Block Public Access enabled.
- [ ] Bucket is not publicly listable.
- [ ] Versioning decision recorded.
- [ ] No app code changed.

### Isolation guard

Only bucket creation. Không upload data, không tạo CloudFront, không sửa code.

---

## Phase 4 — Upload course assets to S3

### Task

Upload selected course assets lên private S3 bucket.

### Files that will be touched

- None required in repo.

### Steps

1. Configure AWS CLI locally with upload/admin credentials.
2. Dry-run:

```bash
aws s3 sync ./data/courses s3://<bucket>/courses --dryrun
```

3. Actual sync:

```bash
aws s3 sync ./data/courses s3://<bucket>/courses
```

4. Record object count and total size.

### DoD checklist

- [ ] Dry-run matches expected files.
- [ ] Actual sync completes without error.
- [ ] S3 object count recorded.
- [ ] S3 total size recorded.
- [ ] At least one expected video exists in S3.
- [ ] No AWS admin credentials committed.
- [ ] No app code changed.

### Isolation guard

Only binary/static data upload. Không đổi metadata scripts, app code, DB, CloudFront.

---

## Phase 5 — Create CloudFront distribution

### Task

Tạo một CloudFront distribution cho S3 asset bucket.

### Files that will be touched

- None required in repo.

### Steps

1. Create CloudFront distribution.
2. Set S3 bucket as origin.
3. Use Origin Access Control so S3 remains private.
4. Allow methods `GET`, `HEAD`.
5. Redirect HTTP to HTTPS.
6. Use cache policy for static/video assets.
7. Confirm range requests work for MP4 seeking.
8. Do not attach custom CDN domain yet.

### DoD checklist

- [ ] CloudFront distribution deployed.
- [ ] S3 bucket remains private.
- [ ] CloudFront can read objects through OAC.
- [ ] One test asset loads through CloudFront.
- [ ] MP4 seek/range request works.
- [ ] Direct public S3 URL does not expose private object.
- [ ] No app code changed.

### CORS note

Nếu frontend chỉ dùng `<video src="...">` thông thường, không cần CORS policy.
Nếu frontend gọi `fetch()`/range XHR/HLS player tự custom, cần Response Headers Policy ở CloudFront set `Access-Control-Allow-Origin` cho frontend domain. Đây là sub-task tùy use case, không bắt buộc trong phase này.

### Isolation guard

Only default CloudFront delivery. Custom domain and app integration are separate phases.

---

## Phase 5.1 — (Conditional) Set up CloudFront signed URL keys

### Trigger

Chỉ chạy phase này nếu **chọn bảo vệ asset bằng CloudFront signed URL**. Bỏ qua nếu demo chấp nhận asset truy cập public qua CloudFront domain.

### Task

Tạo CloudFront key pair / public key / key group cho signed URL.

### Files that will be touched

- None required in repo.
- Render dashboard sẽ nhận secret ở phase deploy backend (Phase 12).

### Steps

1. Generate RSA key pair tại máy admin:

```bash
openssl genrsa -out cloudfront_private_key.pem 2048
openssl rsa -pubout -in cloudfront_private_key.pem -out cloudfront_public_key.pem
```

2. AWS Console → CloudFront → Public keys → upload `cloudfront_public_key.pem`. Lưu `Public key ID`.
3. Tạo Key Group chứa public key đó.
4. Gắn Key Group vào CloudFront distribution behavior cần signing (Restrict viewer access → Trusted key groups).
5. Lưu `cloudfront_private_key.pem` an toàn (password manager / secret store). **Không commit vào git.**
6. Ghi nhận:
   - `CLOUDFRONT_KEY_PAIR_ID` = ID của Public key.
   - `CLOUDFRONT_PRIVATE_KEY` = nội dung file PEM.

### DoD checklist

- [ ] CloudFront public key uploaded với ID rõ ràng.
- [ ] Key group active, gắn vào đúng behavior của distribution.
- [ ] Private key được lưu trong secret store, không nằm trong repo.
- [ ] Test 1 signed URL bằng AWS SDK/CLI tạo từ private key → access được object qua CloudFront.
- [ ] URL không signed bị reject (nếu behavior yêu cầu signed).
- [ ] `CLOUDFRONT_KEY_PAIR_ID` đã ghi vào nơi sẽ paste lên Render env.
- [ ] `CLOUDFRONT_PRIVATE_KEY` đã ghi vào nơi sẽ paste lên Render env.

### Isolation guard

Only signing infra. Không refactor app code, không thay đổi service code Phase 7. App phía code chỉ đọc env, không sinh key.

---

## Phase 6 — Add asset delivery config

### Task

Thêm config fields cho local-vs-S3 asset delivery.

### Files that may be touched

- `src/config.py`
- `deploy/.env.production.example`
- `deploy/ENVIRONMENT_MATRIX.md`

### Config keys

```text
ASSET_STORAGE_PROVIDER=local|s3
AWS_REGION=<region>
AWS_S3_BUCKET=<bucket>
AWS_S3_PREFIX=courses
CLOUDFRONT_DOMAIN=<distribution>.cloudfront.net
CLOUDFRONT_KEY_PAIR_ID=<optional>
CLOUDFRONT_PRIVATE_KEY=<optional>
ASSET_URL_EXPIRE_SECONDS=900
```

### Steps

1. Add typed config fields in `src/config.py`.
2. Default `ASSET_STORAGE_PROVIDER` to `local`.
3. AWS/CloudFront fields optional when provider is `local`.
4. Update env docs/templates with placeholders only.
5. Do not change URL generation behavior yet.

### DoD checklist

- [ ] App starts locally without AWS env values.
- [ ] Existing local asset behavior unchanged.
- [ ] Config parses `ASSET_STORAGE_PROVIDER=local`.
- [ ] Config parses `ASSET_STORAGE_PROVIDER=s3` with required placeholders/manual check.
- [ ] Env docs contain no real secrets.
- [ ] No course/asset service behavior changed yet.

### Isolation guard

Only config. Không đổi routes, DB models, frontend, actual asset URL generation.

---

## Phase 7 — Add CloudFront asset URL service

### Task

Thêm service nhỏ build CloudFront asset URL từ storage key.

### Files that may be touched

- `src/services/asset_signing.py` if extending current signing logic.
- Or new file: `src/services/asset_delivery.py`.
- `tests/services/test_asset_delivery.py` if tests are added.

### Steps

1. Create function accepting normalized storage key.
2. Return CloudFront URL using `CLOUDFRONT_DOMAIN` and prefix rules.
3. If signed CloudFront URL is implemented now, use configured TTL.
4. If signing is deferred, keep interface ready and return unsigned demo URL.
5. Reject unsafe paths: `../`, absolute paths, duplicate leading slashes.
6. Do not call S3 or stream file bytes.

### DoD checklist

- [ ] Service returns stable CloudFront URL for valid key.
- [ ] Service rejects path traversal.
- [ ] Service does not require AWS admin credentials.
- [ ] Service does not proxy/download S3 objects.
- [ ] Test/manual check covers valid key and unsafe key.
- [ ] Existing local signing function still works.

### Isolation guard

Only reusable asset URL builder. Không wire vào course APIs, frontend, DB imports.

---

## Phase 8 — Switch course asset URL generation behind config

### Task

Dùng config provider để chọn local signed URL hoặc CloudFront URL cho course assets.

### Files that may be touched

- `src/services/learning_unit_service.py`
- `src/services/content_service.py` if it owns returned video URL behavior.
- Nearby focused tests if available.

### Steps

1. Locate exact code path returning video/asset URLs to frontend.
2. Add provider branch:
   - `local`: preserve existing `/data/...` signed URL behavior.
   - `s3`: return CloudFront asset URL from Phase 7 service.
3. Keep API field names unchanged.
4. Do not change course selection, quiz, auth, planner, recommendation logic.
5. Add/update focused tests for both modes if available.

### DoD checklist

- [ ] `ASSET_STORAGE_PROVIDER=local` keeps existing local asset URLs working.
- [ ] `ASSET_STORAGE_PROVIDER=s3` returns CloudFront domain URLs.
- [ ] API response schema remains backward compatible.
- [ ] No video bytes are served through backend in S3 mode.
- [ ] Focused tests pass, or manual verification is documented.
- [ ] No unrelated service logic changed.

### Isolation guard

Only asset URL selection. Không refactor course loading, content ordering, auth, quiz, DB schema.

---

## Phase 9 — Create Render PostgreSQL

### Task

Tạo một Render PostgreSQL instance.

### Files that will be touched

- None required in repo.

### Steps

1. Create Render PostgreSQL service named `a20-postgres`.
2. Choose region from Phase 0.
3. Choose demo-appropriate plan.
4. Record connection strings securely.
5. Do not run migrations.
6. Do not enable extensions.

### DoD checklist

- [ ] Render PostgreSQL service exists.
- [ ] Region matches Phase 0 or exception is recorded.
- [ ] Connection string is available securely.
- [ ] Database accepts connection from Render shell or trusted local IP.
- [ ] No schema migration has been run.
- [ ] No repo files changed.

### Isolation guard

Only DB service creation. Extension setup and migrations are separate phases.

---

## Phase 10 — Enable pgvector

### Task

Enable `vector` extension in Render PostgreSQL.

### Files that will be touched

- None required in repo.

### Steps

```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

### DoD checklist

- [ ] `CREATE EXTENSION` completed successfully.
- [ ] Verify query returns `vector`.
- [ ] No migration was run in this phase.
- [ ] No repo files changed.

### Isolation guard

Only DB extension setup. Không tạo tables, import data, sửa app code.

---

## Phase 11 — Create Render Redis/Key Value

### Task

Tạo một Render Redis-compatible Key Value service.

### Files that will be touched

- None required in repo.

### Steps

1. Create Render Key Value service named `a20-redis`.
2. Choose region compatible with backend.
3. Record `REDIS_URL` securely.
4. Do not connect app to it yet.

### DoD checklist

- [ ] Render Key Value service exists.
- [ ] `REDIS_URL` is available securely.
- [ ] Region/network decision recorded.
- [ ] No backend deployment changed yet.
- [ ] No repo files changed.

### Isolation guard

Only Redis creation. Backend env wiring happens during backend deploy.

---

## Phase 12 — Deploy backend to Render

### Task

Deploy FastAPI backend web service on Render.

### Files that may be touched

- None if Phase 1 is complete.
- Render dashboard/env only.

### Required backend env

```text
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://... or rediss://...
SECRET_KEY=<secret>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=["https://<frontend>.onrender.com"]
FRONTEND_BASE_URL=https://<frontend>.onrender.com
MODEL_PROVIDER=<provider>
OPENAI_API_KEY=<secret if using OpenAI>
DEBUG=false
LOG_LEVEL=INFO
ASSET_STORAGE_PROVIDER=s3
AWS_REGION=<region>
AWS_S3_BUCKET=<bucket>
AWS_S3_PREFIX=courses
CLOUDFRONT_DOMAIN=<distribution>.cloudfront.net
ASSET_URL_EXPIRE_SECONDS=900
```

### Steps

1. Create Render Web Service from GitHub repo.
2. Runtime: Docker.
3. Dockerfile path: root `Dockerfile`.
4. Set env variables.
5. Health check path: `/health`.
6. Deploy.

### DoD checklist

- [ ] Backend deploy succeeds.
- [ ] Backend URL recorded.
- [ ] `GET /health` returns 200.
- [ ] Logs show no missing required env values.
- [ ] Logs do not print secrets.
- [ ] Backend does not run migrations automatically unless explicitly configured.

### Isolation guard

Only backend deploy. Không chạy migrations, import scripts, frontend deploy, domain changes.

---

## Phase 13 — Run database migrations

### Task

Run Alembic migrations against Render PostgreSQL.

### Files that may be touched

- None expected.
- Migration files only if a targeted migration bug is found.

### Steps

Run in Render backend shell/job:

```bash
uv run alembic upgrade head
```

### DoD checklist

- [ ] `alembic upgrade head` completes successfully.
- [ ] Current DB revision equals repository head revision.
- [ ] No seed/import script was run.
- [ ] No app code changed unless fixing migration-specific failure.
- [ ] Any migration fix is targeted and reviewed separately.

### Isolation guard

Only schema migration. Không import data, deploy frontend, change cloud infra.

---

## Phase 13.5 — Create `scripts/render_bootstrap.sh` wrapper

### Task

Tạo 1 script duy nhất gói toàn bộ pipeline bootstrap (seed + import + schema-v2 backfill/validate + parity + admin seed) để Phase 14 chỉ chạy 1 lệnh trên Render shell.

### Why this matters

`start.sh` hiện tại chạy nhiều bước trên local. Render shell không có Docker compose, chạy trực tiếp trong container backend. Nếu copy-paste 6-7 lệnh thì dễ rớt giữa chừng và khó tái lập. Một wrapper idempotent sẽ:

- Giữ đúng thứ tự như `start.sh` đã chứng minh hoạt động.
- Idempotent: chạy lại vẫn an toàn.
- Dễ rerun sau redeploy.
- Fail-fast khi có lỗi.

### Files that will be touched

- `scripts/render_bootstrap.sh` (new)

### Files reference (read-only, không sửa)

- `start.sh` (mẫu logic gốc, đặc biệt Bước 3, 3.5, 6).
- `scripts/seed.py`
- `scripts/seed_lectures.py`
- `src/scripts/pipeline/import_canonical_artifacts_to_db.py`
- `src/scripts/pipeline/import_product_shell_to_db.py` (nếu tồn tại; có thể bị thay bởi `seed.py`)
- `src/scripts/schema_v2/backfill_schema_v2.py`
- `src/scripts/schema_v2/validate_schema_v2.py`
- `src/scripts/pipeline/check_canonical_runtime_parity.py`
- `src/scripts/create_seed_accounts.py`

### Script outline

Script chạy trong container backend, không dùng `docker compose exec`:

```bash
#!/usr/bin/env bash
# scripts/render_bootstrap.sh
# Idempotent bootstrap for Render backend shell.
set -euo pipefail

log() { echo "[bootstrap] $*"; }

log "1/8 alembic upgrade head"
uv run alembic upgrade head

log "2/8 seed canonical product shell (skip if learning_units already populated)"
UNIT_COUNT=$(uv run python -c "
import asyncio, os
from sqlalchemy import text
from src.database import async_session_maker
async def main():
    async with async_session_maker() as s:
        r = await s.execute(text('SELECT COUNT(*) FROM learning_units'))
        print(r.scalar() or 0)
asyncio.run(main())
" || echo 0)
if [ "${UNIT_COUNT}" = "0" ]; then
  uv run python scripts/seed.py
else
  log "  -> skipped (${UNIT_COUNT} units already)"
fi

log "3/8 seed CS231n lectures (skip if lectures populated)"
LECTURE_COUNT=$(uv run python -c "
import asyncio
from sqlalchemy import text
from src.database import async_session_maker
async def main():
    async with async_session_maker() as s:
        r = await s.execute(text('SELECT COUNT(*) FROM lectures'))
        print(r.scalar() or 0)
asyncio.run(main())
" || echo 0)
if [ "${LECTURE_COUNT}" = "0" ]; then
  uv run python scripts/seed_lectures.py || log "  -> seed_lectures failed (non-fatal)"
else
  log "  -> skipped (${LECTURE_COUNT} lectures already)"
fi

log "4/8 import canonical artifacts schema v2"
uv run python -m src.scripts.pipeline.import_canonical_artifacts_to_db

log "5/8 backfill schema v2"
uv run python -m src.scripts.schema_v2.backfill_schema_v2 --apply --report-path reports/schema_v2_backfill_report.json

log "6/8 validate schema v2"
uv run python -m src.scripts.schema_v2.validate_schema_v2 --report-path reports/schema_v2_validation_report.json

log "7/8 canonical runtime parity"
uv run python -m src.scripts.pipeline.check_canonical_runtime_parity

log "8/8 create admin/demo accounts (idempotent)"
uv run python -m src.scripts.create_seed_accounts

log "bootstrap complete"
```

### Implementation rules

1. Phải `set -euo pipefail` để fail-fast.
2. Mỗi bước phải log số thứ tự để Render log dễ trace.
3. Các bước seed phải kiểm tra state trước khi chạy (idempotent).
4. Không assume `docker compose exec` — chạy thẳng trong container.
5. Không thay logic của các script Python được gọi.
6. Script được mark executable: `chmod +x scripts/render_bootstrap.sh`, hoặc gọi qua `bash scripts/render_bootstrap.sh`.

### DoD checklist

- [ ] File `scripts/render_bootstrap.sh` tồn tại.
- [ ] Script có shebang `#!/usr/bin/env bash` và `set -euo pipefail`.
- [ ] Có log thứ tự 1/8 → 8/8.
- [ ] Bước seed/seed_lectures có guard idempotent.
- [ ] Chạy thử local trong container backend (`docker compose exec backend bash scripts/render_bootstrap.sh`) thành công lần 1.
- [ ] Chạy thử local lần 2 vẫn thành công, các bước seed report `skipped`.
- [ ] Không sửa script Python nào trong `src/scripts/` hoặc `scripts/`.
- [ ] Không thay đổi `start.sh` hiện hữu.

### Isolation guard

Chỉ thêm 1 file shell. Không sửa Python source, không sửa migration, không sửa Dockerfile. Local dev tiếp tục dùng `start.sh` như cũ.

---

## Phase 14 — Run full bootstrap pipeline on Render

### Task

Chạy `scripts/render_bootstrap.sh` trên Render backend shell để khởi tạo DB hoàn chỉnh: schema, content, lectures, canonical v2, parity, admin/demo users.

### Files that may be touched

- None in repo.
- Optional: import scripts trong `src/scripts/...` chỉ khi phát hiện bug import (targeted fix, separate review).

### Steps

1. Mở Render backend shell (Render dashboard → Shell).
2. Verify cwd là repo root (chứa `Dockerfile`, `pyproject.toml`).
3. Verify env có:
   - `DATABASE_URL` (postgresql+asyncpg)
   - `REDIS_URL`
   - `MODEL_PROVIDER` + API key tương ứng
4. Chạy:

```bash
bash scripts/render_bootstrap.sh
```

5. Đọc log từ 1/8 → 8/8 không có error.
6. Verify dữ liệu nhanh:

```bash
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM learning_units;"
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM lectures;"
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM users WHERE role='admin';"
```

### DoD checklist

- [ ] `bash scripts/render_bootstrap.sh` exit code 0.
- [ ] Log show alembic ran (1/8).
- [ ] `learning_units` count > 0.
- [ ] `lectures` count > 0 (CS231n).
- [ ] Canonical artifact import OK (4/8).
- [ ] Schema v2 backfill OK (5/8).
- [ ] Schema v2 validate OK (6/8).
- [ ] Canonical runtime parity OK (7/8).
- [ ] Admin user count >= 1 (8/8).
- [ ] Backend `/health` vẫn 200 sau khi bootstrap.
- [ ] Không có lỗi trong log Render backend service.

### Failure handling

- Nếu bước 4 (canonical artifact) fail → kiểm tra biến `ASSET_STORAGE_PROVIDER`/`AWS_*` đã set chưa (Phase 12).
- Nếu bước 5/6 (schema v2) fail → snapshot DB rồi report; không tự sửa data tay.
- Nếu bước 7 (parity) fail → đây là defensive check, có thể là tín hiệu artifact và DB lệch nhau, cần root-cause trước khi tiếp Phase 15.

### Isolation guard

Chỉ chạy script đã review ở Phase 13.5. Không sửa source code Python trong phase này. Không deploy frontend, không đụng AWS infra.

---

## Phase 14.1 — Verify S3 ↔ DB asset key parity

### Task

Đảm bảo `storage_key` / `video_filename` trong Render Postgres trỏ đúng tên object thực tế trên S3, để CloudFront URL không bị 404.

### Why this matters

Code hiện build asset URL kiểu `f"courses/<course>/videos/<filename>"`. Nếu DB ghi `Lecture1.mp4` mà S3 có `lecture1.mp4`, video sẽ không phát được. Phase này bắt buộc khi `ASSET_STORAGE_PROVIDER=s3`.

### Files that may be touched

- None expected.
- Optional helper script (read-only): `src/scripts/pipeline/check_s3_asset_parity.py` nếu chưa có và muốn tự động hóa.

### Steps

1. List object keys S3 dưới prefix `courses/`:

```bash
aws s3 ls s3://<bucket>/courses/ --recursive > s3_keys.txt
```

2. Export `storage_key`/`video_filename` từ DB ra CSV (qua psql hoặc một script đọc-only).
3. Diff hai danh sách:
   - Object S3 thiếu trong DB: thường OK, có thể là tài nguyên dư.
   - Storage key DB không tồn tại trên S3: **fail**, phải fix trước khi deploy frontend.
4. Với entry mismatch, chọn 1 trong 2:
   - Đổi tên object S3 cho khớp DB.
   - Update DB metadata cho khớp S3 (chỉ qua import script chuẩn, không sửa tay nếu tránh được).
5. Re-run diff đến khi 0 mismatch ở chiều DB → S3.

### DoD checklist

- [ ] Snapshot S3 keys đã ghi lại.
- [ ] Snapshot DB `storage_key`/`video_filename` đã ghi lại.
- [ ] Diff cho thấy 0 mismatch ở chiều DB → S3.
- [ ] Ít nhất 1 video sample đã test phát qua CloudFront URL build từ `storage_key` thực tế.
- [ ] Không có asset nào ở DB trỏ tới object không tồn tại trên S3.
- [ ] Không sửa logic import/business code trong phase này (chỉ rename hoặc re-import).

### Isolation guard

Read + targeted rename only. Không refactor service, không đổi schema, không deploy lại app.

---

## Phase 15 — Deploy frontend to Render

### Task

Deploy Next.js frontend web service on Render.

### Files that may be touched

- None if Phase 2 is complete.
- Render dashboard/env only.

### Required frontend env

```text
NEXT_PUBLIC_API_URL=https://<backend>.onrender.com
API_INTERNAL_URL=https://<backend>.onrender.com
NEXT_TELEMETRY_DISABLED=1
NODE_ENV=production
```

### Steps

1. Create Render Web Service from same repo.
2. Root directory: `frontend`.
3. Runtime: Docker.
4. Dockerfile path: `Dockerfile` relative to `frontend`.
5. Set frontend env variables.
6. Deploy.

### DoD checklist

- [ ] Frontend deploy succeeds.
- [ ] Frontend URL recorded.
- [ ] `GET /api/health` returns 200.
- [ ] Browser loads frontend home page.
- [ ] Frontend calls Render backend URL, not localhost.
- [ ] Build logs do not print secrets.

### Isolation guard

Only frontend deploy. Không đổi backend code, migrations, imports, domains.

---

## Phase 16 — Smoke test on Render temporary domains

### Task

Validate deployed app using Render temporary domains.

### Files that will be touched

- None required in repo.

### DoD checklist

- [ ] `https://<backend>.onrender.com/health` returns 200.
- [ ] `https://<frontend>.onrender.com/api/health` returns 200.
- [ ] Home page loads.
- [ ] Register/login works.
- [ ] At least one course page loads.
- [ ] At least one video URL uses CloudFront in S3 mode.
- [ ] Video plays and seek works.
- [ ] Quiz/session start works.
- [ ] Quiz/session submit works.
- [ ] Browser console has no localhost API calls.
- [ ] Backend logs have no secrets or repeated errors.

### Isolation guard

Validation only. Failure becomes targeted fix phase with explicit files touched.

---

## Phase 17 — Attach frontend/backend custom domains

### Task

Attach custom domains to Render frontend and backend.

### Files that will be touched

- None required in repo.
- Render dashboard and DNS records only.

### Domain mapping

| Domain | Target |
|---|---|
| `app.<domain>` or `<domain>` | Render frontend |
| `api.<domain>` | Render backend |

### Steps

1. Add custom domain to Render frontend service.
2. Add custom domain to Render backend service.
3. Create DNS records shown by Render.
4. Wait for TLS certificates to become active.
5. Update backend env:

```text
CORS_ORIGINS=["https://app.<domain>"]
FRONTEND_BASE_URL=https://app.<domain>
```

6. Update frontend env:

```text
NEXT_PUBLIC_API_URL=https://api.<domain>
API_INTERNAL_URL=https://api.<domain>
```

7. Redeploy frontend because `NEXT_PUBLIC_API_URL` is build-time.

### DoD checklist

- [ ] Frontend custom domain active with HTTPS.
- [ ] Backend custom domain active with HTTPS.
- [ ] `https://api.<domain>/health` returns 200.
- [ ] `https://app.<domain>/api/health` returns 200.
- [ ] Frontend calls `https://api.<domain>`, not temporary Render backend URL.
- [ ] Backend CORS allows final frontend domain.
- [ ] Temporary domains do not create unintended CORS hole.

### Isolation guard

Only DNS/domain/env values. Không đổi app code, DB data, S3, CloudFront behavior.

---

## Phase 18 — Attach CDN custom domain

### Task

Attach `cdn.<domain>` to CloudFront.

### Files that will be touched

- None required in repo.
- AWS CloudFront, ACM, and DNS only.

### Steps

1. Request ACM certificate in `us-east-1` for `cdn.<domain>`.
2. Validate certificate through DNS.
3. Add `cdn.<domain>` as CloudFront alternate domain name.
4. Attach ACM certificate to distribution.
5. Create DNS CNAME/ALIAS to CloudFront.
6. Update backend env:

```text
CLOUDFRONT_DOMAIN=cdn.<domain>
```

7. Restart/redeploy backend if env change requires it.

### DoD checklist

- [ ] ACM certificate for `cdn.<domain>` is issued.
- [ ] CloudFront accepts `cdn.<domain>` alternate domain.
- [ ] DNS resolves `cdn.<domain>`.
- [ ] Test asset loads through `https://cdn.<domain>/...`.
- [ ] Video play and seek works through custom CDN domain.
- [ ] Backend-generated asset URLs use `cdn.<domain>`.
- [ ] S3 bucket remains private.

### Isolation guard

Only CDN domain mapping. Không touch frontend/backend code, DB, S3 object contents.

---

## Phase 19 — Final production-readiness check

### Task

Run final readiness checklist.

### Files that will be touched

- None required in repo.

### DoD checklist

#### Availability

- [ ] Frontend final domain loads.
- [ ] Backend final domain health passes.
- [ ] CDN final domain serves assets.

#### Functional flow

- [ ] Register/login works.
- [ ] Reset-password link uses final frontend URL if email is enabled.
- [ ] Course page loads.
- [ ] Video plays and seek works.
- [ ] Quiz/session start and submit works.

#### Security

- [ ] `DEBUG=false` on backend.
- [ ] CORS allows only intended frontend origins.
- [ ] Secrets are not present in repo or logs.
- [ ] S3 bucket is private.
- [ ] CloudFront is the public asset entrypoint.
- [ ] Backend does not proxy video bytes.

#### Cost/ops

- [ ] AWS Budget alert enabled.
- [ ] CloudFront usage metric visible.
- [ ] Render service plans known.
- [ ] Logs checked after smoke test.

### Isolation guard

Validation only. Any failure becomes a targeted fix phase with explicit files touched.

---

## Phase 20 — Document rollback commands

### Task

Document rollback commands and manual rollback steps for app, DB, and assets.

### Files that may be touched

- `deploy/DEPLOYMENT_PLAN.md`
- Optional future file if requested: `deploy/ROLLBACK.md`

### Rollback steps

#### Render app rollback

- Backend: Render service -> Deploys -> redeploy previous successful deploy.
- Frontend: Render service -> Deploys -> redeploy previous successful deploy.

#### Database rollback

Before risky migrations:

```bash
pg_dump "$DATABASE_URL" > backup_before_migration.sql
```

Restore if required:

```bash
psql "$DATABASE_URL" < backup_before_migration.sql
```

#### Asset rollback

If S3 versioning is enabled, restore previous object versions.

If CloudFront cache must be cleared:

```bash
aws cloudfront create-invalidation --distribution-id <DIST_ID> --paths "/courses/*"
```

### DoD checklist

- [ ] Backend rollback path documented.
- [ ] Frontend rollback path documented.
- [ ] DB backup command documented.
- [ ] DB restore command documented.
- [ ] S3 versioning status known.
- [ ] CloudFront invalidation command documented.
- [ ] No destructive rollback command executed without explicit confirmation.

### Isolation guard

Documentation only. Do not execute destructive rollback commands unless user explicitly confirms.

---

## Current known future code touch points

These files are not all changed by this plan. They are likely touch points for future implementation phases:

| Area | Likely file(s) | Reason |
|---|---|---|
| Backend Render port | `Dockerfile` | Use `$PORT` instead of hard-coded `8000` if required |
| Frontend Render runtime | `frontend/Dockerfile` | Ensure Render runtime compatibility |
| Config | `src/config.py` | Add AWS/CloudFront asset settings |
| Asset URL builder | `src/services/asset_signing.py` or `src/services/asset_delivery.py` | Generate local or CloudFront asset URLs |
| Course asset URL usage | `src/services/learning_unit_service.py`, `src/services/content_service.py` | Return CloudFront URLs in S3 mode |
| Env docs | `deploy/.env.production.example`, `deploy/ENVIRONMENT_MATRIX.md` | Document Render/AWS env values |
| Tests | `tests/services/test_asset_delivery.py` or nearby tests | Validate URL generation and provider switch |

## Non-goals

- Do not migrate full app to AWS ECS/App Runner in this plan.
- Do not implement DRM.
- Do not implement multi-region HA.
- Do not build full observability stack.
- Do not rewrite course, quiz, auth, planner, or recommendation systems.
- Do not proxy large video files through FastAPI.
