# Deployment Plan — Railway (App) + AWS S3 (Video)

Demo 1–2 tuần. Hybrid stack:
- **Railway**: backend FastAPI, frontend Next.js, Postgres+pgvector, Redis
- **AWS S3**: video assets (~14GB) — backend redirect 302 đến presigned URL

---

## 0. Mục tiêu và phạm vi

**Mục tiêu:** chạy demo public 1–2 tuần với:
- Public HTTPS frontend + backend
- Postgres có pgvector
- Redis
- Video streaming từ S3 (không bake vào image)
- Tổng cost ≤ $10 cho 2 tuần (Railway $5–7 + AWS $1–3)

**Không bao gồm:** TLS thủ công, reverse proxy, observability stack, CI/CD pipeline, backup automation. Railway lo TLS, demo dùng built-in logs.

---

## 1. Kiến trúc

```
                    ┌─────────────────────────────┐
                    │  Browser (user demo)        │
                    └──────────────┬──────────────┘
                                   │ HTTPS
                ┌──────────────────┼──────────────────┐
                │                  │                  │
                ▼                  ▼                  ▼
     <frontend>.up.railway.app   <backend>.up.railway.app
     (Next.js standalone)        (FastAPI)
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
     Postgres (pgvector)     Redis              S3 bucket
     Railway service         Railway plugin     ai-learning-videos-demo
     (custom image)                             (us-east-1)
                                                       │
                                              video files (.mp4)
                                              served via presigned URL
```

**Ghi chú quan trọng:**
- Postgres dùng **custom service** từ image `pgvector/pgvector:pg16` (Railway plugin mặc định không có pgvector).
- Backend khi nhận request `/data/videos/<file>` → tạo S3 presigned URL → redirect 302.
- Slides PDF + JSON metadata vẫn nằm trong image backend (~300MB total, OK).

---

## 2. Pre-flight (làm trước, ~30 phút)

### 2.1. Code changes bắt buộc

Trước khi deploy, **phải sửa 4 chỗ trong code** (chi tiết ở phần `7. Code Patches`):

| File | Sửa | Mục đích |
|---|---|---|
| `Dockerfile` | CMD shell form dùng `$PORT` | Railway inject PORT |
| `frontend/Dockerfile` | Dùng `${PORT:-3000}` | Railway inject PORT |
| `src/api/app.py` | `serve_data_asset` redirect S3 cho videos | Tách video khỏi image |
| `.dockerignore` | Exclude `data/courses/*/videos/` | Image gọn |

### 2.2. Tài khoản và tool

- [ ] Railway account (railway.app) đã link GitHub
- [ ] AWS account có credit, IAM user có quyền S3
- [ ] AWS CLI cài local: `aws configure`
- [ ] Railway CLI (optional, để chạy migration): `npm i -g @railway/cli`
- [ ] OpenAI/Anthropic/Gemini API key

### 2.3. Generate secrets

```bash
# SECRET_KEY cho JWT
openssl rand -hex 32
```
Lưu lại, dùng ở bước 4.

---

## 3. AWS S3 setup (15–30 phút)

### 3.1. Tạo bucket

```bash
aws s3api create-bucket \
  --bucket ai-learning-videos-demo \
  --region us-east-1
```

> Đổi `ai-learning-videos-demo` thành tên unique của bạn. Region nên cùng region với người xem demo (ví dụ Việt Nam → `ap-southeast-1`).

### 3.2. Block public access (giữ default — dùng presigned URL)

```bash
aws s3api put-public-access-block \
  --bucket ai-learning-videos-demo \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

### 3.3. CORS (cho phép browser fetch presigned URL)

Tạo `cors.json`:
```json
{
  "CORSRules": [{
    "AllowedOrigins": ["https://*.up.railway.app"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["Content-Length", "Content-Range"],
    "MaxAgeSeconds": 3600
  }]
}
```

```bash
aws s3api put-bucket-cors \
  --bucket ai-learning-videos-demo \
  --cors-configuration file://cors.json
```

### 3.4. Tạo IAM user cho backend

```bash
aws iam create-user --user-name ai-learning-backend-demo

aws iam create-access-key --user-name ai-learning-backend-demo
# → lưu lại AccessKeyId và SecretAccessKey
```

Policy chỉ cho phép GET object trên bucket cụ thể (file `policy.json`):
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject"],
    "Resource": "arn:aws:s3:::ai-learning-videos-demo/*"
  }]
}
```

```bash
aws iam put-user-policy \
  --user-name ai-learning-backend-demo \
  --policy-name S3ReadVideos \
  --policy-document file://policy.json
```

### 3.5. Upload videos

Từ root project:
```bash
aws s3 sync data/courses/CS224n/videos/ \
  s3://ai-learning-videos-demo/courses/CS224n/videos/ \
  --exclude "*.dvc" --exclude ".gitkeep"

aws s3 sync data/courses/CS230/videos/ \
  s3://ai-learning-videos-demo/courses/CS230/videos/

aws s3 sync data/courses/CS231n/videos/ \
  s3://ai-learning-videos-demo/courses/CS231n/videos/
```

> Đường mạng VN ~30 Mbps → upload 14GB mất ~60–90 phút. Có thể chạy background.

### 3.6. Verify

```bash
aws s3 ls s3://ai-learning-videos-demo/courses/CS224n/videos/ | head -5
```

---

## 4. Railway setup (45–60 phút)

### 4.1. Tạo project

1. railway.app → **New Project** → **Empty Project**
2. Đặt tên: `ai-learning-demo`

### 4.2. Add service backend

1. **+ New** → **GitHub Repo** → chọn repo này → branch `deploy-plan` (hoặc branch deploy của bạn)
2. Railway tự detect `Dockerfile` ở root
3. Đặt tên service: `backend`
4. **Settings → Networking → Generate Domain** → ghi lại URL, ví dụ `backend-production-abc.up.railway.app`

### 4.3. Add service frontend

1. **+ New** → **GitHub Repo** → cùng repo → cùng branch
2. **Settings → Build → Root Directory** = `frontend`
3. **Settings → Build → Build Args** thêm:
   - `NEXT_PUBLIC_API_URL=https://<backend-domain>` (URL từ bước 4.2)
4. Đặt tên service: `frontend`
5. **Settings → Networking → Generate Domain** → ghi lại URL

### 4.4. Add Postgres + pgvector (custom service, KHÔNG dùng plugin)

Plugin mặc định Railway không có pgvector. Phải deploy custom:

1. **+ New** → **Empty Service** → đặt tên `postgres`
2. **Settings → Source → Source Image** = `pgvector/pgvector:pg16`
3. **Settings → Variables** thêm:
   - `POSTGRES_USER=ailearning`
   - `POSTGRES_PASSWORD=<random-32-char>` (generate: `openssl rand -base64 24`)
   - `POSTGRES_DB=ai_learning`
   - `PGDATA=/var/lib/postgresql/data/pgdata`
4. **Settings → Volumes** → **Add Volume**:
   - Mount path: `/var/lib/postgresql/data`
   - Size: 5GB
5. **Settings → Networking** → KHÔNG generate public domain (giữ private)

### 4.5. Add Redis (plugin built-in OK)

1. **+ New** → **Database** → **Add Redis**
2. Railway tự cấp `REDIS_URL`

### 4.6. Set environment variables — service `backend`

Vào service `backend` → **Variables**:

```bash
# Database (sửa scheme thành asyncpg)
DATABASE_URL=postgresql+asyncpg://ailearning:<PASSWORD>@${{postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/ai_learning

# Redis (Railway cấp sẵn qua reference)
REDIS_URL=${{Redis.REDIS_URL}}

# Auth
SECRET_KEY=<từ bước 2.3>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
RATE_LIMIT_LOGIN_PER_MINUTE=5

# CORS (URL frontend từ bước 4.3)
CORS_ORIGINS=["https://<frontend-domain>"]

# LLM
MODEL_PROVIDER=openai
DEFAULT_MODEL=gpt-4o-mini
FAST_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...

# Runtime
DEBUG=false
LOG_LEVEL=INFO
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# AWS S3 (cho video redirect)
AWS_ACCESS_KEY_ID=<từ bước 3.4>
AWS_SECRET_ACCESS_KEY=<từ bước 3.4>
AWS_REGION=us-east-1
S3_VIDEO_BUCKET=ai-learning-videos-demo
S3_PRESIGNED_URL_TTL=3600
```

### 4.7. Set environment variables — service `frontend`

```bash
NEXT_PUBLIC_API_URL=https://<backend-domain>
API_INTERNAL_URL=http://${{backend.RAILWAY_PRIVATE_DOMAIN}}:8000
NODE_ENV=production
```

### 4.8. Override start command — service `backend`

**Settings → Deploy → Custom Start Command**:
```bash
sh -c "uv run alembic upgrade head && uv run python -m uvicorn src.api.app:app --host 0.0.0.0 --port $PORT"
```

→ Auto-migrate mỗi lần deploy.

### 4.9. Healthcheck

**backend** → Settings → Deploy:
- Healthcheck Path: `/health`
- Timeout: 60s

**frontend** → Settings → Deploy:
- Healthcheck Path: `/api/health`
- Timeout: 90s (frontend `/api/health` proxy đến backend, cần backend up trước)
- Start period: 60s

### 4.10. Trigger first deploy

Cả 3 service (backend, frontend, postgres) sẽ tự build khi config xong. Theo dõi tab **Deployments** của từng service.

Thứ tự kỳ vọng:
1. `postgres` up trước (~30s)
2. `redis` up sẵn
3. `backend` up (~3–5 phút build, sau đó migrate)
4. `frontend` up (~5–7 phút build)

---

## 5. Post-deploy seed data (10 phút)

Sau khi backend healthy, chạy import script. Hai cách:

### Cách A: Railway dashboard shell

Service `backend` → tab **...** → **Run a Command**:
```bash
uv run python -m src.scripts.pipeline.import_canonical_artifacts_to_db
```
Lặp lại cho:
```bash
uv run python -m src.scripts.pipeline.import_product_shell_to_db
uv run python -m src.scripts.pipeline.check_canonical_runtime_parity
```

### Cách B: Railway CLI

```bash
railway login
railway link  # chọn project ai-learning-demo
railway run --service backend uv run python -m src.scripts.pipeline.import_canonical_artifacts_to_db
```

---

## 6. Smoke test

Truy cập `https://<frontend-domain>`:

- [ ] Trang home load (status 200)
- [ ] `https://<backend-domain>/health` → 200
- [ ] `https://<frontend-domain>/api/health` → 200 (chứng minh proxy backend OK)
- [ ] Register tài khoản mới
- [ ] Login
- [ ] Course catalog hiện 3 courses (CS224n, CS230, CS231n)
- [ ] Mở 1 learning unit → slide PDF hiện ra
- [ ] Mở 1 video → player play (verify S3 presigned URL hoạt động)
- [ ] Start 1 quiz session, submit
- [ ] Tutor trả lời 1 câu hỏi (verify LLM key OK)

---

## 7. Code patches (bắt buộc)

### 7.1. `Dockerfile` (backend, root)

Sửa `CMD` cuối file:
```dockerfile
# ĐỔI TỪ:
CMD ["uv", "run", "python", "-m", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

# THÀNH:
CMD ["sh", "-c", "uv run python -m uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

### 7.2. `frontend/Dockerfile`

Sửa stage `runner`:
```dockerfile
# ĐỔI:
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# THÀNH (bỏ PORT cứng, để Railway inject):
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0
```

CMD `node server.js` đã đọc `$PORT` mặc định → OK.

### 7.3. `.dockerignore` (root) — bổ sung

```
# Loại video khỏi image — phục vụ qua S3
data/courses/*/videos/
data/courses/*/processed/
data/**/*.mp4
data/**/*.mkv
data/**/*.webm
```

### 7.4. `src/api/app.py` — sửa `serve_data_asset`

Tại `app.py:149`, thêm logic redirect S3 cho videos. Thêm helper:

```python
import os
import boto3
from botocore.config import Config
from fastapi.responses import RedirectResponse

_s3_client = None

def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            config=Config(signature_version="s3v4"),
        )
    return _s3_client

def _maybe_redirect_to_s3(asset_path: str) -> RedirectResponse | None:
    bucket = os.getenv("S3_VIDEO_BUCKET")
    if not bucket:
        return None
    if "/videos/" not in asset_path and not asset_path.startswith("courses/") :
        return None
    # only handle video files
    if not asset_path.lower().endswith((".mp4", ".mkv", ".webm")):
        return None
    ttl = int(os.getenv("S3_PRESIGNED_URL_TTL", "3600"))
    url = _get_s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": asset_path.lstrip("/")},
        ExpiresIn=ttl,
    )
    return RedirectResponse(url=url, status_code=302)
```

Trong `serve_data_asset`, thêm sau bước verify signed URL:
```python
redirect = _maybe_redirect_to_s3(normalized_path)
if redirect is not None:
    return redirect
# fall through to local FileResponse for non-video assets (slides, JSON)
file_path = _resolve_data_file(normalized_path)
return FileResponse(file_path)
```

### 7.5. `pyproject.toml` — thêm boto3

```toml
[project]
dependencies = [
    # ... existing
    "boto3>=1.34.0",
]
```

Sau khi sửa: `uv lock` để cập nhật `uv.lock`.

---

## 8. Cost estimate (2 tuần demo)

### Railway

| Item | Cost |
|---|---|
| Hobby plan | $5/tháng → $2.5/2 tuần |
| Backend service usage (~$0.000463/GB-hour RAM, ~512MB) | ~$1.20/2 tuần |
| Frontend service usage (~256MB) | ~$0.60 |
| Postgres custom service (~512MB + 5GB volume) | ~$2.00 |
| Redis plugin | ~$0.50 |
| **Railway subtotal** | **~$7/2 tuần** |

> Railway $5 trial credit cover ~70%. Với Hobby plan $5/tháng + usage thực tế nhỏ, demo 2 tuần thường hết khoảng $5–10. Có thể dùng trial credit + thêm $5 nếu cần.

### AWS S3

| Item | Cost |
|---|---|
| Storage 14GB × $0.023/GB × 0.5 tháng | $0.16 |
| PUT requests upload (~150 files × $0.005/1000) | <$0.01 |
| GET requests serve (~500 view × $0.0004/1000) | <$0.01 |
| Egress (~50 view × 300MB × $0.09/GB) | $1.35 |
| **S3 subtotal** | **~$1.50/2 tuần** |

> Nếu demo nhiều người xem, egress sẽ tăng. 100GB egress = $9. Credit AWS cover thoải mái.

### LLM (tách biệt, không tính trong infra)

OpenAI gpt-4o-mini: ~$0.15/1M input, $0.60/1M output. Demo 100 user × 20 query × 2K token = ~$1–3.

### **Total demo 2 tuần: ~$10–15** (Railway + S3 + LLM)

---

## 9. Rollback

### App rollback
Service → tab **Deployments** → chọn build cũ → **Redeploy**.

### DB rollback
Demo không setup auto backup. Nếu cần snapshot:
```bash
railway run --service postgres pg_dump -U ailearning ai_learning > backup-$(date +%F).sql
```
Restore:
```bash
railway run --service postgres psql -U ailearning ai_learning < backup-2026-05-02.sql
```

### S3 rollback
Bucket có versioning OFF mặc định. Nếu lỡ overwrite, không recover được. Demo OK.

---

## 10. Cleanup sau demo

Khi demo xong, để tránh charge:

```bash
# Xóa Railway project
# → railway.app dashboard → Project Settings → Delete Project

# Xóa S3 objects
aws s3 rm s3://ai-learning-videos-demo/ --recursive

# Xóa S3 bucket
aws s3api delete-bucket --bucket ai-learning-videos-demo

# Xóa IAM user
aws iam delete-user-policy --user-name ai-learning-backend-demo --policy-name S3ReadVideos
aws iam list-access-keys --user-name ai-learning-backend-demo  # lấy AccessKeyId
aws iam delete-access-key --user-name ai-learning-backend-demo --access-key-id <ID>
aws iam delete-user --user-name ai-learning-backend-demo
```

---

## 11. Troubleshooting

| Triệu chứng | Nguyên nhân khả nghi | Fix |
|---|---|---|
| Backend healthcheck fail | Migration lỗi, DB chưa up | Check logs `backend`, verify `DATABASE_URL` reference đúng |
| `vector type does not exist` | Postgres image sai (dùng plugin mặc định) | Đổi sang `pgvector/pgvector:pg16` (mục 4.4) |
| Frontend không gọi được API | `NEXT_PUBLIC_API_URL` chưa pass build arg | Settings → Build Args, redeploy |
| Frontend `/api/health` timeout | `API_INTERNAL_URL` sai private domain | Dùng `${{backend.RAILWAY_PRIVATE_DOMAIN}}` |
| Video không load, 403 | S3 IAM policy sai hoặc bucket name khác | Test `aws s3 presign s3://bucket/key` |
| Video load nhưng CORS error | `cors.json` chưa apply | `put-bucket-cors` lại |
| `Image too large` build fail | `data/courses/*/videos/` chưa exclude | Check `.dockerignore` mục 7.3 |
| `$PORT` connection refused | Backend bind 8000 cứng | Sửa CMD shell form (mục 7.1) |
| Build chậm 15+ phút | Cache miss, repo lớn | Bình thường lần đầu, lần sau nhanh hơn |

---

## 12. Cái không làm trong demo này

- TLS/cert thủ công (Railway tự lo)
- Reverse proxy config (Railway lo)
- CloudFront CDN trước S3 (chỉ cần khi >1000 view)
- Backup automation (manual khi cần)
- Observability stack (dùng built-in Railway logs)
- CI/CD GitHub Actions (Railway auto-deploy `git push`)
- Rate limiting tầng proxy (FastAPI middleware đủ cho demo)
- Multi-region, HA, autoscale

Khi nào cần các thứ trên → migrate sang Full AWS hoặc VM + Docker Compose. Plan này không cover.
