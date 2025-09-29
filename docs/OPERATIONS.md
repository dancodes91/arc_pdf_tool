# Operations Guide

## Production Deployment

### Health Checks

Monitor service health:
```bash
# Liveness check
curl http://localhost:5000/healthz
# Response: {"status": "healthy", "service": "arc_pdf_tool"}

# Readiness check
curl http://localhost:5000/readyz
# Response: {"status": "ready", "checks": {"database": true, "filesystem": true}}
```

**Kubernetes probes**:
```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 5000
  initialDelaySeconds: 10
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /readyz
    port: 5000
  initialDelaySeconds: 5
  periodSeconds: 10
```

### Logging

Structured JSON logging enabled:

```json
{
  "timestamp": "2025-09-30T01:00:00Z",
  "level": "info",
  "message": "Parser completed",
  "logger_name": "hager_parser",
  "module": "parsers.hager.parser",
  "function": "parse",
  "line_number": 45,
  "manufacturer": "Hager",
  "products_extracted": 1250,
  "parse_time_ms": 89543
}
```

**Log locations**:
- Development: stdout
- Production: `logs/app.log` (rotated daily)
- Docker: Container logs (`docker logs arc_api`)

### Metrics

Key performance metrics:

```python
from core.observability import metrics_collector

# Parse time
metrics_collector.record_histogram('parse_time_ms', 89543, {
    'manufacturer': 'hager',
    'page_count': 479
})

# Extraction quality
metrics_collector.record_gauge('extraction_confidence', 0.94, {
    'manufacturer': 'hager',
    'section': 'products'
})
```

**Prometheus export** (if enabled):
```
# HELP parse_time_seconds Parse duration in seconds
# TYPE parse_time_seconds histogram
parse_time_seconds_bucket{manufacturer="hager",le="60"} 5
parse_time_seconds_bucket{manufacturer="hager",le="120"} 48
parse_time_seconds_bucket{manufacturer="hager",le="+Inf"} 50
```

### Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| SELECT parse time | < 2 min | 43s ✅ |
| Hager parse time | < 2 min | ~1.5 min ✅ |
| Row accuracy | ≥ 98% | Measured per run |
| Numeric accuracy | ≥ 99% | Measured per run |
| Low-confidence items | < 3% | Measured per run |

### Monitoring Alerts

**Critical alerts**:
1. Health check failures (> 3 consecutive)
2. Parse time > 2 minutes
3. Extraction confidence < 0.8
4. Database connection failures
5. Disk space < 10% free

**Warning alerts**:
1. Parse time > 90 seconds
2. Extraction confidence < 0.9
3. Queue depth > 10 jobs
4. Memory usage > 80%

## Backup & Recovery

### Database Backup

```bash
# SQLite (development)
cp arc_pdf_tool.db arc_pdf_tool.db.backup

# PostgreSQL (production)
pg_dump -h localhost -U user -d arc_pdf_tool > backup.sql

# Restore
psql -h localhost -U user -d arc_pdf_tool < backup.sql
```

### File Backup

```bash
# Backup uploads and exports
tar -czf backups/arc_$(date +%Y%m%d).tar.gz uploads/ exports/

# Restore
tar -xzf backups/arc_20250930.tar.gz
```

## Troubleshooting

### Parse Failures

**Symptom**: Parser returns 0 products

**Diagnosis**:
```bash
# Check logs
grep "ERROR" logs/app.log | tail -20

# Run with debug logging
export LOG_LEVEL=DEBUG
uv run python scripts/parse_and_export.py path/to/pdf.pdf --manufacturer hager
```

**Common causes**:
1. Unsupported PDF format → Try OCR
2. Incorrect manufacturer → Check PDF content
3. Corrupted PDF → Validate with `pdfinfo`

### Memory Issues

**Symptom**: OOM errors during large PDF parsing

**Solution**:
```bash
# Increase memory limit (Docker)
docker run --memory="4g" arc_api

# Process in chunks (config)
MAX_PAGES_TO_PROCESS=100
```

### Slow Performance

**Symptom**: Parse time > 2 minutes

**Diagnosis**:
```bash
# Profile parser
python -m cProfile -o profile.stats scripts/parse_and_export.py pdf.pdf

# Analyze
python -m pstats profile.stats
> sort cumtime
> stats 20
```

**Solutions**:
1. Enable page filtering (Hager)
2. Reduce Camelot usage
3. Disable OCR for native PDFs
4. Increase worker count (Docker)

## Maintenance

### Database Cleanup

```sql
-- Remove old price books (> 1 year)
DELETE FROM price_books
WHERE created_at < NOW() - INTERVAL '1 year';

-- Vacuum database
VACUUM ANALYZE;
```

### Log Rotation

```bash
# Configure logrotate
cat > /etc/logrotate.d/arc_pdf_tool <<EOF
/var/log/arc_pdf_tool/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
}
EOF
```

### Dependency Updates

```bash
# Update all dependencies
uv sync --upgrade

# Security patches only
uv sync --upgrade --only-security

# Test after update
pytest
```

## Security

### Secrets Management

**Never commit secrets**:
- Use `.env` files (gitignored)
- Use secret managers (AWS Secrets Manager, etc.)
- Rotate tokens quarterly

### API Security

```python
# Rate limiting (Flask-Limiter)
from flask_limiter import Limiter

limiter = Limiter(
    app=app,
    key_func=lambda: request.remote_addr,
    default_limits=["100 per hour"]
)

# File upload validation
ALLOWED_EXTENSIONS = {'pdf'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
```

### Audit Trail

All operations logged:
```sql
SELECT
  user_id,
  operation,
  timestamp,
  details
FROM audit_log
WHERE timestamp > NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;
```

## Disaster Recovery

### Recovery Time Objectives (RTO)

| Component | RTO | RPO |
|-----------|-----|-----|
| Database | 1 hour | 1 hour (backups) |
| Application | 15 min | N/A (stateless) |
| File storage | 4 hours | 24 hours (daily backups) |

### Recovery Procedures

**1. Application Failure**:
```bash
# Restart service
docker-compose restart

# Or redeploy
docker-compose up -d --force-recreate
```

**2. Database Failure**:
```bash
# Restore from backup
psql -h localhost -U user -d arc_pdf_tool < latest_backup.sql

# Verify
psql -h localhost -U user -d arc_pdf_tool -c "SELECT COUNT(*) FROM price_books;"
```

**3. Complete System Failure**:
```bash
# 1. Provision new infrastructure
# 2. Deploy application (Docker)
docker-compose up -d

# 3. Restore database
psql < backup.sql

# 4. Restore files
tar -xzf backups/latest.tar.gz

# 5. Verify health
curl http://localhost:5000/healthz
```

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.yml
services:
  api:
    image: arc_api
    replicas: 3  # Scale API instances
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G

  worker:
    image: arc_worker
    replicas: 5  # Scale background workers
```

### Vertical Scaling

```yaml
# Increase resources per container
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
```

### Performance Tuning

```python
# Config optimizations
config = {
    'min_confidence': 0.7,        # Lower = more products
    'enable_ocr': False,          # Disable for native PDFs
    'max_pages': 500,             # Limit for very large PDFs
    'camelot_flavor': 'lattice',  # Faster than stream
    'parallel_processing': True    # Multi-threaded
}
```

## CI/CD Integration

### GitHub Actions Workflows

**`.github/workflows/ci.yml`**:
- Runs on: push, pull_request
- Steps: lint, test, type check
- Required: passing tests for merge

**`.github/workflows/security.yml`**:
- Runs: daily
- Steps: dependency audit, SBOM generation
- Alerts on vulnerabilities

**`.github/workflows/performance.yml`**:
- Runs: weekly
- Steps: parse benchmarks, regression detection
- Alerts if > 10% slower

### Deployment Pipeline

```bash
# 1. Tag release
git tag -a v2.0.0 -m "Release v2.0.0"
git push origin v2.0.0

# 2. Build Docker images
docker build -t arc_api:2.0.0 -f Dockerfile.api .
docker build -t arc_worker:2.0.0 -f Dockerfile.worker .

# 3. Push to registry
docker push registry.example.com/arc_api:2.0.0
docker push registry.example.com/arc_worker:2.0.0

# 4. Deploy to production
kubectl set image deployment/arc-api arc-api=registry.example.com/arc_api:2.0.0
kubectl rollout status deployment/arc-api
```

## Support Contacts

- **On-call**: ops-team@example.com
- **Escalation**: engineering-lead@example.com
- **Security issues**: security@example.com

## See Also

- [INSTALL.md](INSTALL.md) - Setup instructions
- [PARSERS.md](PARSERS.md) - Parser architecture
- [DIFF.md](DIFF.md) - Diff engine usage