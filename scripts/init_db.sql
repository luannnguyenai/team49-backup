-- scripts/init_db.sql
-- Runs once on first PostgreSQL container start (via docker-entrypoint-initdb.d).
-- The real schema is managed by Alembic migrations; this only enables required extensions.

-- Enable UUID generation (needed by gen_random_uuid() used in UUIDPrimaryKeyMixin)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
