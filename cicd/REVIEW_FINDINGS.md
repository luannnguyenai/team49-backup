# CI/CD Review Findings — `cicd/` đối chiếu `deploy-ecs/`

**Ngày review**: 2026-05-10
**Phạm vi**: `cicd/workflows/`, `cicd/scripts/`, `cicd/taskdefs/` đối chiếu với `deploy-ecs/AWS_CICD_GUIDE.md`, `deploy-ecs/SESSION_JOURNAL.md`, và state đã deploy thực tế.
**Trạng thái cicd/**: draft, chưa promote sang `.github/workflows/`.

---

## 1. Bối cảnh

ECS production đã deploy hoàn chỉnh ngày 2026-05-09→10 (xem `deploy-ecs/SESSION_JOURNAL.md`):
- 63 Terraform resources (VPC, ALB, ECS cluster, RDS, ElastiCache, ECR, S3+CloudFront, Secrets Manager, IAM/OIDC, observability).
- App release thực hiện **thủ công** qua PowerShell: `docker build` → `docker push` → `aws ecs register-task-definition` → `aws ecs update-service` → smoke. 5 backend revisions, 1 frontend revision đã chạy. Endpoint matrix final ✅ (Section 4.B.5 + 4.C.4).
- Section 5.4 SESSION_JOURNAL: *"OIDC role + workflow đã có IAM. Còn lại viết `.github/workflows/deploy-prod.yml` build/push/update-service."*

Mục đích `cicd/` = đóng gói release loop thủ công đó thành GitHub Actions workflow tự động, theo spec `AWS_CICD_GUIDE.md`.

`.github/workflows/` hiện có:
- `ci.yml` — active.
- `terraform.yml` — dead code (path filter `deploy/terraform/**` không tồn tại; thật là `deploy-ecs/terraform/**`).
- `kg-sync.yml` — knowledge graph sync, không liên quan.

**Không có App Runner, không có Vercel/Railway** trong repo. App Runner chỉ là context lịch sử trong `PLATFORM_ANALYSIS.md` ("Why not App Runner") và Section 1 SESSION_JOURNAL.

---

## 2. Verdict

Kiến trúc `cicd/` **đúng spec** `AWS_CICD_GUIDE.md`: 8-step workflow shape, 12 vars/secrets, OIDC, immutable SHA tag, concurrency `deploy-production`, 4-layer smoke gate (services-stable + TG healthy + HTTP 200 + DB-backed route). Khớp các trap A1–A6 / B1–B8 trong `HOW_TO_FIX.md`.

**Có 4 BLOCKER + 6 nên fix** trước khi promote.

---

## 3. Đối chiếu spec ↔ thực tế ↔ `cicd/`

| Yêu cầu | Spec deploy-ecs | Thực tế đã chạy | `cicd/` implement | Kết luận |
|---|---|---|---|---|
| Region | `ap-southeast-1` | acct 116533674568 | `${vars.AWS_REGION}` | ✅ |
| OIDC, không AWS keys | Bắt buộc | Issue 5: trust policy phải đúng `a20-ai-thuc-chien/A20-App-049` | `configure-aws-credentials@v4 + role-to-assume` | ✅ |
| Immutable SHA tag | Bắt buộc | `7deedc0` (+suffix `-data`, `-units`) | `tag=${GITHUB_SHA}` | ✅ default; ⚠️ không hỗ trợ tag suffix |
| Secrets qua `secrets[]` | trap B4 | 11 keys Secrets Manager | `valueFrom: __BACKEND_SECRET_ARN__:KEY::` | ✅ |
| Role tách execution/task | trap B5 | 4 role qua `iam_oidc` module | `executionRoleArn` ≠ `taskRoleArn` | ✅ |
| Migration one-off task | trap A4 | Bài 6: `aws ecs run-task` migrate | `run-ecs-task.sh` + `backend-migrate.json.tpl` | ✅ |
| Smoke 4-lớp | trap B6 | Bài 7: `/api/course-sections` 50 rows | `wait-ecs-service.sh` + `smoke-ecs.sh` | ✅ |
| Health grace BE 60s / FE 120s | trap B2 | Set ở Terraform service | tpl không override | ✅ |
| CW log group có sẵn | trap B7 | Bài 4: 3 log group `backend`, `frontend`, `migrate` | Workflow không pre-flight | ⚠️ N4 |
| `AGENT_GRAPH_CHECKPOINTER_SETUP=false` | Bài 13a fix chat hang | Đã set qua Terraform | tpl env có | ✅ |
| Frontend `NEXT_PUBLIC_API_URL` build-time | trap B8 | Hiện trỏ ALB DNS, chưa cutover | Build args truyền `$PRODUCTION_BACKEND_URL` | ✅ với điều kiện vars cập nhật |
| ECR immutable + scan-on-push | `ecr` module | Đã set | Workflow không kiểm | ✅ |
| Rollback path | Re-register revision cũ | Manual | Input `image_tag` redeploy | ✅ |
| Bootstrap (seed_lectures + backfill_schema_v2) | One-off | Bài 8–11 thủ công | `backend-bootstrap.json.tpl` + flag `run_bootstrap` | ✅ logic; ❌ template B3 |

---

## 4. BLOCKER

> **STATUS (2026-05-10): All 4 blockers FIXED in commit. Pending: GitHub Variables setup + `terraform apply` + workflow promotion.**

### B1. CloudFront smoke env var mismatch ✅ FIXED
- `scripts/smoke-ecs.sh:39` đòi `CLOUDFRONT_SMOKE_URL`.
- `workflows/deploy-ecs-prod.yml:76` chỉ truyền `CLOUDFRONT_DOMAIN` (domain trần).
- Step 254-257 sẽ fail ngay khi `smoke_cloudfront=true`.
- **Fix**: thêm `vars.CLOUDFRONT_SMOKE_URL` (full URL trỏ object đã upload, ví dụ `https://<cf>/courses/cs230/lectures/L01.pdf`); hoặc đổi script tự build từ `CLOUDFRONT_DOMAIN` + `CLOUDFRONT_SMOKE_KEY`.

### B2. CI workflow không trigger khi sửa `cicd/**` hoặc `deploy-ecs/**` ✅ FIXED
- `.github/workflows/ci.yml:43-61` filter `repo_config: deploy/**` (path không tồn tại). Thiếu `cicd/**` và `deploy-ecs/**`.
- Sửa task-def hoặc Terraform module sẽ không được lint/validate.
- **Fix**: sửa filter `repo_config` thành `cicd/**` + `deploy-ecs/**` + giữ `.github/workflows/**`.

### B3. Bootstrap task family hardcode ✅ FIXED
- `taskdefs/backend-bootstrap.json.tpl:2` ghi cứng `"family": "a20-backend-bootstrap"` thay vì `__BOOTSTRAP_TASK_FAMILY__`.
- Workflow không khai báo `BOOTSTRAP_TASK_FAMILY` (ngược với `MIGRATE_TASK_FAMILY` ở line 72).
- **Fix**: thêm `__BOOTSTRAP_TASK_FAMILY__` vào tpl + `BOOTSTRAP_TASK_FAMILY: ${{ vars.BOOTSTRAP_TASK_FAMILY }}` vào env workflow.

### B4. Bootstrap step ghi log group sai ✅ FIXED
- `deploy-ecs-prod.yml:210` truyền `LOG_GROUP="/ecs/${MIGRATE_TASK_FAMILY}"` cho bootstrap (copy-paste lỗi).
- Bootstrap khác family với migrate. Observability module hiện có 3 log group: `/ecs/a20-backend`, `/ecs/a20-frontend`, `/ecs/a20-backend-migrate`. **Bootstrap chưa có log group riêng**.
- **Fix 2 phần**:
  1. Workflow: đổi thành `LOG_GROUP="/ecs/${BOOTSTRAP_TASK_FAMILY}"`.
  2. `deploy-ecs/terraform/modules/observability/main.tf`: thêm log group thứ 4 `/ecs/a20-backend-bootstrap` (retention 7 ngày, khớp các log group hiện tại).

---

## 5. Nên fix (không block)

### N1. S3 bucket hardcode
- `taskdefs/backend-service.json.tpl` ghi `"value": "a20-course-assets-prod"`.
- Không reusable cho staging.
- **Fix**: `__AWS_S3_BUCKET__`, render qua env workflow.

### N2. `CLOUDFRONT_DOMAIN` placeholder verify
- Workflow truyền từ `vars.CLOUDFRONT_DOMAIN`. Verify giá trị có set trong GitHub repo settings trước run lần đầu.

### N3. CI chạy trên self-hosted `phoenix-runner`
- `ci.yml:31` `runs-on: [self-hosted, phoenix-runner]`. Runner offline → deploy block.
- **Quyết định**: chuyển sang `ubuntu-latest` cho gate critical, hoặc setup runner backup.

### N4. Pre-flight CloudWatch log group
- Hiện tại Terraform đã tạo đủ 3 log group → low risk. Nhưng nếu reset stack hoặc clone staging dễ vỡ.
- **Fix nhẹ**: thêm `aws logs create-log-group --log-group-name "$LOG_GROUP" 2>/dev/null || true` trước register task-def.

### N5. `run-ecs-task.sh` không lấy log khi task fail
- Migrate fail → workflow chỉ thấy exit code, log Alembic không hiện trong UI.
- SESSION_JOURNAL có 19 issue nhiều cái cần CloudWatch log để root cause (Issue 14 chat 504, Issue 7 migration A3 % escape).
- **Fix**: sau `aws ecs wait tasks-stopped`, thêm `aws logs tail "$LOG_GROUP" --since 10m` in vào step output khi exit code ≠ 0.

### N6. Xóa `.github/workflows/terraform.yml` cũ
- Path filter `deploy/terraform/**` không match — dead code.
- Sẽ bị thay bằng `cicd/workflows/terraform-ecs-prod.yml` khi promote.
- **Fix**: xóa khi copy workflow mới sang `.github/workflows/`.

---

## 6. Out-of-scope (không thuộc release loop)

1. Phase 25 cutover domain: HTTPS listener + ACM + Route 53 + frontend rebuild với production `NEXT_PUBLIC_API_URL`.
2. pgvector DDL, asset upload S3, Secrets Manager initial seed: 1-time manual.
3. Bootstrap data flows: đã chạy thủ công, có template cover khi `run_bootstrap=true`, không auto.

---

## 7. Thứ tự thực thi

1. B1 — `smoke-ecs.sh` cloudfront branch + workflow env (≤10 dòng).
2. B2 — `ci.yml` path filter (3 dòng).
3. B3 + B4 — templatize `BOOTSTRAP_TASK_FAMILY`, sửa log group, thêm log group bootstrap trong Terraform observability (4 dòng + 1 var + 1 resource).
4. N1 — templatize `AWS_S3_BUCKET` (3 dòng).
5. N4 — pre-flight log group (5 dòng × 4 step).
6. N5 — log retrieval khi one-off task fail (10 dòng).
7. N3 — quyết định self-hosted vs ubuntu-latest.
8. N6 — xóa `.github/workflows/terraform.yml` cũ.
9. Verify GitHub vars/secrets đầy đủ + 3 vars mới (`BOOTSTRAP_TASK_FAMILY`, `AWS_S3_BUCKET`, `CLOUDFRONT_SMOKE_URL`).
10. Promote: copy `cicd/workflows/*` sang `.github/workflows/`.
11. Test dry: dispatch với 4 deploy flag = false → workflow vào job, OIDC assume, summary chạy, không thay service.
12. Test wet: dispatch full deploy → verify task-def revision mới (backend ≥6, frontend ≥2), service stable, smoke pass, log stream xuất hiện.

---

## 8. File cần chỉnh

| File | Fix |
|---|---|
| `cicd/scripts/smoke-ecs.sh` | B1 |
| `cicd/scripts/run-ecs-task.sh` | N5 |
| `cicd/taskdefs/backend-bootstrap.json.tpl` | B3 |
| `cicd/taskdefs/backend-service.json.tpl` | N1 |
| `cicd/workflows/deploy-ecs-prod.yml` | B1, B3, B4, N1, N4 |
| `.github/workflows/ci.yml` | B2 |
| `.github/workflows/terraform.yml` | N6 (delete) |
| `deploy-ecs/terraform/modules/observability/main.tf` | B4 (thêm log group bootstrap) |
| `cicd/ECS_CICD_PLAN.md` | thêm 3 vars mới |
| `cicd/REVIEW_CHECKLIST.md` | tick fix mới |

---

## 9. Verification

```bash
# Syntax
bash -n cicd/scripts/*.sh
python -c "import yaml; yaml.safe_load(open('cicd/workflows/deploy-ecs-prod.yml'))"

# Render dry-run
IMAGE_URI=test BACKEND_SECRET_ARN=arn:test TASK_EXECUTION_ROLE_ARN=arn:test \
BACKEND_TASK_ROLE_ARN=arn:test BOOTSTRAP_TASK_FAMILY=a20-backend-bootstrap \
LOG_GROUP=/ecs/test AWS_REGION=ap-southeast-1 \
bash cicd/scripts/render-taskdef.sh cicd/taskdefs/backend-bootstrap.json.tpl /tmp/bs.json
jq . /tmp/bs.json   # Không còn placeholder __...__
```

Sau khi promote và run wet, verify trong AWS Console:
- ECR: image mới với tag `<sha>`.
- ECS: task-def revision mới (backend ≥6, frontend ≥2).
- Service event: "service has reached a steady state".
- ALB target group: ≥1 healthy target.
- CloudWatch: stream mới trong `/ecs/a20-backend` + `/ecs/a20-backend-migrate` (+ `/ecs/a20-backend-bootstrap` nếu chạy bootstrap).
- Smoke endpoint `/health`, `/api/course-sections`, `/api/health`, `/` → 200.
