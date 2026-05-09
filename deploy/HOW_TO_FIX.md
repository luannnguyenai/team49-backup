# AWS Deploy How-To-Fix

Date: 2026-05-09

This document records the concrete failure modes, logs, root causes, and fixes
found during the App Runner + Terraform deployment session on `feat-terraform-aws`.

It exists to prevent repeating the same mistakes.

## Scope Of Failures

The deployment hit failures in five layers:

1. backend Docker build context
2. frontend App Runner health checks
3. backend App Runner migration startup
4. Alembic production URL handling
5. Terraform teardown blocked by RDS deletion protection

## Permanent Fixes Applied In Code

### 1. Backend Docker build context

Problem:

- backend Docker build context included `.dvc/tmp/lock`
- Docker build could fail or stall on local DVC artifacts

Fix:

- `.dvc/` added to [../.dockerignore](../.dockerignore)

### 2. Frontend App Runner host binding

Problem:

- Next.js standalone `server.js` reads `process.env.HOSTNAME`
- App Runner runtime can set `HOSTNAME` to an internal hostname
- frontend process did not reliably bind to `0.0.0.0`
- App Runner health checks failed even though local smoke tests passed

Fix:

- [../frontend/Dockerfile](../frontend/Dockerfile) now starts with:

```sh
HOSTNAME=0.0.0.0 node server.js
```

This forces the standalone server to bind all interfaces at process launch.

### 3. Alembic percent-encoded DATABASE_URL

Problem:

- production `DATABASE_URL` contained percent-encoded password content
- Alembic config wiring passed the raw URL into `configparser`
- `configparser` treated `%` as interpolation syntax

Fix:

- [../alembic/env.py](../alembic/env.py) now escapes `%` before setting
  `sqlalchemy.url`

### 4. Migration bootstrap wrapper

Problem:

- App Runner `StartCommand` experiments failed due to quoting and working-dir assumptions

Fix:

- [../scripts/apprunner_migrate_start.sh](../scripts/apprunner_migrate_start.sh)
  added as a stable migration wrapper

Note:

- this wrapper was useful for one-off production migration bootstrap
- do not leave App Runner permanently configured to rerun Alembic on every restart

### 5. Terraform teardown and RDS deletion protection

Problem:

- `terraform destroy` did not finish because the production RDS instance had
  `deletion_protection = true`
- this created a misleading partial teardown where most infrastructure was gone
  but the database and some dependent resources remained

Fix:

- before a full destroy, explicitly disable deletion protection
- then rerun `terraform destroy`

Operational sequence used in this session:

```sh
aws rds modify-db-instance \
  --region ap-southeast-1 \
  --db-instance-identifier a20-postgres-prod \
  --no-deletion-protection \
  --apply-immediately

terraform destroy -auto-approve
```

## Failure Timeline And Logs

## A. Frontend App Runner health check failures

Initial deploy failed on `/api/health`:

```text
[AppRunner] Performing health check on protocol `HTTP` [Path: '/api/health'], [Port: '3000'].
[AppRunner] Health check failed on protocol `HTTP`[Path: '/api/health'], [Port: '3000']. Check your configured port number.
[AppRunner] Deployment with ID : e1994c264adf4e54954be3036fa89bcb failed. Failure reason : Health check failed.
```

Changing health check path to `/` still failed:

```text
[AppRunner] Performing health check on protocol `HTTP` [Path: '/'], [Port: '3000'].
[AppRunner] Health check failed on protocol `HTTP`[Path: '/'], [Port: '3000']. Check your configured port number.
[AppRunner] Deployment with ID : 2ab07dc8d0bf4c79ae11d19f1264dd2f failed. Failure reason : Health check failed.
```

Even `TCP` health check failed on the original image:

```text
[AppRunner] Performing health check on protocol `TCP` [Port: '3000'].
[AppRunner] Health check failed on protocol `TCP` [Port: '3000']. Check your configured port number.
[AppRunner] Deployment with ID : 89cd7074e400449cac5362f660d6e86d failed. Failure reason : Health check failed.
```

Key local and remote evidence:

- local smoke test returned `200` for `GET /`, `HEAD /`, `GET /api/health`, `HEAD /api/health`
- App Runner application log only showed successful Next startup
- generated standalone server used:

```js
const hostname = process.env.HOSTNAME || '0.0.0.0'
```

After forcing `HOSTNAME=0.0.0.0`, frontend bound correctly:

```text
  ▲ Next.js 14.2.3
  - Local:        http://localhost:3000
  - Network:      http://0.0.0.0:3000
  ✓ Starting...
  ✓ Ready in 94ms
```

After that, App Runner health checks passed and the service reached `RUNNING`.

## B. Backend App Runner migration start-command failures

Several startup command forms failed.

Quoted shell form failed:

```text
run: 1: Syntax error: Unterminated quoted string
```

Argument-chaining form failed because App Runner did not hand the command to a shell:

```text
alembic: error: unrecognized arguments: && exec uv run python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

Relative wrapper path failed because App Runner was not starting in `/app`:

```text
sh: 0: cannot open ./scripts/apprunner_migrate_start.sh: No such file
```

Corrective lesson:

- treat App Runner `StartCommand` as fragile
- avoid shell quoting tricks
- use an explicit script
- use an absolute in-container path such as `/app/scripts/...`

## C. Alembic production URL interpolation failure

Once the wrapper script actually ran, Alembic failed before opening a DB connection:

```text
ValueError: invalid interpolation syntax in 'postgresql+asyncpg://a20admin:%5DtsYe%28Mri%5Ban7%3Ezjn%3Ej%23n%2AqA%21XTc@a20-postgres-prod.cbea2u80yox7.ap-southeast-1.rds.amazonaws.com:5432/a20app' at position 30
```

Root cause:

- `config.set_main_option("sqlalchemy.url", settings.database_url)` fed a string containing `%`
- `configparser` interpreted `%` as interpolation

Fix:

- escape `%` first in `alembic/env.py`

## D. Backend schema absence before migrations

Before migrations were successfully applied, DB-backed routes and auth writes failed.

Observed backend error:

```text
asyncpg.exceptions.UndefinedTableError: relation "users" does not exist
```

This confirmed the database was reachable from App Runner, but schema had not been created yet.

## E. Local reproduction that proved the Alembic fix worked

Running the migration wrapper inside the exact rebuilt backend image with the production URL
stopped failing on interpolation and moved on to connectivity:

```text
ConnectionRefusedError: [Errno 111] Connect call failed ('10.20.11.43', 5432)
```

That was expected outside App Runner because local Docker was not inside the VPC.
This was the decisive proof that the remaining issue was network context, not Alembic parsing.

## F. Terraform destroy blocked by RDS deletion protection

The first full teardown attempt failed at the database layer:

```text
Error: deleting RDS DB Instance (a20-postgres-prod): operation error RDS: DeleteDBInstance, https response error StatusCode: 400, RequestID: 84a0b406-973e-49d5-9da0-44eb133e131b, api error InvalidParameterCombination: Cannot delete protected DB Instance, please disable deletion protection and try again.
```

After explicitly disabling deletion protection, the rerun completed and removed
the remaining VPC/RDS resources.

## Final Verified State Reached In Session

Verified before teardown request:

- frontend App Runner:
  - `GET /api/health` -> `200`
- backend App Runner:
  - `GET /health` -> `200`
- DB-backed backend route:
  - `GET /api/course-sections` -> `200 []`

Meaning:

- frontend service was healthy
- backend service was healthy
- schema existed
- data bootstrap had not yet been run

## Guardrails For Next Attempt

Use this order on the next real deployment:

1. build backend image with `.dvc/` ignored
2. build frontend image with forced host binding in Dockerfile
3. deploy backend and frontend App Runner services
4. verify:
   - backend `/health`
   - frontend `/api/health`
5. snapshot RDS
6. run migrations from a one-off migration image or explicit admin path
   - do not leave runtime service permanently configured to rerun Alembic
7. verify a DB-backed route such as `/api/course-sections`
8. run bootstrap/import
9. verify non-empty catalog and asset parity
10. if tearing down, disable RDS deletion protection before running destroy

## Anti-Patterns To Avoid

- do not assume local Docker success implies App Runner success
- do not trust App Runner `StartCommand` with complex shell chains
- do not feed raw percent-encoded URLs into Alembic configparser
- do not use `/health` alone as proof that schema exists
- do not finish deploy before checking a DB-backed route
