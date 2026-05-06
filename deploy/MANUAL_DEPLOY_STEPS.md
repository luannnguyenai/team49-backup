# Manual Deploy Steps — Render + AWS S3/CloudFront

File này là checklist thao tác tay để deploy app lên:

- Render: backend, frontend, PostgreSQL, Redis/Key Value
- AWS: S3 private bucket, CloudFront CDN

Không commit secret thật vào git.

---

## 0. Thông tin cần chốt trước

Điền các giá trị thật của bạn vào bảng này khi làm:

| Key | Value |
|---|---|
| AWS region | `ap-southeast-1` |
| S3 bucket | `a20-course-assets-prod` |
| S3 prefix | `courses` |
| CloudFront domain | `____________________________` |
| Render backend URL | `https://________________.onrender.com` |
| Render frontend URL | `https://________________.onrender.com` |
| Render Postgres URL | `postgresql://________________` |
| Render Redis URL | `redis://________________` |
| Final frontend domain | `app.<domain>` hoặc `<domain>` |
| Final backend domain | `api.<domain>` |
| Final CDN domain | `cdn.<domain>` |

---

## 1. Chuẩn bị local

Chạy ở repo root:

```bash
git status
bash scripts/setup_hooks.sh
openssl rand -hex 32
```

Lưu output của `openssl rand -hex 32`. Giá trị đó dùng cho:

```text
SECRET_KEY=<output>
```

Kiểm tra local course assets:

```bash
ls data/courses
```

Expected có các course như:

```text
CS224n
CS230
CS231n
```

---

## 2. Tạo S3 bucket private

Set biến local:

```bash
export AWS_REGION=ap-southeast-1
export AWS_S3_BUCKET=a20-course-assets-prod
```

Tạo bucket:

```bash
aws s3api create-bucket \
  --bucket "$AWS_S3_BUCKET" \
  --region "$AWS_REGION" \
  --create-bucket-configuration LocationConstraint="$AWS_REGION"
```

Bật Block Public Access:

```bash
aws s3api put-public-access-block \
  --bucket "$AWS_S3_BUCKET" \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

Bật versioning:

```bash
aws s3api put-bucket-versioning \
  --bucket "$AWS_S3_BUCKET" \
  --versioning-configuration Status=Enabled
```

Verify:

```bash
aws s3api get-public-access-block --bucket "$AWS_S3_BUCKET"
aws s3api get-bucket-versioning --bucket "$AWS_S3_BUCKET"
```

---

## 3. Upload course assets lên S3

Upload toàn bộ `data/courses` vào prefix `courses/`:

```bash
aws s3 sync ./data/courses s3://a20-course-assets-prod/courses --delete
```

Verify số lượng và dung lượng:

```bash
aws s3 ls s3://a20-course-assets-prod/courses --recursive --summarize
```

Test vài file cụ thể:

```bash
aws s3 ls s3://a20-course-assets-prod/courses/CS231n/videos/
aws s3 ls s3://a20-course-assets-prod/courses/CS224n/
aws s3 ls s3://a20-course-assets-prod/courses/CS230/
```

Expected key format:

```text
courses/CS231n/videos/<file>.mp4
courses/CS231n/transcripts/<file>.txt
courses/CS231n/slides/<file>.pdf
```

---

## 4. Tạo CloudFront distribution

Vào AWS Console → CloudFront → Create distribution.

Config:

| Field | Value |
|---|---|
| Origin | S3 bucket `a20-course-assets-prod` |
| Origin access | Origin Access Control / OAC |
| S3 bucket public access | Keep private |
| Viewer protocol policy | Redirect HTTP to HTTPS |
| Allowed HTTP methods | GET, HEAD |
| Cache policy | CachingOptimized hoặc default |
| Price class | tùy budget |

Sau khi tạo xong, CloudFront sẽ hiện domain dạng:

```text
dxxxxxxxxxxxxx.cloudfront.net
```

Lưu domain này:

```text
CLOUDFRONT_DOMAIN=dxxxxxxxxxxxxx.cloudfront.net
```

CloudFront sẽ đề xuất S3 bucket policy cho OAC. Copy policy đó và apply vào S3 bucket.

Verify bằng 1 video thật:

```bash
curl -I https://dxxxxxxxxxxxxx.cloudfront.net/courses/CS231n/videos/<file>.mp4
```

Expected:

```text
HTTP/2 200
```

hoặc:

```text
HTTP/2 206
```

Nếu bị `403`, kiểm tra lại OAC bucket policy.

Nếu bị `404`, kiểm tra lại object key trên S3.

---

## 5. Tạo Render PostgreSQL

Vào Render Dashboard → New → PostgreSQL.

Gợi ý:

| Field | Value |
|---|---|
| Name | `a20-db` |
| Region | cùng region Render backend nếu chọn được |
| Plan | Free/Starter tùy demo |

Sau khi DB ready:

1. Copy connection string.
2. Mở Render PostgreSQL shell hoặc dùng external connection.
3. Chạy:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

Render URL thường có dạng:

```text
postgresql://USER:PASSWORD@HOST:PORT/DB
```

Backend cần đổi prefix thành:

```text
postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB
```

Lưu giá trị này để set:

```text
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB
```

---

## 6. Tạo Render Redis / Key Value

Vào Render Dashboard → New → Key Value.

Gợi ý:

| Field | Value |
|---|---|
| Name | `a20-redis` |
| Region | cùng backend nếu chọn được |

Copy Redis URL:

```text
REDIS_URL=redis://...
```

Nếu Render có internal URL và backend cùng region/account, ưu tiên internal URL.

---

## 7. Deploy backend lên Render

Vào Render Dashboard → New → Web Service.

Config:

| Field | Value |
|---|---|
| Name | `a20-backend` |
| Environment | Docker |
| Root Directory | repo root / để trống |
| Dockerfile Path | `Dockerfile` |
| Health Check Path | `/health` |

Set environment variables:

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
PASSWORD_RESET_TOKEN_TTL_MINUTES=30

FRONTEND_BASE_URL=https://<frontend>.onrender.com
CORS_ORIGINS=["https://<frontend>.onrender.com"]

DEBUG=false
LOG_LEVEL=INFO

MODEL_PROVIDER=openai
DEFAULT_MODEL=<real-model-id>
FAST_MODEL=<real-fast-model-id>
OPENAI_API_KEY=<real-openai-key>
ANTHROPIC_API_KEY=
GEMINI_API_KEY=

ASSET_STORAGE_PROVIDER=s3
ASSET_URL_EXPIRE_SECONDS=900
AWS_REGION=ap-southeast-1
AWS_S3_BUCKET=a20-course-assets-prod
AWS_S3_PREFIX=courses
CLOUDFRONT_DOMAIN=dxxxxxxxxxxxxx.cloudfront.net
CLOUDFRONT_KEY_PAIR_ID=
CLOUDFRONT_PRIVATE_KEY=
```

Deploy backend.

Verify:

```bash
curl https://<backend>.onrender.com/health
```

Expected:

```text
200 OK
```

---

## 8. Chạy DB bootstrap trên Render backend

Vào Render backend service → Shell.

Chạy:

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

Nếu fail:

| Error | Cách xử lý |
|---|---|
| DB connection fail | kiểm tra `DATABASE_URL`, prefix `postgresql+asyncpg://`, allow network |
| vector extension missing | chạy lại `CREATE EXTENSION IF NOT EXISTS vector;` |
| missing data file | kiểm tra file data có trong Docker image không; video mp4 không cần trong image, nhưng JSON/bootstrap artifacts cần |
| LLM key fail | kiểm tra `MODEL_PROVIDER` và API key tương ứng |

Sau khi pass, verify DB counts:

```sql
SELECT COUNT(*) FROM learning_units;
SELECT COUNT(*) FROM lectures;
SELECT COUNT(*) FROM users WHERE role='admin';
```

Expected:

```text
learning_units > 0
lectures >= 0 hoặc > 0 nếu lecture data có trong image
admin users >= 1
```

---

## 9. Deploy frontend lên Render

Vào Render Dashboard → New → Web Service.

Config:

| Field | Value |
|---|---|
| Name | `a20-frontend` |
| Environment | Docker |
| Root Directory | `frontend` |
| Dockerfile Path | `Dockerfile` |
| Health Check Path | `/api/health` |

Set environment variables:

```text
NEXT_PUBLIC_API_URL=https://<backend>.onrender.com
API_INTERNAL_URL=https://<backend>.onrender.com
NEXT_PUBLIC_GRAFANA_HOST=
NEXT_PUBLIC_LANGFUSE_HOST=https://cloud.langfuse.com
NEXT_TELEMETRY_DISABLED=1
NODE_ENV=production
```

Deploy frontend.

Verify:

```bash
curl https://<frontend>.onrender.com/api/health
```

Expected:

```text
200 OK
```

Sau khi biết frontend URL thật, quay lại backend env update:

```text
FRONTEND_BASE_URL=https://<frontend>.onrender.com
CORS_ORIGINS=["https://<frontend>.onrender.com"]
```

Redeploy backend nếu Render không tự restart sau env update.

---

## 10. Smoke test app trên temporary domains

Checklist:

- [ ] `https://<backend>.onrender.com/health` trả 200.
- [ ] `https://<frontend>.onrender.com/api/health` trả 200.
- [ ] Home page load.
- [ ] Register/login OK.
- [ ] Course catalog load.
- [ ] Mở ít nhất 1 learning unit.
- [ ] Video URL bắt đầu bằng `https://dxxxxxxxxxxxxx.cloudfront.net/courses/...`.
- [ ] Video play được.
- [ ] Video seek được.
- [ ] Browser console không gọi `localhost`.
- [ ] Backend logs không lộ secret.
- [ ] Backend logs không spam error.

Nếu video không play:

1. Copy URL video trong browser/network tab.
2. Chạy:

```bash
curl -I "<video-url>"
```

3. Debug:

| Status | Nguyên nhân thường gặp |
|---|---|
| 403 | CloudFront OAC/S3 bucket policy sai |
| 404 | S3 object key không khớp DB/generated URL |
| CORS error | cần thêm CloudFront response headers policy nếu frontend fetch video qua XHR |
| `/data/...` URL | backend chưa set `ASSET_STORAGE_PROVIDER=s3` hoặc chưa redeploy |

---

## 11. Gắn custom domain sau khi smoke test pass

Domain layout đề xuất:

```text
app.<domain>  -> Render frontend
api.<domain>  -> Render backend
cdn.<domain>  -> CloudFront
```

### 11.1 Render frontend/backend domain

Trong Render:

1. Frontend service → Settings → Custom Domains → add `app.<domain>`.
2. Backend service → Settings → Custom Domains → add `api.<domain>`.
3. Tạo DNS record theo Render hướng dẫn.
4. Đợi TLS active.

Update backend env:

```text
FRONTEND_BASE_URL=https://app.<domain>
CORS_ORIGINS=["https://app.<domain>"]
```

Update frontend env:

```text
NEXT_PUBLIC_API_URL=https://api.<domain>
API_INTERNAL_URL=https://api.<domain>
```

Redeploy frontend vì `NEXT_PUBLIC_API_URL` được bake vào build.

### 11.2 CloudFront custom domain

Trong AWS Certificate Manager:

1. Region phải là `us-east-1`.
2. Request cert cho `cdn.<domain>`.
3. Verify DNS.
4. Attach cert vào CloudFront distribution.
5. Add alternate domain name `cdn.<domain>`.
6. Tạo DNS CNAME/alias `cdn.<domain>` trỏ về CloudFront.

Update backend env:

```text
CLOUDFRONT_DOMAIN=cdn.<domain>
```

Redeploy backend.

Smoke test lại toàn bộ bằng domain thật.

---

## 12. Final checklist

- [ ] S3 bucket private.
- [ ] CloudFront dùng OAC.
- [ ] Backend không proxy video bytes.
- [ ] `ASSET_STORAGE_PROVIDER=s3` trên Render backend.
- [ ] `CLOUDFRONT_DOMAIN` đúng.
- [ ] `DATABASE_URL` dùng `postgresql+asyncpg://`.
- [ ] `vector` extension enabled.
- [ ] Redis URL set.
- [ ] `DEBUG=false`.
- [ ] `CORS_ORIGINS` chỉ allow frontend domain.
- [ ] Frontend `NEXT_PUBLIC_API_URL` trỏ backend domain đúng.
- [ ] Video URL là CloudFront URL.
- [ ] Login/course/video/quiz smoke test pass.
- [ ] Không secret trong logs.
- [ ] Ghi lại commit SHA đang deploy.

---

## 13. Files liên quan trong repo

- `deploy/DEPLOYMENT_PLAN.md`
- `deploy/ENVIRONMENT_MATRIX.md`
- `deploy/PRODUCTION_CHECKLIST.md`
- `deploy/.env.production.example`
- `deploy/RENDER_AWS_CONFIG_GUIDE.md`
- `scripts/render_bootstrap.sh`
- `Dockerfile`
- `frontend/Dockerfile`
