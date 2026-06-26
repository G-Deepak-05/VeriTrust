.PHONY: help dev build down logs migrate migrate-create test test-cov lint format typecheck clean seed

# ─── Variables ────────────────────────────────────────────────────────────────
COMPOSE = docker compose
API = $(COMPOSE) exec api
PYTEST_FLAGS = -v --tb=short

help: ## Show this help message
	@echo "VeriTrust — Developer Commands"
	@echo "================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Docker ───────────────────────────────────────────────────────────────────
dev: ## Start all services in development mode
	$(COMPOSE) up --build

dev-bg: ## Start all services in background
	$(COMPOSE) up --build -d

build: ## Rebuild Docker images
	$(COMPOSE) build --no-cache

down: ## Stop all services
	$(COMPOSE) down

down-v: ## Stop all services and remove volumes
	$(COMPOSE) down -v

logs: ## Follow API logs
	$(COMPOSE) logs -f api

logs-all: ## Follow all service logs
	$(COMPOSE) logs -f

ps: ## Show running services
	$(COMPOSE) ps

restart: ## Restart API service
	$(COMPOSE) restart api

# ─── Database ─────────────────────────────────────────────────────────────────
migrate: ## Run all pending Alembic migrations
	$(API) alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="add_column")
	$(API) alembic revision --autogenerate -m "$(MSG)"

migrate-down: ## Rollback last migration
	$(API) alembic downgrade -1

migrate-history: ## Show migration history
	$(API) alembic history --verbose

db-shell: ## Open psql shell
	$(COMPOSE) exec postgres psql -U veritrust -d veritrust

# ─── Testing ──────────────────────────────────────────────────────────────────
test: ## Run all tests
	$(API) pytest $(PYTEST_FLAGS) tests/

test-unit: ## Run unit tests only
	$(API) pytest $(PYTEST_FLAGS) tests/unit/

test-integration: ## Run integration tests only
	$(API) pytest $(PYTEST_FLAGS) tests/integration/

test-cov: ## Run tests with coverage report
	$(API) pytest $(PYTEST_FLAGS) --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=80 tests/

test-local: ## Run tests locally (without Docker)
	pytest $(PYTEST_FLAGS) tests/

# ─── Code Quality ─────────────────────────────────────────────────────────────
lint: ## Lint with ruff
	$(API) ruff check app/ tests/

format: ## Format with ruff
	$(API) ruff format app/ tests/

format-check: ## Check formatting without applying
	$(API) ruff format --check app/ tests/

typecheck: ## Type check with mypy
	$(API) mypy app/

check: lint format-check typecheck ## Run all quality checks

# ─── LocalStack / AWS ─────────────────────────────────────────────────────────
aws-buckets: ## List LocalStack S3 buckets
	aws --endpoint-url=http://localhost:4566 s3 ls

aws-health: ## Check LocalStack health
	curl -s http://localhost:4566/_localstack/health | python3 -m json.tool

# ─── Utilities ────────────────────────────────────────────────────────────────
shell: ## Open Python shell in API container
	$(API) python

bash: ## Open bash in API container
	$(COMPOSE) exec api bash

seed: ## Seed database with test data
	$(API) python scripts/seed.py

clean: ## Remove Python cache files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -name ".coverage" -delete

secret: ## Generate a secure SECRET_KEY
	@python3 -c "import secrets; print(secrets.token_hex(32))"
