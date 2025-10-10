# Data Quality Improvements - Clean Output Strategy

## Current Issues (Based on Sample Output)

### Problem Examples:
1. **Broken SKUs**: "400K-X Keyblanks (Priced per 100/sold in box of 50)" - SKU includes description
2. **Missing Model**: Most rows show "N/A" for Model column
3. **Duplicate/Fragmented Data**:
   - "per 100" as separate SKU
   - "Lock-6" as separate SKU
   - "of 10" as separate SKU
4. **No Effective Date**: All rows show "N/A"
5. **Messy Descriptions**: Mixed with prices and units
6. **Price Parsing Issues**: "$3 8.79" should be "$38.79"

---

## Root Cause Analysis

### Issue 1: Table Structure Misdetection
- Parser treating multi-line cells as separate rows
- Column boundaries incorrectly identified
- Header row not properly detected

### Issue 2: SKU Pattern Too Permissive
- Extracting partial text as SKUs
- Not filtering out descriptions/units
- Pattern: `r"\b([A-Z]{2,}[\s-]?\d{1,}[A-Z\d]*)\b"` matches "Lock-6", "per 100"

### Issue 3: Description Extraction Failing
- Not properly identifying description column
- Mixing description with SKU/price data

---

## Solution Strategy

### Phase 1: Improve Table Detection (HIGH PRIORITY)

#### 1.1 Header Detection Enhancement
```python
def _detect_header_row(self, df: pd.DataFrame) -> int:
    """
    Enhanced header detection with multi-line support.

    Returns row index that is the true header.
    """
    header_keywords = ['sku', 'model', 'description', 'price', 'list', 'item', 'part']

    for idx in range(min(5, len(df))):
        row_text = ' '.join(str(cell).lower() for cell in df.iloc[idx]).strip()

        # Count keyword matches
        matches = sum(1 for kw in header_keywords if kw in row_text)

        if matches >= 3:  # At least 3 header keywords
            return idx

    return 0  # Default to first row
```

#### 1.2 Multi-line Cell Merging
```python
def _merge_multiline_cells(self, df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge cells that span multiple rows (common in PDF tables).

    Heuristic: If row has mostly empty cells except 1-2, merge with previous row.
    """
    merged_rows = []
    buffer_row = None

    for idx, row in df.iterrows():
        non_empty = sum(1 for cell in row if pd.notna(cell) and str(cell).strip())

        # If row has very few cells (1-2), it's likely a continuation
        if non_empty <= 2 and buffer_row is not None:
            # Merge with buffer
            for col_idx in range(len(row)):
                if pd.notna(row.iloc[col_idx]) and str(row.iloc[col_idx]).strip():
                    buffer_row[col_idx] += ' ' + str(row.iloc[col_idx])
        else:
            # Save buffer if exists
            if buffer_row is not None:
                merged_rows.append(buffer_row)

            # Start new buffer
            buffer_row = row.tolist()

    # Don't forget last row
    if buffer_row is not None:
        merged_rows.append(buffer_row)

    return pd.DataFrame(merged_rows, columns=df.columns)
```

---

### Phase 2: Stricter SKU Validation (MEDIUM PRIORITY)

#### 2.1 Enhanced SKU Pattern Validation
```python
def _is_valid_sku(self, sku: str) -> bool:
    """
    Strict SKU validation to filter out fragments.

    Valid SKU must:
    - Be 3-20 characters long
    - Have alphanumeric mix (letters + numbers)
    - NOT be common keywords (per, of, to, etc.)
    - NOT be all uppercase generic words
    """
    if not sku or len(sku) < 3 or len(sku) > 20:
        return False

    # Blacklist of invalid SKUs (fragments)
    blacklist = [
        'per', 'of', 'to', 'lock', 'pin', 'sold', 'bag', 'box',
        'uncombinated', 'housing', 'cams', 'cores', 'n/a', 'na'
    ]

    if sku.lower() in blacklist:
        return False

    # Must have alphanumeric mix
    has_letter = any(c.isalpha() for c in sku)
    has_number = any(c.isdigit() for c in sku)

    if not (has_letter and has_number):
        return False

    # Valid SKU patterns (manufacturer-specific)
    valid_patterns = [
        r'^[A-Z]{2,4}[-\s]?\d{3,}',      # AB-1234, ABC1234
        r'^\d{3,6}[A-Z]{1,3}$',           # 12345AB, 1234A
        r'^[A-Z]\d{3,}[A-Z]{0,2}$',       # A1234, A1234B
        r'^[A-Z]{2,}\d+[-A-Z]*$',         # ABC123-X
    ]

    for pattern in valid_patterns:
        if re.match(pattern, sku, re.IGNORECASE):
            return True

    return False
```

#### 2.2 Price Cleaning
```python
def _clean_price(self, price_str: str) -> Optional[float]:
    """
    Clean price strings with spaces/formatting issues.

    Examples:
    - "$3 8.79" -> 38.79
    - "$ 192.00" -> 192.00
    - "5." -> 5.00
    """
    if not price_str:
        return None

    # Remove all spaces from price
    cleaned = re.sub(r'\s+', '', str(price_str))

    # Extract numbers (with decimal)
    match = re.search(r'(\d+\.?\d*)', cleaned)
    if match:
        try:
            price = float(match.group(1))
            if 0.01 <= price <= 100000:
                return price
        except ValueError:
            pass

    return None
```

---

### Phase 3: Post-Processing Cleanup (LOW PRIORITY)

#### 3.1 Remove Invalid Rows
```python
def _filter_invalid_products(self, products: List[Dict]) -> List[Dict]:
    """
    Remove products that are clearly invalid (fragments, noise).
    """
    valid_products = []

    for product in products:
        sku = product.get('sku', '')
        price = product.get('base_price', 0)
        description = product.get('description', '')

        # Rule 1: Must have valid SKU
        if not self._is_valid_sku(sku):
            logger.debug(f"Filtered invalid SKU: {sku}")
            continue

        # Rule 2: Must have realistic price
        if not price or price < 0.10 or price > 50000:
            logger.debug(f"Filtered invalid price: {sku} - ${price}")
            continue

        # Rule 3: Description should not be just numbers/symbols
        if description and len(description) > 2:
            if not any(c.isalpha() for c in description):
                logger.debug(f"Filtered invalid description: {sku}")
                continue

        valid_products.append(product)

    return valid_products
```

#### 3.2 Effective Date Extraction Enhancement
```python
def _extract_effective_date_comprehensive(self, pdf_path: str) -> Optional[str]:
    """
    Extract effective date from PDF using multiple strategies.

    Strategy:
    1. Check first 3 pages for "Effective" keyword
    2. Look in headers/footers
    3. Check filename for date pattern
    """
    import pdfplumber
    from datetime import datetime

    date_patterns = [
        r'Effective(?:\s+Date)?:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',  # Effective: December 1, 2024
        r'Effective:?\s*(\d{1,2}/\d{1,2}/\d{2,4})',                     # Effective: 12/01/2024
        r'Valid\s+from:?\s*(\d{1,2}-[A-Za-z]+-\d{4})',                  # Valid from: 01-Dec-2024
        r'Price\s+List:?\s*([A-Za-z]+\s+\d{4})',                        # Price List: December 2024
        r'(\d{1,2}/\d{1,2}/\d{4})\s+(?:effective|valid)',               # 12/01/2024 effective
    ]

    with pdfplumber.open(pdf_path) as pdf:
        # Check first 3 pages
        for page in pdf.pages[:3]:
            text = page.extract_text() or ""

            for pattern in date_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    date_str = match.group(1).strip()
                    logger.info(f"Found effective date: {date_str}")
                    return date_str

    # Fallback: Check filename
    filename = os.path.basename(pdf_path)
    filename_date = re.search(r'(\d{4})', filename)
    if filename_date:
        year = filename_date.group(1)
        logger.info(f"Using year from filename: {year}")
        return f"January 1, {year}"  # Default to start of year

    return None
```

---

## Implementation Priority

### Week 1: Critical Fixes
1. ✅ **Multi-line cell merging** - Fixes fragmented rows
2. ✅ **Stricter SKU validation** - Removes "per 100", "Lock-6" noise
3. ✅ **Price cleaning** - Fixes "$3 8.79" → "$38.79"

### Week 2: Quality Improvements
4. ✅ **Header detection enhancement** - Better column identification
5. ✅ **Post-processing filters** - Remove invalid products
6. ✅ **Effective date extraction** - Multi-strategy search

### Week 3: Testing & Validation
7. ✅ Test on all 130 sample PDFs
8. ✅ Measure improvement (before/after accuracy)
9. ✅ Update confidence scoring

---

## Expected Results

### Before (Current Output):
```
27 products extracted
- 15 invalid SKUs ("per 100", "Lock-6", "of 10")
- 12 valid products
- Accuracy: ~44%
- No effective date
```

### After (With Improvements):
```
12-15 products extracted
- All valid SKUs (400K-X, 20XSPL-X-XXX, etc.)
- Accuracy: 85-95%
- Clean descriptions
- Effective date extracted
```

---

## Code Files to Modify

1. **`parsers/universal/pattern_extractor.py`**
   - Add `_merge_multiline_cells()`
   - Add `_is_valid_sku()`
   - Add `_clean_price()`
   - Add `_filter_invalid_products()`

2. **`parsers/universal/parser.py`**
   - Add `_extract_effective_date_comprehensive()`
   - Call cleanup methods before returning results

3. **`parsers/universal/img2table_detector.py`**
   - Improve `_detect_header()`
   - Add cell merging logic

---

## Testing Script

```python
# scripts/test_data_quality.py
from parsers.universal import UniversalParser

pdf_path = "test_data/pdfs/problematic-pdf.pdf"

# Before cleanup
parser_old = UniversalParser(pdf_path, config={"use_cleanup": False})
results_old = parser_old.parse()

# After cleanup
parser_new = UniversalParser(pdf_path, config={"use_cleanup": True})
results_new = parser_new.parse()

print(f"Before: {len(results_old['products'])} products")
print(f"After: {len(results_new['products'])} products")
print(f"Improvement: {len(results_new['products']) - len(results_old['products'])} products")

# Show quality comparison
valid_old = sum(1 for p in results_old['products'] if len(p['sku']) >= 4 and p['base_price'] > 0)
valid_new = sum(1 for p in results_new['products'] if len(p['sku']) >= 4 and p['base_price'] > 0)

print(f"Valid products - Before: {valid_old}, After: {valid_new}")
```

---

## Success Criteria

✅ **SKU Quality**: No fragments like "per 100", "of 10"
✅ **Price Accuracy**: All prices properly formatted (no "$3 8.79")
✅ **Description Clarity**: Clean, readable descriptions
✅ **Effective Date**: Extracted on 80%+ of PDFs
✅ **Overall Accuracy**: 85-95% on test PDFs

---

**Next Step**: Implement Phase 1 (multi-line merging + SKU validation) and test on sample PDF
