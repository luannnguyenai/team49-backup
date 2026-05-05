# Environment Matrix — Render + AWS

Set qua Render dashboard (**Service → Environment**) và AWS console/CLI. **Không commit `.env` thật vào git.**

## Service `a20-backend` (FastAPI on Render)

### Core / database / cache

| Variable | Value | Note |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://USER:PASS@HOST:PORT/DB` | Render Postgres cấp dạng `postgresql://...` → đổi prefix sang `postgresql+asyncpg://` cho SQLAlchemy async |
| `REDIS_URL` | `redis://...` hoặc `rediss://...` | Render Key Value/Redis URL |
| `DB_ECHO` | `false` | |
| `DB_POOL_SIZE` | `5` | Demo nhỏ |
| `DB_MAX_OVERFLOW` | `10` | |
| `PORT` | (Render inject) | Backend phải bind `0.0.0.0:$PORT` |

### Auth / security

| Variable | Value | Note |
|---|---|---|
| `SECRET_KEY` | `openssl rand -hex 32` | Bắt buộc rotate khi compromise |
| `ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | `5` | |
| `RATE_LIMIT_FORGOT_PASSWORD_PER_HOUR` | `5` | Per IP và normalized email |
| `EMAIL_FROM` | `noreply@<verified-domain>` | Nếu dùng email/reset password |
| `FRONTEND_BASE_URL` | `https://<frontend>.onrender.com` hoặc `https://app.<domain>` | Build link reset password |
| `PASSWORD_RESET_TOKEN_TTL_MINUTES` | `30` | TTL reset link |
| `CORS_ORIGINS` | `["https://<frontend>.onrender.com"]` hoặc `["https://app.<domain>"]` | JSON array |

### App / runtime

| Variable | Value | Note |
|---|---|---|
| `DEBUG` | `false` | Bắt buộc false trên Render |
| `LOG_LEVEL` | `INFO` | |
| `MODEL_PROVIDER` | `openai` / `anthropic` / `gemini` | |
| `DEFAULT_MODEL` | model id thật của provider | Verify với provider trước khi set |
| `FAST_MODEL` | model id thật của provider | |
| `OPENAI_API_KEY` | `sk-...` | Nếu dùng OpenAI |
| `ANTHROPIC_API_KEY` | | Nếu dùng Anthropic |
| `GEMINI_API_KEY` | | Nếu dùng Gemini |

### Asset delivery (AWS S3 + CloudFront)

| Variable | Value | Note |
|---|---|---|
| `ASSET_STORAGE_PROVIDER` | `s3` | `local` cho dev, `s3` cho Render production |
| `ASSET_URL_EXPIRE_SECONDS` | `900` | TTL signed asset URL |
| `AWS_REGION` | `ap-southeast-1` | Hoặc region S3 bucket đã chọn |
| `AWS_S3_BUCKET` | `a20-course-assets-prod` | Private bucket |
| `AWS_S3_PREFIX` | `courses` | Prefix chứa course assets |
| `CLOUDFRONT_DOMAIN` | `<id>.cloudfront.net` hoặc `cdn.<domain>` | Không kèm scheme `https://` nếu code build URL từ domain thuần |
| `CLOUDFRONT_KEY_PAIR_ID` | `<key-pair-id>` | Chỉ cần nếu bật signed CloudFront URL |
| `CLOUDFRONT_PRIVATE_KEY` | private key nội dung multiline | Chỉ cần nếu bật signed CloudFront URL |

## Service `a20-frontend` (Next.js on Render)

| Variable | Value | Note |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://<backend>.onrender.com` hoặc `https://api.<domain>` | Bake vào build, đổi là phải redeploy/rebuild |
| `API_INTERNAL_URL` | giống backend URL | Cho server-side Next.js calls |
| `NEXT_PUBLIC_GRAFANA_HOST` | optional | Nếu dùng dashboard |
| `NEXT_PUBLIC_LANGFUSE_HOST` | `https://cloud.langfuse.com` | optional |
| `NEXT_TELEMETRY_DISABLED` | `1` | |
| `NODE_ENV` | `production` | |
| `PORT` | (Render inject) | Next runner phải listen `$PORT` nếu Render yêu cầu |

## Render PostgreSQL

Render cấp connection string. Sau khi DB up, chạy 1 lần:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

App dùng SQLAlchemy async nên `DATABASE_URL` phải là `postgresql+asyncpg://...`.

## Render Key Value / Redis

Render cấp:

- Internal Redis URL nếu service cùng network/region.
- External Redis URL nếu connect từ ngoài.

Backend chỉ cần `REDIS_URL`.

## AWS local/admin env

Dùng trên máy admin/local, **không set credential admin trên Render runtime nếu không cần**.

```bash
aws configure
# region nên trùng AWS_REGION ở backend (ví dụ ap-southeast-1)
aws s3 sync ./data/courses s3://a20-course-assets-prod/courses --delete
```

Nếu backend chỉ tạo CloudFront signed URL, backend **không cần AWS access key đọc S3**. Nếu dùng S3 presigned URL thay CloudFront signed URL, tạo IAM user/role với quyền đọc tối thiểu cho bucket/prefix và set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` trên Render backend.

## Sau khi gắn custom domain

Backend:

```text
CORS_ORIGINS=["https://app.<domain>"]
FRONTEND_BASE_URL=https://app.<domain>
CLOUDFRONT_DOMAIN=cdn.<domain>
```

Frontend:

```text
NEXT_PUBLIC_API_URL=https://api.<domain>
API_INTERNAL_URL=https://api.<domain>
```

Đổi `NEXT_PUBLIC_API_URL` luôn cần frontend redeploy/rebuild.

## Lưu ý

- `CORS_ORIGINS` phải JSON array hợp lệ, parse bởi `src/config.py`.
- `EMAIL_FROM` phải thuộc sender identity/domain đã verify với email provider.
- `FRONTEND_BASE_URL` phải là domain frontend public để link reset password mở đúng trang.
- Không cần `POSTGRES_*` riêng vì Render Postgres tự quản lý credential qua `DATABASE_URL`.
- Không log secret trong stdout/stderr.
