# MILESTONE 2 - TODO LIST
**Status**: M1 ✅ 100% Complete | M2 🟡 78% → Target 100%
**Timeline**: 4-6 days

---

## 🎯 CRITICAL PATH (Required for M2 Completion)

### ⭐ TASK 1: FIX BASEROW INTEGRATION (18% of M2)
**Priority**: HIGHEST | **Effort**: 1.5-2 days | **Tests Failing**: 12

#### Subtasks:
- [ ] **Fix StructuredLogger Signature Error**
  - Location: `core/observability.py`
  - Issue: `_create_log_entry()` parameter conflict
  - Action: Review signature, fix all call sites in Baserow code
  - Time: 2-3 hours

- [ ] **Add Natural Key Hash Generation**
  - Issue: Missing `natural_key_hash` field in Baserow records
  - Action: Create hash function `hash(manufacturer + model + finish)`
  - Files: `integrations/baserow_publisher.py`
  - Time: 2-3 hours

- [ ] **Fix Async/Await Issues**
  - Location: `integrations/baserow_client.py`
  - Issue: Coroutine iterator errors
  - Action: Fix async method patterns, ensure proper `await`
  - Time: 3-4 hours

- [ ] **Integration Testing**
  - Run: `pytest tests/test_baserow*.py -v`
  - Verify dry-run mode works
  - Test circuit breaker functionality
  - Time: 4-6 hours

**Success Criteria**:
- ✅ All 12 Baserow tests passing
- ✅ StructuredLogger calls work without errors
- ✅ Natural key hash generated for all records
- ✅ Circuit breaker functional

---

### ⭐ TASK 2: TUNE DIFF ENGINE V2 (9% of M2)
**Priority**: HIGH | **Effort**: 1 day | **Tests Failing**: 5

#### Subtasks:
- [ ] **Analyze Fuzzy Matching Failures**
  - Run: `pytest tests/test_diff_engine_v2.py::test_fuzzy_matching_renames -vv`
  - Review actual scores vs expected
  - Check current threshold value (likely 70)
  - Time: 2-3 hours

- [ ] **Tune Fuzzy Thresholds**
  - Location: `core/diff_engine_v2.py`
  - Experiment with values: 65, 70, 75
  - Test rename scenarios:
    - "BB1168" → "BB-1168"
    - "1168 Series" → "1168-Series"
    - "Hager BB1168" → "BB1168 Hager"
  - Time: 3-4 hours

- [ ] **Fix Rule Change Counting**
  - Test: `test_rule_changes`
  - Issue: Counts off by 1-2
  - Action: Debug counting logic, fix off-by-one errors
  - Time: 2-3 hours

**Success Criteria**:
- ✅ Fuzzy rename detection working for common patterns
- ✅ At least 2/5 fuzzy tests passing
- ✅ Rule change counts accurate
- ✅ Review queue filtering correct

---

### 📝 TASK 3: UPDATE TEST SUITE (5% of M2)
**Priority**: MEDIUM | **Effort**: 1 day | **Current**: 166/200 passing

#### Category A: Parser Tests (7 failures)
- [ ] **Update Product Count Expectations**
  - Tests: `test_extract_model_tables_from_dataframe`, `test_parse_with_products`
  - Change: 252 → 99 products (strict validation removes invalid finishes)
  - Files: `tests/test_select_parser.py`
  - Time: 1-2 hours

- [ ] **Update Finish Code Validation**
  - Change assertions to expect only valid codes: CL, BR, BK, WE
  - Remove expectations for invalid codes: V1, V4, V8
  - Time: 1-2 hours

#### Category B: Parser Hardening (8 failures)
- [ ] **Triage Edge Cases**
  - Assess each failure: < 2 hours to fix?
  - Critical business impact?
  - If NO to both: Document and skip
  - Time: 2-3 hours

- [ ] **Create KNOWN_LIMITATIONS.md**
  - Document OCR edge cases
  - Document multi-row header limitations
  - Document price normalization edge cases
  - Time: 1 hour

#### Category C: Exception Handling (3 failures)
- [ ] **Fix Retry Test**
  - Test: `test_retry_max_attempts_exceeded`
  - Check tenacity configuration
  - Time: 1 hour

- [ ] **Fix Performance Tracker**
  - Test: `test_performance_tracker`
  - Verify metrics collection
  - Time: 1 hour

- [ ] **Fix Timeout Scenario**
  - Ensure timeout mechanism works
  - Verify proper cleanup
  - Time: 1 hour

**Success Criteria**:
- ✅ Parser tests aligned with strict validation
- ✅ Test pass rate ≥90% (180/200 tests)
- ✅ Edge cases documented
- ✅ Exception handling tests passing (3/3)

---

## 🔧 OPTIONAL TASKS (If Time Permits)

### Task 4: Docker/CI Validation (9% of M2)
**Priority**: LOW | **Effort**: 0.5-1 day

- [ ] Test Docker build on Linux/Mac
- [ ] Verify `ci.yml` workflow
- [ ] Verify `security.yml` workflow
- [ ] Document Windows Docker limitations
- [ ] Remove or fix `performance.yml`

### Task 5: Final Exception Handling Polish (4.5% of M2)
**Priority**: LOW | **Effort**: 0.5 day

- [ ] Final retry mechanism testing
- [ ] Performance tracker edge cases
- [ ] Timeout scenario edge cases

### Task 6: Parser Hardening Edge Cases (3% of M2)
**Priority**: VERY LOW | **Effort**: 0.5 day

- [ ] OCR trigger improvements (only if < 2 hours)
- [ ] Multi-row header welding (only if < 2 hours)
- [ ] Otherwise: SKIP and document

---

## 📅 RECOMMENDED SCHEDULE

### **4-Day Fast Track** (Target: 95% M2 Completion)

**Day 1: Baserow Integration Part 1**
- Morning: Fix StructuredLogger signature (3 hours)
- Afternoon: Add natural key hash generation (3 hours)
- Evening: Start async/await fixes (2 hours)

**Day 2: Baserow Integration Part 2**
- Morning: Finish async/await fixes (3 hours)
- Afternoon: Integration testing (4 hours)
- Evening: Verify all 12 Baserow tests pass (1 hour)

**Day 3: Diff Engine v2 Tuning**
- Morning: Analyze failures (3 hours)
- Afternoon: Tune fuzzy thresholds (3 hours)
- Evening: Fix rule counting (2 hours)

**Day 4: Test Suite Updates**
- Morning: Update parser expectations (3 hours)
- Afternoon: Fix exception handling tests (3 hours)
- Evening: Document limitations (2 hours)

**Result**: M2 at **95%+** (all critical features complete)

---

### **6-Day Thorough Track** (Target: 100% M2 Completion)

Follow 4-day track, then add:

**Day 5: Docker/CI + Exception Polish**
- Morning: Docker validation (3 hours)
- Afternoon: CI workflow testing (3 hours)
- Evening: Final exception handling (2 hours)

**Day 6: Final Integration & Documentation**
- Morning: End-to-end integration testing (3 hours)
- Afternoon: Final documentation updates (3 hours)
- Evening: Code review and cleanup (2 hours)

**Result**: M2 at **100%** (everything polished)

---

## 📊 PROGRESS TRACKING

### Current Status (M2 78% Complete)
```
✅ Core Functionality     [████████████░░░░░░░░] 65%
🟡 Baserow Integration   [███████████░░░░░░░░░] 60% → Need 18%
🟡 Diff Engine v2        [███████████████░░░░░] 82% → Need 9%
✅ Exception Handling    [█████████████████░░░] 85%
🟡 Parser Hardening      [█████████████████░░░] 90% → Need 3%
⚠️  Docker/CI            [░░░░░░░░░░░░░░░░░░░░] 0% → Need 9%
🟡 Test Coverage         [████████████████░░░░] 82.5% → Need 5%
```

### Completion Targets
- **Minimum Viable (95%)**: Complete Tasks 1-3
- **Fully Polished (100%)**: Complete Tasks 1-6

---

## 🚀 GET STARTED

### Option A: Start with Baserow ⭐ RECOMMENDED
**Why**: Biggest impact (18%), critical integration feature
```bash
# Step 1: Run tests to see current failures
pytest tests/test_baserow*.py -v

# Step 2: Read the observability module
cat core/observability.py | grep -A 20 "_create_log_entry"

# Step 3: Start fixing
# Follow Task 1 subtasks above
```

### Option B: Quick Win with Tests
**Why**: Fast progress, boosts metrics quickly
```bash
# Step 1: Update parser test expectations
pytest tests/test_select_parser.py -v

# Step 2: Fix the 7 easy parser tests
# Update counts: 252 → 99 products
# Update finish codes: remove V1, V4, V8
```

### Option C: Diff Engine First
**Why**: Pure algorithm work, no external dependencies
```bash
# Step 1: Analyze fuzzy matching
pytest tests/test_diff_engine_v2.py::test_fuzzy_matching_renames -vv

# Step 2: Tune thresholds
# Experiment with values in core/diff_engine_v2.py
```

---

## 📋 COMPLETION CHECKLIST

### Critical (Required for 95%):
- [ ] Baserow: StructuredLogger fixed
- [ ] Baserow: Natural key hash added
- [ ] Baserow: Async/await working
- [ ] Baserow: 12 tests passing
- [ ] Diff v2: Fuzzy thresholds tuned
- [ ] Diff v2: 5 tests passing
- [ ] Tests: Parser expectations updated
- [ ] Tests: 90%+ pass rate (180/200)

### Optional (For 100%):
- [ ] Docker: Build tested
- [ ] Docker: CI workflows validated
- [ ] Exception: 3 remaining tests fixed
- [ ] Parser: Edge cases documented

---

## 🎯 SUCCESS METRICS

**M2 at 95%** (Minimum Viable):
- ✅ Baserow integration working
- ✅ Diff engine v2 tuned
- ✅ 90%+ test pass rate
- ✅ Core features production-ready

**M2 at 100%** (Fully Polished):
- All above PLUS:
- ✅ Docker/CI validated
- ✅ All exception handling tests pass
- ✅ Edge cases documented
- ✅ Performance optimized

---

**Ready to start?** Pick an option above and let's knock out M2! 🚀
