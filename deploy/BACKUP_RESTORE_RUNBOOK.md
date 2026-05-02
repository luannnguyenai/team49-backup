# Backup And Restore Runbook

## Scope

This runbook covers PostgreSQL backup and restore for production deployments of this repo.

## Backup Policy

Minimum recommendation:
- nightly full logical backup with `pg_dump`
- retain daily backups for `7` days
- retain weekly backups for `4` weeks
- retain monthly backups for `3` months
- take an on-demand pre-release backup before every production migration

If the provider supports snapshots and PITR:
- enable daily snapshots
- enable point-in-time recovery
- still keep a periodic logical backup for portability

## Logical Backup Commands

Environment assumptions:
- `DATABASE_URL` points to production
- `PGPASSWORD` is injected securely at runtime

Example:

```bash
export PGHOST=db-host
export PGPORT=5432
export PGDATABASE=ai_learning
export PGUSER=app_user
export PGPASSWORD='replace-me'

STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p /srv/ai-learning/backups

pg_dump \
  --format=custom \
  --no-owner \
  --no-privileges \
  --file "/srv/ai-learning/backups/ai_learning-${STAMP}.dump" \
  "$PGDATABASE"
```

Optional integrity check:

```bash
pg_restore --list "/srv/ai-learning/backups/ai_learning-${STAMP}.dump" >/dev/null
```

## Restore Drill

Never restore first into live production.

Use a scratch database:

```bash
createdb ai_learning_restore_test
pg_restore \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  --dbname ai_learning_restore_test \
  "/srv/ai-learning/backups/ai_learning-YYYYMMDD-HHMMSS.dump"
```

Then verify:
- expected tables exist
- Alembic head is compatible
- app can connect
- canonical product flows load correctly

## Pre-Release Backup Drill

Before production migration:

```bash
STAMP="$(date +%Y%m%d-%H%M%S)"
pg_dump \
  --format=custom \
  --no-owner \
  --no-privileges \
  --file "/srv/ai-learning/backups/predeploy-${STAMP}.dump" \
  "$PGDATABASE"
```

Record:
- git commit SHA
- backup filename
- release operator
- migration window time

## Restore Decision Policy

Prefer forward-fix when:
- schema migration succeeded
- app bug is isolated to business logic
- no irreversible data corruption happened

Restore when:
- data corruption is confirmed
- the release introduced unrecoverable schema or data damage
- forward-fix would take longer than acceptable downtime

## Retention Cleanup Example

Example cleanup for files older than 30 days:

```bash
find /srv/ai-learning/backups -type f -name '*.dump' -mtime +30 -delete
```

Use object storage replication if backups stay on the same VM. Local-only backups are not enough.
