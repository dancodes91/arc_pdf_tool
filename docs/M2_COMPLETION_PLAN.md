# MILESTONE 2 - COMPLETION PLAN
## Path from 78% → 100%

**Created**: 2025-10-02
**Status**: M1 now 100% ✅ | M2 at 78% → Target 100%
**Timeline**: 4-6 days total effort

---

## EXECUTIVE SUMMARY

**Current M2 Status**: 78% Complete
**Gap to 100%**: 22% remaining work

**3 Critical Tasks**:
1. ⭐ **Baserow Integration Fixes** (18% gap) - 1.5-2 days
2. ⭐ **Diff Engine v2 Tuning** (9% gap) - 1 day
3. **Test Suite Updates** (5% gap) - 1 day

**Optional Tasks**:
4. Docker/CI Validation (9% gap) - 0.5-1 day
5. Exception Handling Polish (4.5% gap) - 0.5 day
6. Parser Hardening Edge Cases (3% gap) - 0.5 day

---

## PRIORITY ORDERING

### **Week 1: Critical Path** (Required for 100%)

**Day 1-2: Baserow Integration** ⭐ HIGHEST PRIORITY
- Fix StructuredLogger signature errors
- Add natural key hash generation
- Fix async/await issues
- Get 12 tests passing

**Day 3: Diff Engine v2 Tuning** ⭐ HIGH PRIORITY
- Calibrate fuzzy matching thresholds
- Fix rename detection (5 test failures)
- Fix rule change counting

**Day 4: Test Suite Updates**
- Update parser test expectations for strict validation
- Document edge cases
- Get pass rate to 90%+ (180/200)

### **Week 2: Polish** (Nice-to-Have)

**Day 5 (Optional): Docker/CI + Exception Handling**
- Validate Docker builds
- Fix 3 exception handling tests
- Document any limitations

**Day 6 (Optional): Final Polish**
- Address parser hardening edge cases (if time)
- Integration testing
- Final documentation

---

## TASK 1: FIX BASEROW INTEGRATION ⭐

**Priority**: HIGHEST (18% of M2)
**Effort**: 1.5-2 days
**Status**: Framework exists, 12 tests failing

### Issues to Fix

#### Issue 1: StructuredLogger Signature Error ⚠️
```
Error: _create_log_entry() got multiple values for argument 'message'
Location: core/observability.py
```

**Root Cause**: Method signature conflict in logging calls
**Fix**:
1. Review `core/observability.py:_create_log_entry()` signature
2. Check all call sites in Baserow integration
3. Ensure consistent parameter passing (positional vs keyword)

#### Issue 2: Natural Key Hash Missing ⚠️
```
Error: Missing required field 'natural_key_hash'
Location: Baserow publisher logic
```

**Root Cause**: Natural key hash not generated during publish
**Fix**:
1. Add hash generation function: `hash(manufacturer + model + finish)`
2. Integrate into BaserowPublisher
3. Update all Baserow record creation to include hash
4. Add validation in tests

#### Issue 3: Async/Await Issues ⚠️
```
Error: 'coroutine' object is not iterable
Location: integrations/baserow_client.py
```

**Root Cause**: Incorrect async/await patterns
**Fix**:
1. Review `baserow_client.py` async methods
2. Ensure proper `await` on coroutines
3. Fix generator/iterator issues
4. Test with mock Baserow instance

### Implementation Plan

#### Phase 1: StructuredLogger (2-3 hours)
```python
# Steps:
1. Read core/observability.py:_create_log_entry()
2. Identify parameter signature
3. Search for all Baserow integration call sites
4. Fix parameter passing (use kwargs consistently)
5. Run Baserow tests to verify
```

#### Phase 2: Natural Key Hash (2-3 hours)
```python
# Steps:
1. Create hash generation utility:
   def generate_natural_key_hash(manufacturer, model, finish):
       import hashlib
       key = f"{manufacturer}:{model}:{finish}"
       return hashlib.sha256(key.encode()).hexdigest()[:16]

2. Add to BaserowPublisher.publish_products()
3. Update BaserowPublisher.publish_finishes()
4. Update BaserowPublisher.publish_options()
5. Add tests for hash generation
```

#### Phase 3: Async/Await (3-4 hours)
```python
# Steps:
1. Review integrations/baserow_client.py
2. Fix async method patterns:
   - Ensure all async methods use 'async def'
   - Ensure all calls use 'await'
   - Fix any generator comprehensions
3. Test with asyncio.run() in tests
4. Verify circuit breaker works with async
```

#### Phase 4: Integration Testing (4-6 hours)
```bash
# Steps:
1. Run full Baserow test suite:
   pytest tests/test_baserow*.py -v

2. Fix any remaining failures one by one

3. Test dry-run mode:
   - Verify no actual API calls in dry-run
   - Check logging output

4. Test circuit breaker:
   - Verify it opens on failures
   - Verify it closes after recovery

5. Document Baserow setup requirements
```

### Acceptance Criteria
- [ ] All 12 Baserow tests passing
- [ ] StructuredLogger calls work without errors
- [ ] Natural key hash generated for all records
- [ ] Async/await patterns correct
- [ ] Can publish to Baserow (dry-run mode works)
- [ ] Circuit breaker functional
- [ ] Documentation updated

### Files to Modify
- `core/observability.py` - Fix logger signature
- `integrations/baserow_client.py` - Fix async patterns
- `integrations/baserow_publisher.py` - Add natural key hash
- `tests/test_baserow*.py` - Verify fixes

---

## TASK 2: TUNE DIFF ENGINE V2 ⭐

**Priority**: HIGH (9% of M2)
**Effort**: 1 day
**Status**: Core works, 5 tests failing on fuzzy matching

### Issues to Fix

#### Issue 1: Fuzzy Rename Detection (5 failures)
```
Tests failing:
- test_fuzzy_matching_renames
- test_synthetic_rename_scenario
- test_fuzzy_threshold_calibration (possibly)
```

**Root Cause**: Threshold too strict or scoring logic off
**Current Threshold**: 70 (likely in config or hardcoded)

#### Issue 2: Rule Change Detection
```
Symptom: Counts off by 1-2
Test: test_rule_changes
```

**Root Cause**: Counting logic doesn't match test expectations

### Implementation Plan

#### Morning: Analyze Failures (2-3 hours)
```bash
# Steps:
1. Run specific failing tests with verbose output:
   pytest tests/test_diff_engine_v2.py::test_fuzzy_matching_renames -vv

2. Review test expectations vs actual results

3. Check fuzzy_threshold value in:
   - core/diff_engine_v2.py
   - config.py
   - Test fixtures

4. Analyze RapidFuzz scoring behavior:
   - Print actual scores for failing cases
   - Understand why renames not detected

5. Identify if issue is threshold or logic
```

#### Afternoon: Tune Thresholds (3-4 hours)
```python
# Steps:
1. Experiment with threshold values:
   - Try 65 (more lenient)
   - Try 75 (more strict)
   - Try adaptive threshold based on string length

2. Test with real rename scenarios:
   - "BB1168" → "BB-1168" (formatting change)
   - "1168 Series" → "1168-Series" (punctuation)
   - "Hager BB1168" → "BB1168 Hager" (word order)

3. If logic is correct but tests wrong:
   - Update test expectations
   - Document the behavior
   - Get stakeholder approval

4. Add logging to show fuzzy match scores during diff
```

#### Evening: Fix Rule Changes (2-3 hours)
```python
# Steps:
1. Review test_rule_changes test expectations

2. Debug rule counting logic in diff_engine_v2.py:
   - Count how many rules added
   - Count how many rules removed
   - Count how many rules modified

3. Fix off-by-one errors (common in counting logic)

4. Validate with sample data from tests

5. Update test if counting is actually correct
```

### Acceptance Criteria
- [ ] Fuzzy rename detection working for common patterns
- [ ] At least 2/5 fuzzy tests passing
- [ ] Rule change counts accurate (or tests updated)
- [ ] Review queue filtering works correctly
- [ ] Summary generation matches expectations
- [ ] All 5 diff v2 tests passing (or documented why not)

### Files to Modify
- `core/diff_engine_v2.py` - Adjust thresholds, fix counting
- `tests/test_diff_engine_v2.py` - Update expectations if needed
- `config.py` - Add fuzzy_threshold config if missing

---

## TASK 3: UPDATE TEST SUITE EXPECTATIONS

**Priority**: MEDIUM (5% of M2)
**Effort**: 1 day
**Status**: 165/200 passing (82.5%), 35 failures expected from stricter validation

### Categories of Failures

#### Category A: Parser Tests (7 failures) - EXPECTED ✅
```
Issue: Tests expect products with invalid finish codes (V1, V4, V8)
Cause: New strict validation correctly rejects these
Action: Update test expectations to match new behavior
```

**Tests to Update**:
- `test_extract_model_tables_from_dataframe`
- `test_extract_net_add_options`
- `test_parse_with_products`

**Fix Strategy**:
```python
# OLD expectation:
assert len(products) == 252  # Includes invalid finishes

# NEW expectation:
assert len(products) == 99   # Only valid finishes (CL, BR, BK)
assert all(p.finish_code in ['CL', 'BR', 'BK', 'WE'] for p in products)
```

#### Category B: Parser Hardening (8 failures) - EDGE CASES
```
Issue: OCR and table processing edge cases
Status: Not critical for core functionality
Action: Document as known limitations OR fix if simple
```

**Tests Affected**:
- OCR trigger scenarios
- Multi-row header welding
- Price normalization edge cases

**Fix Strategy**:
```python
# Option 1: Mark as known limitations
@pytest.mark.skip(reason="Known limitation: OCR edge case")

# Option 2: Fix if simple (only if < 2 hours effort)
```

#### Category C: Exception Handling (3 failures) - MINOR
```
Issue: Retry mechanism and performance tracking
Tests: test_retry_max_attempts_exceeded, test_performance_tracker
Action: Fix minor issues
```

### Implementation Plan

#### Morning: Update Parser Tests (3-4 hours)
```python
# Steps:
1. Review each failing parser test

2. Update expected product counts:
   - Change from 252 to 99 (SELECT)
   - Verify finish code validation

3. Update assertions:
   # OLD
   assert 'V1' in finish_codes

   # NEW (if valid codes only)
   assert 'V1' not in finish_codes
   assert all_valid_finish_codes(finish_codes)

4. Run tests and verify they pass

5. Document the stricter validation behavior
```

#### Afternoon: Triage Edge Cases (3-4 hours)
```python
# Steps:
1. Review 8 parser_hardening failures

2. For each failure:
   a. Assess complexity to fix (< 2 hours? fix it)
   b. Assess business impact (critical? fix it)
   c. Otherwise: document and skip

3. Create KNOWN_LIMITATIONS.md documenting edge cases

4. Mark non-critical tests with @pytest.mark.known_limitation
```

#### Evening: Fix Exception Handling (2 hours)
```python
# Steps:
1. Fix test_retry_max_attempts_exceeded:
   - Check tenacity configuration
   - Ensure proper exception raising

2. Fix test_performance_tracker:
   - Verify metrics collection
   - Check histogram/gauge recording

3. Fix timeout scenario test:
   - Ensure timeout mechanism works
   - Verify proper cleanup
```

### Acceptance Criteria
- [ ] Parser tests aligned with strict validation
- [ ] Test pass rate ≥90% (180/200)
- [ ] Edge cases documented in KNOWN_LIMITATIONS.md
- [ ] Exception handling tests passing (3/3)
- [ ] Test documentation updated
- [ ] Known limitations communicated to stakeholders

### Files to Modify
- `tests/test_parser*.py` - Update expectations
- `tests/test_exception_handling.py` - Fix 3 failures
- `KNOWN_LIMITATIONS.md` - Document edge cases (NEW FILE)

---

## OPTIONAL TASKS (If Time Permits)

### Task 4: Validate Docker/CI (0.5-1 day)
**Impact**: 9% of M2
**Priority**: LOW (not blocking production use)

```bash
# Quick wins:
1. Test Docker build on Linux/Mac (if accessible)
2. Verify ci.yml and security.yml work
3. Document Windows Docker limitations
4. Remove or refactor performance.yml
```

### Task 5: Polish Exception Handling (0.5 day)
**Impact**: 4.5% of M2
**Priority**: LOW (already 85% complete)

```python
# Quick fixes:
1. Fix retry test (1 hour)
2. Fix performance tracker (1 hour)
3. Fix timeout scenario (1 hour)
```

### Task 6: Parser Hardening Edge Cases (0.5 day)
**Impact**: 3% of M2
**Priority**: VERY LOW (90% already done)

```python
# Only if very simple:
1. OCR trigger improvements (if < 2 hours)
2. Multi-row header welding (if < 2 hours)
3. Otherwise: SKIP and document
```

---

## TIMELINE & MILESTONES

### **Fast Track** (4 days to 95%+)
```
Day 1:     Baserow Integration (Part 1)
           - Fix StructuredLogger
           - Add natural key hash

Day 2:     Baserow Integration (Part 2)
           - Fix async/await
           - Integration testing
           - Get 12 tests passing ✅

Day 3:     Diff Engine v2 Tuning
           - Analyze failures
           - Tune thresholds
           - Fix rule counting
           - Get 5 tests passing ✅

Day 4:     Test Suite Updates
           - Update parser expectations
           - Fix exception handling
           - Document limitations
           - Get to 90% pass rate ✅

Result: M2 at 95%+ (all critical features complete)
```

### **Thorough Track** (6 days to 100%)
```
Day 1-2:   Baserow Integration ✅
Day 3:     Diff Engine v2 ✅
Day 4:     Test Suite Updates ✅
Day 5:     Docker/CI Validation + Exception Polish
Day 6:     Final integration testing + documentation

Result: M2 at 100% (everything polished)
```

---

## SUCCESS METRICS

### **M2 at 95% Complete** (Minimum Viable)
- ✅ Baserow integration working (12 tests passing)
- ✅ Diff engine v2 tuned (5 tests passing)
- ✅ Test pass rate ≥90% (180/200)
- ✅ Core features production-ready

### **M2 at 100% Complete** (Fully Polished)
- ✅ All above PLUS:
- ✅ Docker/CI validated
- ✅ Exception handling robust (all tests passing)
- ✅ Edge cases documented
- ✅ Performance workflow fixed or removed

---

## RISK MITIGATION

### Risk 1: Baserow Integration More Complex Than Expected
**Mitigation**:
- Allocate 2 full days instead of 1.5
- Focus on dry-run mode first (no real API calls)
- Document issues for async support from maintainers

### Risk 2: Fuzzy Matching Logic Fundamentally Wrong
**Mitigation**:
- Get stakeholder input on expected behavior
- Update test expectations if current logic is correct
- Document fuzzy matching algorithm clearly

### Risk 3: Test Failures Are Actual Bugs
**Mitigation**:
- Triage each failure individually
- Fix high-impact bugs, document low-impact ones
- Don't block M2 completion on edge cases

### Risk 4: Time Constraints
**Mitigation**:
- Prioritize: Baserow → Diff v2 → Tests
- Skip optional tasks if needed
- Accept 95% completion if 100% takes too long

---

## NEXT STEPS - START HERE

### **Immediate Action** (Choose One):

#### Option A: Start with Baserow ⭐ RECOMMENDED
```bash
# Why: Biggest impact (18%), critical feature
# Time: 1.5-2 days

1. Run Baserow tests to see current failures:
   pytest tests/test_baserow*.py -v

2. Read core/observability.py to understand StructuredLogger

3. Start fixing logger signature issues

4. Move to natural key hash generation
```

#### Option B: Quick Win with Tests
```bash
# Why: Fast progress, boosts metrics
# Time: 4-6 hours for easy wins

1. Update parser test expectations (7 tests)
2. Get pass rate from 82.5% to 86-87%
3. Build momentum before tackling Baserow
```

#### Option C: Diff Engine v2 First
```bash
# Why: Pure algorithm work, no dependencies
# Time: 1 day

1. Analyze fuzzy matching failures
2. Tune thresholds
3. Get 5 tests passing
4. Then tackle Baserow
```

---

## RESOURCE REQUIREMENTS

**Developer Time**: 4-6 days full-time
**External Dependencies**: None (all internal fixes)
**Testing Environment**: Local dev environment sufficient
**Stakeholder Review**: Needed for fuzzy matching behavior

---

## COMPLETION CHECKLIST

### Critical (Required for M2 95%+):
- [ ] Baserow: StructuredLogger fixed
- [ ] Baserow: Natural key hash added
- [ ] Baserow: Async/await working
- [ ] Baserow: 12 tests passing
- [ ] Diff v2: Fuzzy thresholds tuned
- [ ] Diff v2: 5 tests passing
- [ ] Tests: Parser expectations updated
- [ ] Tests: 90%+ pass rate (180/200)

### Optional (For M2 100%):
- [ ] Docker: Build tested on Linux/Mac
- [ ] Docker: ci.yml and security.yml validated
- [ ] Exception: 3 remaining tests fixed
- [ ] Parser: Edge cases documented

---

## ESTIMATED COMPLETION

**Conservative**: 6 days to 100%
**Realistic**: 5 days to 98%
**Aggressive**: 4 days to 95%

**Recommended Approach**: Target 4 days for 95%, then assess if final polish is worth the extra 1-2 days.

---

**Let's start with Task 1: Baserow Integration!** 🚀

Would you like to begin with:
1. Running Baserow tests to see failures?
2. Analyzing StructuredLogger signature?
3. Something else?
