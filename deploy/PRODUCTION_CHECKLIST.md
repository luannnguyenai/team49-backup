# Demo Deploy Checklist — Railway + AWS S3

Tick song song khi thực thi `DEPLOYMENT_PLAN.md`.

## A. Pre-flight (mục 2)

### A.1. Code patches
- [ ] `Dockerfile` CMD đã đổi shell form `${PORT:-8000}`
- [ ] `frontend/Dockerfile` đã bỏ `PORT=3000` cứng
- [ ] `.dockerignore` đã exclude `data/courses/*/videos/` và `*.mp4`
- [ ] `src/api/app.py` đã thêm `_maybe_redirect_to_s3` + import boto3
- [ ] `pyproject.toml` đã thêm `boto3>=1.34.0`
- [ ] Đã chạy `uv lock` cập nhật `uv.lock`
- [ ] Test build local OK: `docker build -t test-backend .`

### A.2. Tài khoản
- [ ] Railway account, link GitHub
- [ ] AWS account có credit, IAM user có S3 permission
- [ ] AWS CLI `aws configure` xong (verify `aws sts get-caller-identity`)
- [ ] Railway CLI cài (optional)
- [ ] LLM API key (OpenAI/Anthropic/Gemini) còn quota

### A.3. Secrets
- [ ] `SECRET_KEY` generate xong (`openssl rand -hex 32`)
- [ ] Postgres password generate xong (`openssl rand -base64 24`)

## B. AWS S3 (mục 3)

- [ ] Bucket tạo xong (`ai-learning-videos-demo` hoặc tên khác)
- [ ] Block public access ON
- [ ] CORS rule apply (allow `https://*.up.railway.app`)
- [ ] IAM user `ai-learning-backend-demo` tạo xong
- [ ] Access key + secret key lưu lại (chưa commit)
- [ ] Inline policy `S3ReadVideos` apply (chỉ GetObject trên bucket này)
- [ ] Upload videos CS224n xong
- [ ] Upload videos CS230 xong
- [ ] Upload videos CS231n xong
- [ ] Verify `aws s3 ls s3://<bucket>/courses/CS224n/videos/`

## C. Railway setup (mục 4)

### C.1. Project + services
- [ ] Project `ai-learning-demo` tạo xong
- [ ] Service `backend` add từ GitHub repo
- [ ] Service `backend` đã generate domain
- [ ] Service `frontend` add từ GitHub repo, root dir = `frontend`
- [ ] Service `frontend` Build Args có `NEXT_PUBLIC_API_URL`
- [ ] Service `frontend` đã generate domain
- [ ] Service `postgres` empty service, image `pgvector/pgvector:pg16`
- [ ] Service `postgres` có volume 5GB mount `/var/lib/postgresql/data`
- [ ] Service `postgres` env: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, PGDATA
- [ ] Service `postgres` KHÔNG public domain
- [ ] Redis plugin add xong

### C.2. Backend env vars
- [ ] `DATABASE_URL` (prefix `postgresql+asyncpg://`, host = `${{postgres.RAILWAY_PRIVATE_DOMAIN}}`)
- [ ] `REDIS_URL` = `${{Redis.REDIS_URL}}`
- [ ] `SECRET_KEY`
- [ ] `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `RATE_LIMIT_LOGIN_PER_MINUTE`
- [ ] `CORS_ORIGINS` (JSON array, domain frontend Railway)
- [ ] `MODEL_PROVIDER`, `DEFAULT_MODEL`, `FAST_MODEL`
- [ ] LLM API key (`OPENAI_API_KEY` hoặc tương ứng)
- [ ] `DEBUG=false`, `LOG_LEVEL=INFO`
- [ ] `DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=10`
- [ ] `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
- [ ] `S3_VIDEO_BUCKET`, `S3_PRESIGNED_URL_TTL=3600`

### C.3. Frontend env vars
- [ ] `NEXT_PUBLIC_API_URL` (cũng là build arg)
- [ ] `API_INTERNAL_URL` = `http://${{backend.RAILWAY_PRIVATE_DOMAIN}}:8000`
- [ ] `NODE_ENV=production`

### C.4. Deploy config
- [ ] Backend custom start command có `alembic upgrade head` chain
- [ ] Backend healthcheck `/health` (timeout 60s)
- [ ] Frontend healthcheck `/api/health` (timeout 90s, start period 60s)
- [ ] Cả 3 service deploy thành công (Deployments tab xanh)

## D. Seed data (mục 5)

- [ ] `import_canonical_artifacts_to_db` chạy thành công
- [ ] `import_product_shell_to_db` chạy thành công
- [ ] `check_canonical_runtime_parity` không báo lỗi

## E. Smoke test (mục 6)

- [ ] `https://<backend>/health` → 200
- [ ] `https://<frontend>/api/health` → 200
- [ ] Frontend home load OK
- [ ] Register user mới OK
- [ ] Login OK
- [ ] Course catalog hiện 3 courses
- [ ] Learning unit load slide PDF OK
- [ ] **Video player play được (S3 presigned URL OK)** ← critical
- [ ] Quiz start + submit OK
- [ ] Tutor trả lời OK (LLM key OK)

## F. Post-deploy

- [ ] Note 2 public domain để share demo
- [ ] Note git commit SHA đang chạy
- [ ] Theo dõi logs 30 phút đầu (Railway dashboard)
- [ ] Theo dõi Railway credit usage hằng ngày
- [ ] Theo dõi AWS S3 egress (CloudWatch)
- [ ] Note known issues + LLM cost burn rate

## G. Sau demo (mục 10 — cleanup)

- [ ] Railway project deleted
- [ ] S3 bucket emptied + deleted
- [ ] IAM user + access key deleted
- [ ] LLM API key revoke (nếu cấp riêng cho demo)
