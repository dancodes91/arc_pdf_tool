# MILESTONE 2 - TESTABLE ACCEPTANCE CHECKLIST

**Date Created**: 2025-10-03
**Branch**: alex-feature
**Current Status**: In Progress

---

## HOW TO USE THIS CHECKLIST

Run each command below and check the box if it passes. When **all boxes are ✅**, Milestone 2 is complete.

---

## A) Parser Hardening (Hager + SELECT)

### A1) Edge-page coverage ⬜
**Test golden tests for merged headers, cross-page tables, rotated text, scanned pages**

```bash
pytest -q tests/parsers -k "edge or rotated or scanned or cross_page"
```

- [ ] **PASS**: All edge case tests pass
- [ ] **Expected**: 10+ tests collected and passing
- **Current Status**: ❌ 0 tests collected - need to create edge case fixtures

---

### A2) OCR fallback ⬜
**Pages with near-zero embedded text route through OCR automatically**

```bash
pytest -q tests/ -k "ocr"
```

- [ ] **PASS**: All OCR tests pass
- [ ] **Confidence ≤ "Low"**: < 3% of rows
- [ ] **Logs**: Low-confidence rows logged for review
- **Current Status**: ⚠️ 3/5 tests passing - OCR returns empty strings

---

### A3) Header welding & merged-cell recovery ⬜
**Multi-row headers produce correct column names; no "Unnamed"/blank headers**

```bash
pytest -q tests/ -k "header"
```

- [ ] **PASS**: Header welding tests pass
- [ ] **Export check**: No "Unnamed" columns in Excel exports
- **Current Status**: ❌ 0/1 tests passing - header merging logic broken

---

### A4) Cross-page stitching ⬜
**Tables split across pages stitch into single logical table**

```bash
pytest -q tests/ -k "cross_page"
```

- [ ] **PASS**: Cross-page stitching tests pass
- [ ] **No duplicate headers**: Tables properly merged
- **Current Status**: ❌ Not implemented

---

### A5) No regressions ⬜
**M1 suites still green (SELECT/Hager core sections)**

```bash
pytest -q
```

- [ ] **PASS**: All tests pass (200/200)
- [ ] **Acceptable**: ≥ 190/200 (95%)
- **Current Status**: ⚠️ 166/200 passing (83%) - 34 failures

---

## B) Diff Engine v2 (rename detection + richer deltas)

### B1) Rename detection ⬜
**Synthetic test renaming 10-20% of models matches ≥ 95% correctly**

```bash
uv run python scripts/synthetic_diff_test.py --rename --pct 0.2
```

- [ ] **PASS**: ≥ 95% of renames detected correctly
- [ ] **Fuzzy matching**: RapidFuzz threshold tuned
- **Current Status**: ❌ Script missing (`scripts/synthetic_diff_test.py`)

---

### B2) Delta coverage ⬜
**Engine emits price delta, new/retired SKUs, option changes, finish-rule changes, currency changes**

```bash
pytest -q tests/test_diff_engine_v2.py
```

- [ ] **PASS**: All diff engine tests pass (17/17)
- [ ] **Deltas include**: abs/% price, new/retired, options, finishes, currency
- **Current Status**: ⚠️ 12/17 passing - fuzzy matching broken (0 matches)

---

### B3) Confidence & review ⬜
**Deltas include confidence + reason; low-confidence entries visible in UI**

```bash
pytest -q tests/test_diff_engine_v2.py -k "confidence"
```

- [ ] **PASS**: Confidence scoring tests pass
- [ ] **UI**: Review queue shows low-confidence entries
- **Current Status**: ✅ Confidence scoring implemented

---

### B4) Idempotent apply + dry-run ⬜
**--dry-run produces same diff as UI; applying twice makes no extra changes**

```bash
uv run python scripts/diff_apply.py --old <id> --new <id> --dry-run
uv run python scripts/diff_apply.py --old <id> --new <id> --apply
```

- [ ] **PASS**: Dry-run and apply produce consistent results
- [ ] **Idempotent**: 2nd run shows 0 changes
- **Current Status**: ❌ Script missing (`scripts/diff_apply.py`)

---

## C) Exception Handling & Reliability

### C1) Error taxonomy wired ⬜
**Custom exceptions raised and mapped to clean API errors (no raw tracebacks)**

```bash
pytest -q tests/test_exception_handling.py
```

- [ ] **PASS**: All exception handling tests pass (47/47)
- [ ] **Errors**: ParseError, OcrError, TableShapeError, RuleExtractError, DiffMatchError, BaserowError, ExportError
- **Current Status**: ⚠️ 44/47 passing - one Tenacity test failing

---

### C2) Retries & timeouts ⬜
**Tenacity backoff on parsing/HTTP; page-level timeout enforced; long OCR cancels safely**

```bash
pytest -q tests/test_exception_handling.py -k "retry or timeout"
```

- [ ] **PASS**: Retry/timeout tests pass
- [ ] **Observed**: Exponential backoff in logs
- **Current Status**: ⚠️ Tenacity decorators present but 1 test failing

---

### C3) Structured logs ⬜
**JSON logs include doc_id, page, extractor, error_code, latency_ms**

```bash
grep -E '"timestamp"|"level"|"message"' logs/*.log | head -5
```

- [ ] **PASS**: Logs are JSON formatted
- [ ] **Fields**: timestamp, level, message, logger_name, module, function
- [ ] **No unhandled exceptions**: During full book run
- **Current Status**: ✅ JSON logging operational

---

### C4) Health/ready endpoints ⬜
**/healthz returns 200; /readyz checks DB/queue and returns 200 when ready**

```bash
curl -s http://localhost:8000/healthz
curl -s http://localhost:8000/readyz
```

- [ ] **PASS**: `/healthz` returns 200 (always)
- [ ] **PASS**: `/readyz` returns 200 when DB connected
- **Current Status**: ❌ Endpoints missing from `app.py`

---

## D) Baserow ↔ Postgres Integration

### D1) Mapping documented ⬜
**Field mapping and stable natural key defined and documented**

```bash
cat docs/BASEROW.md | grep -i "natural key"
```

- [ ] **PASS**: Natural key strategy documented (e.g., `manufacturer|family|model|finish|size`)
- [ ] **PASS**: Field mapping table exists in docs
- **Current Status**: ⚠️ `docs/BASEROW.md` exists but natural key not documented

---

### D2) Idempotent upsert ⬜
**Re-publishing same price_book_id updates rows without dupes; 2nd run reports zero creates**

```bash
uv run python scripts/publish_baserow.py --book <id> --dry-run
uv run python scripts/publish_baserow.py --book <id>
# Run again:
uv run python scripts/publish_baserow.py --book <id>
```

- [ ] **PASS**: 1st run creates N rows
- [ ] **PASS**: 2nd run shows 0 creates, N updates
- **Current Status**: ❌ 12 Baserow tests failing - async/await bugs

---

### D3) Rate-limit safe ⬜
**429/5xx handled with exponential backoff; run completes; summary stored**

```bash
pytest -q tests/test_baserow_integration.py -k "rate_limit"
```

- [ ] **PASS**: Rate-limit tests pass
- [ ] **Backoff**: Exponential retry on 429/5xx
- [ ] **Audit**: Summary in `baserow_syncs` table
- **Current Status**: ⚠️ Circuit breaker tests failing

---

### D4) Admin button ⬜
**"Publish to Baserow" button exists, shows job status (created/updated/failed)**

- [ ] **PASS**: UI has "Publish to Baserow" button
- [ ] **PASS**: Status shows counts: created/updated/failed
- **Current Status**: ❓ Need to verify in frontend

---

## E) Docker/Compose (reproducible runtime)

### E1) Images build ⬜
**API and worker images build successfully with Tesseract/poppler present**

```bash
docker compose build
```

- [ ] **PASS**: All images build without errors
- [ ] **Tesseract**: `docker compose run api tesseract --version`
- [ ] **Poppler**: `docker compose run api pdfinfo --version`
- **Current Status**: ⚠️ Dockerfiles present, not tested

---

### E2) Stack runs ⬜
**docker compose up brings up api, worker, db, redis; health checks pass**

```bash
docker compose up -d
docker compose ps
curl -s http://localhost:8000/healthz
```

- [ ] **PASS**: All services running (api, worker, db, redis)
- [ ] **PASS**: Health checks pass
- **Current Status**: ⚠️ Requires `/healthz` endpoint (see C4)

---

### E3) In-container parse ⬜
**Full Hager/SELECT run succeeds inside containers; exports written**

```bash
docker compose exec api uv run python scripts/parse_and_export.py /data/2025-hager-price-book.pdf
```

- [ ] **PASS**: Parse completes without errors
- [ ] **PASS**: Exports written to mounted volume
- **Current Status**: ⚠️ Not tested

---

## F) CI/CD (GitHub Actions)

### F1) Pipeline green ⬜
**Lint (ruff), format check (black), type check (mypy --strict), tests (pytest) all pass**

- [ ] **PASS**: GitHub Actions CI workflow passes
- [ ] **Checks**: lint, format, type check, tests
- **Current Status**: ⚠️ Workflows present (`.github/workflows/ci.yml`), need to verify run

---

### F2) Image build & scan ⬜
**Docker images build in CI; SBOM + vuln scan show no critical vulns**

- [ ] **PASS**: CI builds Docker images
- [ ] **PASS**: Security scan (Trivy/Syft) shows 0 critical vulns
- [ ] **Artifacts**: Coverage/SBOM uploaded
- **Current Status**: ⚠️ Security workflow exists (`.github/workflows/security.yml`)

---

### F3) Tag & changelog ⬜
**Tagging release builds/pushes images (GHCR/Docker Hub) and posts changelog**

- [ ] **PASS**: Tagged release triggers image build
- [ ] **PASS**: Images pushed to registry
- [ ] **PASS**: Changelog notes posted
- **Current Status**: ⚠️ Workflow needs testing

---

## G) Documentation & Handover

### G1) Runbooks ⬜
**docs/INSTALL.md (local & Docker), docs/OPERATIONS.md (run, migrate, troubleshoot)**

```bash
ls -la docs/INSTALL.md docs/OPERATIONS.md
```

- [ ] **PASS**: `docs/INSTALL.md` exists and comprehensive
- [ ] **PASS**: `docs/OPERATIONS.md` exists with runbooks
- **Current Status**: ❌ Both missing

---

### G2) Parsers & Diff docs ⬜
**docs/PARSERS.md (heuristics, OCR thresholds), docs/DIFF.md (matching, thresholds, review flow)**

```bash
ls -la docs/PARSERS.md docs/DIFF.md
```

- [ ] **PASS**: `docs/PARSERS.md` documents parser architecture
- [ ] **PASS**: `docs/DIFF.md` documents diff engine
- **Current Status**: ⚠️ `docs/DIFF.md` exists (6KB), `docs/PARSERS.md` missing

---

### G3) Data dictionary & ERD ⬜
**docs/DATA_DICTIONARY.md and ERD (PNG/SVG) match actual schema**

```bash
ls -la docs/DATA_DICTIONARY.md docs/ERD.*
```

- [ ] **PASS**: `docs/DATA_DICTIONARY.md` exists
- [ ] **PASS**: ERD diagram (PNG/SVG) matches current schema
- **Current Status**: ❌ Both missing

---

### G4) Baserow guide ⬜
**docs/BASEROW.md with mapping, keys, idempotency notes, rate-limit behavior**

```bash
cat docs/BASEROW.md | wc -l
```

- [ ] **PASS**: `docs/BASEROW.md` is comprehensive (≥ 100 lines)
- [ ] **Sections**: Mapping, natural keys, idempotency, rate limits
- **Current Status**: ⚠️ Exists (5.5KB) but incomplete (see D1)

---

### G5) Demo bundle ⬜
**Sample exports, synthetic diff report (+5% test), screen-capture of upload → preview → diff → approve → publish**

```bash
ls -la demo/
```

- [ ] **PASS**: `demo/` folder exists
- [ ] **Files**: Sample exports, diff report, screen-capture video
- **Current Status**: ❌ Missing

---

## H) Performance & Accuracy (targets on real books)

### H1) Accuracy ⬜
**Rows extracted ≥ 98%, numeric accuracy ≥ 99%, option→rule mapping ≥ 95%**

```bash
uv run python scripts/measure_accuracy.py --book <id>
```

- [ ] **PASS**: Row extraction ≥ 98%
- [ ] **PASS**: Numeric accuracy ≥ 99%
- [ ] **PASS**: Option mapping ≥ 95%
- **Current Status**: ❌ No accuracy measurement script

---

### H2) Latency ⬜
**P75 parse time per 50-page PDF ≤ 2 minutes on dev box or container**

```bash
# SELECT (20 pages)
timeout 300 uv run python scripts/parse_and_export.py "test_data/pdfs/2025-select-hinges-price-book.pdf"

# Hager (50 pages sample)
timeout 300 uv run python scripts/parse_and_export.py "test_data/pdfs/hager-sample-50pages.pdf"
```

- [ ] **PASS**: SELECT parses in ≤ 2 min (currently: 43s ✅)
- [ ] **PASS**: Hager 50-page sample parses in ≤ 2 min
- **Current Status**: ⚠️ SELECT ✅, Hager times out (3+ min for full book)

---

### H3) Low-confidence rows ⬜
**< 3% low-confidence rows; visible in logs/review; explainable**

```bash
grep -i "low confidence" logs/*.log | wc -l
```

- [ ] **PASS**: < 3% of rows flagged low-confidence
- [ ] **Logs**: Low-confidence rows logged with reasons
- [ ] **UI**: Review queue highlights for manual check
- **Current Status**: ❓ Need to verify

---

## I) Security & Config

### I1) Secrets via env ⬜
**No secrets in code; .env.example updated; CORS allowlist includes frontend hosts**

```bash
grep -r "SECRET_KEY\|API_KEY\|TOKEN" *.py | grep -v ".env"
cat .env.example
grep -i "cors" app.py
```

- [ ] **PASS**: No hardcoded secrets in Python files
- [ ] **PASS**: `.env.example` has all required placeholders
- [ ] **PASS**: CORS configured for frontend hosts
- **Current Status**: ✅ `.env.example` exists, CORS configured

---

### I2) Upload guardrails ⬜
**MIME allow-list and size limits enforced; invalid inputs return 4xx with clear JSON error**

```bash
# Test invalid MIME type
curl -X POST -F "file=@test.txt" http://localhost:8000/api/upload

# Test oversized file (> 50MB)
curl -X POST -F "file=@huge.pdf" http://localhost:8000/api/upload
```

- [ ] **PASS**: Invalid MIME returns 415 with JSON error
- [ ] **PASS**: Oversized file returns 413 with JSON error
- **Current Status**: ⚠️ MIME checking exists in `api_routes.py`, not fully tested

---

### I3) Dependency hygiene ⬜
**Lock/constraints updated; CI scan shows no critical vulns**

```bash
uv pip list --outdated
npm audit --production  # for frontend
```

- [ ] **PASS**: Dependencies up-to-date
- [ ] **PASS**: Security scan shows 0 critical vulns
- **Current Status**: ⚠️ Need to run audit

---

## ONE-COMMAND SMOKE TESTS

### Local Quick Smoke ⬜

```bash
pytest -q && \
uv run python scripts/parse_and_export.py "test_data/pdfs/2025-select-hinges-price-book.pdf" && \
uv run python scripts/parse_and_export.py "test_data/pdfs/2025-hager-price-book.pdf" && \
uv run python scripts/synthetic_diff_test.py --rename --pct 0.2 && \
uv run python scripts/publish_baserow.py --book <new_book_id> --dry-run
```

- [ ] **PASS**: All commands succeed without errors

---

### Docker Quick Smoke ⬜

```bash
docker compose up -d --build && \
curl -s http://localhost:8000/healthz && \
docker compose exec api uv run python scripts/parse_and_export.py /data/2025-hager-price-book.pdf
```

- [ ] **PASS**: Stack builds, health check passes, parse succeeds

---

## MILESTONE 2 COMPLETION CRITERIA

**M2 is COMPLETE when ALL boxes above are ✅**

### Current Summary (as of 2025-10-03):

| Area | Status | Completion % | Critical Gaps |
|------|--------|--------------|---------------|
| A) Parser Hardening | ⬜⬜⬜⬜⬜ | 20% | Edge tests, OCR, header welding, cross-page |
| B) Diff Engine v2 | ⬜⬜⬜⬜ | 25% | Rename detection broken, scripts missing |
| C) Exception Handling | ⬜⬜⬜✅ | 75% | Health endpoints missing |
| D) Baserow Integration | ⬜⬜⬜⬜ | 25% | Upsert bugs, natural key docs |
| E) Docker/Compose | ⬜⬜⬜ | 33% | Build/run not tested |
| F) CI/CD | ⬜⬜⬜ | 33% | Pipeline runs not verified |
| G) Documentation | ⬜⬜⬜⬜⬜ | 20% | 4 of 6 docs missing |
| H) Performance | ⬜✅⬜ | 33% | Hager timeout, no accuracy metrics |
| I) Security | ✅⬜⬜ | 33% | Upload validation, dependency audit |

**Overall M2 Status**: ~35% complete (estimated)

---

## NEXT ACTIONS (Priority Order)

### CRITICAL (Week 1):
1. ✅ Add `/healthz` and `/readyz` endpoints (C4)
2. ✅ Fix fuzzy rename detection in diff engine (B2)
3. ✅ Create `scripts/synthetic_diff_test.py` (B1)
4. ✅ Create `scripts/diff_apply.py` (B4)
5. ✅ Optimize Hager parser for 2-min target (H2)

### HIGH (Week 2):
6. ✅ Fix Baserow upsert async bugs (D2)
7. ✅ Create edge case test fixtures (A1)
8. ✅ Fix header welding logic (A3)
9. ✅ Document natural key strategy (D1)
10. ✅ Create missing docs: INSTALL.md, PARSERS.md, OPERATIONS.md, DATA_DICTIONARY.md (G1-G3)

### MEDIUM (Week 3):
11. ✅ Implement cross-page stitching (A4)
12. ✅ Create accuracy measurement script (H1)
13. ✅ Test Docker build and run (E1-E3)
14. ✅ Create demo bundle (G5)
15. ✅ Fix remaining test failures (A5)

**Estimated Time to M2 Completion**: 3-4 weeks focused work

---

**Document Version**: 1.0
**Last Updated**: 2025-10-03
**Maintainer**: Project Team
