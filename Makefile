# =============================================================================
# Makefile — AI Adaptive Learning Platform
# =============================================================================
# Targets:
#   make dev          Start development stack (hot-reload)
#   make dev-build    Rebuild images then start dev stack
#   make down         Stop all containers
#   make seed         Seed curriculum data into the database
#   make migrate      Run Alembic migrations (upgrade head)
#   make test         Run backend + frontend tests
#   make test-be      Run backend pytest only
#   make test-fe      Run frontend type-check + lint only
#   make deploy       Production build + start (compose override)
#   make logs         Tail logs for all services
#   make logs-be      Tail backend logs
#   make shell-be     Open bash in running backend container
#   make db-shell     Open psql in running db container
#   make redis-cli    Open redis-cli in running redis container
#   make clean        Remove containers, volumes, images
#   make help         Print this message
# =============================================================================

.PHONY: help dev dev-build down seed migrate \
        test test-be test-fe \
        deploy logs logs-be \
        shell-be db-shell redis-cli clean

# Compose files
DC      = docker compose
DC_PROD = docker compose -f docker-compose.yml -f docker-compose.prod.yml

# Container names
BE_CTR  = al_backend
FE_CTR  = al_frontend
DB_CTR  = al_db
RD_CTR  = al_redis

# Colours
BOLD  = \033[1m
RESET = \033[0m
GREEN = \033[0;32m
CYAN  = \033[0;36m

# ---------------------------------------------------------------------------
help: ## Print available make targets
	@echo ""
	@echo "$(BOLD)AI Adaptive Learning Platform$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*##"}; {printf "  $(CYAN)%-15s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------

dev: ## Start dev stack (hot-reload, source mounted)
	@echo "$(GREEN)▶ Starting development stack...$(RESET)"
	$(DC) up -d
	@echo ""
	@echo "  Frontend → http://localhost:$${FRONTEND_PORT:-3000}"
	@echo "  Backend  → http://localhost:$${BACKEND_PORT:-8000}"
	@echo "  API docs → http://localhost:$${BACKEND_PORT:-8000}/docs"
	@echo ""

dev-build: ## Rebuild images then start dev stack
	@echo "$(GREEN)▶ Rebuilding and starting development stack...$(RESET)"
	$(DC) up -d --build

down: ## Stop all containers (keep volumes)
	$(DC) down

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

migrate: ## Run Alembic migrations (upgrade head)
	@echo "$(GREEN)▶ Running database migrations...$(RESET)"
	docker exec $(BE_CTR) alembic upgrade head

seed: ## Seed curriculum data (modules, topics, questions)
	@echo "$(GREEN)▶ Seeding curriculum data...$(RESET)"
	docker exec $(BE_CTR) python scripts/seed.py

seed-clear: ## Clear existing data then re-seed (DESTRUCTIVE)
	@echo "$(GREEN)▶ Clearing and re-seeding...$(RESET)"
	docker exec $(BE_CTR) python scripts/seed.py --clear

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

test: test-be test-fe ## Run all tests (backend + frontend)

test-be: ## Run backend pytest suite
	@echo "$(GREEN)▶ Running backend tests...$(RESET)"
	docker exec $(BE_CTR) python -m pytest tests/ -v --tb=short

test-fe: ## Run frontend TypeScript type-check + ESLint
	@echo "$(GREEN)▶ Running frontend lint + type-check...$(RESET)"
	docker exec $(FE_CTR) sh -c "npm run lint && npx tsc --noEmit"

test-local-be: ## Run backend tests locally (needs .venv)
	@echo "$(GREEN)▶ Running backend tests locally...$(RESET)"
	python -m pytest tests/ -v --tb=short

# ---------------------------------------------------------------------------
# Production
# ---------------------------------------------------------------------------

deploy: ## Production build + start (compose override)
	@echo "$(GREEN)▶ Starting production stack...$(RESET)"
	$(DC_PROD) up -d --build

deploy-down: ## Stop production stack
	$(DC_PROD) down

# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

logs: ## Tail logs for all services
	$(DC) logs -f

logs-be: ## Tail backend logs
	$(DC) logs -f backend

logs-fe: ## Tail frontend logs
	$(DC) logs -f frontend

logs-db: ## Tail database logs
	$(DC) logs -f db

# ---------------------------------------------------------------------------
# Shells / CLI
# ---------------------------------------------------------------------------

shell-be: ## Open bash shell inside backend container
	docker exec -it $(BE_CTR) bash

db-shell: ## Open psql inside the database container
	docker exec -it $(DB_CTR) psql -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-ai_learning}

redis-cli: ## Open redis-cli inside the Redis container
	docker exec -it $(RD_CTR) redis-cli -a $${REDIS_PASSWORD:-redis123secure}

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

ps: ## List running containers and their status
	$(DC) ps

restart-be: ## Restart the backend service only
	$(DC) restart backend

restart-fe: ## Restart the frontend service only
	$(DC) restart frontend

clean: ## Remove all containers, networks, volumes, and images
	@echo "$(GREEN)▶ Removing all containers, volumes, and images...$(RESET)"
	$(DC) down -v --remove-orphans
	docker image prune -f --filter "label=com.docker.compose.project=ai-adaptive-learning"

generate-secret: ## Generate a secure SECRET_KEY value
	@python -c "import secrets; print(secrets.token_hex(32))"
