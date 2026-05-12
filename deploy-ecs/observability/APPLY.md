# Observability stack — deploy steps

This stack adds Prometheus, Loki, Grafana, postgres_exporter, redis_exporter to ECS Fargate. Grafana is exposed via the shared ALB at `/grafana/*`.

The Terraform module is gated behind `enable_observability_stack=true` so you can apply in 3 ordered phases.

## Prerequisites

- Terraform CLI 1.6+ initialised against the prod backend (`deploy-ecs/terraform/live/prod`).
- AWS CLI logged in with permission to create ECR repos, ECS services, EFS, Cloud Map, ALB rules.
- Docker Desktop running (for building observability images).
- AWS account & region: `116533674568` / `ap-southeast-1`.

## Phase 1 — create ECR repos (~30 s)

```powershell
cd deploy-ecs/terraform/live/prod
terraform apply -refresh=false
# Confirm: 6 resources to add (3 repos + 3 lifecycle policies).
```

After apply, capture the URLs:

```powershell
terraform output observability_repository_urls
# {
#   "a20-prometheus" = "116533674568.dkr.ecr.ap-southeast-1.amazonaws.com/a20-prometheus"
#   "a20-loki"       = "..."
#   "a20-grafana"    = "..."
# }
```

## Phase 2 — build & push the 3 observability images (~5 min)

```powershell
$REGION = "ap-southeast-1"
$ACCOUNT = "116533674568"
$REGISTRY = "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REGISTRY

docker build -t "$REGISTRY/a20-prometheus:v2.55.1" deploy-ecs/observability/prometheus
docker push      "$REGISTRY/a20-prometheus:v2.55.1"

docker build -t "$REGISTRY/a20-loki:3.2.1"        deploy-ecs/observability/loki
docker push      "$REGISTRY/a20-loki:3.2.1"

docker build -t "$REGISTRY/a20-grafana:11.3.0"    deploy-ecs/observability/grafana
docker push      "$REGISTRY/a20-grafana:11.3.0"
```

## Phase 3 — apply the observability stack (~3 min)

Ensure the observability secret contains `GRAFANA_ADMIN_PASSWORD` along with the Postgres / Redis fields used by exporters:

```powershell
aws secretsmanager get-secret-value `
  --secret-id arn:aws:secretsmanager:ap-southeast-1:116533674568:secret:a20/prod/observability-Ea5JOh `
  --query SecretString --output text
```

Apply with the stack enabled:

```powershell
terraform apply -refresh=false `
  -var="enable_observability_stack=true" `
  -var="image_prometheus=$REGISTRY/a20-prometheus:v2.55.1" `
  -var="image_loki=$REGISTRY/a20-loki:3.2.1" `
  -var="image_grafana=$REGISTRY/a20-grafana:11.3.0"
```

Outputs:

```powershell
terraform output grafana_url
# "http://a20-prod-alb-1105228802.ap-southeast-1.elb.amazonaws.com/grafana"
```

## Phase 4 — wire frontend embed (~5 min, requires CI deploy)

1. In **GitHub → Settings → Environments → production → Variables**, set:
   - `NEXT_PUBLIC_GRAFANA_HOST` = output of `terraform output grafana_url`
   - `NEXT_PUBLIC_LANGFUSE_HOST` = `https://cloud.langfuse.com`
2. Trigger a new deploy (push or workflow_dispatch). The frontend Docker build will bake the URLs into the bundle.
3. After deploy, visit `/admin/traffic`, `/admin/system`, `/admin/langfuse` — iframes should load.

## Phase 5 — verify

```powershell
aws ecs list-services --cluster a20-prod-cluster --region ap-southeast-1
# Expect: a20-backend, a20-frontend, a20-prod-prometheus, a20-prod-loki, a20-prod-grafana,
#         a20-prod-postgres-exporter, a20-prod-redis-exporter

curl http://<alb-dns>/grafana/api/health
# {"database":"ok","version":"11.3.0"}
```

Grafana iframes in the admin dashboard use anonymous Viewer access. For full Grafana administration, log in at `<alb-dns>/grafana/` with `admin` plus the password stored in `GRAFANA_ADMIN_PASSWORD` inside the observability secret. Datasources Prometheus, Loki, and Postgres should be auto-provisioned. The 3 dashboards (api-traffic, system-health, user-activity) should appear under the "A20 Admin" folder.

## Rollback

```powershell
terraform apply -refresh=false -var="enable_observability_stack=false"
# Tears down: 5 ECS services, EFS, access points, Cloud Map, log groups, ALB rule, SGs.
# ECR repos are NOT destroyed (lifecycle policy keeps last 10 images). Run `terraform destroy -target=module.ecr.aws_ecr_repository.observability` if you want them gone too.
```

## Open items (separate work)

- **Logs**: backend logs still go to CloudWatch. To send them to Loki, add a FireLens (Fluent Bit) sidecar to `cicd/taskdefs/backend-bootstrap.json.tpl` writing to `loki.obs.a20-prod.internal:3100`. See Part 2.5 of the parent plan.
- **Grafana auth**: anonymous Viewer is enabled. For real prod, disable anonymous and add OAuth (Google or GitHub) via `GF_AUTH_GOOGLE_*` envs.
- **TLS**: ALB is HTTP-only. Add ACM cert + HTTPS listener to encrypt Grafana traffic before exposing to internet.
- **Alerting**: no Alertmanager configured. Add Grafana Unified Alerting + email/PagerDuty channel as next phase.
