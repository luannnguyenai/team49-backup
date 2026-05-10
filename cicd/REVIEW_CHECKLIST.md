# ECS CI/CD Review Checklist

Use this before promoting files from `cicd/workflows/` into `.github/workflows/`.

## Security

- [ ] Workflows use `id-token: write` and OIDC role assumption.
- [ ] No `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` is required.
- [ ] `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, and provider API keys appear only in task definition `secrets[]`.
- [ ] Task execution role and task role are distinct.
- [ ] `iam:PassRole` is scoped before production activation.

## Release Safety

- [ ] Images are tagged by commit SHA, never `latest`.
- [ ] ECR tag immutability remains enabled.
- [ ] Backend and frontend image digests are written to `GITHUB_STEP_SUMMARY`.
- [ ] Task definition ARNs are written to `GITHUB_STEP_SUMMARY`.
- [ ] Rollback can point ECS service to a previous task definition revision.

## ECS Gates

- [ ] `aws ecs wait services-stable` is not the only deployment gate.
- [ ] Target group health is checked after each service update.
- [ ] Backend smoke includes `/health`.
- [ ] DB-backed smoke includes `/api/course-sections`.
- [ ] Frontend smoke includes `/api/health` and `/`.
- [ ] Migration task must stop with exit code `0`.

## Known Failure Modes

- [ ] `.dockerignore` excludes `.dvc/`, `.git/`, `node_modules/`, and `frontend/`.
- [ ] Frontend Docker command forces `HOSTNAME=0.0.0.0`.
- [ ] `alembic/env.py` still escapes `%` in `DATABASE_URL`.
- [ ] Migrations run as one-off ECS tasks only.
- [ ] CloudWatch log groups exist before ECS tasks start.
- [ ] Private subnet tasks have NAT or required VPC endpoints.
- [ ] Frontend is rebuilt when `NEXT_PUBLIC_API_URL` changes.

## Promotion

- [ ] Claude review approves `cicd/ECS_CICD_PLAN.md`.
- [ ] GitHub production environment variables and secrets are created.
- [ ] Workflow drafts are copied into `.github/workflows/`.
- [ ] CI path filters include `deploy-ecs/**` and `cicd/**`.
