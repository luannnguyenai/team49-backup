# AWS CI/CD Guide — ECS

## Goal

Deploy production through one GitHub Actions workflow that:

1. Runs CI gate
2. Assumes AWS role via OIDC
3. Builds backend/frontend Docker images
4. Pushes images to ECR tagged by commit SHA
5. Registers new ECS task definition revisions
6. Updates ECS services
7. Waits for service stability
8. Smoke tests backend and frontend through ALB

## Required GitHub Environment Values

| Name | Type | Purpose |
|---|---|---|
| `AWS_REGION` | variable | Primary AWS region |
| `AWS_ACCOUNT_ID` | variable | Registry/account scope |
| `AWS_DEPLOY_ROLE_ARN` | secret | OIDC deploy role |
| `ECR_BACKEND_REPOSITORY` | variable | Backend ECR repository |
| `ECR_FRONTEND_REPOSITORY` | variable | Frontend ECR repository |
| `ECS_CLUSTER_NAME` | variable | ECS cluster name |
| `ECS_BACKEND_SERVICE_NAME` | variable | Backend ECS service |
| `ECS_FRONTEND_SERVICE_NAME` | variable | Frontend ECS service |
| `BACKEND_TASK_FAMILY` | variable | Backend task definition family |
| `FRONTEND_TASK_FAMILY` | variable | Frontend task definition family |
| `PRODUCTION_BACKEND_URL` | variable | Smoke test target |
| `PRODUCTION_FRONTEND_URL` | variable | Smoke test target |

## Workflow Shape

```text
push main
  -> CI gate
  -> configure AWS credentials via OIDC
  -> login ECR
  -> docker build/push backend
  -> docker build/push frontend
  -> render backend task definition JSON with new image
  -> register backend revision
  -> update backend ECS service
  -> wait ecs service stable
  -> smoke backend
  -> render frontend task definition JSON with new image
  -> register frontend revision
  -> update frontend ECS service
  -> wait ecs service stable
  -> smoke frontend
```

## Deployment Rules

- Use immutable SHA tags
- Keep `concurrency: deploy-production`
- Fail deploy on failed smoke test
- Record image digests and task definition revisions in `GITHUB_STEP_SUMMARY`
- Do not store AWS access keys in GitHub secrets

## Rollback

- Re-register previous task definition revision or
- Update service to previous task definition ARN directly

Rollback is valid only if previous image digests remain in ECR and config/secrets are still compatible.
