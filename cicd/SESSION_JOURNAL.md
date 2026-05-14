# Session Journal — CI/CD Setup

**Date:** 2026-05-10 → 2026-05-11
**Operator:** edward1503 / vanhuydz210@gmail.com
**Branch:** main
**Goal:** Promote `cicd/` review package thành GitHub Actions pipeline active, deploy code mới hôm nay (`1346ab0 fix freshstart ui`, `90d5edf learning_unit_service`) lên production ECS.

---

## 1. Mục tiêu phiên làm việc

ECS production đã deploy thủ công xong từ session 2026-05-09→10 (xem `deploy-ecs/SESSION_JOURNAL.md`). `cicd/` folder đã có draft GitHub Actions workflow nhưng chưa promote. Phiên này:
1. Review `cicd/` đối chiếu spec `deploy-ecs/AWS_CICD_GUIDE.md`.
2. Fix các vấn đề chặn promotion.
3. Setup vars/secrets, promote workflow, kích hoạt auto-deploy mỗi push lên main.

---

## 2. Tóm tắt thành quả

| Hạng mục | Trạng thái |
|---|---|
| Review document | ✅ `cicd/REVIEW_FINDINGS.md`, `cicd/REVIEW_FOR_EXTERNAL.md` |
| 4 BLOCKER fix | ✅ B1, B2, B3, B4 |
| Workflow promote `.github/workflows/` | ✅ deploy-ecs-prod.yml, terraform-ecs-prod.yml |
| Xóa workflow legacy | ✅ `.github/workflows/terraform.yml` |
| Self-hosted runner switch ubuntu-latest | ✅ `ci.yml` |
| Terraform apply log group bootstrap | ✅ `+1 resource added` |
| GitHub Variables (production env) | ✅ 16/16 |
| GitHub Secrets (production env) | ✅ 12/12 |
| Push main trigger workflow | ✅ commit `2763240` |
| First workflow run success | ❌ **startup_failure** |

---

## 3. Timeline + Issues

### 3.1 Review `cicd/` ↔ `deploy-ecs/` (Bài 1)

Spawn 3 Explore agent song song, đối chiếu code thật với spec. Phát hiện:
- **4 BLOCKER**: smoke cloudfront env mismatch, ci path filter sai, bootstrap family hardcode, bootstrap log group sai.
- **6 nên fix**: S3 bucket hardcode, log group pre-flight, log retrieval khi fail, self-hosted runner risk, dead `terraform.yml`, run-task không có timeout.

Lần đầu agent báo nhầm "App Runner legacy" và "deploy.yml frozen Vercel/Railway". User push back đúng — repo này **chưa từng deploy App Runner thật**, chỉ có context lịch sử trong `PLATFORM_ANALYSIS.md`. File `deploy.yml` cũng đã bị xóa (commit `9e0e9b3 Delete deploy.yml`).

**Issue 1 — Tin agent quá nhanh, không verify file thật**:
- Fix: re-Glob `.github/workflows/`, đọc lại `PLATFORM_ANALYSIS.md` confirm App Runner chỉ là "Why not" section.
- Lessons learned: Glob trước khi reference workflow files.

### 3.2 Fix 4 BLOCKER (Bài 2)

Commit `ab47460 fix(cicd): resolve 4 blockers + promote ECS workflows to .github/workflows`:

| Blocker | File | Patch |
|---|---|---|
| B1 | `cicd/workflows/deploy-ecs-prod.yml` | + `CLOUDFRONT_SMOKE_URL` env var |
| B2 | `.github/workflows/ci.yml` | filter `repo_config`: `deploy/**` → `cicd/**` + `deploy-ecs/**` |
| B3 | `cicd/taskdefs/backend-bootstrap.json.tpl` | `"family": "a20-backend-bootstrap"` → `"__BOOTSTRAP_TASK_FAMILY__"` |
| B3 | `cicd/workflows/deploy-ecs-prod.yml` | + `BOOTSTRAP_TASK_FAMILY` env |
| B4 | `cicd/workflows/deploy-ecs-prod.yml` | bootstrap step `LOG_GROUP=/ecs/${MIGRATE_TASK_FAMILY}` → `${BOOTSTRAP_TASK_FAMILY}` |
| B4 | `deploy-ecs/terraform/modules/observability/main.tf` | + `aws_cloudwatch_log_group.bootstrap` |
| B4 | `deploy-ecs/terraform/modules/observability/outputs.tf` | + `bootstrap_log_group_name` output |

Verify: `bash -n cicd/scripts/*.sh` OK, `python -c "yaml.safe_load(...)"` OK, render dry-run produce JSON valid với `__BOOTSTRAP_TASK_FAMILY__` resolve đúng.

### 3.3 Promote workflow + xóa legacy (Bài 3)

```bash
cp cicd/workflows/deploy-ecs-prod.yml .github/workflows/
cp cicd/workflows/terraform-ecs-prod.yml .github/workflows/
rm .github/workflows/terraform.yml   # path filter trỏ deploy/terraform/** không tồn tại
```

End state `.github/workflows/`:
- `ci.yml` (CI gate)
- `deploy-ecs-prod.yml` (release pipeline)
- `terraform-ecs-prod.yml` (infra plan/apply)
- `kg-sync.yml` (knowledge graph sync)

### 3.4 Check GitHub permissions (Bài 4)

```bash
gh api repos/a20-ai-thuc-chien/A20-App-049 --jq '.permissions'
# {"admin":false,"maintain":true,"pull":true,"push":true,"triage":true}
```

Có Maintain role. Test set/delete:
- ✅ Set repo-level vars/secrets
- ✅ Set environment-level vars/secrets (kể cả env `production` đã tồn tại sẵn)
- ❌ Set environment protection rules (required reviewers) — cần admin
- ❌ Set branch protection on main — cần admin

**Hệ quả**: workflow chạy được, nhưng **không có approval gate** — mỗi push main auto deploy. Phải tự kỷ luật cho đến khi admin enable protection.

### 3.5 Set 16 vars + 12 secrets (Bài 5)

Đọc `terraform output -json > tf-outputs.json` để lấy giá trị thật:
- ALB DNS: `a20-prod-alb-1105228802.ap-southeast-1.elb.amazonaws.com`
- CloudFront: `d2syr4kpiu8d9n.cloudfront.net`
- 4 IAM role ARN, 2 target group ARN, security group, subnet IDs
- Backend Secret ARN: `arn:aws:secretsmanager:ap-southeast-1:116533674568:secret:a20/prod/backend-nwKKWN`

CloudFront smoke URL: chọn 1 PDF có thật `https://d2syr4kpiu8d9n.cloudfront.net/courses/CS224n/slides/cs224n-2024-lecture01-wordvecs.pdf`. Verify `curl -I` → 200 OK, 4.97 MB.

**Issue 2 — `gh variable list` pagination 30 items**:
- Set xong 16 vars, list ra chỉ thấy 10 → tưởng failed.
- Fix: dùng `gh api ".../variables?per_page=100"` thay `gh variable list`. Confirm `total_count: 16`.

**Issue 3 — `gh secret set` không có `--body-file` flag**:
- 10 secrets one-line set OK qua `--body`. 2 file secret (`TF_BACKEND_HCL_PROD`, `TFVARS_PROD`) fail với `unknown flag --body-file`.
- Fix: pipe stdin: `cat backend.hcl | gh secret set TF_BACKEND_HCL_PROD --env production`.

### 3.6 Terraform apply log group bootstrap (Bài 6)

```bash
cd deploy-ecs/terraform/live/prod
terraform plan -out plan.tfplan
# Plan: 1 to add, 0 to change, 0 to destroy.
#   + module.observability.aws_cloudwatch_log_group.bootstrap
terraform apply plan.tfplan
```

✅ `/ecs/a20-backend-bootstrap` created, retention 7d.

**Issue 4 — Git Bash mangle absolute path `/ecs/...`**:
- `aws logs describe-log-groups --log-group-name-prefix "/ecs/a20-backend-bootstrap"` báo error: path bị expand thành `C:/Program Files/Git/ecs/a20-backend-bootstrap`.
- Fix: prefix `MSYS_NO_PATHCONV=1` cho lệnh AWS có path bắt đầu bằng `/`. Hoặc dùng double slash `//ecs/...`.

### 3.7 Self-hosted runner permission check (Bài 7)

```bash
gh api repos/a20-ai-thuc-chien/A20-App-049/actions/runners
# {"message":"Not Found","status":"404"}
gh api orgs/a20-ai-thuc-chien/actions/runners
# {"message":"You must be an org admin or have the runners and runner groups fine-grained permission.","status":"403"}
```

**Issue 5 — Không kiểm được status `phoenix-runner-02`**:
- Cần admin permission để list runner. Maintain role không đủ.
- Rủi ro: nếu runner offline, CI block, deploy không bắt đầu.
- Fix: thay tạm `runs-on: [self-hosted]` → `runs-on: ubuntu-latest` cho 7 job trong `ci.yml`. Postgres + Redis service container vẫn hoạt động trên `ubuntu-latest`.
- Commit `2763240 fix(ci): switch ci.yml from self-hosted phoenix-runner-02 to ubuntu-latest`.

### 3.8 Push trigger workflow (Bài 8)

```bash
git push origin main
# 01eadc1..2763240  main -> main
```

Workflow `Deploy ECS Production` trigger ngay.

### 3.9 ❌ Startup failure (Bài 9 — chưa giải quyết)

```bash
gh run list --workflow="Deploy ECS Production" --limit 3
# completed   startup_failure   fix(ci): switch ci.yml...   25636147058   1s
# completed   startup_failure   Merge pull request #500     25635548585   0s
# completed   startup_failure   Merge branch 'rin/fine-tune'  25635173735  1s
```

3 run liên tiếp đều `startup_failure`, mỗi run < 1s, **0 jobs created**. Workflow file YAML parse OK ở local (`python yaml.safe_load`), nhưng GitHub reject ở stage validate.

**Issue 6 — Root cause startup_failure chưa xác định**:
- API responses không cho error message rõ ràng:
  - `gh run view <id> --log-failed` → "log not found"
  - `gh api .../jobs` → `{"total_count":0,"jobs":[]}`
  - `gh api .../check-suite` → 404
- Theo `display_title` và metadata: workflow trigger đúng, nhưng failed trước khi spawn job.
- **Hypothesis chưa verify**:
  1. Reusable workflow `uses: ./.github/workflows/ci.yml` không pass secrets/inputs đúng kiểu.
  2. `environment: production` chưa có deployment branch policy → block? (env tồn tại nhưng `protection_rules: []`).
  3. Workflow_dispatch inputs (5 cái) parse fail trên push event vì không default value của 1 input nào đó.
  4. GitHub schema strict reject mảng/object nào đó local YAML accept.

**Cần làm**:
- Mở UI `https://github.com/a20-ai-thuc-chien/A20-App-049/actions/runs/25636147058` đọc message annotation (API endpoint không expose).
- Hoặc thử disable trigger `push:` tạm, dispatch tay từng input để bisect lỗi.

---

## 4. Trạng thái hiện tại (cuối phiên)

### Đã ổn

- ✅ Review docs: `cicd/REVIEW_FINDINGS.md`, `cicd/REVIEW_FOR_EXTERNAL.md`
- ✅ 4 blocker fixed (commit `ab47460`)
- ✅ Workflow promoted `.github/workflows/`
- ✅ Legacy `terraform.yml` xóa
- ✅ CI runner switched ubuntu-latest (commit `2763240`)
- ✅ 16 vars set environment `production`
- ✅ 12 secrets set environment `production`
- ✅ Log group `/ecs/a20-backend-bootstrap` created
- ✅ OIDC role + Backend Secret ARN + 4 IAM role + ALB + targets sẵn sàng

### Chưa xong

| # | Item | Note |
|---|---|---|
| 1 | **Root cause `Deploy ECS Production` startup_failure** | 3 run fail, 0 jobs, không có log. Phải debug qua UI. |
| 2 | First successful deploy | Phụ thuộc fix #1 |
| 3 | Verify code hôm nay deploy production | `1346ab0 fix freshstart ui`, `90d5edf learning_unit_service` chưa lên production (vẫn image `7deedc0-units`) |
| 4 | Approval gate | Cần admin enable: Environment `production` → Required reviewers; Branch protection main → Required PR review |
| 5 | Domain cutover (Phase 25) | HTTPS listener + ACM + Route 53 + frontend rebuild với production domain |
| 6 | N1 N4 N5 N6 (non-blocking) | S3 bucket templatize, log group pre-flight, run-task log retrieval, decision self-hosted dài hạn |
| 7 | `phoenix-runner-02` decision | Tạm dùng ubuntu-latest. Quyết định dài hạn sau khi pipeline chạy ổn |

---

## 5. Issues + Fix tham chiếu nhanh

| Issue | Triệu chứng | Fix |
|---|---|---|
| 1 | Agent đầu báo nhầm App Runner legacy | Re-verify file thật bằng Glob/Read; agent's summary ≠ reality |
| 2 | `gh variable list` chỉ hiện 10/16 | Dùng `gh api .../variables?per_page=100` |
| 3 | `gh secret set --body-file` unknown flag | Pipe stdin: `cat file \| gh secret set NAME --env production` |
| 4 | Git Bash mangle path `/ecs/...` | `MSYS_NO_PATHCONV=1` prefix hoặc double slash `//ecs/...` |
| 5 | Không list được self-hosted runner status | Maintain không đủ; cần admin. Workaround: chuyển ubuntu-latest |
| 6 | Workflow startup_failure không có log | **CHƯA FIX** — debug qua UI annotation |

---

## 6. Lessons learned

1. **Verify file thật trước khi tin agent summary** (Issue 1). Agent có thể infer sai từ doc cũ.
2. **GitHub API list endpoint default 30 items, max 100** — `?per_page=100` để tránh false negative (Issue 2).
3. **`gh secret set` ≠ `gh variable set`** về flag — secret không có `--body-file`, phải stdin (Issue 3).
4. **Git Bash POSIX path conversion**: bất kỳ aws/az CLI argument bắt đầu `/` đều bị mangle thành Windows path. Luôn `MSYS_NO_PATHCONV=1` cho aws CLI trên Git Bash (Issue 4).
5. **Maintain role giới hạn** — set vars/secrets được, set protection rules + list runners không. Protection gate phải nhờ admin (Issue 5).
6. **Local YAML valid ≠ GitHub Actions valid** — `yaml.safe_load` chỉ check syntax, không check schema. Validate cuối cùng vẫn phải push test (Issue 6).
7. **`environment:` block tồn tại ≠ có protection** — env rỗng vẫn cho job chạy không cần approve.

---

## 7. Bài tiếp theo (next session)

1. **Debug startup_failure** workflow Deploy ECS Production:
   - Mở UI run detail xem annotation
   - Bisect: tạm bỏ `environment: production` block, push lại → nếu pass thì env config có vấn đề
   - Hoặc tạm bỏ `uses: ./.github/workflows/ci.yml` reusable, push lại → nếu pass thì ci.yml workflow_call có vấn đề
2. **Sau khi pipeline chạy thành công**:
   - Verify endpoint matrix sau deploy mới
   - Confirm code `1346ab0` + `90d5edf` live trên production
   - Check CloudWatch log stream xuất hiện trong `/ecs/a20-backend` revision mới
3. **Apply N1/N4/N5** (low priority, sau khi pipeline ổn)
4. **Nhờ admin** enable required reviewer + branch protection main
