# Manual Deploy Steps - AWS-First Simple Managed

Use this runbook when executing the plan by hand from an approved admin machine.
It follows `DEPLOYMENT_PLAN.md` and keeps AWS infrastructure Terraform-first.

## Runbook Definition Of Done

This runbook is complete only when every command or console action needed for
the selected launch scope has evidence recorded, temporary AWS domains pass the
smoke test, final domains pass after cutover, and rollback data is captured.

Done means:

- AWS identity, region, production branch, domain, and service names are filled
  in before infrastructure changes.
- Legacy non-AWS deploys are frozen before pushing production changes.
- Terraform bootstrap, plan review, and apply evidence is recorded.
- App Runner and Amplify native GitHub connections are authorized and their
  deployment IDs are recorded.
- S3 upload summary, RDS migration result, pgvector verification, and bootstrap
  data checks are recorded.
- Backend and frontend health endpoints return 200 on temporary and final URLs.
- CloudFront video playback and seeking work from the browser.
- Budgets, alarms, log retention, and rollback records exist before launch is
  considered complete.

## Runbook Completion Checklist

- [ ] Section 0 values are filled in.
- [ ] Sections 1 through 5 have command output or AWS console evidence recorded.
- [ ] Section 6 asset upload records object count, total size, and sample MP4
  key.
- [ ] Sections 7 through 12 verify RDS, migrations, bootstrap/import, and S3 to
  DB asset parity.
- [ ] Sections 13 and 14 pass on temporary AWS domains.
- [ ] Section 15 passes on custom domains after env/CORS/API URL updates.
- [ ] Sections 16 and 17 record operations controls and rollback data.
- [ ] Any skipped item has an owner, reason, risk, and follow-up date.

## 0. Fill Deployment Values

| Item | Value |
|---|---|
| AWS account ID | `________________` |
| AWS region | `ap-southeast-1` |
| Production branch | `main` or `________________` |
| Domain | `________________` |
| Backend App Runner service | `a20-backend` |
| Frontend Amplify app | `a20-frontend` |
| Backend temporary URL | `https://________________` |
| Frontend temporary URL | `https://________________` |
| RDS endpoint | `________________.rds.amazonaws.com` |
| ElastiCache endpoint | `________________.cache.amazonaws.com` |
| S3 bucket | `a20-course-assets-prod` |
| CloudFront domain | `________________.cloudfront.net` |
| Final frontend domain | `app.<domain>` |
| Final backend domain | `api.<domain>` |
| Final CDN domain | `cdn.<domain>` |

## 1. Verify AWS CLI Identity

```bash
aws sts get-caller-identity
aws configure get region
```

Expected region: `ap-southeast-1`.

## 2. Freeze Legacy Deploy Workflow

Before pushing to `main`, confirm `.github/workflows/deploy.yml` cannot deploy
to Vercel/Railway/Supabase.

Acceptable actions:

- Disable its `push main` trigger.
- Replace it with a manual/no-op reference workflow.
- Delete it after confirming the old deployment stack is retired.

## 3. Bootstrap Terraform State

Run once:

```bash
cd deploy/terraform/bootstrap-state
terraform init
terraform plan -out bootstrap.tfplan
terraform apply bootstrap.tfplan
```

Then initialize production:

```bash
cd ../live/prod
cp backend.hcl.example backend.hcl
cp terraform.tfvars.example terraform.tfvars
terraform init -backend-config=backend.hcl
terraform validate
terraform plan -var-file=terraform.tfvars -out prod.tfplan
```

Review every plan before apply:

```bash
terraform apply prod.tfplan
```

## 4. Create Native GitHub Connections

App Runner:

- Create/authorize the App Runner GitHub connection in AWS.
- Use the repository root `Dockerfile`.
- Do not wait for Terraform app-service ownership before the first deploy.

Amplify:

- Create/authorize the Amplify GitHub connection in AWS.
- Use app root `frontend`.
- Do not use token-based Terraform creation for the first deploy.

## 5. Apply Terraform Infrastructure In Phases

Run targeted plans only when helpful for review. Full plans are acceptable after
module wiring is stable.

Suggested order for foundational infrastructure:

```bash
cd deploy/terraform/live/prod
terraform plan -var-file=terraform.tfvars -out prod-assets.tfplan
terraform apply prod-assets.tfplan

terraform plan -var-file=terraform.tfvars -out prod-network-data.tfplan
terraform apply prod-network-data.tfplan

terraform plan -var-file=terraform.tfvars -out prod-ops.tfplan
terraform apply prod-ops.tfplan
```

Confirm every plan creates only resources for the intended phase.

## 6. Upload Course Assets

Run only after Terraform creates the S3 bucket.

```bash
aws s3 sync ./data/courses s3://a20-course-assets-prod/courses --delete
aws s3 ls s3://a20-course-assets-prod/courses --recursive --summarize
```

Record:

- Object count.
- Total uploaded size.
- Representative MP4 key.

## 7. Enable Pgvector

After RDS is available and reachable from a trusted environment:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

Expected result: `vector`.

## 8. Store Backend Secrets And Env

Configure App Runner env/secret refs:

```text
DATABASE_URL
REDIS_URL
SECRET_KEY
OPENAI_API_KEY / ANTHROPIC_API_KEY / GEMINI_API_KEY
DEBUG=false
LOG_LEVEL=INFO
FRONTEND_BASE_URL=https://<amplify-temp-url>
CORS_ORIGINS=["https://<amplify-temp-url>"]
ASSET_STORAGE_PROVIDER=s3
AWS_REGION=ap-southeast-1
AWS_S3_BUCKET=a20-course-assets-prod
AWS_S3_PREFIX=courses
CLOUDFRONT_DOMAIN=<cloudfront-domain>
```

Do not paste real secrets into committed files or Terraform variables.

## 9. Verify Backend App Runner

Confirm service settings:

- Service name: `a20-backend`.
- Source: repository root `Dockerfile`.
- Branch: `main` or production branch.
- Auto deploy: enabled.
- Port: `8000` or runtime `PORT`.
- VPC connector attached if RDS/Redis are private.
- Health path: `/health`.
- Service can be imported into Terraform later after this health check passes.

Verify:

```bash
curl --fail https://<backend-app-runner-url>/health
```

Confirm backend can reach:

- RDS.
- Redis/Valkey.
- Selected LLM/email provider if enabled.

## 10. Run Migrations

Create or confirm an RDS snapshot first. Then run:

```bash
alembic upgrade head
```

Verify migration head after completion.

## 11. Run Bootstrap/Import

Run the reviewed production bootstrap wrapper if available:

```bash
bash scripts/aws_bootstrap.sh
```

If the wrapper does not exist, record the exact existing import commands used.

Verify:

```sql
SELECT COUNT(*) FROM courses;
SELECT COUNT(*) FROM learning_units;
```

## 12. Verify S3 To DB Asset Parity

Export DB asset keys and compare with S3 object keys under `courses/`.

Failure condition:

```text
any DB asset key points to a missing S3 object
```

Verify one representative video through CloudFront and confirm browser seeking
works.

## 13. Verify Frontend Amplify

Confirm service settings:

- App name: `a20-frontend`.
- Source: GitHub repository.
- Branch: `main` or production branch.
- App root: `frontend`.
- Auto deploy: enabled.
- Install command: `npm ci --legacy-peer-deps`.
- Build command: `npm run build`.
- App can be imported into Terraform later after this health check passes.

Set Amplify env:

```text
NEXT_PUBLIC_API_URL=https://<backend-app-runner-url>
API_INTERNAL_URL=https://<backend-app-runner-url>
NEXT_TELEMETRY_DISABLED=1
NODE_ENV=production
```

Verify:

```bash
curl --fail https://<frontend-amplify-url>/api/health
```

## 14. Smoke Test Temporary AWS Domains

- [ ] Backend `/health` returns 200.
- [ ] Frontend health returns 200.
- [ ] Home page loads.
- [ ] Register and login work.
- [ ] Forgot-password works if enabled.
- [ ] Course catalog loads.
- [ ] Learning flow opens at least one ready course.
- [ ] Video URL uses CloudFront.
- [ ] Video play and seek work.
- [ ] Tutor/email calls work if enabled.
- [ ] Browser console has no `localhost` calls.
- [ ] No mixed-content HTTP warnings.

## 15. Attach Custom Domains

Use Terraform for Route 53, ACM, and service domain resources when possible.

```text
app.<domain>  -> Amplify frontend
api.<domain>  -> App Runner backend
cdn.<domain>  -> CloudFront distribution
```

CloudFront certificate must be in `us-east-1`.

Update backend:

```text
FRONTEND_BASE_URL=https://app.<domain>
CORS_ORIGINS=["https://app.<domain>"]
CLOUDFRONT_DOMAIN=cdn.<domain>
```

Update frontend and rebuild:

```text
NEXT_PUBLIC_API_URL=https://api.<domain>
API_INTERNAL_URL=https://api.<domain>
```

## 16. Configure Budgets And Alarms

- [ ] AWS Budget alerts.
- [ ] CloudFront bytes alarm.
- [ ] App Runner 5xx alarm.
- [ ] RDS CPU/storage alarms.
- [ ] NAT cost review if NAT is used.
- [ ] CloudWatch log retention.
- [ ] S3 lifecycle policy reviewed.

## 17. Record Rollback Data

Record:

- Git commit SHA.
- Amplify deployment/build ID.
- App Runner deployment ID.
- RDS snapshot ID before migration.
- CloudFront distribution ID.
- Terraform plan/apply timestamp.

Rollback:

- Frontend: redeploy previous Amplify build or revert commit.
- Backend: redeploy previous App Runner deployment or revert commit.
- DB: restore from RDS snapshot into a new instance and repoint `DATABASE_URL`.
- Assets: restore S3 object versions and invalidate CloudFront paths if needed.
