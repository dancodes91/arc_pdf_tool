# Risks, Technical Debt & TODOs

**Project**: ARC PDF Tool
**Commit**: b5cc7561410ed07570d77209e8467ef83536c492
**Generated**: 2025-10-02T14:46:34+03:30

---

## 🔴 CRITICAL Priority

### 1. Missing Authentication & Authorization

**Severity**: CRITICAL
**Component**: API Layer (app.py, api_routes.py)
**Evidence**:
- app.py:1-281 - No authentication middleware registered
- api_routes.py:1-204 - All endpoints accessible without auth
- api/auth.py:1-end exists but never imported or used
- CORS configured but no session/token validation (app.py:23)

**Impact**:
- Any user can upload PDFs, delete price books, export data
- No audit trail for user actions
- Compliance violations for data access control
- Potential data exfiltration or malicious uploads

**Suggested Fix**:
```python
# 1. Enable api/auth.py and implement JWT or Flask-Login
# 2. Add authentication decorator to all routes:

from api.auth import require_auth

@api.route('/api/upload', methods=['POST'])
@require_auth  # <-- Add this decorator
def upload_pdf():
    # existing code

# 3. Add middleware to Flask app:
from flask_jwt_extended import JWTManager

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
jwt = JWTManager(app)

# 4. Protect Next.js routes with middleware:
// frontend/middleware.ts
export { default } from "next-auth/middleware"
export const config = { matcher: ["/upload", "/compare", "/preview/:path*"] }
```

**Estimated Effort**: 2-3 days (backend) + 1 day (frontend integration)

---

### 2. Hardcoded Development Secret Key

**Severity**: CRITICAL
**Component**: Configuration (config.py)
**Evidence**:
- config.py:61 - `SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')`
- Default secret is predictable and used for Flask session signing
- No validation that production environments override this value

**Impact**:
- Session hijacking via forged session cookies
- CSRF token bypass
- Potential privilege escalation if auth is implemented

**Suggested Fix**:
```python
# config.py:61-62
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if os.getenv('ENV') == 'production':
        raise ValueError("SECRET_KEY must be set in production environment")
    else:
        # Only allow default in development
        import warnings
        warnings.warn("Using insecure default SECRET_KEY for development")
        SECRET_KEY = 'dev-secret-key-do-not-use-in-production'
```

**Estimated Effort**: 1 hour
**Related**: Add SECRET_KEY to .env.example with generated secure value example

---

### 3. No Rate Limiting on Upload Endpoints

**Severity**: CRITICAL
**Component**: API Routes (api_routes.py, app.py)
**Evidence**:
- api_routes.py:72-129 - `/api/upload` POST endpoint has no rate limiting
- app.py:56-113 - `/upload` POST endpoint has no rate limiting
- No Flask-Limiter or similar middleware configured

**Impact**:
- Denial of Service (DoS) via upload flooding
- Storage exhaustion (uploads/ directory)
- Resource exhaustion (PDF parsing is CPU-intensive)
- Celery worker starvation

**Suggested Fix**:
```python
# 1. Install Flask-Limiter:
# pyproject.toml dependencies section:
# "flask-limiter>=3.5.0",

# 2. Configure in app.py:
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
)

# 3. Apply to upload endpoints:
@app.route('/upload', methods=['POST'])
@limiter.limit("10 per hour")  # <-- Restrict uploads
def upload_pdf():
    # existing code

# 4. Add X-RateLimit headers in response for client visibility
```

**Estimated Effort**: 2 hours
**Related**: Add rate limit configuration to .env.example

---

## 🟠 HIGH Priority

### 4. Unpinned Dependency Versions

**Severity**: HIGH
**Component**: Dependencies (pyproject.toml)
**Evidence**:
- pyproject.toml:21-64 - All 43 production dependencies use `>=` version specifiers
- No lockfile committed (uv.lock should be in git)
- CI uses "latest" uv version (.github/workflows/ci.yml:58)

**Impact**:
- Non-reproducible builds across environments
- Unexpected breaking changes in dependencies
- Difficult rollback if regression occurs
- Security vulnerabilities in updated packages go unnoticed

**Suggested Fix**:
```toml
# 1. Pin exact versions in pyproject.toml:
[project]
dependencies = [
    "pdfplumber==0.10.3",  # <-- Use == instead of >=
    "camelot-py==0.11.0",
    # ... pin all dependencies
]

# 2. Commit uv.lock to version control:
git add uv.lock
git commit -m "chore: add lockfile for reproducible builds"

# 3. Add Renovate or Dependabot config:
# .github/renovate.json
{
  "extends": ["config:base"],
  "packageRules": [
    {
      "matchUpdateTypes": ["minor", "patch"],
      "automerge": true
    }
  ]
}
```

**Estimated Effort**: 3-4 hours
**Related**: Update CI to fail if uv.lock is not committed

---

### 5. Missing Database Indexes on High-Read Tables

**Severity**: HIGH
**Component**: Database Schema (database/models.py)
**Evidence**:
- database/models.py:57-78 - `products` table has no index on `price_book_id` foreign key
- database/models.py:133-151 - `change_logs` table missing composite index on `(old_price_book_id, new_price_book_id)`
- Query in api_routes.py:55-58 filters by `price_book_id` (likely full table scan)
- Dashboard in app.py:48 calls `list_price_books()` which may join products without index

**Impact**:
- Slow queries as data scales (O(n) instead of O(log n))
- High database CPU usage under load
- Poor user experience on preview/dashboard pages
- Potential timeouts on large price books (>10,000 products)

**Suggested Fix**:
```python
# 1. Create Alembic migration:
# alembic revision -m "add indexes for performance"

# migrations/versions/XXXXXX_add_indexes_for_performance.py
from alembic import op

def upgrade():
    op.create_index(
        'ix_products_price_book_id',
        'products',
        ['price_book_id']
    )
    op.create_index(
        'ix_change_logs_price_books',
        'change_logs',
        ['old_price_book_id', 'new_price_book_id']
    )
    op.create_index(
        'ix_products_sku',
        'products',
        ['sku']  # For SKU lookups in diff engine
    )

def downgrade():
    op.drop_index('ix_products_price_book_id')
    op.drop_index('ix_change_logs_price_books')
    op.drop_index('ix_products_sku')

# 2. Apply migration:
# alembic upgrade head
```

**Estimated Effort**: 1 hour (migration) + 1 hour (testing/verification)
**Verification**: Use `EXPLAIN ANALYZE` on production queries to confirm index usage

---

### 6. CORS Misconfiguration for Production

**Severity**: HIGH
**Component**: API Configuration (app.py)
**Evidence**:
- app.py:23 - `CORS(app, origins=['http://localhost:3000', 'http://127.0.0.1:3000'])`
- Hardcoded localhost origins, won't work in production
- No environment-based configuration
- No CORS headers validation for preflight OPTIONS requests

**Impact**:
- Frontend cannot call API in production (CORS errors)
- Must redeploy API to add new frontend domains
- Potential for misconfigured wildcard `*` in production

**Suggested Fix**:
```python
# app.py:23
ALLOWED_ORIGINS = os.getenv(
    'CORS_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000'
).split(',')

CORS(
    app,
    origins=ALLOWED_ORIGINS,
    methods=['GET', 'POST', 'PUT', 'DELETE'],
    allow_headers=['Content-Type', 'Authorization'],
    supports_credentials=True,
    max_age=3600
)

# .env.example
# CORS_ORIGINS=https://arc-pdf.example.com,https://www.arc-pdf.example.com
```

**Estimated Effort**: 30 minutes
**Related**: Add validation to reject `*` wildcard in production

---

### 7. Lack of Input Validation on Pagination Parameters

**Severity**: HIGH
**Component**: API Routes (api_routes.py)
**Evidence**:
- api_routes.py:51-52 - `page` and `per_page` parameters not validated
- `per_page` could be set to 1,000,000 causing memory exhaustion
- No maximum limit enforced

**Impact**:
- Memory exhaustion via large `per_page` values
- Database overload from large result sets
- DoS vector via malicious query strings

**Suggested Fix**:
```python
# api_routes.py:48-69
@api.route('/products/<int:price_book_id>', methods=['GET'])
def get_products(price_book_id):
    try:
        page = max(1, request.args.get('page', 1, type=int))  # Min 1
        per_page = min(100, max(1, request.args.get('per_page', 50, type=int)))  # Max 100

        # ... existing code

# Or use Pydantic for validation:
from pydantic import BaseModel, Field

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, le=10000)
    per_page: int = Field(default=50, ge=1, le=100)

# In route:
params = PaginationParams(**request.args)
```

**Estimated Effort**: 1 hour (add validation) + 1 hour (update frontend tests)

---

### 8. Error Messages Expose Internal Details

**Severity**: HIGH
**Component**: Error Handling (api_routes.py, app.py)
**Evidence**:
- api_routes.py:32-33 - `return jsonify({'error': str(e)}), 500` exposes stack traces
- app.py:106-107 - Exception messages shown to user via flash()
- No centralized error handler with sanitized messages

**Impact**:
- Leaks internal paths, database structure, library versions
- Aids attackers in reconnaissance
- Non-user-friendly error messages

**Suggested Fix**:
```python
# api/error_handlers.py (use existing file)
from flask import jsonify
from core.exceptions import ValidationError, NotFoundError
from core.observability import get_logger

logger = get_logger("api.errors")

def register_error_handlers(app):
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        logger.warning(f"Validation error: {e}")
        return jsonify({'error': 'Invalid input provided'}), 400

    @app.errorhandler(NotFoundError)
    def handle_not_found(e):
        logger.info(f"Resource not found: {e}")
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(Exception)
    def handle_generic_error(e):
        logger.error(f"Unexpected error: {e}", exc_info=True)
        if app.config['DEBUG']:
            return jsonify({'error': str(e)}), 500
        else:
            return jsonify({'error': 'An internal error occurred'}), 500

# app.py - call during initialization:
from api.error_handlers import register_error_handlers
register_error_handlers(app)
```

**Estimated Effort**: 2 hours
**Related**: Add custom exceptions to core/exceptions.py

---

## 🟡 MEDIUM Priority

### 9. Legacy Diff Engine Still in Use

**Severity**: MEDIUM
**Component**: Diff Engine (diff_engine.py, core/diff_engine_v2.py)
**Evidence**:
- diff_engine.py:1-end - Legacy implementation
- core/diff_engine_v2.py:1-end - New implementation
- app.py:11 imports `diff_engine.DiffEngine` (legacy)
- api_routes.py:12 imports `diff_engine.DiffEngine` (legacy)
- api/admin/diff_endpoints.py likely uses v2 (need to verify)

**Impact**:
- Technical debt and confusion for new developers
- Potential bugs from maintaining two implementations
- Wasted CI/test time on deprecated code

**Suggested Fix**:
```python
# 1. Create migration task checklist:
# [ ] Update app.py imports to use core.diff_engine_v2
# [ ] Update api_routes.py imports to use core.diff_engine_v2
# [ ] Verify api/admin uses v2
# [ ] Run full regression test suite
# [ ] Delete diff_engine.py
# [ ] Update documentation

# 2. Implementation:
# app.py:11-12 (change)
from core.diff_engine_v2 import DiffEngine  # Changed from diff_engine

# 3. After migration:
git rm diff_engine.py
git commit -m "chore: remove legacy diff engine (v1)"
```

**Estimated Effort**: 4 hours (testing + migration)
**Risk**: Regressions if v2 behavior differs from v1 (needs thorough testing)

---

### 10. Missing Health Check Dependencies in Docker

**Severity**: MEDIUM
**Component**: Docker Configuration (docker-compose.yml, Dockerfile.api)
**Evidence**:
- docker-compose.yml:70 - `test: ["CMD", "curl", "-f", "http://localhost:5000/api/health"]`
- curl is not installed in Python base images by default
- Healthcheck will always fail in production

**Impact**:
- Kubernetes/Docker health probes fail
- Service marked unhealthy incorrectly
- Rollouts blocked or containers restarted unnecessarily

**Suggested Fix**:
```dockerfile
# Dockerfile.api - add curl or use Python httpx
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# OR better: use Python for healthcheck (no extra dependency)
# docker-compose.yml:70
healthcheck:
  test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:5000/api/health').raise_for_status()"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s

# Note: httpx is already in dependencies (pyproject.toml:43)
```

**Estimated Effort**: 30 minutes
**Related**: Test healthcheck in local Docker environment before deploying

---

### 11. No Test Coverage Threshold Enforcement

**Severity**: MEDIUM
**Component**: Testing Configuration (pyproject.toml, .github/workflows/ci.yml)
**Evidence**:
- pyproject.toml:149-165 - Coverage reporting configured but no `fail_under` threshold
- .github/workflows/ci.yml:105 - pytest runs with `--cov` but doesn't fail on low coverage
- .github/workflows/ci.yml:108-114 - Codecov upload set to `fail_ci_if_error: false`

**Impact**:
- Code coverage can regress silently
- No incentive to write tests for new code
- Hard to enforce quality gates

**Suggested Fix**:
```toml
# pyproject.toml:149-165 - add fail_under
[tool.coverage.report]
fail_under = 80  # <-- Fail if coverage drops below 80%
exclude_lines = [
    "pragma: no cover",
    # ... existing exclusions
]

# Or use pytest-cov CLI flag:
# .github/workflows/ci.yml:105
uv run python -m pytest tests/ -v --cov=. --cov-report=xml --cov-report=term-missing --cov-fail-under=80

# Gradually increase threshold:
# - Start at 60% (current level)
# - Increase 5% per sprint until reaching 80-85%
```

**Estimated Effort**: 1 hour (add threshold) + ongoing effort to improve coverage
**Related**: Add coverage badge to README.md

---

### 12. Frontend Environment Variables Not Documented

**Severity**: MEDIUM
**Component**: Frontend Configuration (frontend/.env.local)
**Evidence**:
- .env.example:1-33 only contains backend variables
- frontend/.env.local not tracked in git (correct) but no .env.example equivalent
- frontend/package.json:6-9 references environment variables implicitly

**Impact**:
- New developers cannot run frontend without guessing env vars
- Production deployment fails without proper NEXT_PUBLIC_API_URL
- No documentation of required/optional variables

**Suggested Fix**:
```bash
# Create frontend/.env.example:
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:5000

# Optional: Analytics
# NEXT_PUBLIC_GOOGLE_ANALYTICS=G-XXXXXXXXXX

# Optional: Feature Flags
# NEXT_PUBLIC_ENABLE_BASEROW=true

# Add to README.md:
## Frontend Setup
1. Copy environment template: `cp frontend/.env.example frontend/.env.local`
2. Update `NEXT_PUBLIC_API_URL` to point to your API server
3. Run `npm run dev`
```

**Estimated Effort**: 15 minutes

---

### 13. Lack of Request ID Tracking for Debugging

**Severity**: MEDIUM
**Component**: Observability (core/observability.py)
**Evidence**:
- core/observability.py uses structlog for logging (good!)
- No request ID middleware to track requests across services
- Logs from API → Celery → Database cannot be correlated

**Impact**:
- Difficult to debug issues spanning multiple services
- Cannot trace a single user request through the system
- Logs are scattered without correlation

**Suggested Fix**:
```python
# Add middleware to app.py:
import uuid
from flask import g, request

@app.before_request
def add_request_id():
    g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))

@app.after_request
def add_request_id_header(response):
    response.headers['X-Request-ID'] = g.request_id
    return response

# Update logging in core/observability.py:
from flask import g

def get_logger(name):
    return structlog.get_logger(name).bind(
        request_id=lambda: getattr(g, 'request_id', 'no-request-id')
    )

# Frontend should preserve request ID in API calls:
axios.interceptors.request.use(config => {
    config.headers['X-Request-ID'] = uuidv4();
    return config;
});
```

**Estimated Effort**: 2 hours
**Related**: Add request ID to Celery task context

---

## 🟢 LOW Priority

### 14. Unused api/auth.py Module

**Severity**: LOW
**Component**: API Auth Module (api/auth.py)
**Evidence**:
- api/auth.py:1-end exists
- Never imported in app.py or api_routes.py
- No tests referencing auth module

**Impact**:
- Dead code clutters codebase
- Confuses developers about auth status
- Wastes maintenance effort

**Suggested Fix**:
```bash
# Option 1: Delete if truly unused
git rm api/auth.py
git commit -m "chore: remove unused auth module"

# Option 2: If planned for future use, document intent
# Add TODO comment in api/auth.py:
# TODO: Implement JWT authentication (see issue #123)
# This module is a placeholder for Phase 3 auth implementation
```

**Estimated Effort**: 5 minutes (decision + action)

---

### 15. Missing Alembic Autogenerate Verification

**Severity**: LOW
**Component**: Database Migrations (migrations/)
**Evidence**:
- migrations/ directory exists with one migration
- No CI check that migrations are up-to-date with models
- Developers could modify models without creating migrations

**Impact**:
- Schema drift between models.py and database
- Production deployments fail due to missing migrations
- Hard-to-debug errors from outdated schema

**Suggested Fix**:
```yaml
# .github/workflows/ci.yml - add migration check job
- name: Check migrations are up-to-date
  run: |
    # Generate migration to see if any changes exist
    uv run alembic revision --autogenerate -m "temp_check" > /dev/null

    # Check if new migration was created (file count changed)
    NEW_MIGRATIONS=$(git status --porcelain migrations/versions/ | wc -l)
    if [ "$NEW_MIGRATIONS" -gt 0 ]; then
      echo "❌ Models were changed without creating migrations!"
      echo "Run: alembic revision --autogenerate -m 'describe changes'"
      exit 1
    fi

    echo "✅ Migrations are up-to-date"
```

**Estimated Effort**: 30 minutes
**Related**: Add pre-commit hook for local validation

---

### 16. No Graceful Shutdown for Celery Workers

**Severity**: LOW
**Component**: Celery Tasks (core/tasks.py, Dockerfile.worker)
**Evidence**:
- core/tasks.py:35 sets `task_time_limit=30*60` but no graceful shutdown handling
- Dockerfile.worker likely uses default signal handling
- Long-running tasks may be killed mid-processing during deployments

**Impact**:
- PDF processing interrupted mid-parse
- Partial data written to database
- Baserow syncs left incomplete

**Suggested Fix**:
```python
# core/tasks.py - add signal handling
from celery.signals import worker_shutdown

@worker_shutdown.connect
def on_worker_shutdown(sender, **kwargs):
    logger.info("Worker shutting down gracefully...")
    # Allow current tasks to finish (up to 30s)

# Dockerfile.worker - use proper stop signal
# Add to docker-compose.yml:
worker:
  # ... existing config
  stop_signal: SIGTERM
  stop_grace_period: 35s  # Slightly longer than task_time_limit soft limit
```

**Estimated Effort**: 1 hour
**Related**: Add Celery task retries for transient failures

---

### 17. Hardcoded Feature Flags in Code

**Severity**: LOW
**Component**: Various (scattered)
**Evidence**:
- No centralized feature flag system
- Features like Baserow integration toggled via environment variables inconsistently
- No UI to toggle features without redeployment

**Impact**:
- Difficult to A/B test features
- Cannot disable broken features without redeployment
- No gradual rollout capability

**Suggested Fix**:
```python
# Create core/feature_flags.py:
from typing import Dict, Callable
import os

class FeatureFlags:
    _flags: Dict[str, Callable[[], bool]] = {
        'baserow_integration': lambda: os.getenv('FEATURE_BASEROW', 'false').lower() == 'true',
        'async_pdf_processing': lambda: os.getenv('FEATURE_ASYNC_PROCESSING', 'true').lower() == 'true',
        'excel_export': lambda: True,  # Always enabled
    }

    @classmethod
    def is_enabled(cls, flag_name: str) -> bool:
        getter = cls._flags.get(flag_name, lambda: False)
        return getter()

# Usage:
from core.feature_flags import FeatureFlags

if FeatureFlags.is_enabled('baserow_integration'):
    # ... baserow code
```

**Estimated Effort**: 2 hours (create system) + ongoing migration of flags
**Future**: Consider LaunchDarkly or similar service for advanced flags

---

### 18. No Monitoring/Alerting Configuration

**Severity**: LOW
**Component**: Observability (Sentry SDK included but not configured)
**Evidence**:
- pyproject.toml:62 includes sentry-sdk>=2.39.0
- No Sentry DSN configuration in .env.example
- No Prometheus metrics exported
- No alerting rules defined

**Impact**:
- Cannot detect production issues proactively
- No metrics on API latency, error rates, queue depth
- Relies on user reports for outages

**Suggested Fix**:
```python
# app.py - add Sentry initialization
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

if os.getenv('SENTRY_DSN'):
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        integrations=[
            FlaskIntegration(),
            CeleryIntegration(),
        ],
        environment=os.getenv('ENV', 'development'),
        traces_sample_rate=0.1,  # 10% of transactions
        profiles_sample_rate=0.1,
    )

# .env.example
# SENTRY_DSN=https://xxx@sentry.io/xxx

# For Prometheus metrics, add flask-prometheus-metrics:
from prometheus_flask_exporter import PrometheusMetrics
metrics = PrometheusMetrics(app)
# Exports to /metrics endpoint
```

**Estimated Effort**: 2 hours (Sentry) + 3 hours (Prometheus)
**Related**: Set up Grafana dashboards for key metrics

---

### 19. Large PDF Files May Cause OOM Errors

**Severity**: LOW
**Component**: PDF Processing (parsers/)
**Evidence**:
- config.py:12 - MAX_CONTENT_LENGTH=50MB allows large uploads
- parsers/hager/parser.py loads entire PDF into memory (pdf_extractor.extract_document())
- No streaming or pagination of PDF processing

**Impact**:
- Large scanned PDFs (40+ MB) may exhaust worker memory
- Worker crashes and restarts
- Task retries exacerbate the problem

**Suggested Fix**:
```python
# Add memory monitoring to tasks:
import resource

@celery_app.task
def process_pdf_task(file_path):
    max_memory_mb = 1024  # 1GB limit

    def check_memory():
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # MB
        if usage > max_memory_mb:
            raise MemoryError(f"Task exceeded {max_memory_mb}MB memory limit")

    # ... processing with periodic check_memory() calls

# Alternative: Process PDFs page-by-page instead of all at once
# parsers/shared/pdf_io.py - add streaming mode
def extract_document(self, stream=False):
    if stream:
        # Yield pages one at a time
        for page_num in range(self.doc.page_count):
            yield self._extract_page(page_num)
    else:
        # Existing all-at-once logic
```

**Estimated Effort**: 4 hours
**Related**: Add memory limit to Celery worker config

---

### 20. Missing Performance Tests in CI

**Severity**: LOW
**Component**: CI Pipeline (.github/workflows/ci.yml)
**Evidence**:
- .github/workflows/ci.yml has no performance test job
- scripts/ci_performance_test.py exists but not invoked in CI
- No baseline metrics to detect performance regressions

**Impact**:
- Performance can regress silently
- No early warning of slow queries or parsing bottlenecks
- Manual performance testing is inconsistent

**Suggested Fix**:
```yaml
# .github/workflows/ci.yml - add job after test job
performance:
  name: Performance Tests
  runs-on: ubuntu-latest
  needs: test

  steps:
  - uses: actions/checkout@v4
  - name: Set up Python 3.12
    uses: actions/setup-python@v4
    with:
      python-version: '3.12'

  - name: Install dependencies
    run: uv sync --dev

  - name: Run performance tests
    run: |
      uv run python scripts/ci_performance_test.py

      # Fail if parsing time exceeds threshold
      MAX_PARSE_TIME_MS=5000
      ACTUAL_TIME=$(cat perf_results.json | jq '.parse_time_ms')
      if [ "$ACTUAL_TIME" -gt "$MAX_PARSE_TIME_MS" ]; then
        echo "❌ Parsing time $ACTUAL_TIME ms exceeds threshold $MAX_PARSE_TIME_MS ms"
        exit 1
      fi
```

**Estimated Effort**: 3 hours
**Related**: Add performance baseline metrics to docs/

---

## Summary Statistics

| Severity | Count | Estimated Total Effort |
|----------|-------|------------------------|
| CRITICAL | 3     | 3-5 days               |
| HIGH     | 5     | 11-14 hours            |
| MEDIUM   | 6     | 11-13 hours            |
| LOW      | 6     | 15-18 hours            |
| **TOTAL**| **20**| **~2.5-3 weeks**       |

## Recommended Prioritization Order

1. **Week 1 (Critical + High Security)**:
   - #2: Hardcoded Secret Key (1 hour)
   - #1: Authentication/Authorization (3-4 days)
   - #3: Rate Limiting (2 hours)
   - #6: CORS Configuration (30 min)

2. **Week 2 (High Performance + Stability)**:
   - #5: Database Indexes (2 hours)
   - #4: Pin Dependencies (4 hours)
   - #7: Input Validation (2 hours)
   - #8: Error Handling (2 hours)

3. **Week 3 (Medium Quality + Low Debt)**:
   - #9: Remove Legacy Diff Engine (4 hours)
   - #10: Fix Docker Healthchecks (30 min)
   - #11: Coverage Threshold (1 hour)
   - #13: Request ID Tracking (2 hours)
   - Low priority items as time allows

## Acceptance Criteria for Completion

Each risk/TODO is considered resolved when:
1. ✅ Code changes merged to main branch
2. ✅ Tests added/updated to prevent regression
3. ✅ Documentation updated (README, .env.example, etc.)
4. ✅ CI pipeline passes all checks
5. ✅ Deployed to staging and verified
6. ✅ This document updated to reflect completion status

---

**Next Review**: 2025-10-16 (2 weeks from generation)
**Owner**: Development Team
**Stakeholders**: Security Team, DevOps, Product
