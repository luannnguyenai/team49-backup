# Production Checklist

## Pre-Deploy

- [ ] Production domain and DNS are ready
- [ ] `app` and `api` subdomains point to the production host
- [ ] Linux host is provisioned and patched
- [ ] Docker and Docker Compose are installed
- [ ] Reverse proxy is installed
- [ ] TLS certificates are configured
- [ ] `SECRET_KEY` is replaced with a strong random value
- [ ] LLM provider keys are valid and funded
- [ ] `NEXT_PUBLIC_API_URL` points to the public API domain
- [ ] PostgreSQL persistence and backups are configured
- [ ] Redis password is changed from default
- [ ] Host firewall blocks public DB and Redis access
- [ ] Production `.env` is stored securely
- [ ] Staging smoke tests pass

## First Deploy

- [ ] Build and start production containers
- [ ] Run Alembic migrations
- [ ] Import canonical content
- [ ] Import product shell data
- [ ] Run parity validation
- [ ] Verify backend health endpoint
- [ ] Verify frontend health endpoint
- [ ] Verify login and registration
- [ ] Verify course catalog
- [ ] Verify learning-unit content
- [ ] Verify quiz or assessment flow
- [ ] Verify tutor endpoint with the selected model provider

## Post-Deploy

- [ ] Monitor logs for errors during the first 30 minutes
- [ ] Verify CPU, memory, and disk usage on host
- [ ] Verify database connections stay healthy
- [ ] Confirm Redis is reachable only from private network
- [ ] Confirm backups completed successfully
- [ ] Confirm one rollback path has been tested
- [ ] Record the deployed git commit SHA
- [ ] Record known issues and follow-up tasks
