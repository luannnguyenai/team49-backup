# CI/CD Workflow Run Refactor Design

## Goal

Refactor GitHub Actions release orchestration to match the working organization pattern: `CI` runs independently, `Build & Push to ECR` triggers from `workflow_run`, and `Deploy ECS Production` triggers from the build workflow. Preserve the repository's richer ECS deployment behavior, including task definition rendering, migrations, bootstrap tasks, and smoke checks.

## Current Problem

The current release flow embeds `ci.yml` as a reusable workflow inside `deploy-ecs-prod.yml`. That differs from the known-good `cicd-ref` design, makes event flow harder to reason about, and couples CI execution to deployment. The deploy job also runs on `ubuntu-latest`, which does not match the organization's known-good self-hosted runner path.

## Target Design

### Workflow 1: `CI`

Keep `.github/workflows/ci.yml` as the standalone validation workflow. It remains the source of truth for code and repo-config checks and continues to run on pushes and pull requests.

### Workflow 2: `Build & Push to ECR`

Add `.github/workflows/build-push.yml` with:

- `workflow_run` trigger on successful `CI` completion for branch `main`
- optional `workflow_dispatch` for manual rebuilds
- self-hosted `phoenix-runner`
- AWS credential setup via OIDC role assumption
- backend and frontend image builds pushed to ECR with immutable SHA tags

For `workflow_run`, the workflow checks out `github.event.workflow_run.head_sha` so image contents match the exact commit that passed CI.

### Workflow 3: `Deploy ECS Production`

Refactor `.github/workflows/deploy-ecs-prod.yml` to:

- trigger from successful `Build & Push to ECR` completion on `main`
- keep `workflow_dispatch` for manual deploys and rollbacks
- run on self-hosted `phoenix-runner`
- remove build/push steps entirely
- resolve image tags from `workflow_run.head_sha` for automatic deploys, or from `image_tag` / `github.sha` for manual deploys
- preserve ECS task definition registration, service updates, migration/bootstrap tasks, and smoke checks

## Data Flow

1. A push to `main` completes `CI`.
2. `Build & Push to ECR` starts from the `CI` `workflow_run` event.
3. The build workflow pushes `backend:<head_sha>` and `frontend:<head_sha>`.
4. `Deploy ECS Production` starts from the successful build workflow.
5. The deploy workflow resolves `head_sha` as the image tag and deploys the exact images built in step 3.

## Operational Implications

- Event flow becomes observable in Actions UI and matches the working organization reference.
- Deploy no longer depends on re-running CI inline.
- Image build and deploy use the same commit SHA, reducing ambiguity.
- Manual deploy remains available for rollback and selective operations.

## Risks And Mitigations

- `workflow_run` only fires for workflows on the default branch. This is acceptable because release automation should only promote `main`.
- If production vars/secrets are environment-scoped, the new build workflow may also need `environment: production`. The implementation will include it to preserve current access assumptions.
- Manual dispatch without `image_tag` assumes an image for the selected commit already exists. This is acceptable for redeploys; operators can provide `image_tag` explicitly when needed.
