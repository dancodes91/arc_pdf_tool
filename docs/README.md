# ARC PDF Tool Documentation

**Version**: 2.0
**Last Updated**: 2025-09-30

## Overview

ARC PDF Tool is a production-ready system for parsing, comparing, and exporting manufacturer price books. It specializes in hardware price list processing with robust diff detection and Baserow integration.

## Supported Manufacturers

- **Hager** - Door hardware (hinges, closers, locks)
- **SELECT Hinges** - Architectural hinges and accessories

## Key Features

### Core Capabilities
- **PDF Parsing** - Extracts products, prices, finishes, options, rules
- **Diff Engine v2** - Detects changes, renames, price updates with confidence scoring
- **Baserow Integration** - Syncs parsed data to Baserow database
- **Export Pipeline** - JSON, CSV, XLSX formats
- **Docker Deployment** - Containerized API + worker architecture

### Data Extraction
- Products with SKUs, prices, descriptions
- Finish codes (US3, US10B, etc.) with BHMA mappings
- Net-add options with constraints
- Price rules and mappings
- Effective dates
- Page provenance tracking

## Architecture

```
arc_pdf_tool/
├── parsers/          # Manufacturer-specific parsers
│   ├── hager/       # Hager price book parser
│   ├── select/      # SELECT hinges parser
│   └── shared/      # Shared extraction utilities
├── core/            # Core business logic
│   ├── diff_engine_v2.py    # Change detection
│   ├── exceptions.py        # Error taxonomy
│   └── observability.py     # Logging & metrics
├── integrations/    # External system integrations
│   └── baserow_client.py    # Baserow API client
├── services/        # Application services
│   ├── exporters.py         # Export formatters
│   └── publish_baserow.py   # Baserow publisher
├── database/        # Database models & manager
├── api_routes.py    # REST API endpoints
└── app.py           # Flask application

```

## Quick Start

### Installation
```bash
# Clone repository
git clone <repo-url>
cd arc_pdf_tool

# Install dependencies
uv sync

# Set up environment
cp .env.example .env
# Edit .env with your configuration
```

### Parse a PDF
```bash
uv run python scripts/parse_and_export.py \
  "test_data/pdfs/2025-hager-price-book.pdf" \
  --manufacturer hager \
  --output exports/hager_2025
```

### Run Web Application
```bash
python app.py
# Access at http://localhost:5000
```

### Docker Deployment
See [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)

## Documentation Index

- **[INSTALL.md](INSTALL.md)** - Detailed installation guide
- **[PARSERS.md](PARSERS.md)** - Parser architecture and customization
- **[DIFF.md](DIFF.md)** - Diff engine usage and configuration
- **[BASEROW.md](BASEROW.md)** - Baserow integration setup
- **[OPERATIONS.md](OPERATIONS.md)** - Production operations guide
- **[DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)** - Docker deployment

## API Endpoints

### Health Checks
- `GET /healthz` - Liveness check
- `GET /readyz` - Readiness check (validates database, filesystem)

### Core Operations
- `POST /api/upload` - Upload and parse PDF
- `GET /api/price-books` - List all price books
- `GET /api/price-books/<id>` - Get specific price book
- `POST /api/compare` - Compare two price books
- `POST /api/export/<id>` - Export price book data

## Performance

### Parse Times (Target: < 2 minutes)
- **SELECT Hinges** (20 pages): ~43 seconds ✅
- **Hager** (479 pages): ~1.5 minutes ✅ (optimized)

### Accuracy Targets
- Row extraction: ≥98%
- Numeric accuracy: ≥99%
- Low-confidence items: <3%

## Configuration

Key environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host/db

# Security
SECRET_KEY=your-secret-key-change-in-production

# Parsing
MIN_TABLE_CONFIDENCE=0.7
MAX_PAGES_TO_PROCESS=1000

# Baserow (optional)
BASEROW_TOKEN=your_token_here
BASEROW_DATABASE_ID=12345
```

## Testing

```bash
# Run full test suite
pytest

# Run specific tests
pytest tests/test_hager_parser.py -v

# Run with coverage
pytest --cov=. --cov-report=html
```

## Support

- **Issues**: Report bugs and feature requests on GitHub
- **Documentation**: See docs/ directory for detailed guides
- **Examples**: Check test_data/ for sample PDFs and expected outputs

## License

Proprietary - All Rights Reserved