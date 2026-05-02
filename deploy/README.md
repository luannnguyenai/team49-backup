# Deploy Folder

This folder contains the practical deployment plan for the current product.

Files:
- `DEPLOYMENT_PLAN.md`: recommended production architecture, rollout phases, and risks.
- `PRODUCTION_CHECKLIST.md`: pre-deploy, deploy-day, and post-deploy checks.
- `ENVIRONMENT_MATRIX.md`: required environment variables and where each one is used.

Current recommendation:
- Start with a single Linux VM using Docker Compose production mode.
- Put Nginx or Caddy in front for TLS and reverse proxy.
- Keep PostgreSQL and Redis managed or isolated from the public internet.
- Add CI/CD only after the first manual production deployment path is stable.
