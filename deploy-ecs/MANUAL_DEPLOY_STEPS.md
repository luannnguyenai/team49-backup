# Manual Deploy Steps — ECS

Operator runbook for first-time setup or guided rollout. Each step has the
exact command and the trap it prevents. Cross-reference
[`HOW_TO_FIX.md`](HOW_TO_FIX.md) before starting.

Variables used below:

```sh
export AWS_REGION=ap-southeast-1
export AWS_ACCOUNT_ID=<account-id>
export CLUSTER=a20-prod-cluster
export BACKEND_SVC=a20-backend
export FRONTEND_SVC=a20-frontend
export BACKEND_REPO=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/a20-backend
export FRONTEND_REPO=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/a20-frontend
export SHA=$(git rev-parse --short HEAD)
```

## 1. Provision foundation

1. Create Terraform state bucket (one-time, `bootstrap-state` stack)
2. Configure `backend.hcl` and `terraform.tfvars` locally (never commit)
3. `terraform init -backend-config=backend.hcl`
4. `terraform plan -out=plan.tfplan`
5. Review plan. Confirm: NAT Gateway present, RDS `deletion_protection = true`, two distinct IAM roles for tasks
6. `terraform apply plan.tfplan`

**Trap (B1):** if NAT Gateway is missing or private route table has no
`0.0.0.0/0 -> nat` entry, every Fargate task will fail to pull from ECR.

## 2. Prepare shared services

1. Confirm RDS endpoint reachable from a temporary admin path
2. Enable `pgvector`:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Confirm ElastiCache primary endpoint
4. Upload assets:
   ```sh
   aws s3 sync ./data/courses s3://a20-course-assets-prod/courses
   ```
5. Validate CloudFront delivery for one known asset, including a `Range:` header probe

## 3. Prepare application deploy

1. ECR repos exist (created by Terraform `ecr` module)
2. OIDC IAM roles exist (`a20-gha-deploy`, `a20-gha-terraform`)
3. GitHub environment variables/secrets configured per `ENVIRONMENT_MATRIX.md`
4. Login to ECR locally (only if doing manual push):
   ```sh
   aws ecr get-login-password --region $AWS_REGION | \
     docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
   ```
5. Build backend (verify `.dockerignore` first — trap A1):
   ```sh
   docker build -t $BACKEND_REPO:$SHA .
   docker push $BACKEND_REPO:$SHA
   ```
6. Build frontend with production build args (trap B8):
   ```sh
   docker build -f frontend/Dockerfile \
     --build-arg NEXT_PUBLIC_API_URL=https://api.<domain> \
     --build-arg API_INTERNAL_URL=https://api.<domain> \
     -t $FRONTEND_REPO:$SHA frontend
   docker push $FRONTEND_REPO:$SHA
   ```
   For pre-domain smoke testing, substitute the ALB DNS for `<domain>` and
   plan to **rebuild** at Phase 25.

## 4. Deploy backend first

1. Render task definition JSON from template substituting image SHA, secret ARNs, log group, port 8000
2. Register revision:
   ```sh
   aws ecs register-task-definition --cli-input-json file://backend-taskdef.json
   ```
3. Update service:
   ```sh
   aws ecs update-service --cluster $CLUSTER --service $BACKEND_SVC \
     --task-definition a20-backend --force-new-deployment
   ```
4. Wait stable (this alone is **not** proof of success — trap B6):
   ```sh
   aws ecs wait services-stable --cluster $CLUSTER --services $BACKEND_SVC
   ```
5. Verify target group:
   ```sh
   aws elbv2 describe-target-health --target-group-arn <backend-tg-arn>
   ```
   At least one target must be `healthy`.
6. HTTP smoke through ALB:
   ```sh
   curl -i http://<alb-dns>/health     # via /api/* fallback rule, expect 200
   ```

## 5. Run migrations as one-off task (trap A4)

Do **not** put alembic into the service start command.

1. Render `backend-migrate.json` (same image, same secrets, same network as service, plus `command=["alembic","upgrade","head"]`)
2. Register:
   ```sh
   aws ecs register-task-definition --cli-input-json file://backend-migrate.json
   ```
3. Run:
   ```sh
   aws ecs run-task \
     --cluster $CLUSTER \
     --launch-type FARGATE \
     --task-definition a20-backend-migrate \
     --network-configuration "awsvpcConfiguration={subnets=[<priv-a>,<priv-b>],securityGroups=[<backend-sg>],assignPublicIp=DISABLED}"
   ```
4. Tail logs:
   ```sh
   aws logs tail /ecs/a20-backend-migrate --follow
   ```
   Expect a clean `alembic upgrade head` run. If you see `invalid interpolation
   syntax`, the `%` escape (trap A3) is missing in `alembic/env.py`.
5. Wait task `STOPPED`, exit code `0`.
6. Verify schema by querying a DB-backed route through ALB:
   ```sh
   curl -i http://<alb-dns>/api/course-sections   # expect 200, possibly []
   ```
   A successful 200 here is the proof App Runner taught us to require (trap A5).

## 6. Run bootstrap/import

1. Either rerun a similar one-off task with `command=["python","-m","scripts.bootstrap"]` or use admin path
2. Verify catalog row counts
3. Verify `GET /api/course-sections` returns non-empty array

## 7. Deploy frontend second

1. Render frontend task definition (port 3000, `HOSTNAME=0.0.0.0` in `environment` as belt-and-suspenders even though Dockerfile CMD already enforces it — trap A2)
2. Register revision and update service
3. `aws ecs wait services-stable` then check target group health
4. Smoke `GET http://<alb-dns>/api/health` -> `200`
5. Smoke `GET http://<alb-dns>/` -> `200`

## 8. Cut over domains

1. Issue ACM certs:
   - ALB cert in `ap-southeast-1` for `app.<domain>`, `api.<domain>`
   - CloudFront cert in `us-east-1` for `cdn.<domain>` (and any aliases)
2. Validate certs via DNS in Route 53
3. Attach certs to ALB HTTPS listener and CloudFront distribution
4. Add Route 53 alias records: `app -> ALB`, `api -> ALB`, `cdn -> CloudFront`
5. **Rebuild frontend image** with `NEXT_PUBLIC_API_URL=https://api.<domain>` (trap B8) and redeploy
6. Final smoke pack:
   - `curl -i https://api.<domain>/health` -> `200`
   - `curl -i https://app.<domain>/api/health` -> `200`
   - `curl -i https://api.<domain>/api/course-sections` -> `200`
   - `curl -I https://cdn.<domain>/<known-asset>` -> `200`

## 9. Stabilize

1. Watch ECS service events, ALB request metrics, app logs for 30 min
2. Confirm alarms armed and budgets active
3. Record in deploy log:
   - Task definition revisions deployed
   - Image digests pushed
   - Approximate cold-start time observed (calibration for grace period)

## 10. Rollback procedure

Service rollback (preferred when previous revision still works):

```sh
aws ecs update-service --cluster $CLUSTER --service $BACKEND_SVC \
  --task-definition arn:aws:ecs:$AWS_REGION:$AWS_ACCOUNT_ID:task-definition/a20-backend:<previous-rev>
aws ecs wait services-stable --cluster $CLUSTER --services $BACKEND_SVC
```

Image rollback (when revision still references old image but image was overwritten — should not happen because tag immutability is on):

```sh
docker pull $BACKEND_REPO:<previous-sha>
docker tag $BACKEND_REPO:<previous-sha> $BACKEND_REPO:$SHA
docker push $BACKEND_REPO:$SHA
```

DB rollback caveat: `alembic downgrade` is risky on production data. Prefer
restoring the latest automated snapshot.

## 11. Teardown procedure (trap A6)

Terraform `destroy` will fail mid-way unless these run first:

```sh
# 1. Disable RDS deletion protection
aws rds modify-db-instance \
  --region $AWS_REGION \
  --db-instance-identifier a20-postgres-prod \
  --no-deletion-protection \
  --apply-immediately

# 2. Take a final manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier a20-postgres-prod \
  --db-snapshot-identifier a20-postgres-prod-final-$(date +%Y%m%d)

# 3. Disable CloudFront distribution and wait Deployed (or `terraform destroy` will hang)
aws cloudfront update-distribution ... # set Enabled=false
aws cloudfront wait distribution-deployed --id <dist-id>

# 4. Empty S3 versions (versioned bucket cannot be deleted otherwise)
aws s3api list-object-versions --bucket a20-course-assets-prod \
  --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' \
  > to-delete.json
aws s3api delete-objects --bucket a20-course-assets-prod --delete file://to-delete.json

# 5. Now destroy
terraform destroy -auto-approve
```
