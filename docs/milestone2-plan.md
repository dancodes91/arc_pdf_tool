# Milestone 2 - Parser Hardening & Production Readiness

| Property | Value |
|----------|-------|
| **Status** | PLANNED |
| **Start Date** | September 26, 2025 |
| **Target Completion** | October 3, 2025 (7 days) |
| **Branch** | `alex-feature` |
| **Prerequisites** | Milestone 1 Complete (80/80 tests passing) |

## Executive Summary

Milestone 2 focuses on production hardening with advanced parser capabilities, comprehensive diff engine v2, robust exception handling, Baserow/Postgres integration, Docker containerization, CI/CD pipeline, and complete documentation handover. This milestone transforms the system from functional prototype to production-ready enterprise solution.

## 8-Phase Implementation Plan

### Phase 1: Parser Hardening (Days 1-2)
**Goal**: Raise recall/precision on tricky pages; stabilize across layout drift; robust scanned pages.

#### 1.1 Layout Classifier & Routing
- **File**: `parsers/shared/page_classifier.py`
- **Features**:
  - Classify page types (title/TOC/data, option lists, finish symbols, footnotes)
  - Regex + density analysis (lines/rects detection)
  - Route to optimal extractor (pdfplumber vs Camelot lattice/stream)
  - OCR fallback when extract_text < threshold

#### 1.2 Table Heuristics Enhancement
- **Header welding**: Multi-row headers → single logical row
- **Merged cells recovery**: Propagate header/row labels downward/rightward
- **Cross-page table stitching**: Match column fingerprints + header continuity
- **Rotated text handling**: Detect rotation, normalize via PyMuPDF angle
- **Units/currency normalizer**: USD symbol, comma/decimal variants

#### 1.3 "Net Add" & Rule Extraction Hardening
- Harden regex for option blocks (CTW/EPT/EMS/TIPIT/HT/FR3) with tolerant spacing
- Capture constraints (handing/material/voltage notes) as structured JSON
- Hager finish symbols: ensure US→BHMA mapping + "use price of X" rules parsed into `rules.rule_json`

#### 1.4 OCR Fallback System
- **Trigger**: When page text length < N or table detection returns empty
- **Process**: Render via pdf2image → Tesseract → post-process (whitespace, columns by projection)
- **Confidence routing**: Prefer native text; only OCR rows with medium/low initial confidence

#### 1.5 Enhanced Confidence & Provenance
- Keep 4-level confidence; add per-column confidence
- Store extraction path (lattice/stream/plumber/ocr), bbox, page
- Comprehensive provenance tracking

#### 1.6 Golden Fixtures Testing
- Add edge pages to `/tests/fixtures`: merged headers, rotated tables, cross-page, scanned samples
- Property tests for currency/number parsing
- Regression tests for SELECT/Hager sections that previously failed

**Commits**:
- `feat(parser): page classifier + routed extraction`
- `feat(parser): header welding, merged-cell recovery, cross-page stitching`
- `feat(parser): OCR fallback with thresholds`
- `test(parser): golden + property tests`

### Phase 2: Diff Engine v2 (Day 3)
**Goal**: Better matching, rename detection, rules/option diffs, human review.

#### 2.1 Advanced Matching Strategy
- **Block strategy**: `{manufacturer, family}`
- **Key strategy**: Normalized `{model_code, size_attr, finish}`
- **RapidFuzz fallback**: Near-renames (CTW-4 ↔ CTW4) with threshold
- **Clustering**: Pick highest score candidates
- **Option matching**: By `{code, label}` with fuzzy backup

#### 2.2 Comprehensive Delta Types
- **Price deltas**: Percentage/absolute, currency changes
- **Option changes**: Add/remove/amount change; constraints diffs
- **Finish rule diffs**: e.g., US10B → US10A mapping changed
- **Lifecycle**: New/retired items

#### 2.3 Confidence & Review System
- Score each match; flag < threshold for review queue
- `change_log`: add confidence, reason, match_key, old_ref, new_ref
- Human review workflow

#### 2.4 Admin API/UI
- `/admin/diff/{old_book}/{new_book}` with filters: added/removed/changed/low-confidence
- "Apply" writes versioning and stamps reviewer+timestamp
- Review queue management

**Commits**:
- `feat(diff): v2 matching + rename detection`
- `feat(diff): option/rule diffing + confidence`
- `feat(admin): diff review UI with approve/apply`
- `test(diff): synthetic delta suite`

### Phase 3: Exception Handling & Reliability (Day 4)
**Goal**: Predictable failures, retries, and observability.

#### 3.1 Error Taxonomy
- **Exception Types**: ParseError, OcrError, TableShapeError, RuleExtractError, DiffMatchError, BaserowError, ExportError
- **HTTP Mapping**: Map to 4xx/5xx codes in API
- **Structured hierarchy**: Clear inheritance and error codes

#### 3.2 Retries & Timeouts
- **Tenacity integration**: max_retries=3, exponential backoff + jitter
- **Per-page timeout guards**: Cancel long OCR tasks
- **Circuit breaker**: For Baserow/network failures
- **Graceful degradation**: Fallback strategies

#### 3.3 Structured Logging & Alerts
- **JSON logs**: file, page, extractor, error_code, doc_id
- **Sentry hook**: If key provided for error tracking
- **Prometheus metrics**: Log error metrics for monitoring
- **Alert thresholds**: Define critical failure rates

#### 3.4 Comprehensive Testing
- **Force exceptions**: Bad page, empty OCR, network mock errors
- **Verify fallbacks**: Ensure user-visible messages are clear
- **Failure-path coverage**: Test all error scenarios

**Commits**:
- `feat(core): exception hierarchy + handlers`
- `chore(obs): structured logs + metrics`
- `test(core): failure-path coverage`

### Phase 4: Baserow ↔ Postgres Integration (Day 5)
**Goal**: One-way publish to Baserow (idempotent), plus status reporting.

#### 4.1 Schema Mapping
- **Baserow tables**: Items, ItemPrices, Options, ItemOptions, Rules, ChangeLog
- **Unique keys**: Stable natural key (manufacturer|family|model|finish|size)
- **Hash storage**: Store key hash in dedicated field for upserts
- **Field mapping**: Complete schema translation

#### 4.2 Baserow Client & Upsert
- **File**: `integrations/baserow_client.py`
- **Functions**:
  - `get_or_create_table()`
  - `ensure_fields()`
  - `upsert_rows(table_id, rows, key_field="natural_key_hash", chunk=200)`
- **Features**: Pagination, rate-limit handling, exponential backoff on 429/5xx

#### 4.3 Publish Service
- **File**: `services/publish_baserow.py`
- **Process**: Read normalized tables for price_book_id → map to Baserow rows → upsert
- **Tracking**: Record sync summary to DB (`baserow_syncs`: status, counts, errors)
- **Idempotency**: Ensure safe re-runs

#### 4.4 CLI & Admin Interface
- **CLI**: `scripts/publish_baserow.py --book <id>`
- **Admin**: "Publish to Baserow" button with job status
- **Monitoring**: Real-time sync progress and error reporting

**Commits**:
- `feat(integrations): baserow client + upsert`
- `feat(services): publish to baserow`
- `feat(admin): publish button + status`
- `test(integrations): baserow mocks`

### Phase 5: Docker & Compose (Day 6)
**Goal**: Reproducible dev/prod runtime.

#### 5.1 Multi-Service Dockerfiles
- **Dockerfile.api**: FastAPI/HTMX app
- **Dockerfile.worker**: Parsing worker with Tesseract + poppler
- **Base dependencies**: tesseract-ocr, poppler-utils, ghostscript, libgl1, libxml2
- **Optimization**: Slim base images, layer caching

#### 5.2 Docker Compose Stack
- **Services**: api, worker, db (Postgres), redis, minio (if used), optional baserow (local)
- **Configuration**: Healthchecks and depends_on
- **Volumes**: Mount /data for PDFs
- **Networking**: Internal service discovery

#### 5.3 Make Targets
- `make build`: Build all images
- `make up`: Start stack
- `make logs`: View logs
- `make down`: Stop and cleanup
- **Development workflow**: Hot reloading support

**Commits**:
- `chore(docker): api/worker images + compose`
- `docs: docker quickstart`

### Phase 6: CI/CD Pipeline (Day 6)
**Goal**: Lint → type → test → build → scan → package.

#### 6.1 GitHub Actions Pipeline
- **Job 1**: Python matrix (3.11/3.12) - ruff, black-check, mypy --strict, pytest with Testcontainers Postgres
- **Job 2**: Build Docker images with layer caching
- **Job 3**: SBOM + vulnerability scan (Syft/Trivy) → fail on critical vulnerabilities
- **Job 4**: Push to GHCR/Docker Hub on tags
- **Artifact**: Coverage report upload

#### 6.2 Security & Secrets
- **Secrets**: DOCKERHUB_USERNAME, DOCKERHUB_TOKEN (or GHCR PAT)
- **Optional**: SENTRY_DSN for error tracking
- **Security scanning**: Automated vulnerability checks
- **SBOM generation**: Software Bill of Materials

**Commits**:
- `.github/workflows/ci.yml` (updated)
- `ci: enable docker build + scan`

### Phase 7: Documentation & Final Handover (Day 7)
**Goal**: Clear ops/dev docs + demo assets.

#### 7.1 Complete Documentation Structure
- **docs/README.md**: Overview, scope, architecture
- **docs/INSTALL.md**: Local & Docker installation
- **docs/PARSERS.md**: Selectors, heuristics, OCR thresholds, adding new section/manufacturer
- **docs/DIFF.md**: Matching rules, thresholds, review flow
- **docs/DATA_DICTIONARY.md**: Tables/fields reference
- **docs/OPERATIONS.md**: Runbook - backups, migrations, troubleshooting
- **docs/BASEROW.md**: Schema mapping, upsert keys, limits

#### 7.2 Acceptance Bundle
- **ERD**: Exported PNG/SVG database diagram
- **Sample exports**: CSV/XLSX/JSON examples
- **Change log**: From synthetic update (+5% test)
- **Demo**: Screen-capture (upload → preview → diff → apply → export → publish to Baserow)

**Commits**:
- `docs: full handover set`
- `chore: demo script + fixtures`

### Phase 8: Final Acceptance & Quality Gates

#### 8.1 Acceptance Criteria Checklist
- [ ] **Parser hardening**: Edge cases pass; golden tests green; OCR fallback exercised; accuracy ≥ targets
- [ ] **Diff v2**: Correct rename mapping, price/option/rule deltas; low-confidence queue; approve/apply works
- [ ] **Exceptions**: Clear error codes/messages; retries/backoff; structured logs; failure tests pass
- [ ] **Baserow sync**: Idempotent upsert; mapping documented; publish job resumable; status recorded
- [ ] **Docker**: `docker compose up` brings full stack; healthchecks pass
- [ ] **CI**: Lint/type/test OK; images build; SBOM & scans clean (no criticals)
- [ ] **Docs**: Complete runbook and data dictionary; demo provided

#### 8.2 Final Validation
- End-to-end test with real PDF files
- Performance benchmarking
- Security review
- Documentation review
- Demo preparation

## Daily Working Cadence

| Day | Focus | Deliverables |
|-----|--------|-------------|
| **Day 1-2** | Parser hardening | Classifier, header welds, merged cells, cross-page, OCR + tests |
| **Day 3** | Diff v2 | Matching/rename + option/rule diffs + tests |
| **Day 4** | Exception handling | Hierarchy, retries/timeouts, structured logging + tests |
| **Day 5** | Baserow integration | Client + publish service + admin button + tests |
| **Day 6** | Docker & CI | Dockerfiles/compose + CI updates + docs draft |
| **Day 7** | Documentation & handover | Polish, acceptance run, handover bundle |

## Success Metrics

- **Parser Accuracy**: ≥95% precision/recall on golden test suite
- **Test Coverage**: Maintain 100% test passage (expand to 100+ tests)
- **Performance**: Process 500-page PDF in <2 minutes
- **Reliability**: <1% unhandled exceptions in production scenarios
- **Documentation**: Complete runbook enabling independent operation
- **Docker**: One-command stack startup (`docker compose up`)
- **CI**: <5 minute build pipeline with security scanning

## Risk Mitigation

- **OCR Complexity**: Start with simple Tesseract, iterate based on results
- **Baserow API Limits**: Implement chunking and rate limiting from start
- **Docker Complexity**: Use proven patterns, test locally first
- **Timeline Risk**: Prioritize core functionality over polish features

---

**Branch Strategy**: Continue on `alex-feature` → merge to `main` upon completion
**Communication**: Daily progress updates with specific deliverables
**Quality Gates**: Each phase must pass tests before proceeding to next