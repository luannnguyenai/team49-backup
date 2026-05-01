# Deploy Folder

This folder contains the practical deployment plan for the current product.

Files:
- `DEPLOYMENT_PLAN.md`: recommended production architecture, rollout phases, and risks.
- `PRODUCTION_CHECKLIST.md`: pre-deploy, deploy-day, and post-deploy checks.
- `ENVIRONMENT_MATRIX.md`: required environment variables and where each one is used.
- `BACKUP_RESTORE_RUNBOOK.md`: concrete PostgreSQL backup, restore, and retention guidance.
- `Caddyfile`: reverse-proxy and TLS baseline for `app.` and `api.` domains.
- `nginx.conf`: reverse-proxy alternative with built-in request limiting.
- `.env.production.example`: production environment template.
- `deploy.sh`: basic Linux deployment script for compose-based releases.

Current recommendation:
- Start with a single Linux VM using Docker Compose production mode.
- Put Nginx or Caddy in front for TLS and reverse proxy.
- Keep PostgreSQL and Redis managed or isolated from the public internet.
- Add CI/CD only after the first manual production deployment path is stable.
