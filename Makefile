# Makefile
# --------
# Shortcuts for common development / database tasks.

.PHONY: help up down build logs ps restart db-shell migrate seed clean

help:
	@echo "Available commands:"
	@echo "  up             Start all services in Docker"
	@echo "  down           Stop all services"
	@echo "  build          Build or rebuild services"
	@echo "  logs           View logs for all services"
	@echo "  ps             List running containers"
	@echo "  restart        Restart backend service"
	@echo "  db-shell       Connect to PostgreSQL shell"
	@echo "  migrate-sql    Migrate data from SQLite to PostgreSQL"
	@echo "  migrate        Run Alembic migrations (auto-migrate)"

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

ps:
	docker compose ps

restart:
	docker compose restart backend

db-shell:
	docker exec -it al_db psql -U postgres -d ai_learning

migrate-sql:
	docker exec al_backend python scripts/migrate_sqlite.py

migrate:
	docker exec al_backend alembic upgrade head
