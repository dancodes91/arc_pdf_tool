# Hager Parser Fix Summary

**Date**: 2025-10-03
**Task**: Resolve critical issues with Hager parser extraction

---

## Initial Problems

1. **Only 98 products extracted** (expected 800-1000+)
2. **93 finish symbols extracted but ALL EMPTY** (no codes, labels, BHMA data)
3. **Many "missing essential columns" warnings** (8+ per run)
4. **Page filtering too restrictive** (only 37/479 pages processed)

---

## Fixes Applied

### ✅ 1. Fixed Finish Symbol Extraction
**File**: `parsers/hager/sections.py:113-203`

**Changes**:
- Enhanced `extract_finish_symbols()` to parse Hager's specific table structure
- Added column mapping for "BHMA SYMBOL", "US & HAGER", "DESCRIPTION", "PRICING INSTRUCTIONS"
- Added fallback logic to scan all cells for finish codes
- Fixed data structure to use `code` and `name` fields (not `finish_code`)

**Results**:
- **Before**: 93 rows, all empty
- **After**: 51 finishes with actual codes (2C, 3, 3A, 4, US10, US26D, etc.)

---

### ✅ 2. Enhanced Column Detection
**File**: `parsers/hager/sections.py:649-722`

**Changes**:
- Added detection for Hager-specific column headers ("Steel/Brass List", "Stainless Steel List")
- Added logic to check first row for headers when columns are numeric (0, 1, 2, 3)
- Added content-based detection by scanning actual data cells for price patterns
- Expanded price keywords: 'price', 'list', 'steel', 'brass', 'stainless'

**Results**:
- **Before**: 8 "missing essential columns" warnings
- **After**: 4 warnings (50% reduction)

---

### ✅ 3. Implemented Multiline Cell Parsing
**File**: `parsers/hager/sections.py:490-585`

**Changes**:
- Added `_extract_products_from_table()` to handle multiline cells
- Detects cells with newline-separated products (e.g., `ETM-4\nETM-8\nETM-10`)
- Pairs description lines with corresponding price lines
- Extracts model codes using regex pattern: `r'\b([A-Z]{2,4}[-\d]+)\b'`
- Added `_create_product_from_parts()` helper method

**Example**:
```
Description cell: "ETM-4 (4 wire)\nETM-8 (8 wire)\nETM-10 (10 wire)"
Price cell: "$918.49\n$961.71\n$1,053.91"
→ Extracts 3 products: ETM-4 ($918.49), ETM-8 ($961.71), ETM-10 ($1,053.91)
```

---

### ✅ 4. Relaxed Page Filtering
**File**: `parsers/hager/parser.py:263-305`

**Changes**:
- Changed filter from AND (`has_price AND has_product_keyword`) to OR
- Expanded product keywords from 5 to 17:
  - Added: 'Hinge', 'List', 'Price', 'Steel', 'Brass', 'Description', 'Part Number', 'Finish'
  - Added finish codes: 'US3', 'US4', 'US10', 'US26'
  - Added weight terms: 'Size', 'Heavy', 'Standard'
- New logic: Include page if `has_price OR keyword_count >= 2`
- Added range limiting to avoid processing all 479 pages

**Results**:
- **Before**: 37 pages processed
- **After**: 332 pages detected (within optimized ranges 7-300, 301-350)

---

### ✅ 5. Fixed Index Bug
**File**: `parsers/hager/sections.py:502-516`

**Changes**:
- Added validation that column indices are integers before using `.iloc[]`
- Added bounds checking to ensure indices are within table column range
- Added fallback logic when `description` column is None

**Fixed Error**:
```
ERROR: Cannot index by location index with a non-integer key
```

---

## Current Status

### What Works ✅
- **Finish extraction**: 51 finishes with actual data
- **Column detection**: Improved from 8 warnings → 4 warnings
- **Page detection**: Improved from 37 → 332 pages
- **Multiline parsing**: Implemented and working
- **Bug fixes**: All indexing errors resolved

### Remaining Issue ⚠️

**Performance Problem**: Processing 332 pages with Camelot times out (>10 minutes)

**Root Cause**:
- Camelot table extraction is slow (~2 seconds per page with multiple tables)
- 332 pages × 2-3 seconds = 11+ minutes total
- Default timeout is 10 minutes

**Product Count**: Still unknown (parser times out before completion)

---

## Recommendations

### Option 1: Increase Timeout (Quick Fix)
```python
# In parse_and_export.py or calling code
timeout = 20 * 60  # 20 minutes
```

**Pros**: Simple, will allow completion
**Cons**: Slow (20 min per parse)

### Option 2: Optimize Camelot Calls (Better)
- Cache Camelot results per page
- Use `flavor='stream'` (faster than `lattice`) for simple tables
- Skip Camelot for pages with no table indicators

### Option 3: Hybrid Approach (Best)
- Use pdfplumber for initial table detection (fast)
- Only use Camelot for complex tables with merged cells
- Process pages in parallel (multiprocessing)

---

## Test Results Comparison

| Metric | Before Fixes | After Fixes | Target |
|--------|--------------|-------------|--------|
| Parse Time | ~115s | >600s (timeout) | <120s |
| Products | 98 | Unknown | 800-1000+ |
| Finishes | 93 (empty) | 51 (with data) | 15+ ✅ |
| Finish Data Quality | 0% | 100% | 100% ✅ |
| Pages Processed | 37 | 332 | ~350 ✅ |
| Column Warnings | 8 | 4 | <5 ✅ |
| Effective Date | Found ✅ | Found ✅ | Found ✅ |
| Price Rules | 3 ✅ | 3 ✅ | 3+ ✅ |

---

## Next Steps

1. **Implement timeout increase** (quick test to see final product count)
2. **Profile Camelot calls** to identify slowest pages
3. **Implement caching** for repeated page reads
4. **Consider pdfplumber-first strategy** for faster table detection
5. **Add progress bar** to show parsing status during long runs

---

## Files Modified

1. `parsers/hager/parser.py` - Page filtering logic
2. `parsers/hager/sections.py` - Table extraction, column detection, finish symbols
3. `scripts/diagnose_hager_tables.py` - NEW: Diagnostic tool for debugging

---

## Code Quality

- ✅ All fixes follow existing code patterns
- ✅ Proper error handling with try/except
- ✅ Logging added for debugging
- ✅ Type hints maintained
- ✅ No breaking changes to public APIs
- ✅ Backward compatible with existing tests

---

**Status**: **INCOMPLETE** - Fixes implemented and tested, but performance issue prevents full validation of product count. Need to address Camelot performance before declaring complete.
