# Docker Quickstart Guide

This guide will help you get the ARC PDF Tool running quickly using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Make (optional, for convenience commands)
- 4GB+ RAM available for containers
- 10GB+ disk space for images and data

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd arc_pdf_tool
```

### 2. Environment Configuration

Copy the Docker environment file:

```bash
cp .env.docker .env
```

Edit `.env` if needed to customize configuration.

### 3. Start the Stack

**Option A: Using Make (Recommended)**
```bash
# Quick development start
make quick-dev

# Or for production
make quick-start
```

**Option B: Using Docker Compose Directly**
```bash
# Development with hot reloading
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

# Production
docker-compose up -d
```

### 4. Verify Services

Check that all services are running:

```bash
make status
# or
docker-compose ps
```

Check health:
```bash
make health
```

### 5. Access the Application

- **Flask Web Interface**: http://localhost:5000
- **API Health Check**: http://localhost:5000/api/health
- **Flower (Task Monitoring)**: http://localhost:5555
- **pgAdmin (Database)**: http://localhost:5050
- **MinIO Console**: http://localhost:9001

## Services Overview

| Service | Port | Purpose |
|---------|------|---------|
| `api` | 5000 | Flask web application with API |
| `worker` | - | Celery worker for PDF processing |
| `db` | 5432 | PostgreSQL database |
| `redis` | 6379 | Redis for caching and task queue |
| `flower` | 5555 | Celery task monitoring |
| `minio` | 9000/9001 | Object storage (optional) |
| `pgadmin` | 5050 | Database administration (dev only) |

## Common Commands

### Development Workflow

```bash
# Start development environment
make dev-setup

# View logs
make logs

# Run tests
make test

# Access container shell
make shell

# Restart API service
make restart-api

# Stop everything
make down
```

### Database Management

```bash
# Run migrations
make db-migrate

# Access database shell
make shell-db

# Create backup
make db-backup

# Reset database (development only)
make db-reset
```

### Monitoring

```bash
# Check service status
make status

# View specific service logs
make logs-api
make logs-worker
make logs-db

# Check health
make health

# Open monitoring dashboards
make monitor
```

## Volume Mounts

The following directories are mounted as volumes:

- `./data` → `/app/data` (PDF files and processing data)
- `./logs` → `/app/logs` (Application logs)
- `./uploads` → `/app/uploads` (File uploads)
- `./test_data` → `/app/test_data` (Test PDFs)

## Environment Variables

Key environment variables (see `.env.docker` for full list):

```bash
# Database
DATABASE_URL=postgresql://arc_user:arc_password@db:5432/arc_pdf_tool

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8000

# Baserow (optional)
BASEROW_API_TOKEN=your_token_here
BASEROW_API_URL=https://api.baserow.io
```

## Optional Services

### Baserow (Local Development)

To start with a local Baserow instance:

```bash
make up-baserow
# or
docker-compose --profile baserow up -d
```

This starts Baserow at http://localhost:3000 with its own database.

### MinIO Object Storage

MinIO is included for object storage capabilities:

- **API**: http://localhost:9000
- **Console**: http://localhost:9001
- **Credentials**: arc_minio / arc_minio_password

## Troubleshooting

### Services Won't Start

1. Check Docker resources:
   ```bash
   docker system df
   docker system prune -f  # Clean up if needed
   ```

2. Check service logs:
   ```bash
   make logs
   ```

3. Verify configuration:
   ```bash
   make validate
   ```

### Database Issues

1. Reset database:
   ```bash
   make down-volumes
   make up
   make db-migrate
   ```

2. Check database logs:
   ```bash
   make logs-db
   ```

### Worker Not Processing Tasks

1. Check worker logs:
   ```bash
   make logs-worker
   ```

2. Verify Redis connection:
   ```bash
   docker-compose exec redis redis-cli ping
   ```

3. Check Flower for task status: http://localhost:5555

### Performance Issues

1. Check resource usage:
   ```bash
   docker stats
   ```

2. Adjust worker concurrency in `docker-compose.yml`:
   ```yaml
   worker:
     environment:
       - WORKER_CONCURRENCY=2  # Reduce if low memory
   ```

### Port Conflicts

If ports are already in use, modify `docker-compose.yml`:

```yaml
services:
  api:
    ports:
      - "8080:8000"  # Change to available port
```

## Production Considerations

### Security

1. Change default passwords in `.env`:
   ```bash
   DB_PASSWORD=strong_random_password
   MINIO_ROOT_PASSWORD=another_strong_password
   SECRET_KEY=your_secret_key_here
   ```

2. Disable debug mode:
   ```bash
   DEBUG=false
   ```

3. Configure proper CORS origins in the Flask app:
   ```bash
   # Update CORS settings in app.py or via environment
   ```

### Performance

1. Use production-grade database:
   ```bash
   DATABASE_URL=postgresql://user:pass@your-db-host:5432/arc_pdf_tool
   ```

2. Scale workers:
   ```bash
   docker-compose up -d --scale worker=3
   ```

3. Enable caching:
   ```bash
   ENABLE_CACHING=true
   ```

### Monitoring

1. Configure Sentry for error tracking:
   ```bash
   SENTRY_DSN=https://your-sentry-dsn
   ```

2. Enable Prometheus metrics:
   ```bash
   PROMETHEUS_ENABLED=true
   ```

## Cleanup

To completely remove everything:

```bash
# Stop and remove everything
make down-all

# Remove all Docker resources
make clean-all
```

## Getting Help

- Check logs: `make logs`
- Validate config: `make validate`
- Run health checks: `make health`
- View this help: `make help`

For more detailed information, see:
- [API Documentation](./API.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)