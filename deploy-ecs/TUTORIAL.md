# Tutorial — Deploy A20 lên AWS ECS từng bước

Tutorial này hướng dẫn deploy ứng dụng A20 (FastAPI backend + Next.js frontend
+ PostgreSQL + Redis + S3/CloudFront) lên AWS ECS Fargate từ đầu đến hết.

Đối tượng: lần đầu deploy ECS, đã từng deploy App Runner.

Mỗi bước có:

- **What**: bạn đang làm gì
- **Why**: vì sao cần
- **Commands**: lệnh chạy
- **Verify**: cách kiểm tra bước đó OK
- **Trap**: lỗi đã từng gặp, cách tránh (xem `HOW_TO_FIX.md`)

> Nếu bước nào fail, **dừng lại fix trước khi đi tiếp**. Đừng chồng lỗi lên lỗi.

---

## Pre-requisites (làm 1 lần)

### P1. Cài tool local

```sh
aws --version          # >= 2.15
terraform --version    # >= 1.6
docker --version       # >= 24
gh --version           # GitHub CLI, optional
```

### P2. Cấu hình AWS CLI

```sh
aws configure
# Access key của IAM user có quyền admin (chỉ dùng để bootstrap)
# Region: ap-southeast-1
```

Verify:

```sh
aws sts get-caller-identity
```

Phải in ra `Account` và `Arn`. Ghi lại `AWS_ACCOUNT_ID`.

### P3. Set biến môi trường

```sh
export AWS_REGION=ap-southeast-1
export AWS_ACCOUNT_ID=<account-id-vừa-lấy-được>
export CLUSTER=a20-prod-cluster
export BACKEND_SVC=a20-backend
export FRONTEND_SVC=a20-frontend
export BACKEND_REPO=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/a20-backend
export FRONTEND_REPO=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/a20-frontend
```

PowerShell:

```powershell
$env:AWS_REGION = "ap-southeast-1"
$env:AWS_ACCOUNT_ID = "<account-id>"
# ...
```

---

## Step 1 — Verify code đã ECS-ready (Phase 1, 2)

### What
Confirm code base đã có 4 fix carry-forward từ App Runner trước khi build image.

### Why
Build image lỗi ⇒ phát hiện muộn, tốn nhiều giờ trên ECS rồi mới biết là lỗi
code. Verify ngay.

### Commands

Check `.dockerignore`:

```sh
grep -E "^\.dvc/" .dockerignore   # phải có
grep -E "^\.git" .dockerignore
grep -E "^node_modules" .dockerignore
grep -E "^frontend" .dockerignore
```

Check frontend Dockerfile force `HOSTNAME=0.0.0.0`:

```sh
grep "HOSTNAME=0.0.0.0 node server.js" frontend/Dockerfile
```

Check Alembic escape `%`:

```sh
grep 'replace("%", "%%")' alembic/env.py
```

Local smoke backend:

```sh
docker build -t a20-backend:local .
docker run --rm -p 8000:8000 -e DATABASE_URL=... a20-backend:local &
sleep 5
curl -i http://localhost:8000/health   # 200 OK
```

Local smoke frontend (test xem có bind 0.0.0.0 không):

```sh
docker build -f frontend/Dockerfile -t a20-frontend:local frontend
docker run --rm -p 3000:3000 a20-frontend:local &
sleep 10
curl -i http://localhost:3000/api/health   # 200 OK
```

### Verify
Tất cả grep ra dòng đúng, cả hai `curl` đều `200`.

### Trap
- A1: Nếu `docker build` chậm bất thường ⇒ check context size (`docker build`
  in dòng `transferring context: ... MB` đầu output). > 200MB là dấu hiệu
  `.dockerignore` chưa loại trừ `.dvc/`.
- A2: Nếu local frontend `200` nhưng sau này trên ECS health check fail ⇒
  Dockerfile CMD bị mất `HOSTNAME=0.0.0.0`. Đừng skip step verify này.

---

## Step 2 — Bootstrap Terraform state (Phase trước Phase 0)

### What
Tạo S3 bucket lưu Terraform state, cũng là nơi giữ lock.

### Why
Nếu sau này có nhiều người chạy `terraform apply`, state phải share. Local
state là dead-end.

### Commands

```sh
cd deploy-ecs/terraform/bootstrap-state
terraform init
terraform plan -out=plan.tfplan
terraform apply plan.tfplan
```

Output sẽ in tên bucket. Ghi lại.

### Verify

```sh
aws s3 ls | grep a20-terraform-state
```

### Trap
- Bucket name phải globally unique. Nếu trùng ⇒ đổi tên trong tfvars.

---

## Step 3 — Apply Terraform foundation (Phase 4–17 trừ DDL/data)

### What
Apply toàn bộ infra: VPC, subnets, NAT, ALB, ECS cluster, RDS, ElastiCache,
S3, CloudFront, IAM OIDC, ECR, log groups, security groups.

### Why
Một `terraform apply` lớn an toàn hơn 10 lần `apply` nhỏ vì dependency được
quản. Chỉ tách ra khi cần (data, secrets thật).

### Commands

```sh
cd deploy-ecs/terraform/live/prod
cp backend.hcl.example backend.hcl       # điền state bucket
cp terraform.tfvars.example terraform.tfvars   # điền non-secret values
terraform init -backend-config=backend.hcl
terraform plan -out=plan.tfplan
```

Trước khi apply, **đọc plan**. Confirm các điểm sau:

- [ ] `aws_nat_gateway` xuất hiện (trap B1)
- [ ] `aws_db_instance` có `deletion_protection = true` (trap A6)
- [ ] 2 IAM role riêng cho task: `*-task-execution-role` và `*-task-role` (trap B5)
- [ ] CloudWatch log groups `/ecs/a20-backend`, `/ecs/a20-frontend`, `/ecs/a20-backend-migrate` xuất hiện (trap B7)
- [ ] Security group rules theo chain `alb-sg → frontend-sg/backend-sg → db-sg/redis-sg`
- [ ] RDS storage encrypted, automated backup ≥ 7 days

Nếu OK:

```sh
terraform apply plan.tfplan
```

Apply mất 15–20 phút (RDS chiếm phần lớn).

### Verify

```sh
terraform output
# Ghi lại: alb_dns_name, rds_endpoint, redis_endpoint, cloudfront_domain,
# backend_repo_url, frontend_repo_url, backend_log_group_name, ...

aws ecs describe-clusters --clusters $CLUSTER
aws elbv2 describe-load-balancers --names a20-public-alb
aws rds describe-db-instances --db-instance-identifier a20-postgres-prod
```

### Trap
- **B1**: Nếu sau khi apply tasks không khởi động được với
  `ResourceInitializationError: unable to pull secrets or registry auth`,
  kiểm tra route table của private subnet:
  ```sh
  aws ec2 describe-route-tables --filters "Name=vpc-id,Values=<vpc-id>"
  ```
  Phải có route `0.0.0.0/0 → nat-...`.

---

## Step 4 — Tạo secrets thật trong Secrets Manager (Phase 17)

### What
Tạo secret `a20/prod/backend` chứa `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`.

### Why
Secret thật KHÔNG nằm trong tfvars hay git. Terraform có thể tạo placeholder,
nhưng giá trị thật điền tay.

### Commands

Lấy mật khẩu RDS (Terraform sinh ngẫu nhiên, đẩy vào Secrets Manager dạng JSON
master credentials, ARN khác với secret app):

```sh
aws secretsmanager get-secret-value \
  --secret-id a20/prod/rds-master \
  --query SecretString --output text
```

Build `DATABASE_URL`:

```text
postgresql+asyncpg://a20admin:<PASSWORD-URL-ENCODED>@<rds-endpoint>:5432/a20app?ssl=require
```

> Production RDS requires encrypted connections. For SQLAlchemy `asyncpg`,
> use `?ssl=require` in `DATABASE_URL`.
> Nếu password chứa ký tự đặc biệt (`@`, `/`, `%`, …), phải URL-encode.
> Nếu sau encode chứa `%`, **vẫn OK** vì `alembic/env.py` đã escape (trap A3).

Tạo secret app:

```sh
aws secretsmanager put-secret-value \
  --secret-id a20/prod/backend \
  --secret-string '{
    "DATABASE_URL": "postgresql+asyncpg://...?ssl=require",
    "REDIS_URL": "redis://<redis-endpoint>:6379/0",
    "SECRET_KEY": "<random-64-char>"
  }'
```

### Verify

```sh
aws secretsmanager describe-secret --secret-id a20/prod/backend
# Confirm ARN, không in giá trị
```

### Trap
- **B4**: Đừng copy `DATABASE_URL` vào `terraform.tfvars` để "đỡ phải tạo
  secret tay". Một khi vào tfvars là vào state file là vào git (nếu lỡ commit).

---

## Step 5 — Build và push images lên ECR (Phase 5–7)

### What
Build backend + frontend image, push lên ECR với tag là commit SHA.

### Why
Tag SHA cho phép rollback. Tag `latest` thì không. Tag immutability đã bật ở
Phase 5 sẽ chặn `latest` overwrite.

### Commands

```sh
export SHA=$(git rev-parse --short HEAD)

aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Backend
docker build -t $BACKEND_REPO:$SHA .
docker push $BACKEND_REPO:$SHA

# Frontend (lần đầu, chưa có domain → dùng ALB DNS làm placeholder)
ALB_DNS=$(aws elbv2 describe-load-balancers --names a20-public-alb \
  --query 'LoadBalancers[0].DNSName' --output text)

docker build -f frontend/Dockerfile \
  --build-arg NEXT_PUBLIC_API_URL=http://$ALB_DNS \
  --build-arg API_INTERNAL_URL=http://$ALB_DNS \
  -t $FRONTEND_REPO:$SHA frontend
docker push $FRONTEND_REPO:$SHA
```

### Verify

```sh
aws ecr describe-images --repository-name a20-backend \
  --image-ids imageTag=$SHA \
  --query 'imageDetails[0].imageDigest'
aws ecr describe-images --repository-name a20-frontend \
  --image-ids imageTag=$SHA
```

Cả hai phải in ra digest `sha256:...`.

### Trap
- **B8**: Image frontend này là "ALB-version", **sẽ phải build lại** ở Step 11
  khi có domain. Đây là chi phí hiển nhiên của Next.js bake env build-time.

---

## Step 6 — Đăng ký + chạy task migrate (Phase 20) ⚠️ Bước nguy hiểm nhất

### What
Chạy `alembic upgrade head` như **một ECS task riêng**, không phải embed vào
service start command.

### Why
Trap A4: App Runner StartCommand chain shell quá fragile. Trên ECS, nguyên tắc
là không chèn migration vào service start vì:

1. Service restart = migration chạy lại = race condition
2. Migration crash = service không boot được = downtime
3. Rollback service revision = migration đã chạy rồi không undo được

Tách hẳn ra one-off task vừa an toàn vừa explicit.

### Commands

Render task definition migrate (template ở `deploy-ecs/taskdefs/backend-migrate.json.tpl`):

```sh
sed -e "s|__IMAGE__|$BACKEND_REPO:$SHA|g" \
    -e "s|__SECRET_ARN__|arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:a20/prod/backend|g" \
    -e "s|__EXEC_ROLE__|arn:aws:iam::$AWS_ACCOUNT_ID:role/a20-task-execution-role|g" \
    -e "s|__TASK_ROLE__|arn:aws:iam::$AWS_ACCOUNT_ID:role/a20-backend-task-role|g" \
    deploy-ecs/taskdefs/backend-migrate.json.tpl > /tmp/migrate.json

aws ecs register-task-definition --cli-input-json file:///tmp/migrate.json
```

Chạy task:

```sh
PRIV_SUBNETS=$(terraform -chdir=deploy-ecs/terraform/live/prod output -raw private_subnet_ids_csv)
BACKEND_SG=$(terraform -chdir=deploy-ecs/terraform/live/prod output -raw backend_sg_id)

TASK_ARN=$(aws ecs run-task \
  --cluster $CLUSTER \
  --launch-type FARGATE \
  --task-definition a20-backend-migrate \
  --network-configuration "awsvpcConfiguration={subnets=[$PRIV_SUBNETS],securityGroups=[$BACKEND_SG],assignPublicIp=DISABLED}" \
  --query 'tasks[0].taskArn' --output text)

echo "Task: $TASK_ARN"
```

Theo dõi:

```sh
aws logs tail /ecs/a20-backend-migrate --follow
```

Đợi task `STOPPED`:

```sh
aws ecs wait tasks-stopped --cluster $CLUSTER --tasks $TASK_ARN
aws ecs describe-tasks --cluster $CLUSTER --tasks $TASK_ARN \
  --query 'tasks[0].{exitCode:containers[0].exitCode,stop:stoppedReason}'
```

`exitCode` phải là `0`.

### Verify

Log phải kết thúc bằng dòng dạng:

```text
INFO  [alembic.runtime.migration] Running upgrade ... -> <head>
```

Verify schema bằng cách query DB từ một admin path tạm hoặc bằng task `psql`
debug:

```sql
\dt
-- phải thấy users, course_sections, ...
```

### Trap
- **A3**: Nếu log có `ValueError: invalid interpolation syntax` ⇒ password
  chứa `%` nhưng `alembic/env.py` chưa escape. Quay lại Step 1.
- **B1**: Nếu task không khởi động (`STOPPED` ngay với
  `ResourceInitializationError`) ⇒ NAT thiếu hoặc execution role không có
  quyền `secretsmanager:GetSecretValue`.
- **A4**: TUYỆT ĐỐI không bypass step này bằng cách thêm
  `alembic upgrade head &&` vào service container command.

---

## Step 7 — Deploy backend service (Phase 19)

### What
Tạo / update ECS service backend trỏ đến image SHA + secret ARN.

### Why
Backend phải healthy trước frontend, vì frontend gọi backend.

### Commands

```sh
sed -e "s|__IMAGE__|$BACKEND_REPO:$SHA|g" \
    -e "s|__SECRET_ARN__|arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:a20/prod/backend|g" \
    -e "s|__EXEC_ROLE__|arn:aws:iam::$AWS_ACCOUNT_ID:role/a20-task-execution-role|g" \
    -e "s|__TASK_ROLE__|arn:aws:iam::$AWS_ACCOUNT_ID:role/a20-backend-task-role|g" \
    deploy-ecs/taskdefs/backend.json.tpl > /tmp/backend.json

aws ecs register-task-definition --cli-input-json file:///tmp/backend.json

aws ecs update-service \
  --cluster $CLUSTER \
  --service $BACKEND_SVC \
  --task-definition a20-backend \
  --force-new-deployment

aws ecs wait services-stable --cluster $CLUSTER --services $BACKEND_SVC
```

### Verify (3 lớp, không bỏ lớp nào — trap B6)

Lớp 1: ECS service stable

```sh
aws ecs describe-services --cluster $CLUSTER --services $BACKEND_SVC \
  --query 'services[0].{running:runningCount,desired:desiredCount,deployments:length(deployments)}'
```

`running == desired`, `deployments == 1`.

Lớp 2: Target group healthy

```sh
TG_ARN=$(aws elbv2 describe-target-groups --names a20-backend-tg \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

aws elbv2 describe-target-health --target-group-arn $TG_ARN \
  --query 'TargetHealthDescriptions[].TargetHealth.State'
```

Tất cả phải là `healthy`.

Lớp 3: HTTP smoke

```sh
curl -i http://$ALB_DNS/health
```

`200 OK`.

Lớp 4 (sau bootstrap): DB-backed route

```sh
curl -i http://$ALB_DNS/api/course-sections
```

`200`. Nếu là `[]` là OK (chưa import data). Nếu là `500` với
`relation "users" does not exist` ⇒ migrate chưa chạy thành công, quay lại
Step 6 (trap A5).

### Trap
- Nếu Lớp 1 OK nhưng Lớp 2 báo `unhealthy` ⇒ container start được nhưng ALB
  không kết nối được. Check:
  - Target group port = 8000 (trap B3)
  - SG `backend-sg` cho phép ingress 8000 từ `alb-sg`
  - Container thực sự listen `0.0.0.0:8000`, không phải `127.0.0.1:8000`

---

## Step 8 — Bootstrap data (Phase 21)

### What
Import course catalog vào DB.

### Why
DB đã có schema (sau migrate), chưa có row nào.

### Commands

Chạy như một one-off task khác, command tương tự:

```sh
# Đăng ký task family a20-backend-bootstrap (giống migrate, đổi command)
sed ... > /tmp/bootstrap.json   # command = ["python","-m","scripts.bootstrap"]
aws ecs register-task-definition --cli-input-json file:///tmp/bootstrap.json
aws ecs run-task ... --task-definition a20-backend-bootstrap
```

### Verify

```sh
curl -s http://$ALB_DNS/api/course-sections | jq 'length'
# > 0
```

---

## Step 9 — Deploy frontend service (Phase 22)

### What
Tạo / update frontend service.

### Commands

```sh
sed -e "s|__IMAGE__|$FRONTEND_REPO:$SHA|g" \
    -e "s|__EXEC_ROLE__|arn:aws:iam::$AWS_ACCOUNT_ID:role/a20-task-execution-role|g" \
    -e "s|__TASK_ROLE__|arn:aws:iam::$AWS_ACCOUNT_ID:role/a20-frontend-task-role|g" \
    deploy-ecs/taskdefs/frontend.json.tpl > /tmp/frontend.json

aws ecs register-task-definition --cli-input-json file:///tmp/frontend.json
aws ecs update-service --cluster $CLUSTER --service $FRONTEND_SVC \
  --task-definition a20-frontend --force-new-deployment

aws ecs wait services-stable --cluster $CLUSTER --services $FRONTEND_SVC
```

### Verify

```sh
TG_ARN=$(aws elbv2 describe-target-groups --names a20-frontend-tg --query 'TargetGroups[0].TargetGroupArn' --output text)
aws elbv2 describe-target-health --target-group-arn $TG_ARN

curl -i http://$ALB_DNS/api/health   # 200
curl -i http://$ALB_DNS/             # 200, HTML
```

### Trap
- **A2**: Nếu target group `unhealthy` mà container log lại in
  `Ready in 94ms` thành công ⇒ Next.js bind 127.0.0.1 thay vì 0.0.0.0. Verify
  task definition env có `HOSTNAME=0.0.0.0` và Dockerfile CMD `HOSTNAME=0.0.0.0
  node server.js`.
- **B2**: Frontend cold start ~90s. Nếu service grace period < 90s, ECS sẽ
  kill task trước khi nó kịp ready. Verify
  `health_check_grace_period_seconds >= 120`.

---

## Step 10 — Smoke test full pack (Phase 24)

### What
4 check bắt buộc trước khi gọi "deploy thành công".

### Commands

```sh
echo "1. Backend health"
curl -s -o /dev/null -w "%{http_code}\n" http://$ALB_DNS/health   # 200

echo "2. Frontend health"
curl -s -o /dev/null -w "%{http_code}\n" http://$ALB_DNS/api/health   # 200

echo "3. DB-backed route"
curl -s -o /dev/null -w "%{http_code}\n" http://$ALB_DNS/api/course-sections   # 200

echo "4. CloudFront asset"
CF=$(terraform -chdir=deploy-ecs/terraform/live/prod output -raw cloudfront_domain)
curl -I https://$CF/<known-asset-key>   # 200, có Content-Length
```

Tất cả `200` ⇒ pass.

### Trap
- **A5**: Nếu chỉ check 1 và 2 mà bỏ 3, bạn đang lặp lại đúng cái fail mode
  của App Runner đã từng tốn nửa ngày debug.

---

## Step 11 — Mua domain + cutover (Phase 25)

### What
Gắn `app.<domain>`, `api.<domain>`, `cdn.<domain>`.

### Commands

```sh
# 1. Issue ACM certs (ap-southeast-1 cho ALB, us-east-1 cho CloudFront)
aws acm request-certificate --region ap-southeast-1 \
  --domain-name "*.<domain>" --validation-method DNS

aws acm request-certificate --region us-east-1 \
  --domain-name "*.<domain>" --validation-method DNS

# 2. Add validation CNAME records vào Route 53, đợi cert ISSUED

# 3. Update ALB HTTPS listener cert ARN qua Terraform
# 4. Update CloudFront alias + cert qua Terraform
# 5. Add Route 53 alias records
terraform plan -out=plan.tfplan
terraform apply plan.tfplan

# 6. REBUILD frontend với production URL (trap B8)
docker build -f frontend/Dockerfile \
  --build-arg NEXT_PUBLIC_API_URL=https://api.<domain> \
  --build-arg API_INTERNAL_URL=https://api.<domain> \
  -t $FRONTEND_REPO:$SHA-prod frontend
docker push $FRONTEND_REPO:$SHA-prod

# 7. Update frontend service trỏ image mới
sed "s|__IMAGE__|$FRONTEND_REPO:$SHA-prod|g" ... > /tmp/frontend.json
aws ecs register-task-definition --cli-input-json file:///tmp/frontend.json
aws ecs update-service --cluster $CLUSTER --service $FRONTEND_SVC \
  --task-definition a20-frontend --force-new-deployment
```

### Verify (rerun smoke pack trên domain thật)

```sh
curl -i https://api.<domain>/health
curl -i https://app.<domain>/api/health
curl -i https://api.<domain>/api/course-sections
curl -I https://cdn.<domain>/<asset-key>
```

---

## Step 12 — Setup CI/CD GitHub Actions (Phase 3)

### What
Tự động hoá Step 5–9 mỗi khi push lên `main`.

### What to commit

`.github/workflows/deploy-prod.yml` với jobs:

1. CI gate (lint, test)
2. Configure AWS via OIDC (assume `a20-gha-deploy`)
3. Login ECR
4. Build/push backend + frontend với SHA tag
5. Render task definition templates với image mới
6. Register revision + update service backend
7. Wait stable + smoke (3 lớp)
8. Repeat cho frontend
9. Record digests vào `GITHUB_STEP_SUMMARY`

> Migration tự động trong CI? **Không** ở v1. Migrations chạy thủ công bằng
> `aws ecs run-task` (Step 6) để giữ control rõ ràng. Khi pipeline đã ổn,
> mới cân nhắc gate "run migrate task before service update" trong workflow.

---

## Step 13 — Rollback khi cần

### Service rollback (most common)

```sh
# Liệt kê revision
aws ecs list-task-definitions --family-prefix a20-backend --status ACTIVE

# Trỏ service về revision trước
aws ecs update-service --cluster $CLUSTER --service $BACKEND_SVC \
  --task-definition arn:aws:ecs:$AWS_REGION:$AWS_ACCOUNT_ID:task-definition/a20-backend:<prev-rev>

aws ecs wait services-stable --cluster $CLUSTER --services $BACKEND_SVC
curl -i http://$ALB_DNS/health
```

### DB rollback

`alembic downgrade` rủi ro. Khôi phục từ snapshot tự động RDS:

```sh
aws rds describe-db-snapshots --db-instance-identifier a20-postgres-prod \
  --snapshot-type automated
aws rds restore-db-instance-from-db-snapshot ...
```

---

## Step 14 — Teardown an toàn (chỉ khi muốn xoá hết)

> Trap A6: `terraform destroy` sẽ fail giữa chừng nếu không làm 4 bước dưới
> trước. Đã từng tốn 30 phút.

```sh
# 1. Disable RDS deletion protection
aws rds modify-db-instance \
  --region $AWS_REGION \
  --db-instance-identifier a20-postgres-prod \
  --no-deletion-protection \
  --apply-immediately

# 2. Final snapshot
aws rds create-db-snapshot \
  --db-instance-identifier a20-postgres-prod \
  --db-snapshot-identifier a20-postgres-prod-final-$(date +%Y%m%d)

# 3. Disable CloudFront, đợi Deployed
DIST_ID=$(terraform -chdir=deploy-ecs/terraform/live/prod output -raw cloudfront_distribution_id)
ETAG=$(aws cloudfront get-distribution-config --id $DIST_ID --query 'ETag' --output text)
aws cloudfront get-distribution-config --id $DIST_ID --query 'DistributionConfig' > /tmp/cf.json
# sửa Enabled=false trong /tmp/cf.json
aws cloudfront update-distribution --id $DIST_ID --if-match $ETAG --distribution-config file:///tmp/cf.json
aws cloudfront wait distribution-deployed --id $DIST_ID

# 4. Empty S3 versions
aws s3api list-object-versions --bucket a20-course-assets-prod \
  --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' > /tmp/del.json
aws s3api delete-objects --bucket a20-course-assets-prod --delete file:///tmp/del.json

# 5. Destroy
cd deploy-ecs/terraform/live/prod
terraform destroy -auto-approve
```

---

## Cheat sheet — gặp lỗi thì xem section nào

| Triệu chứng | Nguyên nhân | Section |
|---|---|---|
| `ResourceInitializationError: unable to pull secrets/registry` | Thiếu NAT hoặc VPC endpoint | Step 3 trap, HOW_TO_FIX B1 |
| Target group `unhealthy` mà container log OK | Frontend bind 127.0.0.1 | Step 9 trap, HOW_TO_FIX A2 |
| `ValueError: invalid interpolation syntax` | Password chứa `%`, env.py chưa escape | Step 6 trap, HOW_TO_FIX A3 |
| `relation "users" does not exist` | Migrate chưa chạy hoặc chạy lỗi | Step 6, HOW_TO_FIX A5 |
| `services-stable` xong mà 5xx | Task crash-loop về revision cũ | Step 7 Lớp 2/3, HOW_TO_FIX B6 |
| Frontend gọi API sai URL | Image build với placeholder, chưa rebuild | Step 11, HOW_TO_FIX B8 |
| `terraform destroy` treo ở RDS | `deletion_protection = true` | Step 14, HOW_TO_FIX A6 |
| Image pull lỗi do `latest` | Tag immutability + dùng SHA | Step 5 |

---

## Khi nào hoàn thành

Đánh dấu deploy thành công khi:

- [ ] `PRODUCTION_CHECKLIST.md` toàn bộ checked
- [ ] 4 lớp smoke test trên domain thật pass
- [ ] Budget alert + ECS/ALB/RDS alarm armed
- [ ] Image digest và task definition revision đã ghi log
- [ ] Rollback procedure đã thử nghiệm 1 lần (rollback rồi roll forward) trên staging hoặc trong cửa sổ bảo trì

Khi 5 điểm trên đều ✅ ⇒ production ready.
