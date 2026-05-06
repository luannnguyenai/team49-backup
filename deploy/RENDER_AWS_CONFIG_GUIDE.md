# Render + AWS Configuration Guide

Hướng dẫn này dùng cho deploy demo/prod nhẹ:

- Backend: Render Web Service từ root `Dockerfile`
- Frontend: Render Web Service từ `frontend/Dockerfile`
- Database: Render PostgreSQL
- Cache: Render Key Value/Redis
- Course/video assets: private AWS S3 bucket
- Public asset delivery: AWS CloudFront

## 1. Chuẩn bị local

```bash
git status
bash scripts/setup_hooks.sh
openssl rand -hex 32
```

Giữ lại output `openssl rand -hex 32` để set `SECRET_KEY` trên Render.

## 2. AWS S3 bucket

Chọn cùng region với plan hiện tại:

```text
AWS_REGION=ap-southeast-1
AWS_S3_BUCKET=a20-course-assets-prod
AWS_S3_PREFIX=courses
```

Tạo bucket private:

```bash
aws s3api create-bucket \
  --bucket a20-course-assets-prod \
  --region ap-southeast-1 \
  --create-bucket-configuration LocationConstraint=ap-southeast-1

aws s3api put-public-access-block \
  --bucket a20-course-assets-prod \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

aws s3api put-bucket-versioning \
  --bucket a20-course-assets-prod \
  --versioning-configuration Status=Enabled
```

Upload course assets:

```bash
aws s3 sync ./data/courses s3://a20-course-assets-prod/courses --delete
aws s3 ls s3://a20-course-assets-prod/courses --recursive --summarize
```

Expected key format:

```text
s3://a20-course-assets-prod/courses/CS231n/videos/...
s3://a20-course-assets-prod/courses/CS231n/transcripts/...
s3://a20-course-assets-prod/courses/CS231n/slides/...
```

## 3. AWS CloudFront

Create distribution:

1. Origin domain: S3 bucket `a20-course-assets-prod`.
2. Origin access: use **Origin Access Control (OAC)**.
3. Viewer protocol policy: **Redirect HTTP to HTTPS**.
4. Allowed methods: `GET`, `HEAD`.
5. Cache policy: default is OK for demo.
6. Do not make the S3 bucket public.

After CloudFront creates the distribution, copy its domain:

```text
CLOUDFRONT_DOMAIN=dxxxxxxxxxxxxx.cloudfront.net
```

Update the S3 bucket policy with the OAC policy CloudFront suggests. Verify:

```bash
curl -I https://dxxxxxxxxxxxxx.cloudfront.net/courses/CS231n/videos/<one-video-file>.mp4
```

Expected: `200`, `206`, or redirect-to-HTTPS then `200/206`.

## 4. Render PostgreSQL

Create Render PostgreSQL, then open the DB shell and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

Copy the external/internal database URL from Render and convert:

```text
postgresql://USER:PASSWORD@HOST:PORT/DB
```

to:

```text
postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB
```

Set this converted value as backend `DATABASE_URL`.

## 5. Render Redis / Key Value

Create Render Key Value/Redis. Copy its Redis URL and set it as backend:

```text
REDIS_URL=redis://...
```

Use the internal URL if Render provides one and backend is in the same account/region.

## 6. Render backend service

Create Web Service:

```text
Name: a20-backend
Environment: Docker
Root directory: repo root
Dockerfile path: Dockerfile
Health check path: /health
```

Set backend environment variables:

```text
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB
REDIS_URL=redis://...
DB_ECHO=false
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

SECRET_KEY=<openssl-rand-hex-32-output>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
RATE_LIMIT_LOGIN_PER_MINUTE=5
RATE_LIMIT_FORGOT_PASSWORD_PER_HOUR=5
FRONTEND_BASE_URL=https://a20-frontend.onrender.com
CORS_ORIGINS=["https://a20-frontend.onrender.com"]
PASSWORD_RESET_TOKEN_TTL_MINUTES=30

DEBUG=false
LOG_LEVEL=INFO
MODEL_PROVIDER=openai
DEFAULT_MODEL=<real-model-id>
FAST_MODEL=<real-fast-model-id>
OPENAI_API_KEY=<real-openai-key>

ASSET_STORAGE_PROVIDER=s3
ASSET_URL_EXPIRE_SECONDS=900
AWS_REGION=ap-southeast-1
AWS_S3_BUCKET=a20-course-assets-prod
AWS_S3_PREFIX=courses
CLOUDFRONT_DOMAIN=dxxxxxxxxxxxxx.cloudfront.net
```

Do not set AWS admin credentials on Render unless a future phase explicitly needs server-side S3 API access. Current production asset flow only returns CloudFront URLs.

Deploy backend, then verify:

```bash
curl https://a20-backend.onrender.com/health
```

## 7. Run backend bootstrap on Render

Open backend service → Shell, then run:

```bash
bash scripts/render_bootstrap.sh
```

Expected output:

```text
[1/8] Run Alembic migrations
[2/8] Seed canonical product shell
[3/8] Seed lecture runtime data
[4/8] Import canonical artifacts Schema v2
[5/8] Backfill Schema v2
[6/8] Validate Schema v2
[7/8] Check canonical runtime parity
[8/8] Create admin/demo accounts
Render bootstrap completed.
```

If a step fails, fix that step first and rerun the same script. The pipeline is intended to be rerunnable for normal bootstrap.

## 8. Render frontend service

Create Web Service:

```text
Name: a20-frontend
Environment: Docker
Root directory: frontend
Dockerfile path: Dockerfile
Health check path: /api/health
```

Set frontend environment variables:

```text
NEXT_PUBLIC_API_URL=https://a20-backend.onrender.com
API_INTERNAL_URL=https://a20-backend.onrender.com
NEXT_PUBLIC_GRAFANA_HOST=
NEXT_PUBLIC_LANGFUSE_HOST=https://cloud.langfuse.com
NEXT_TELEMETRY_DISABLED=1
NODE_ENV=production
```

Deploy frontend, then verify:

```bash
curl https://a20-frontend.onrender.com/api/health
```

## 9. Smoke test

Use the temporary Render/CloudFront domains first:

- Home page loads.
- Register/login works.
- Course catalog loads.
- One learning unit loads.
- Video URL starts with `https://<cloudfront-domain>/courses/...`.
- Video plays and seek works.
- Browser console does not call `localhost`.
- Backend logs do not contain secrets.

## 10. Custom domain later

After buying a domain:

```text
Frontend: app.<domain>  -> Render frontend
Backend:  api.<domain>  -> Render backend
CDN:      cdn.<domain>  -> CloudFront
```

Update backend:

```text
CORS_ORIGINS=["https://app.<domain>"]
FRONTEND_BASE_URL=https://app.<domain>
CLOUDFRONT_DOMAIN=cdn.<domain>
```

Update frontend and redeploy:

```text
NEXT_PUBLIC_API_URL=https://api.<domain>
API_INTERNAL_URL=https://api.<domain>
```

For CloudFront custom domain, create/attach ACM certificate in `us-east-1`.
