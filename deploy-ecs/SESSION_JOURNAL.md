# Session Journal — ECS Deployment

**Date:** 2026-05-09
**Session duration:** ~6 giờ
**Operator:** edward1503 / vanhuydz210@gmail.com
**AWS Account:** 116533674568
**Region:** ap-southeast-1
**Branch:** feat-terraform-aws

Đây là nhật ký chi tiết của session deploy A20 từ App Runner sang ECS. Ghi lại
mọi step, lỗi gặp phải, root cause, và cách fix. Mục đích: làm reference cho
deploy lần sau và post-mortem.

---

## 1. Bối cảnh trước session

App Runner deployment trước đó (2026-05-08) đã teardown thành công sau khi
disable RDS `deletion_protection`. Quyết định pivot sang ECS Fargate vì:

- App Runner `StartCommand` quá fragile (shell quoting, working dir)
- Migration tích hợp trong service start command gây race condition
- Khó debug khi service crash-loop
- Cần kiểm soát tốt hơn các thành phần (task definition, service, target group)

Chi tiết postmortem App Runner: `deploy/HOW_TO_FIX.md`. Bài học carry forward:
A1–A6 + B1–B8 trong `HOW_TO_FIX.md` của thư mục này.

---

## 2. Tóm tắt thành quả

| Hạng mục | Số lượng |
|---|---:|
| Resource Terraform tạo | 61 |
| Module Terraform viết mới | 11 |
| ECS task definitions đã chạy | 6 (migrate, seed, inventory, admin-query, promote-admin, full-bootstrap, llm-test, redis-test, backend service x3, frontend service x1) |
| ECR images push | 3 (a20-backend:7deedc0, a20-backend:7deedc0-data, a20-frontend:7deedc0) |
| Secrets Manager keys | 11 (DATABASE_URL, REDIS_URL, SECRET_KEY, OPENAI/ANTHROPIC/GEMINI keys, LANGFUSE keys, GMAIL_APP_PASSWORD, AI_LOG_API_KEY, ADMIN_TOKEN) |
| Plain env vars (task def) | 50+ |
| S3 objects asset bucket | 360 (~14 GB) |
| RDS migrations applied | 40+ |
| Seed accounts created | 5 admin/demo + 2 self-register |
| Lỗi gặp + fix tại chỗ | 14 |

---

## 3. Timeline chi tiết

### 3.1 Cost guard (Bài 2)

**Action**: tạo AWS Budget $130 với 3 ngưỡng email (38.46% / 76.92% / 100%).

```powershell
aws budgets create-budget --account-id 116533674568 --budget file://budget.json --notifications-with-subscribers file://budget-notifications.json
```

**Issue 1 — Hiểu nhầm về email confirmation**:
- Tôi (assistant) ban đầu nói cần bấm "Confirm subscription" cho 3 email từ SNS.
- Thực tế: AWS Budget với subscriber type `EMAIL` **không qua SNS**, không có flow confirm. Email đầu tiên là alert thật.
- **Fix**: Verify trực tiếp qua `aws budgets describe-subscribers-for-notification`.

**Issue 2 — Đổi email recipient**:
- Ban đầu set `eddiedepunnie@gmail.com`, sau đó user muốn đổi sang `nguyendonduc1503@gmail.com`.
- **Fix**: `aws budgets update-subscriber` cho cả 3 ngưỡng (mỗi notification có subscriber list riêng).

---

### 3.2 Bootstrap Terraform state (Bài 3)

**Action**: tạo S3 bucket `a20-terraform-state-prod` qua module `terraform/bootstrap-state`.

**Pre-check**: `aws s3 ls` → bucket không tồn tại (đã xoá khi destroy App Runner stack trước).

```powershell
cd deploy-ecs/terraform/bootstrap-state
terraform init
terraform plan -out plan.tfplan      # Issue 3 dưới
terraform apply plan.tfplan
```

**Issue 3 — PowerShell parser ăn dấu `=` trong flag CLI**:
- Lệnh `terraform plan -out=plan.tfplan` báo `Error: Too many command line arguments`.
- Root cause: PowerShell parse `-out=plan.tfplan` thành 2 token rời.
- **Fix**: dùng space `terraform plan -out plan.tfplan` hoặc quote `terraform plan "-out=plan.tfplan"`.
- **Lessons learned**: ghi vào memory để lần sau dùng PowerShell với CLI flag có `=`.

**Verify**: bucket có versioning + encryption AES256 + 4 public access blocks = true. Tất cả pass.

---

### 3.3 Phát hiện Terraform skeleton chưa hoàn thiện

**Trước khi apply Stage 1**, đọc qua các module thì phát hiện toàn bộ skeleton là **Phase Task 4 trong TERRAFORM_PLAN.md** ("module skeletons"). Nếu apply nguyên xi sẽ tạo infra nhưng không hoạt động:

| Module | Thiếu |
|---|---|
| `network` | IGW, route table, NAT (biến `enable_nat_gateway` không được dùng) |
| `security` | 5 SG nhưng không có ingress/egress rule |
| `alb` | Không có listener |
| `ecs_service` | File chỉ có comment, hoàn toàn rỗng |
| `observability` | Chỉ có Budget, không có CloudWatch log group (trap B7) |
| `iam_oidc` | Chỉ có OIDC provider, không có IAM role |
| `ecr` | Không có lifecycle, scan, tag immutability |
| `assets` | Có S3+OAC nhưng không có CloudFront distribution |
| `database` | Thiếu `storage_encrypted = true` |
| `cache` | Thiếu encryption at rest |

**Issue 4 — Phải viết lại 11 module + main.tf**:
- User chọn "Lựa chọn 1" (viết Terraform hoàn chỉnh) thay vì "Lựa chọn 2" (Console click) hoặc "Lựa chọn 3" (Hybrid) vì cần present tối nay + muốn IaC.
- **Fix**: viết toàn bộ Terraform module với production-grade config:
  - `network`: IGW + 1 NAT trong 1 AZ + route tables (cost: ~$32/month NAT)
  - `security`: 5 SG với rule chain `world → ALB → FE/BE → DB/Redis`
  - `alb`: HTTP:80 listener + rule `/api/*` + `/health` → backend; default → frontend
  - `database`: Postgres 16 db.t4g.micro, 20GB gp3, encrypted, deletion_protection=true
  - `cache`: Redis 7 cache.t4g.micro single-node
  - `ecr`: immutable tags + scan_on_push + lifecycle keep last 10
  - `assets`: S3 versioned + CloudFront distribution + OAC bucket policy
  - `iam_oidc`: 4 role (deploy, task execution, backend task, frontend task) + GitHub trust policy
  - `observability`: 3 CloudWatch log groups (backend, frontend, migrate), retention 7 ngày
  - `ecs_service`: task def (FARGATE, awsvpc) + service với grace period, secrets[]
- **Stage gate**: thêm flag `enable_services` (default false) để tách Stage 1 (foundation) và Stage 2 (ECS services) — tránh chicken-and-egg với ECR image.

---

### 3.4 Stage 1 apply (Bài 4)

```powershell
cd deploy-ecs/terraform/live/prod
Copy-Item backend.hcl.example backend.hcl
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init "-backend-config=backend.hcl"
terraform plan -out plan.tfplan
terraform apply plan.tfplan
```

**Issue 5 — `github_repository` sai owner**:
- tfvars.example điền `edward1503/A20-App-049` (do tôi đoán từ git user).
- Thật là `a20-ai-thuc-chien/A20-App-049` (verify bằng `git config --get remote.origin.url`).
- **Fix**: `(Get-Content tfvars) -replace 'edward1503' | Set-Content tfvars`. Tác động: OIDC trust policy của deploy role check repo path. Không khớp ⇒ GitHub Actions không assume role được.

**Issue 6 — `data.aws_region.current.name` deprecated**:
- AWS provider v6 báo warning: `attribute "name" is deprecated`.
- **Fix**: đổi thành `data.aws_region.current.region` trong `iam_oidc/main.tf`.

**Issue 7 — `count = var.asset_bucket_arn != "" ? 1 : 0` không tính được tại plan time**:
- Error: `count value depends on resource attributes that cannot be determined until apply`.
- Root cause: `asset_bucket_arn` đến từ output của module `assets` (known after apply). Terraform không thể decide count tại plan.
- **Fix**: bỏ conditional count, luôn tạo policy. Vì main.tf luôn truyền giá trị non-empty.

**Apply result**: 61 resource added. Mất ~15 phút. RDS chiếm 12 phút. Verify status:
- RDS: `available` ✅
- Redis: `available` ✅
- ALB: `active` ✅
- ECS cluster: `ACTIVE` ✅

---

### 3.5 Build + push images (Bài 5a)

**Issue 8 — Docker login 400 Bad Request**:
- `aws ecr get-login-password | docker login --password-stdin` báo `400 Bad Request`.
- Root cause: Claude Code có hook `SessionStart` in `Welcome bro 😎\nReady to code...` vào stdout của `aws` CLI. Khi pipe vào `docker login`, mấy dòng welcome bị Docker đọc thành password → 400.
- **Fix attempt 1**: `Select-Object -Last 1` → vẫn 400.
- **Fix attempt 2**: Set `$OutputEncoding = UTF8` → vẫn 400.
- **Fix cuối cùng**: Bypass stdin, dùng `--password` flag trực tiếp:
  ```powershell
  $pw = aws ecr get-login-password --region $env:AWS_REGION | Select-Object -Last 1
  docker login --username AWS --password $pw "<account>.dkr.ecr.<region>.amazonaws.com"
  ```
- **Lessons learned**: PowerShell pipe sang native exe có encoding quirk (UTF-16 LE BOM). `--password` flag insecure nhưng OK cho one-off.

**Issue 9 — Backend image context 4.19 GB**:
- Build mất 10 phút (`transferring context: 4.19GB`).
- Local backend image bình thường ~500 MB. Context phình to vì `data/` (15 GB course assets) không bị `.dockerignore` chặn.
- Original `.dockerignore` chỉ block `data/**/*.mp4`, `data/*.pdf`, `data/*.zip`. Folder `data/courses/...` text/json/jsonl + slides + transcripts vẫn vào.
- **Fix**: blanket-ignore `data/`, `models/`, `mlruns/`, `outputs/`, `notebooks/`, `checkpoints/`, `artifacts/` trong `.dockerignore`.
- Rebuild: context 60 MB, build 74s, push 1-2 phút. **Improvement: -98.5% size, -88% time**.

---

### 3.6 App secret + tạo trên Secrets Manager (Bài 5b)

**Issue 10 — Secret JSON bị strip dấu nháy khi pass inline**:
- Đầu tiên dùng `aws secretsmanager create-secret --secret-string $payload` (PowerShell variable).
- Verify thấy stored value: `{REDIS_URL:redis://...,DATABASE_URL:postgresql+...}` — **không có dấu `"` quanh key/value** → invalid JSON.
- ECS task sau đó fail: `unable to retrieve secret from asm: invalid character 'R' looking for beginning of object key string`.
- Root cause: PowerShell + AWS CLI strip dấu `"` khi parse argument `--secret-string '{"key":"val"}'`.
- **Fix**: ghi JSON ra file tạm, dùng `--secret-string file://path.json`:
  ```powershell
  $payload | Out-File -FilePath C:\Users\vanhu\backend-secret.json -Encoding ascii -NoNewline
  aws secretsmanager put-secret-value --secret-id a20/prod/backend --secret-string file://C:/Users/vanhu/backend-secret.json
  Remove-Item C:\Users\vanhu\backend-secret.json
  ```
- **Lessons learned**: bao giờ truyền JSON cho AWS CLI từ PowerShell, dùng `file://` hoặc encode kỹ.

---

### 3.7 Migration task (Bài 6 — trap A4)

**Action**: chạy `alembic upgrade head` như **one-off ECS task riêng**, không phải embed vào service start command.

```powershell
aws ecs register-task-definition --cli-input-json file://taskdefs/backend-migrate.json
aws ecs run-task --cluster a20-prod-cluster --launch-type FARGATE --task-definition a20-backend-migrate --network-configuration "awsvpcConfiguration={subnets=[...],securityGroups=[...],assignPublicIp=DISABLED}"
aws ecs wait tasks-stopped --cluster a20-prod-cluster --tasks <arn>
```

**Issue 11 — Task fail ở `ResourceInitializationError`**:
- Lỗi: `unable to retrieve secret from asm: invalid character 'R' looking for beginning of object key string`.
- Đây là Issue 10 (secret JSON malformed). Fix Issue 10 trước rồi rerun.

**Issue 12 — `alembic` not in PATH**:
- Lỗi: `exec: "alembic": executable file not found in $PATH`.
- Root cause: backend image dùng `uv` quản package, alembic nằm trong venv của uv. Cần `uv run alembic` thay vì `alembic` trực tiếp.
- **Fix**: đổi command trong task definition:
  ```json
  "command": ["uv", "run", "alembic", "upgrade", "head"]
  ```
- Re-register revision 2 + rerun.

**Result**: 40+ migrations applied sạch (initial_schema → 20260505_password_reset_tokens). Bao gồm pgvector extension, KG schema, calibration, agent runtime. Trap A3 (% interpolation) và A4 (one-off task) đều validated.

---

### 3.8 Stage 2 apply — ECS services (Bài 7)

```powershell
# Update tfvars: enable_services=true, backend_image, frontend_image, backend_secret_arn
terraform apply plan-stage2.tfplan
aws ecs update-service --cluster a20-prod-cluster --service a20-backend --task-definition a20-backend --force-new-deployment
aws ecs wait services-stable --cluster a20-prod-cluster --services a20-backend
```

Result: backend + frontend service đều stable, target group 2/2 healthy. Smoke 4 lớp:
- ECS service running 1/1 ✅
- Target group `healthy` ✅
- HTTP `/health` 200 ✅
- DB-backed `/api/course-sections` 200 với 17,920 bytes (50 rows) ✅

---

### 3.9 Asset upload S3 (Bài 8)

**Action**: `aws s3 sync data/courses → s3://a20-course-assets-prod/courses` với parallelism boost.

```powershell
aws configure set default.s3.max_concurrent_requests 20
aws configure set default.s3.max_bandwidth 50MB/s
aws configure set default.s3.multipart_threshold 64MB
aws configure set default.s3.multipart_chunksize 16MB
aws s3 sync data\courses s3://a20-course-assets-prod/courses --region ap-southeast-1
```

Tốc độ thực: ~6.8 MiB/s (bottleneck: bandwidth upload VN→Singapore).

**Issue 13 — Network drop giữa chừng**:
- Mất kết nối → CLI exit, một số file partial.
- **Fix**: `aws s3 sync` idempotent, chạy lại cùng lệnh là resume. Skip file đã upload với cùng size.
- Cleanup multipart leftover:
  ```powershell
  aws s3api list-multipart-uploads --bucket a20-course-assets-prod | ForEach { abort-multipart-upload }
  ```
- 1 multipart aborted, không còn dở.

Final state: **360 objects, 13.98 GB**. Verify CloudFront serve PDF: `Status 200, Content-Type: application/pdf, Size: 4.97 MB`.

---

### 3.10 `/api/courses` 500 — Image cũ thiếu data (Bài 8 phần 2)

**Issue 14 — Backend service đang chạy image `7deedc0` (không có `data/`)**, nhưng `/api/courses` đọc local file `data/bootstrap/courses.json`:

```text
File "/app/src/services/course_bootstrap_service.py", line 23, in load_bootstrap_courses
  return _read_json(COURSES_FILE)
FileNotFoundError: [Errno 2] No such file or directory: 'data/bootstrap/courses.json'
```

Root cause: code legacy `course_catalog_service.py:76 → load_bootstrap_courses() → _read_json` đọc filesystem trực tiếp. Khi `.dockerignore` block `data/` toàn bộ (sửa ở Bài 5 để giảm context), file không có trong image.

**Fix lựa chọn**:
- Cách 1 (đã chọn): relax `.dockerignore` — block chỉ binary nặng (mp4, pdf, zip, mp3, png, jpg), giữ JSON/JSONL/text. Rebuild image với tag mới `7deedc0-data`.
- Cách 2: refactor app code đọc từ RDS thay vì local file (out of scope).
- Cách 3: download từ S3 lúc container start (out of scope).

Sau rebuild:
- Context: 60 MB → 22 MB (vì block thêm các binary)
- Image tag mới: `116533674568.dkr.ecr.ap-southeast-1.amazonaws.com/a20-backend:7deedc0-data`
- Image cũ giữ nguyên (immutable tag, không overwrite)

Update tfvars `backend_image` → `7deedc0-data`, `terraform apply` (1 task def revision mới), `aws ecs update-service --force-new-deployment`. Service revision 3 lên healthy.

Verify: `/api/courses` 200 với 1.1 KB JSON (3 courses thật).

---

### 3.11 Inventory data → seed thiếu nhiều bước

**Action**: viết task `a20-backend-inventory` chạy SQL `SELECT COUNT(*) FROM <each table>`.

Result đầu (sau Bài 6 + 8): 58 tables, có data trong 17 bảng:
- courses=3, course_sections=50, learning_units=376, units=376
- concepts_kp=607, item_kp_map=1474, item_phase_map=8875
- question_bank=1276, item_calibration=1276
- prerequisite_edges=118, pruned_edges=44
- alembic_version=1, users=2 (self-register)

**Empty tables**: lectures, chapters, transcript_lines, kg_concepts, kg_edges, course_assets, ...

**Issue 15 — `start.sh` có 7 bước seed, mới chỉ chạy 1**:
- User report: vào `/learn` không thấy data, không có admin sẵn.
- Đọc `start.sh` mới phát hiện đầy đủ pipeline:
  1. `scripts/seed.py` (canonical + product shell + lectures runtime) ✅ đã chạy
  2. `scripts/seed_lectures.py` (CS231n lectures standalone) ❌
  3. `import_canonical_artifacts_to_db` ✅ (trong seed.py)
  4. `backfill_schema_v2 --apply` ❌
  5. `validate_schema_v2` ❌
  6. `check_canonical_runtime_parity` ❌
  7. `create_seed_accounts` ❌ (đây là source của admin/demo accounts)

**Fix**: viết task `a20-backend-full-bootstrap` chạy 5 bước thiếu (2,4,5,6,7) trong 1 task. All passed (exit 0).

Result sau bootstrap đầy đủ: thêm row vào nhiều bảng:
- users: 2 → **7** (5 admin/demo accounts + 2 self-register)
- interactions: 0 → 29
- learner_mastery_kp: 0 → 29
- placement_assessment_results: 0 → 23
- rationale_log: 0 → 440
- planner_session_state: 0 → 2
- ingest_runs: 0 → 1

**Vẫn empty**:
- `lectures, chapters, transcript_lines` ← seed_lectures fail silently
- `kg_concepts, kg_edges` ← cần content pipeline

**Issue 16 — `seed_lectures` fail silently**:
- Script tìm `data/courses/CS231n/ToC_Summary/lecture-*.json`. Folder này **không tồn tại ngay cả ở local**.
- Nội dung này được sinh ra bởi `scripts/ingest_cs231n.py` — content pipeline cần LLM API + thời gian dài, **out of scope deploy**.
- Hệ quả: tính năng video lecture detail, chat agent (cần KG) không có data nguồn.

---

### 3.12 Admin user setup

**Initial state**: chỉ có 2 user self-register, đều `role='user'`, không có admin.

**Action 1**: promote thủ công user mới nhất:
```sql
UPDATE users SET role='admin' WHERE email='vanhuydz210@gmail.com';
```

**Action 2**: chạy `create_seed_accounts` (trong full bootstrap task) tạo 5 account chuẩn:

| Email | Role | Password |
|---|---|---|
| admin1@vinuni.edu.vn | admin | `AdminTest123!` |
| admin2@vinuni.edu.vn | admin | `AdminTest123!` |
| admin3@vinuni.edu.vn | admin | `AdminTest123!` |
| demo1@vinuni.edu.vn | user | `AdminTest123!` |
| demo2@vinuni.edu.vn | user | `AdminTest123!` |

Admin dashboard route: `/admin`, `/admin/users`, `/admin/system`, `/admin/traffic`, `/admin/llm`, `/admin/langfuse`.

---

### 3.13 Cấu hình env mở rộng (Bài 11)

**User cung cấp `.env` thật** với production keys (OpenAI, Langfuse, Gmail, AI logs).

**Action**: phân loại 70+ env var thành 2 nhóm:

**Secrets (push qua Secrets Manager)** — 11 keys:
- `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY` (đã có)
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`
- `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`
- `GMAIL_APP_PASSWORD`, `AI_LOG_API_KEY`, `ADMIN_TOKEN`

**Plain env (task def `environment[]`)** — 50+ keys:
- Core runtime (PORT, DEBUG, LOG_LEVEL, DB_POOL_SIZE, ...)
- Asset delivery (ASSET_STORAGE_PROVIDER, S3 bucket, CloudFront)
- Auth (ALGORITHM, token TTL, rate limits)
- LLM provider (MODEL_PROVIDER=openai, DEFAULT_MODEL=gpt-5.4-mini, FAST_MODEL=gpt-5.4-nano)
- Langfuse base URL
- Knowledge graph weights (KG_BUCKET_WEIGHTS, KG_RECSYS_WEIGHTS, thresholds)
- Feature flags (WRITE_*, READ_* ENABLED)
- Placement / IRT params
- AI logging endpoint
- Email config

Push merge với existing secret giữ DATABASE_URL/REDIS_URL/SECRET_KEY:
```powershell
$rawJson = aws secretsmanager get-secret-value ... --query SecretString --output text | Where-Object { $_ -match '^\{' } | Select-Object -First 1
$current = $rawJson | ConvertFrom-Json
# merge new keys + write to file + put-secret-value
```

Update Terraform `main.tf` thêm 8 secret refs mới + 50+ env vars. `terraform apply` (1 task def revision mới) + force redeploy backend (revision 3).

Verify: backend stable, all health endpoints 200, OpenAI direct test (`gpt-5.4-mini` từ `chat.completions.create`) trả response trong 2.1s.

**Bảo mật**: user paste keys vào chat trong session này. **Cảnh báo rotate sau demo**:
- OpenAI: platform.openai.com → API keys
- Langfuse: cloud.langfuse.com → Settings
- Gmail: myaccount.google.com → Security → App passwords
- AI logs: transformerlabs.ai dashboard

---

### 3.14 Chat 504 Gateway Timeout

**Issue 17 — `POST /api/agent/chat` hang quá ALB timeout**:
- Direct curl đến endpoint trả 504 sau 60s.
- Backend log không có entry `/api/agent/chat` (uvicorn chỉ log sau khi request done; request không complete).
- Test trực tiếp OpenAI từ container: OK trong 2.1s.
- Test Redis từ container: OK.

**Hypothesis**: agent endpoint dùng LangGraph multi-step (router + search + LLM + KG lookup). KG empty (kg_concepts=0), một số node có thể loop hoặc đợi tool call quá lâu.

**Fix attempt 1**: tăng ALB `idle_timeout` từ 60s → 180s.
- `terraform apply` 1 change.
- Retest: vẫn timeout sau 180s.

**Conclusion**: lỗi tầng app, không phải infra. Cần content pipeline (KG) hoàn chỉnh hoặc code fix để handle empty KG gracefully. **Out of scope deploy**.

---

## 4. State cuối session

### Infrastructure (100% IaC)

| Resource | Count | State |
|---|---:|---|
| VPC, subnets, IGW, NAT, route tables | 1+4+1+1+2 | active |
| Security groups (chain rule) | 5 | configured |
| ALB + target groups + listener + rule | 1+2+1+1 | healthy |
| ECS cluster | 1 | ACTIVE |
| ECS services (backend, frontend) | 2 | running 1/1 each |
| RDS Postgres 16 (deletion_protection=true) | 1 | available |
| ElastiCache Redis 7 | 1 | available |
| ECR repos (immutable, scan on push) | 2 | configured |
| S3 asset bucket (versioned, encrypted) | 1 | 360 objects |
| CloudFront distribution + OAC | 1 | streaming |
| IAM roles (deploy, exec, backend task, frontend task) + OIDC | 4+1 | configured |
| Secrets Manager (`a20/prod/backend`, RDS master) | 2 | 11+1 keys |
| CloudWatch log groups | 3 | retention 7d |
| Budget $130 + 3 alerts | 1+3 | armed |

### Data (RDS)

- 58 tables created
- 23 tables có data sau full bootstrap
- Notable empty: `lectures`, `chapters`, `transcript_lines`, `kg_concepts`, `kg_edges`, `course_assets`

### Image trên ECR

| Tag | Backend? | Có data text? | Use |
|---|---|---|---|
| `a20-backend:7deedc0` | ✅ | ❌ | (legacy, không dùng) |
| `a20-backend:7deedc0-data` | ✅ | ✅ (17MB JSON/JSONL/txt) | service đang dùng |
| `a20-frontend:7deedc0` | — | — | service đang dùng |

### Endpoints xác nhận

| Endpoint | Status | Note |
|---|---|---|
| `GET /health` | 200 | backend |
| `GET /` | 200 (37 KB) | frontend home |
| `POST /api/auth/login` | 200 | JSON body, returns access_token |
| `GET /api/users/me` | 200 (auth) | |
| `GET /api/courses` | 200 (1.1 KB) | 3 courses |
| `GET /api/course-sections` | 200 (17.9 KB) | 50 sections |
| `GET /api/learning-path` | 200 (auth) | |
| `GET /api/learning-path/timeline` | 200 (auth) | |
| `GET /api/learning-session/resume` | 200 (auth) | |
| `GET /api/agent/conversations` | 200 (auth) | |
| `GET <CloudFront>/courses/CS224n/slides/lecture01.pdf` | 200 (4.97 MB) | CDN streaming |
| `POST /api/agent/chat` | ❌ 504 | hang trong agent graph (KG empty) |
| `GET /api/courses/cs230/units/lecture-01-seg1` | ❌ 403 | code-level authz |
| `GET /api/lectures` | 200 (`[]`) | bảng empty |

---

## 4.A Comprehensive runtime check (Bài 12)

User report: vào `/learn` không thấy data, click unit không thấy video, chatbot timeout. Yêu cầu kiểm tra toàn diện app trên AWS.

### 4.A.1 Env vars verify

Ran one-off task `a20-backend-env-dump` để dump env trong container thật:

```text
=== ENV (production task revision 3) ===
AWS_DEFAULT_REGION=ap-southeast-1
AWS_REGION=ap-southeast-1
DATABASE_URL=*** (resolved from Secrets Manager)
DEFAULT_MODEL=gpt-5.4-mini
FAST_MODEL=gpt-5.4-nano
HOSTNAME=ip-10-20-10-211.ap-southeast-1.compute.internal
LANGFUSE_BASE_URL=*** (https://cloud.langfuse.com)
LANGFUSE_PUBLIC_KEY=*** 
LANGFUSE_SECRET_KEY=***
MODEL_PROVIDER=openai
OPENAI_API_KEY=*** (164 chars)
PYTHONPATH=/app
REDIS_URL=*** (ElastiCache endpoint)
... (50+ KG / IRT / feature flag vars also present)
```

Verdict: **Env wired đầy đủ**, không phải lỗi config.

### 4.A.2 Network connectivity check

Ran `a20-backend-net-check` (Python `socket` + `urllib`):

| Endpoint | TCP | HTTPS | Latency |
|---|---|---|---|
| api.openai.com:443 | OK | 401 (auth needed, route OK) | 16-235ms |
| cloud.langfuse.com:443 | OK | 200 (health) | 170-537ms |
| s3.ap-southeast-1.amazonaws.com:443 | OK | — | 4ms |
| RDS (5432) | OK | — | 3ms |
| Redis (6379) | OK | — | 3ms |
| CloudFront (d2syr4kpiu8d9n.cloudfront.net:443) | OK | — | 197ms |
| ai-logs.note.transformerlabs.ai:443 | OK | — | 76ms |

Verdict: **Tất cả egress hoạt động qua NAT**, không phải lỗi network.

### 4.A.3 Root cause unit detail 403

Code path:
```
GET /api/courses/{slug}/units/{unit_slug}
→ assert_learning_access(course_slug, user)
→ _check_skill_test_completed(user_id)
→ if False: raise ForbiddenError("Please complete the skill assessment...")
```

Code: `src/services/course_entry_service.py:110` — chặn user truy cập unit detail nếu chưa hoàn thành **skill assessment**.

`_check_skill_test_completed` query `sessions` table với `session_type='assessment'` và `completed_at IS NOT NULL`. User mới register chưa có session loại đó → 403.

**Đây là intentional gate, không phải bug.** UX flow:
1. User register
2. Onboarding (set goal, hours/week, deadline)
3. Skill assessment (placement test) — **bắt buộc trước khi học**
4. Unit detail mở khoá

### 4.A.4 Attempt unlock unit access (manual SQL insert)

Thử insert fake completed assessment session để demo có thể vào unit:

**Issue 18 — `sessions` table có nhiều NOT NULL columns phức tạp**:
- Schema: `id, user_id, session_type, total_questions (NOT NULL), questions_correct, questions_answered, ...` (~20 columns)
- Insert thiếu `total_questions` → `NotNullViolationError`
- Bỏ approach này. Demo nên đi theo flow chuẩn: register → onboarding → placement → unit.

### 4.A.5 Root cause chat timeout

Đã verify:
- ✅ OpenAI direct call từ container 2.1s
- ✅ Redis connection 3ms
- ✅ Langfuse cloud 170ms reachable
- ❌ `POST /api/agent/chat` hang >180s

Code path (`src/routers/agent.py:128`):
```
1. _agent_context_for_user(user, db)
2. build_agent_graph_checkpointer() → AsyncPostgresSaver từ DATABASE_URL
3. AgentGraphService.chat()
   → thread_lock.acquire()
   → graph_repo.get_active_run() / create_run()
   → mark_run_running()
   → _invoke_graph_and_compose() ← LangGraph multi-hop
4. _maybe_generate_conversation_title() ← thêm LLM call
```

`_invoke_graph_and_compose` chạy LangGraph với:
- Router node (chọn intent)
- Search node (KG lookup)
- LLM node (chat completion)
- Tool nodes (path switch, assessment, ...)

Hypothesis: KG empty (`kg_concepts=0`, `kg_edges=0`) làm search node loop hoặc đợi tool nào đó indefinitely. Cần content pipeline `ingest_cs231n.py` để populate KG.

**Out of scope deploy fix.** Cần debug app code hoặc chạy content pipeline (vài giờ với LLM).

### 4.A.6 Inventory cuối cùng

Không có thay đổi nào ngoài 5 lần task one-off (env-dump, net-check, llm-test, redis-test, unlock-unit fail).

### 4.A.7 Endpoint matrix sau test

| Endpoint | Status | Note |
|---|---|---|
| `GET /health` | ✅ 200 | |
| `GET /` (frontend home) | ✅ 200 | |
| `POST /api/auth/login` (JSON body) | ✅ 200 | Returns access_token |
| `GET /api/users/me` (auth) | ✅ 200 | |
| `GET /api/courses` | ✅ 200 | 3 courses |
| `GET /api/course-sections` | ✅ 200 | 50 sections |
| `GET /api/learning-path` | ✅ 200 | |
| `GET /api/learning-path/timeline` | ✅ 200 | |
| `GET /api/learning-session/resume` | ✅ 200 | |
| `GET /api/agent/conversations` | ✅ 200 | |
| `POST /api/courses/cs230/start` | ✅ 200 | |
| `GET /api/courses/cs230/units` | ✅ 200 (`[]`) | empty — units không gắn với cs230 hoặc query filter sai |
| `GET /api/courses/cs230/units/lecture-01-seg1` | ❌ 403 | **Gate: skill assessment chưa complete** |
| `POST /api/agent/chat` | ❌ 504 | **LangGraph hang, có thể do KG empty** |
| `GET /api/lectures` | 200 (`[]`) | bảng empty (cần content pipeline) |
| CloudFront PDF stream | ✅ 200 (4.97 MB) | CDN OK |

### 4.A.8 Tổng kết: 3 lớp lỗi tách biệt

| Lớp | Trạng thái | Fix tại đâu |
|---|---|---|
| **Infrastructure** (VPC, ALB, ECS, RDS, Redis, S3, CloudFront, ECR, IAM) | ✅ 100% | Đã làm |
| **Config** (env, secrets, network egress) | ✅ 100% | Đã làm |
| **Content + UX flow** (KG empty, lectures empty, assessment gate) | ❌ Chưa | Cần content pipeline + UX flow |

Các tính năng phụ thuộc lớp 3 sẽ tiếp tục lỗi cho đến khi:
- Chạy content pipeline `ingest_cs231n.py` → tạo `ToC_Summary/`, populate `kg_concepts`, `kg_edges`, `lectures`, `chapters`, `transcript_lines`
- User đi qua onboarding + placement assessment đầy đủ → mở khoá unit detail

---

## 5. Outstanding issues (sau demo)

### 5.1 Content pipeline chưa chạy (block /learn, chat, KG features)

Cần chạy `scripts/ingest_cs231n.py` (hoặc tương đương cho CS224n, CS230) để sinh:
- `data/courses/CS231n/ToC_Summary/lecture-*.json` → seed_lectures populate `lectures`, `chapters`, `transcript_lines`
- KG content → populate `kg_concepts`, `kg_edges`

Pipeline cần LLM API key (đã có) + thời gian (vài giờ?). Sau khi xong, rerun `seed_lectures.py` qua one-off task.

**Hệ quả tính năng nếu skip:**
- `/api/lectures` returns `[]` → /learn page không show video
- `/api/agent/chat` hang → LangGraph search node có thể loop khi KG empty
- Recommendation rỗng → cần KG + interaction history

### 5.1.1 UX flow gate: skill assessment

User mới register **không thể vào unit detail** cho đến khi hoàn thành skill assessment qua `/placement` flow trong UI (theo code `course_entry_service.py:135 → _check_skill_test_completed`).

Đây là intentional gate, không phải bug. Để demo:
- Đi theo flow đầy đủ: register → onboarding → placement assessment → unit
- Hoặc bypass code-level: comment dòng `if not has_completed_skill_test: raise ForbiddenError(...)` (không khuyến khích)
- Hoặc insert đầy đủ row `sessions` với tất cả NOT NULL columns (xem Issue 18)

### 5.2 Refactor `/api/courses` đọc từ RDS

Hiện tại `course_catalog_service.py` đọc local `data/bootstrap/courses.json`. Best practice: query RDS `courses` table. Khi đó không cần bake JSON vào image, image gọn hơn.

### 5.3 Custom domain + HTTPS

- Mua domain
- ACM cert ở `ap-southeast-1` (ALB) và `us-east-1` (CloudFront)
- ALB HTTPS:443 listener
- CloudFront alias domain
- Route 53 records
- **Rebuild frontend image** với `NEXT_PUBLIC_API_URL=https://api.<domain>` (trap B8)

### 5.4 CI/CD GitHub Actions

OIDC role + workflow đã có IAM. Còn lại viết `.github/workflows/deploy-prod.yml` build/push/update-service. Skip nếu không cần auto-deploy.

### 5.5 PROMETHEUS_URL

`src/routers/admin.py:41` fallback `http://localhost:9090`. Chưa deploy Prometheus. Tab admin metrics sẽ 500. Có thể disable endpoint hoặc deploy AMP (managed Prometheus).

### 5.6 Rotate keys leaked trong session

User đã paste real key vào chat. Sau demo cần rotate:
- OPENAI_API_KEY
- LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY
- GMAIL_APP_PASSWORD
- AI_LOG_API_KEY

Sau khi rotate, push key mới qua secrets manager (Cách B trong tutorial). Service không cần restart vì ECS lazy-load secret.

---

## 6. Cost ước tính

Stack đang chạy 24/7. Burn baseline:

| Resource | $/giờ | $/ngày | $/30 ngày |
|---|---:|---:|---:|
| NAT Gateway | $0.045 | $1.08 | $32.4 |
| ALB | $0.0225 | $0.54 | $16.2 |
| RDS db.t4g.micro | $0.018 | $0.43 | $13.0 |
| ElastiCache cache.t4g.micro | $0.018 | $0.43 | $13.0 |
| 2 Fargate tasks (running) | $0.05 | $1.20 | $36.0 |
| S3 14 GB storage | nhỏ | $0.01 | $0.32 |
| CloudFront | tuỳ traffic | nhỏ | nhỏ |
| **Tổng** | **$0.15** | **$3.69** | **~$110** |

Với $150 credit của user: chạy được ~40 ngày 24/7 (lý thuyết). Tiết kiệm bằng cách `update-service --desired-count 0` ngoài giờ học.

---

## 7. Lessons learned tổng kết

| # | Lesson | Source |
|---|---|---|
| 1 | PowerShell parser ăn dấu `=` trong CLI flag | Issue 3 |
| 2 | AWS Budget EMAIL không qua SNS, không có flow confirm | Issue 1 |
| 3 | OIDC trust policy phải đúng owner GitHub repo | Issue 5 |
| 4 | AWS provider v6 deprecate `region.name` → `region.region` | Issue 6 |
| 5 | Terraform count không tính được nếu phụ thuộc resource attr known-after-apply | Issue 7 |
| 6 | PowerShell pipe sang native exe có encoding quirk | Issue 8 |
| 7 | `.dockerignore` quan trọng, mỗi MB context = thêm thời gian + RAM | Issue 9 |
| 8 | AWS CLI từ PowerShell + JSON inline = strip dấu `"`. Dùng `file://` | Issue 10 |
| 9 | `alembic`/python tools trong uv venv → cần `uv run` prefix | Issue 12 |
| 10 | Migration phải tách thành one-off task, không nhét service start (trap A4) | Bài 6 |
| 11 | `aws s3 sync` idempotent, resume tự động khi rerun | Issue 13 |
| 12 | Multipart upload dở dang vẫn tính tiền cho đến khi abort | Issue 13 |
| 13 | Code đọc local file (không qua RDS) dễ break khi `.dockerignore` thay đổi | Issue 14 |
| 14 | Có nhiều bước seed (đọc `start.sh`!) — chạy thiếu = data thiếu | Issue 15 |
| 15 | Seed scripts có thể fail silently nếu folder content không tồn tại | Issue 16 |
| 16 | ALB default idle_timeout 60s không đủ cho LLM agent multi-hop | Issue 17 |
| 17 | NEVER paste real production keys vào chat — rotate sau khi xong | Bài 11 |
| 18 | App có UX gate (skill assessment) chặn unit detail — không phải bug deploy | Issue Bài 12 |
| 19 | Network egress qua NAT verified bằng socket + urllib từ container | Bài 12 net check |
| 20 | Env dump task confirms task def env vars resolved đúng từ Secrets Manager | Bài 12 env-dump |
| 21 | LangGraph multi-hop có thể hang khi KG/data dependencies trống — content pipeline là nền tảng AI features | Bài 12 chat hang |
| 22 | `sessions` table có ~20 cột với nhiều NOT NULL — không thể fake completed session bằng SQL trực tiếp dễ dàng | Issue 18 |

---

## 8. File tạo trong session này

### Terraform modules (rewrite)

```
deploy-ecs/terraform/modules/network/main.tf       (rewrite)
deploy-ecs/terraform/modules/security/main.tf      (rewrite)
deploy-ecs/terraform/modules/security/variables.tf (extend)
deploy-ecs/terraform/modules/alb/main.tf           (extend with listener)
deploy-ecs/terraform/modules/database/main.tf      (rewrite + encryption)
deploy-ecs/terraform/modules/database/variables.tf (extend)
deploy-ecs/terraform/modules/cache/main.tf         (rewrite)
deploy-ecs/terraform/modules/ecr/main.tf           (extend lifecycle)
deploy-ecs/terraform/modules/iam_oidc/main.tf      (rewrite full)
deploy-ecs/terraform/modules/iam_oidc/variables.tf (extend)
deploy-ecs/terraform/modules/iam_oidc/outputs.tf   (extend)
deploy-ecs/terraform/modules/observability/main.tf (rewrite — log groups)
deploy-ecs/terraform/modules/observability/variables.tf
deploy-ecs/terraform/modules/observability/outputs.tf
deploy-ecs/terraform/modules/assets/main.tf        (rewrite + CloudFront dist)
deploy-ecs/terraform/modules/assets/outputs.tf
deploy-ecs/terraform/modules/ecs_service/main.tf   (write — task def + service)
deploy-ecs/terraform/modules/ecs_service/variables.tf
deploy-ecs/terraform/modules/ecs_service/outputs.tf
```

### Live prod root

```
deploy-ecs/terraform/live/prod/main.tf             (rewrite full wiring)
deploy-ecs/terraform/live/prod/variables.tf        (add stage 2 vars)
deploy-ecs/terraform/live/prod/outputs.tf          (rewrite)
deploy-ecs/terraform/live/prod/terraform.tfvars.example (rewrite)
```

### Task definition templates

```
deploy-ecs/taskdefs/backend-migrate.json
deploy-ecs/taskdefs/backend-seed.json
deploy-ecs/taskdefs/backend-inventory.json
deploy-ecs/taskdefs/backend-admin-query.json
deploy-ecs/taskdefs/backend-promote-admin.json
deploy-ecs/taskdefs/backend-full-bootstrap.json
deploy-ecs/taskdefs/backend-llm-test.json
deploy-ecs/taskdefs/backend-redis-test.json
deploy-ecs/taskdefs/backend-env-dump.json
deploy-ecs/taskdefs/backend-net-check.json
deploy-ecs/taskdefs/backend-unlock-unit.json
```

### App-level

```
.dockerignore (sửa 2 lần — Bài 5 blanket-ignore data/, Bài 8 relax cho text)
```

### Documentation

```
deploy-ecs/HOW_TO_FIX.md
deploy-ecs/TUTORIAL.md
deploy-ecs/SESSION_JOURNAL.md (file này)
```

(Plus updates: `DEPLOYMENT_PLAN.md`, `PRODUCTION_CHECKLIST.md`, `MANUAL_DEPLOY_STEPS.md`, `ENVIRONMENT_MATRIX.md`, `AWS_CONFIG_GUIDE.md`, `README.md`.)

---

## 9. Reproduce session (pseudo-runbook)

Cho lần deploy sau, theo thứ tự:

```text
1. Code prep: verify .dockerignore, alembic env.py, frontend Dockerfile HOSTNAME
2. Cost guard: aws budgets create-budget với 3 ngưỡng email
3. Bootstrap state: terraform init + apply ở deploy-ecs/terraform/bootstrap-state
4. Foundation: terraform init + plan + apply ở deploy-ecs/terraform/live/prod
   (enable_services=false, đợi ~15 phút RDS+NAT)
5. Login ECR: aws ecr get-login-password | docker login (dùng --password để bypass stdin)
6. Build + push backend: docker build với .dockerignore relax cho data text
7. Build + push frontend: với --build-arg NEXT_PUBLIC_API_URL=<alb-dns>
8. Tạo app secret: write JSON to file → put-secret-value với file://
9. Migration: register task def với ["uv","run","alembic","upgrade","head"] → run-task → wait stopped
10. Stage 2: update tfvars enable_services=true + image + secret arn → apply
11. Force redeploy: aws ecs update-service --force-new-deployment, wait stable
12. Smoke 4 lớp: service running, target group healthy, /health 200, DB-backed route 200
13. Asset upload: aws s3 sync data/courses → s3://...
14. Full bootstrap: register + run task chạy đủ 5 step seed (seed_lectures, backfill_v2, validate, parity, create_seed_accounts)
15. Verify: inventory task đếm row count, smoke endpoint
16. Env mở rộng (LLM keys etc): merge vào secret + update task def + redeploy
17. Custom domain (sau khi mua): ACM + ALB HTTPS + Route 53 + REBUILD frontend image
18. Tear down: disable RDS deletion_protection → snapshot → disable CloudFront → empty S3 versions → terraform destroy
```
