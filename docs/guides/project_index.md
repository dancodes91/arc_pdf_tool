# Project Index
Commit: b5cc7561410ed07570d77209e8467ef83536c492 • Generated: 2025-10-02T14:46:34+03:30

## 1. Executive Summary

ARC PDF Tool is a comprehensive Python-based PDF price book parsing and management system designed for architectural hardware manufacturers. The system extracts structured pricing data from manufacturer PDFs (digital and scanned), stores it in a normalized database, generates automated diff reports between editions, and provides export capabilities in multiple formats (Excel, CSV, JSON). The architecture follows a hybrid Flask+FastAPI approach with Next.js frontend, PostgreSQL/SQLite database, Redis-backed Celery workers for async processing, and optional Baserow integration for data publishing.

**Primary services/processes**:
- Flask/FastAPI API server (port 5000)
- Next.js frontend (port 3000)
- Celery workers for background PDF processing
- PostgreSQL database (port 5432)
- Redis broker/cache (port 6379)
- Optional MinIO object storage (ports 9000/9001)
- Optional Baserow instance (port 3000, separate profile)

**Data stores**: PostgreSQL (primary), SQLite (dev), Redis (cache/broker), local filesystem (uploads/exports)

## 2. Tech Stack

### Languages & Frameworks
- **Backend**: Python 3.11/3.12 with Flask 3.0.0, FastAPI 0.104.1, SQLAlchemy 2.0.23
- **Frontend**: TypeScript/JavaScript with Next.js 14.0.4, React 18.2.0, TailwindCSS 3.3.5
- **Database**: PostgreSQL 15 (prod), SQLite 3 (dev), Alembic 1.13.1 (migrations)
- **Task Queue**: Celery 5.3.4 with Redis 5.0.1
- **PDF Processing**: pdfplumber 0.10.3, camelot-py 0.11.0, PyMuPDF 1.23.18, pytesseract 0.3.10

### Package Managers & Key Dependencies
- **Python**: `uv` (primary), pip (fallback) - managed via pyproject.toml:1-166
- **Node.js**: npm - managed via frontend/package.json:1-56

**Top 20 Python dependencies** (pyproject.toml:21-64):
1. pdfplumber>=0.10.3 (core PDF extraction)
2. camelot-py>=0.11.0 (table extraction)
3. pytesseract>=0.3.10 (OCR fallback)
4. PyMuPDF>=1.23.18 (PDF rendering)
5. pandas>=2.1.4 (data manipulation)
6. polars>=0.20.3 (high-performance data processing)
7. sqlalchemy>=2.0.23 (ORM)
8. psycopg2-binary>=2.9.9 (PostgreSQL driver)
9. fastapi>=0.104.1 (modern API framework)
10. uvicorn[standard]>=0.24.0 (ASGI server)
11. flask>=3.0.0 (legacy API framework)
12. celery>=5.3.4 (async task queue)
13. redis>=5.0.1 (cache + broker)
14. rapidfuzz>=3.5.2 (fuzzy matching)
15. deepdiff>=6.7.1 (diff engine)
16. alembic>=1.13.1 (database migrations)
17. pandera>=0.17.2 (data validation)
18. httpx>=0.25.2 (HTTP client)
19. structlog>=23.2.0 (structured logging)
20. sentry-sdk>=2.39.0 (error tracking)

**Top 10 Node.js dependencies** (frontend/package.json:11-42):
1. next@14.0.4
2. react@18.2.0
3. @radix-ui/* (UI components)
4. zustand@4.4.7 (state management)
5. axios@1.6.2 (HTTP client)
6. recharts@2.8.0 (charting)
7. zod@3.22.4 (schema validation)
8. react-hook-form@7.48.2 (form handling)
9. tailwindcss@3.3.5
10. typescript@5.3.2

## 3. Build & Run

### Backend Service (Flask API + Celery)

**Build**:
```bash
# Development
uv sync --dev                                    # Install all dependencies with dev tools

# Production (Docker)
docker build -f Dockerfile.base -t arc-base .    # Base image with system deps
docker build -f Dockerfile.api -t arc-api .      # API service
docker build -f Dockerfile.worker -t arc-worker .# Celery worker
```

**Dev Run**:
```bash
# Local development
export DATABASE_URL=postgresql://arc_user:arc_password@localhost:5432/arc_pdf_tool
export REDIS_URL=redis://localhost:6379/0
uv run python app.py                             # Starts Flask on 0.0.0.0:5000
```
Evidence: app.py:276-281

**Prod Run**:
```bash
# Via Docker Compose
docker-compose up -d                             # Starts all services (api, worker, db, redis)
# OR individual container
docker run -p 5000:5000 --env-file .env arc-api  # API only
```
Evidence: docker-compose.yml:1-206

### Frontend Service (Next.js)

**Build**:
```bash
cd frontend
npm install                                       # Install dependencies
npm run build                                     # Production build
```
Evidence: frontend/package.json:6-8

**Dev Run**:
```bash
cd frontend
npm run dev                                       # Starts Next.js on localhost:3000
```

**Prod Run**:
```bash
cd frontend
npm run build && npm run start                    # Production server on port 3000
```

### Required Environment Variables (.env.example:1-33)

**Critical**:
- `DATABASE_URL`: postgresql://user:password@host:port/arc_pdf_tool (or sqlite:///arc_pdf_tool.db)
- `REDIS_URL`: redis://localhost:6379/0
- `SECRET_KEY`: Flask secret for sessions
- `TESSERACT_CMD`: Path to tesseract binary (default: tesseract)

**Optional**:
- `ENV`: development|production
- `DEBUG`: true|false
- `CELERY_BROKER_URL`: redis://redis:6379/0
- `CELERY_RESULT_BACKEND`: redis://redis:6379/0
- `MAX_CONTENT_LENGTH`: 52428800 (50MB)
- `BASEROW_TOKEN`: Baserow API token (Phase 2)
- `BASEROW_DATABASE_ID`: Target Baserow database

### Local Infrastructure (docker-compose.yml:3-206)

**Exposed Ports**:
- 5000: Flask API (docker-compose.yml:63)
- 3000: Next.js frontend or Baserow (docker-compose.yml:150, profile: baserow)
- 5432: PostgreSQL (docker-compose.yml:17)
- 6379: Redis (docker-compose.yml:33)
- 5555: Celery Flower (monitoring, docker-compose.yml:115)
- 9000: MinIO API (docker-compose.yml:132)
- 9001: MinIO Console (docker-compose.yml:133)

**Health Endpoints**:
- `/healthz`: Liveness check (app.py:229-235)
- `/readyz`: Readiness check with DB + filesystem validation (app.py:238-266)
- `/api/health`: API health (api_routes.py:188-194)

## 4. Architecture & Data Flow

### Service Map

**API Service (app.py + api_routes.py)**:
- Responsibilities: HTTP request handling, file upload, PDF parsing orchestration, export generation
- Entry: app.py:21-26 (Flask app initialization)
- Routes: Template rendering (`/`, `/upload`, `/preview`, `/compare`) + REST API (`/api/*`)
- Dependencies: PriceBookManager, DiffEngine, ExportManager, HagerParser, SelectHingesParser

**Worker Service (core/tasks.py)**:
- Responsibilities: Async PDF processing, Baserow publishing, file cleanup
- Entry: core/tasks.py:23-39 (Celery app config)
- Tasks: process_pdf_task, publish_to_baserow_task, health_check_task, cleanup_old_files_task
- Dependencies: Parsers, Database models, Baserow client

**Database Service (database/models.py + database/manager.py)**:
- Responsibilities: Data persistence, ORM models, migrations
- Models: Manufacturer, PriceBook, Product, ProductFamily, Finish, ProductOption, ProductPrice, ChangeLog
- Manager: PriceBookManager (database/manager.py) - CRUD operations

**Parser Service (parsers/\*)**:
- Responsibilities: PDF extraction, table detection, OCR fallback, data normalization
- Implementations: HagerParser (parsers/hager/parser.py), SelectHingesParser (parsers/select/parser.py)
- Shared utilities: parsers/shared/* (normalization, provenance, confidence scoring, OCR)

**Diff Engine (core/diff_engine_v2.py, diff_engine.py)**:
- Responsibilities: Compare price book editions, generate change logs
- Entry: diff_engine.py:30 (legacy), core/diff_engine_v2.py (v2 implementation)

**Export Service (services/exporters.py)**:
- Responsibilities: Excel/CSV/JSON export with multi-sheet support
- Classes: DataExporter (full exports), QuickExporter (simple exports)

### Dependency Graph
See `docs/dependency_graph.dot` for visual service/module dependencies.

### External Integrations

**Baserow (integrations/baserow_client.py:1-end, services/publish_baserow.py:1-end)**:
- Purpose: Publish parsed pricing data to Baserow tables for collaborative editing
- Auth: Bearer token via `BASEROW_TOKEN` environment variable
- Config: `BASEROW_DATABASE_ID` for target database
- Endpoints: POST /api/database/tables/{table_id}/rows/batch/
- Data sync tracked in: models/baserow_syncs.py

**Sentry (pyproject.toml:62)**:
- Purpose: Error tracking and performance monitoring
- SDK: sentry-sdk>=2.39.0
- Config: Likely via DSN environment variable (not in .env.example)

**Tesseract OCR (config.py:16)**:
- Purpose: Fallback OCR for scanned PDFs
- Binary: Configured via `TESSERACT_CMD` env var
- Language: eng (config.py:17)

## 5. APIs / Interfaces

### HTTP REST API Endpoints (api_routes.py:16-204)

| Method | Path | Handler | Auth | Description |
|--------|------|---------|------|-------------|
| GET | `/api/price-books` | api_routes.py:26-33 | None | List all price books |
| GET | `/api/price-books/<id>` | api_routes.py:36-45 | None | Get price book summary |
| GET | `/api/products/<id>` | api_routes.py:48-69 | None | Get products (paginated) |
| POST | `/api/upload` | api_routes.py:72-129 | None | Upload + parse PDF |
| POST | `/api/compare` | api_routes.py:132-151 | None | Compare two price books |
| GET | `/api/export/<id>` | api_routes.py:154-175 | None | Export price book (Excel/CSV) |
| GET | `/api/change-log/<old>/<new>` | api_routes.py:178-185 | None | Get change log between editions |
| GET | `/api/health` | api_routes.py:188-194 | None | Health check |

### Web Interface Routes (app.py:44-226)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/` | app.py:45-53 | Dashboard with price book list |
| GET/POST | `/upload` | app.py:56-113 | Upload PDF form + processing |
| GET | `/preview/<id>` | app.py:116-129 | Preview parsed data (50 products) |
| GET | `/compare` | app.py:132-140 | Compare price books UI |
| POST | `/api/compare` | app.py:143-163 | Compare API (deprecated, use api_routes) |
| GET | `/export/<id>` | app.py:166-182 | Export trigger |
| GET | `/healthz` | app.py:229-235 | Kubernetes liveness probe |
| GET | `/readyz` | app.py:238-266 | Kubernetes readiness probe |

### Celery Task API (core/tasks.py:41-258)

| Task Name | Signature | Description |
|-----------|-----------|-------------|
| `core.tasks.process_pdf` | (file_path, options) → Dict | Async PDF processing |
| `core.tasks.publish_to_baserow` | (price_book_id, options) → Dict | Publish to Baserow |
| `core.tasks.health_check` | () → Dict | Worker health check |
| `core.tasks.cleanup_old_files` | (days=7) → Dict | Cleanup old exports/logs |

## 6. Data Model

### Database Schema (database/models.py:10-151)

**Manufacturers** (models.py:10-22):
- `id` (PK), `name`, `code` (unique), `created_at`
- Relationships: price_books, product_families, finishes

**PriceBooks** (models.py:24-40):
- `id` (PK), `manufacturer_id` (FK), `edition`, `effective_date`, `upload_date`, `file_path`, `file_size`, `status`, `parsing_notes`
- Relationships: manufacturer, products
- Status enum: 'processing', 'completed', 'failed'

**Products** (models.py:57-78):
- `id` (PK), `family_id` (FK), `price_book_id` (FK), `sku`, `model`, `description`, `base_price` (DECIMAL), `effective_date`, `retired_date`, `is_active`, `created_at`, `updated_at`
- Relationships: family, price_book, options, prices

**ProductOptions** (models.py:95-113):
- `id` (PK), `product_id` (FK), `option_type`, `option_code`, `option_name`, `adder_type`, `adder_value` (DECIMAL), `requires_option`, `excludes_option`, `is_required`, `sort_order`
- Option types: 'finish', 'size', 'preparation', 'net_add'
- Adder types: 'net_add', 'percent', 'replace', 'multiply'

**Finishes** (models.py:80-93):
- `id` (PK), `manufacturer_id` (FK), `code`, `name`, `bhma_code`, `description`
- Example: US3=Satin Chrome, US26D=Oil Rubbed Bronze

**ChangeLogs** (models.py:133-151):
- `id` (PK), `old_price_book_id` (FK), `new_price_book_id` (FK), `change_type`, `product_id` (FK), `old_value`, `new_value`, `change_percentage` (DECIMAL), `description`
- Change types: 'price_change', 'new_product', 'retired_product', 'option_change'

### Migrations (migrations/versions/)
- Current: dd1b80615a02_initial_schema_with_normalized_price_.py (initial schema)
- Migration tool: Alembic 1.13.1 (alembic.ini:1-end)

### Key Constraints & Indexes
- Manufacturer.code: UNIQUE constraint (models.py:16)
- Product foreign keys: Cascading deletes on price_book/family deletion
- ProductPrice.effective_date: NOT NULL (models.py:127)

### Persistence Hotspots (High Read/Write Paths)
- **Write-heavy**: Products table (parsing inserts), ChangeLogs table (diff generation)
- **Read-heavy**: Products table (preview/export queries), PriceBooks table (dashboard listing)
- **Optimization needed**: Products.price_book_id index, ChangeLog composite index on (old_price_book_id, new_price_book_id)

## 7. CI/CD & Quality

### Pipelines (GitHub Actions)

**.github/workflows/ci.yml:1-397** (Primary CI/CD):

**Jobs**:
1. **test** (matrix: Python 3.11, 3.12) - ci.yml:16-114
   - Runs on ubuntu-latest with Postgres 15 + Redis 7 services
   - Steps: ruff lint → black format check → mypy type check → alembic migrations → pytest with coverage
   - Coverage: Uploads to Codecov (ci.yml:108-114)

2. **build** (needs: test) - ci.yml:117-214
   - Docker Buildx multi-platform (linux/amd64, linux/arm64)
   - Builds: base, API, worker images
   - Registry: ghcr.io with GitHub Packages
   - Layer caching: GitHub Actions cache

3. **security** (needs: build) - ci.yml:217-298
   - Trivy vulnerability scanner (fs + container image scans)
   - Syft SBOM generation (SPDX-JSON format)
   - Uploads to GitHub Security tab (SARIF)

4. **release** (needs: [test, build, security], on: tags/v*) - ci.yml:301-382
   - Tags images with semver
   - Generates changelog from git log
   - Creates GitHub Release with Docker pull instructions

5. **deploy-staging** (needs: release) - ci.yml:385-397
   - Placeholder for staging deployment

**.github/workflows/security.yml:1-101** (Scheduled Security):
- Runs daily at 6 AM UTC (security.yml:6)
- Jobs: dependency-check (safety, bandit), secrets-scan (GitLeaks), code-quality (radon complexity/maintainability)

### Test Suites & Coverage Tools

**Test Discovery** (pyproject.toml:139-147):
- Framework: pytest>=7.4.3 with pytest-cov>=4.1.0
- Test paths: tests/
- Markers: unit, integration, slow, asyncio
- Coverage config: pyproject.toml:149-165 (source=., omit=venv/tests/migrations)

**Test Files**:
- tests/test_parsers.py (parser unit tests)
- tests/test_hager_parser.py (Hager-specific tests)
- tests/test_select_parser.py (SELECT Hinges tests)
- tests/test_database.py (database CRUD tests)
- tests/test_exporters.py (export format tests)
- tests/test_diff_engine_v2.py (diff engine tests)
- tests/test_baserow_integration.py (Baserow integration tests)
- tests/test_exception_handling.py (error handling tests)

**Linters & Static Analysis**:
- **ruff** (pyproject.toml:103-121): E/W/F/I/B/C4/UP rules, line-length=100, target-version=py311
- **mypy** (pyproject.toml:123-137): strict mode with disallow_untyped_defs
- **radon** (security.yml:84-92): Cyclomatic complexity + maintainability index
- **bandit** (security.yml:36-39): Security linter

**Coverage Thresholds**: Not enforced in config (pyproject.toml:149-165 defines reporting only)

## 8. Security & Compliance

### Secrets/Config Handling
- **Environment Variables**: All secrets via .env files (never committed)
- **Secret Detection**: GitLeaks in CI (security.yml:48-60)
- **Docker Secrets**: docker-compose.yml uses env vars (docker-compose.yml:8-12, 48-55)
- **Hardcoded Risks**: config.py:61 contains dev default secret key ('dev-secret-key-change-in-production')

### Input Validation
- **PDF Upload**: File extension check (config.py:13), size limit 50MB (config.py:12)
- **API Inputs**: Werkzeug secure_filename (api_routes.py:89), request.get_json() for JSON endpoints
- **Schema Validation**: Pandera for data validation (pyproject.toml:35), Zod in frontend (frontend/package.json:40)

### Authentication/Authorization Model
- **Current State**: No authentication implemented
- **Session Management**: Flask SECRET_KEY for session cookies (config.py:61)
- **API Security**: api/auth.py exists but appears unused (no imports in app.py or api_routes.py)
- **CORS**: Enabled for localhost:3000 (app.py:23)

### Compliance Considerations
- **Data Privacy**: No PII handling detected, pricing data only
- **Audit Logging**: ChangeLog table tracks price changes (models.py:133-151)
- **SBOM**: Generated in CI via Syft (ci.yml:278-288)
- **Vulnerability Scanning**: Trivy scans in CI (ci.yml:232-276)

## 9. Risks / Debt / TODOs

See `docs/risks_and_todos.md` for detailed prioritized list with evidence and fix suggestions.

**Critical Highlights**:
- No authentication/authorization (api_routes.py, app.py)
- Hardcoded dev secret key in config.py:61
- Missing database indexes on high-read tables
- Unpinned dependency ranges (pyproject.toml uses >=)
- Lack of rate limiting on upload endpoints

## 10. Appendix

### Repo Layout Tree

```
arc_pdf_tool/
├── .github/workflows/          # CI/CD pipelines (ci.yml, security.yml)
├── .venv/                      # Python virtual environment (excluded)
├── api/                        # API modules
│   ├── admin/                  # Admin endpoints (diff, baserow)
│   ├── auth.py                 # Authentication (unused)
│   ├── schemas.py              # Pydantic/validation schemas
│   └── error_handlers.py       # Global error handlers
├── app.py                      # Flask application entry point
├── api_routes.py               # REST API blueprint
├── config.py                   # Configuration settings
├── core/                       # Core business logic
│   ├── database.py             # Database utilities
│   ├── diff_engine_v2.py       # V2 diff engine
│   ├── exceptions.py           # Custom exceptions
│   ├── observability.py        # Logging/monitoring
│   ├── resilience.py           # Retry logic
│   └── tasks.py                # Celery tasks
├── database/                   # Database layer
│   ├── models.py               # SQLAlchemy ORM models
│   ├── manager.py              # PriceBookManager CRUD
│   └── init/                   # DB init scripts
├── diff_engine.py              # Legacy diff engine
├── docs/                       # Documentation
│   ├── progress.md             # Development progress
│   ├── project-index-agent.md  # This analysis manifest
│   ├── project_index.md        # **THIS FILE**
│   ├── project_index.json      # Machine-readable index
│   ├── dependency_graph.dot    # Graphviz service map
│   └── risks_and_todos.md      # Prioritized issues
├── export_manager.py           # Legacy export manager
├── frontend/                   # Next.js React frontend
│   ├── app/                    # Next.js app directory
│   │   ├── page.tsx            # Home page
│   │   ├── layout.tsx          # Root layout
│   │   ├── upload/             # Upload flow
│   │   ├── preview/            # Preview pages
│   │   └── compare/            # Comparison UI
│   ├── components/ui/          # Reusable UI components
│   ├── lib/stores/             # Zustand state stores
│   ├── package.json            # Node dependencies
│   ├── tsconfig.json           # TypeScript config
│   ├── tailwind.config.js      # Tailwind CSS config
│   └── next.config.js          # Next.js config
├── integrations/               # External integrations
│   └── baserow_client.py       # Baserow API client
├── migrations/                 # Alembic database migrations
│   ├── versions/               # Migration scripts
│   ├── env.py                  # Alembic environment
│   └── script.py.mako          # Migration template
├── models/                     # Additional models
│   ├── diff_results.py         # Diff result schemas
│   └── baserow_syncs.py        # Baserow sync tracking
├── parsers/                    # PDF parsing modules
│   ├── base_parser.py          # Abstract base parser
│   ├── hager/                  # Hager-specific parser
│   │   ├── parser.py           # Main Hager parser
│   │   └── sections.py         # Section extractors
│   ├── select/                 # SELECT Hinges parser
│   │   ├── parser.py           # Main SELECT parser
│   │   └── sections.py         # Section extractors
│   └── shared/                 # Shared parsing utilities
│       ├── confidence.py       # Confidence scoring
│       ├── normalization.py    # Data normalization
│       ├── provenance.py       # Provenance tracking
│       ├── page_classifier.py  # Page type detection
│       ├── table_processor.py  # Table extraction
│       ├── ocr_processor.py    # OCR fallback
│       ├── enhanced_extractor.py # Multi-method extraction
│       └── pdf_io.py           # PDF I/O utilities
├── scripts/                    # Utility scripts
│   ├── demo_milestone1.py      # M1 demo script
│   ├── parse_and_export.py     # CLI parser + exporter
│   └── publish_baserow.py      # Baserow publish CLI
├── services/                   # Service layer
│   ├── diff_service.py         # Diff service
│   ├── etl_loader.py           # ETL data loader
│   ├── exporters.py            # Data exporters
│   └── publish_baserow.py      # Baserow publishing service
├── static/                     # Static assets (CSS, JS)
├── templates/                  # Jinja2 HTML templates
├── tests/                      # Test suite
├── uploads/                    # Uploaded PDFs
├── exports/                    # Generated export files
├── test_data/pdfs/             # Test PDF fixtures
├── Dockerfile.base             # Base Docker image
├── Dockerfile.api              # API service image
├── Dockerfile.worker           # Worker service image
├── docker-compose.yml          # Docker Compose orchestration
├── docker-compose.override.yml # Local overrides
├── alembic.ini                 # Alembic configuration
├── pyproject.toml              # Python project metadata + deps
├── .env.example                # Environment variable template
├── README.md                   # Project README
└── run.py                      # Application runner script
```

### Glossary

- **BHMA**: Builders Hardware Manufacturers Association (finish standards)
- **Camelot**: Python library for PDF table extraction
- **Diff Engine**: Component that compares two price book editions
- **Hager**: Architectural hardware manufacturer (hinges, locks, closers)
- **Net-add**: Pricing option that adds a fixed amount to base price
- **OCR**: Optical Character Recognition (for scanned PDFs)
- **Provenance**: Metadata tracking source page/location of extracted data
- **SELECT Hinges**: Manufacturer specializing in hinges
- **SKU**: Stock Keeping Unit (product identifier)

### Open Questions

1. **Authentication Implementation**: api/auth.py exists but is not integrated. What is the planned auth strategy (OAuth, JWT, API keys)?
2. **Baserow Integration Status**: Optional in Phase 2. What is the current adoption/testing status?
3. **Legacy Code Migration**: Both diff_engine.py and core/diff_engine_v2.py exist. When is v1 being removed?
4. **Docker Image Registry**: CI pushes to ghcr.io - is there a private registry for production?
5. **Frontend API Base URL**: frontend/.env.local not in .env.example. How is NEXT_PUBLIC_API_URL configured?
6. **Database Migration Strategy**: How are production migrations applied (manual alembic, automated in CI, init container)?
7. **OCR Performance**: pytesseract is synchronous. Is async OCR via Celery planned for large scanned PDFs?
8. **Test Coverage Target**: No coverage threshold enforced. What is the target coverage percentage?
9. **Monitoring Stack**: Sentry SDK is included but not configured. What is the observability strategy (logs, metrics, traces)?
10. **Secrets Management**: Production uses env vars. Is there a plan for Vault/AWS Secrets Manager integration?
