# MILESTONE 2 GATE CHECK - Current Status

## A) Parser Hardening: ⬜⬜⬜⬜⬜ 0/5 (0%)
- [ ] Edge-page coverage tests
- [ ] OCR fallback routing
- [ ] Header welding & merged-cell recovery
- [ ] Cross-page stitching
- [ ] M1 regression tests passing

## B) Diff Engine v2: ⬜⬜⬜⬜ 0/4 (0%)
- [ ] Rename detection with RapidFuzz
- [ ] Delta coverage (price/options/finishes)
- [ ] Confidence & review queue
- [ ] Idempotent apply + dry-run

## C) Exception Handling: ⬜⬜⬜⬜ 0/4 (0%)
- [ ] Error taxonomy wired
- [ ] Retries & timeouts (Tenacity)
- [ ] Structured JSON logging
- [ ] Health/ready endpoints

## D) Baserow Integration: ⬜⬜⬜⬜ 0/4 (0%)
- [ ] Natural key mapping documented
- [ ] Idempotent upsert logic
- [ ] Rate-limit handling (429/5xx)
- [ ] Admin UI button + audit table

## E) Docker/Compose: ⬜⬜⬜ 0/3 (0%)
- [ ] Dockerfile.api + Dockerfile.worker
- [ ] docker-compose.yml stack
- [ ] In-container parse succeeds

## F) CI/CD Pipeline: ⬜⬜⬜ 0/3 (0%)
- [ ] GitHub Actions (lint/test/type)
- [ ] Docker build + SBOM/vuln scan
- [ ] Tag & changelog automation

## G) Documentation: ⬜⬜⬜⬜⬜⬜ 0/6 (0%)
- [ ] docs/README.md, INSTALL.md
- [ ] docs/PARSERS.md, DIFF.md
- [ ] docs/BASEROW.md, OPERATIONS.md
- [ ] ERD + data dictionary
- [ ] Sample exports + demo
- [ ] Screencast

## H) Performance: ⬜⬜⬜ 1/3 (33%)
- [x] SELECT parses ≤ 2 min ✓
- [ ] Hager parses ≤ 2 min (currently 3+ min timeout)
- [ ] Accuracy ≥ 98%, low-confidence < 3%

## I) Security: ⬜⬜⬜ 0/3 (0%)
- [ ] Secrets via .env
- [ ] Upload MIME validation
- [ ] CORS + dependency audit

---

## OVERALL M2 STATUS: 1/35 requirements = 3% complete

### Priority Order (based on dependencies):
1. **C) Exception Handling** (foundation for everything)
2. **A) Parser Hardening** (needed for quality)
3. **B) Diff Engine v2** (core feature)
4. **D) Baserow Integration** (integration)
5. **E) Docker** (deployment)
6. **F) CI/CD** (automation)
7. **I) Security** (production-ready)
8. **G) Documentation** (handover)
9. **H) Performance** (optimization)

### Estimated Timeline:
- **Week 1**: C, A, B (Foundation + Core Features)
- **Week 2**: D, E, I (Integration + Infrastructure)
- **Week 3**: F, G, H (Automation + Documentation)

**RECOMMENDATION**: Begin with Exception Handling (C) as it's foundational.
