# Makefile for ARC PDF Tool Docker Management
.PHONY: help build up down logs shell test clean

# Default target
help: ## Show this help message
	@echo "ARC PDF Tool - Docker Management Commands"
	@echo "========================================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Docker build commands
build: ## Build all Docker images
	@echo "🏗️  Building Docker images..."
	docker-compose build --parallel

build-no-cache: ## Build all Docker images without cache
	@echo "🏗️  Building Docker images (no cache)..."
	docker-compose build --no-cache --parallel

build-api: ## Build only API image
	@echo "🏗️  Building API image..."
	docker-compose build api

build-worker: ## Build only worker image
	@echo "🏗️  Building worker image..."
	docker-compose build worker

# Docker run commands
up: ## Start all services
	@echo "🚀 Starting ARC PDF Tool services..."
	docker-compose up -d
	@echo "✅ Services started! Check status with 'make status'"

up-build: ## Build and start all services
	@echo "🚀 Building and starting ARC PDF Tool services..."
	docker-compose up -d --build

up-dev: ## Start development environment with hot reloading
	@echo "🔧 Starting development environment..."
	docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
	@echo "✅ Development environment started!"

up-baserow: ## Start with local Baserow instance
	@echo "🚀 Starting services with Baserow..."
	docker-compose --profile baserow up -d

# Docker stop commands
down: ## Stop all services
	@echo "🛑 Stopping services..."
	docker-compose down

down-volumes: ## Stop services and remove volumes
	@echo "🗑️  Stopping services and removing volumes..."
	docker-compose down -v

down-all: ## Stop services, remove volumes and images
	@echo "🧹 Complete cleanup..."
	docker-compose down -v --rmi all

# Monitoring commands
logs: ## Show logs from all services
	docker-compose logs -f

logs-api: ## Show API logs
	docker-compose logs -f api

logs-worker: ## Show worker logs
	docker-compose logs -f worker

logs-db: ## Show database logs
	docker-compose logs -f db

status: ## Show service status
	@echo "📊 Service Status:"
	@docker-compose ps

health: ## Check service health
	@echo "🏥 Health Check:"
	@docker-compose exec api curl -f http://localhost:5000/api/health || echo "❌ API unhealthy"
	@docker-compose exec db pg_isready -U arc_user -d arc_pdf_tool || echo "❌ Database unhealthy"
	@docker-compose exec redis redis-cli ping || echo "❌ Redis unhealthy"

# Development commands
shell: ## Open shell in API container
	docker-compose exec api bash

shell-worker: ## Open shell in worker container
	docker-compose exec worker bash

shell-db: ## Open PostgreSQL shell
	docker-compose exec db psql -U arc_user -d arc_pdf_tool

# Testing commands
test: ## Run tests in container
	@echo "🧪 Running tests..."
	docker-compose exec api uv run python -m pytest tests/ -v

test-integration: ## Run integration tests
	@echo "🧪 Running integration tests..."
	docker-compose exec api uv run python -m pytest tests/test_integration.py -v

test-baserow: ## Run Baserow integration tests
	@echo "🧪 Running Baserow tests..."
	docker-compose exec api uv run python -m pytest tests/test_baserow_integration_simple.py -v

# Database commands
db-migrate: ## Run database migrations
	@echo "🔄 Running database migrations..."
	docker-compose exec api uv run alembic upgrade head

db-reset: ## Reset database (development only)
	@echo "⚠️  Resetting database..."
	docker-compose exec api uv run alembic downgrade base
	docker-compose exec api uv run alembic upgrade head

db-backup: ## Backup database
	@echo "💾 Creating database backup..."
	docker-compose exec db pg_dump -U arc_user arc_pdf_tool > backup_$$(date +%Y%m%d_%H%M%S).sql

# Utility commands
clean: ## Clean up Docker resources
	@echo "🧹 Cleaning up Docker resources..."
	docker system prune -f
	docker volume prune -f

clean-all: ## Clean up all Docker resources including images
	@echo "🧹 Complete Docker cleanup..."
	docker system prune -af
	docker volume prune -f

restart: ## Restart all services
	@echo "🔄 Restarting services..."
	$(MAKE) down
	$(MAKE) up

restart-api: ## Restart only API service
	@echo "🔄 Restarting API service..."
	docker-compose restart api

restart-worker: ## Restart only worker service
	@echo "🔄 Restarting worker service..."
	docker-compose restart worker

# Development workflow
dev-setup: ## Setup development environment
	@echo "🔧 Setting up development environment..."
	$(MAKE) down-volumes
	$(MAKE) build
	$(MAKE) up-dev
	sleep 30
	$(MAKE) db-migrate
	@echo "✅ Development environment ready!"

prod-setup: ## Setup production environment
	@echo "🚀 Setting up production environment..."
	$(MAKE) build
	$(MAKE) up
	sleep 30
	$(MAKE) db-migrate
	@echo "✅ Production environment ready!"

# Monitoring
monitor: ## Open monitoring dashboards
	@echo "📊 Opening monitoring dashboards..."
	@echo "🌐 Flask API: http://localhost:5000"
	@echo "🌸 Flower: http://localhost:5555"
	@echo "🗄️  pgAdmin: http://localhost:5050"
	@echo "📦 MinIO: http://localhost:9001"

# Quick commands for common workflows
quick-start: build up db-migrate ## Quick start (build, up, migrate)
	@echo "🚀 Quick start completed!"

quick-dev: down-volumes build up-dev db-migrate ## Quick development start
	@echo "🔧 Development environment ready!"

# Validation
validate: ## Validate Docker configuration
	@echo "✅ Validating Docker configuration..."
	docker-compose config
	@echo "✅ Configuration valid!"