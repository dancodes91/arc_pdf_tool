# Installation Guide

## Prerequisites

### Required
- Python 3.11 or 3.12
- Git
- 4GB+ RAM
- 2GB+ disk space

### Optional
- Docker & Docker Compose (for containerized deployment)
- PostgreSQL 14+ (production database)
- Redis 6+ (background jobs)
- Tesseract OCR (for scanned PDFs)

## Installation Methods

### Method 1: Local Development (UV - Recommended)

UV is a fast Python package manager that handles virtual environments automatically.

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone <repo-url>
cd arc_pdf_tool

# Install dependencies (creates .venv automatically)
uv sync

# Activate environment
source .venv/bin/activate  # Linux/Mac
# OR
.venv\Scripts\activate  # Windows

# Verify installation
uv run python scripts/parse_and_export.py --help
```

### Method 2: Local Development (pip)

```bash
# Clone repository
git clone <repo-url>
cd arc_pdf_tool

# Create virtual environment
python -m venv .venv

# Activate environment
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -e ".[dev]"

# Verify installation
python scripts/parse_and_export.py --help
```

### Method 3: Docker (Production)

See [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) for full Docker setup.

```bash
# Quick start
docker compose up -d

# Check health
curl http://localhost:5000/healthz
```

## Configuration

### 1. Create Environment File

```bash
cp .env.example .env
```

### 2. Edit Configuration

**Minimum configuration (.env)**:
```bash
# Application
ENV=development
DEBUG=true
SECRET_KEY=change-this-in-production

# Database (SQLite for dev)
DATABASE_URL=sqlite:///arc_pdf_tool.db

# File Limits
MAX_CONTENT_LENGTH=52428800  # 50MB

# Parsing
MIN_TABLE_CONFIDENCE=0.7
MAX_PAGES_TO_PROCESS=1000
```

**Production configuration**:
```bash
# Application
ENV=production
DEBUG=false
SECRET_KEY=<generate-strong-secret>

# Database (PostgreSQL)
DATABASE_URL=postgresql://user:password@localhost:5432/arc_pdf_tool

# Redis (for background jobs)
REDIS_URL=redis://localhost:6379/0

# Baserow Integration
BASEROW_TOKEN=<your-token>
BASEROW_DATABASE_ID=<your-db-id>
```

### 3. Initialize Database

```bash
# Create database schema
uv run python scripts/init_db.py

# Or start Flask app (auto-initializes)
python app.py
```

## Optional Dependencies

### Tesseract OCR (for scanned PDFs)

**Ubuntu/Debian**:
```bash
sudo apt-get install tesseract-ocr
```

**macOS**:
```bash
brew install tesseract
```

**Windows**:
Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

Configure in `.env`:
```bash
TESSERACT_CMD=/usr/bin/tesseract
OCR_LANGUAGE=eng
```

### PostgreSQL (Production Database)

**Ubuntu/Debian**:
```bash
sudo apt-get install postgresql postgresql-contrib
sudo -u postgres createdb arc_pdf_tool
```

**Docker**:
```bash
docker run -d \
  --name arc_postgres \
  -e POSTGRES_PASSWORD=mysecretpassword \
  -e POSTGRES_DB=arc_pdf_tool \
  -p 5432:5432 \
  postgres:14
```

### Redis (Background Jobs)

**Ubuntu/Debian**:
```bash
sudo apt-get install redis-server
```

**Docker**:
```bash
docker run -d \
  --name arc_redis \
  -p 6379:6379 \
  redis:6
```

## Verification

### 1. Check Installation

```bash
# Verify Python version
python --version  # Should be 3.11 or 3.12

# Check dependencies
uv run python -c "import camelot; import pdfplumber; print('OK')"

# Run health check
uv run python -c "from app import app; print('Flask app OK')"
```

### 2. Run Tests

```bash
# Run test suite
pytest

# Expected: 166/200 passing (83%)
# Known failures are tracked in M2_ACCEPTANCE_REPORT.md
```

### 3. Parse Sample PDF

```bash
uv run python scripts/parse_and_export.py \
  "test_data/pdfs/2025-select-hinges-price-book.pdf" \
  --manufacturer select \
  --output exports/test

# Should complete in ~43 seconds
# Check exports/test/ for output files
```

### 4. Start Web Application

```bash
python app.py
```

Visit http://localhost:5000 - should see dashboard.

## Troubleshooting

### Import Errors

```bash
# Reinstall dependencies
uv sync --reinstall

# Or with pip
pip install -e ".[dev]" --force-reinstall
```

### Camelot Installation Issues

Camelot requires Ghostscript:

**Ubuntu/Debian**:
```bash
sudo apt-get install ghostscript
```

**macOS**:
```bash
brew install ghostscript
```

**Windows**:
Download from: https://ghostscript.com/releases/gsdnld.html

### Database Connection Errors

**SQLite** (development):
- Ensure write permissions to project directory
- Database file created automatically

**PostgreSQL** (production):
- Verify connection string in .env
- Check PostgreSQL is running: `pg_isready`
- Test connection: `psql $DATABASE_URL`

### Permission Errors

```bash
# Ensure directories exist and are writable
chmod -R 755 uploads exports static templates
mkdir -p uploads exports static/css static/js templates
```

## Next Steps

- [PARSERS.md](PARSERS.md) - Learn about parser architecture
- [DIFF.md](DIFF.md) - Use the diff engine
- [BASEROW.md](BASEROW.md) - Set up Baserow integration
- [OPERATIONS.md](OPERATIONS.md) - Deploy to production

## Support

If installation issues persist:
1. Check [GitHub Issues](https://github.com/your-repo/issues)
2. Review test suite output for specific errors
3. Check logs in `logs/` directory