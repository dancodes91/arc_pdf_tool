# PDF Analysis & Parser Enhancement Guide

## Problem: Low Product Extraction Count

This guide documents the exact steps used to diagnose and fix the Hager parser (98 → 778 products, 694% improvement) and can be applied to enhance the SELECT parser.

---

## Step 1: Analyze Current Parser Performance

### 1.1 Run Current Parser
```bash
python -c "
from parsers.select.parser import SelectParser
parser = SelectParser('test_data/pdfs/select-price-book.pdf')
result = parser.parse()
print(f'Products: {len(result[\"products\"])}')
"
```

**Expected**: Baseline product count (e.g., 150 products)

### 1.2 Identify the Gap
- Compare with expected catalog size (e.g., 800-1000 products)
- Calculate the gap (products missing)

---

## Step 2: Deep PDF Analysis - Find Missing Products

### 2.1 Create Comprehensive Page Analysis Script

Create `scripts/analyze_select_pages.py`:

```python
"""Analyze SELECT PDF to find all product pages."""
import pdfplumber
import json
import re

def analyze_all_pages(pdf_path: str):
    results = {
        'total_pages': 0,
        'pages_with_prices': [],
        'pages_with_models': [],
        'pages_with_tables': [],
        'page_details': {}
    }

    with pdfplumber.open(pdf_path) as pdf:
        results['total_pages'] = len(pdf.pages)

        for page_num in range(1, len(pdf.pages) + 1):
            page = pdf.pages[page_num - 1]
            text = page.extract_text() or ''
            tables = page.extract_tables()

            # Analyze indicators
            has_price = '$' in text
            has_model = bool(re.search(r'model_pattern_here', text))
            has_part_number = bool(re.search(r'part_number_pattern', text))
            table_count = len(tables)

            page_info = {
                'page': page_num,
                'has_price': has_price,
                'has_model': has_model,
                'has_part_number': has_part_number,
                'table_count': table_count,
                'text_length': len(text)
            }

            results['page_details'][page_num] = page_info

            if has_price:
                results['pages_with_prices'].append(page_num)
            if has_model:
                results['pages_with_models'].append(page_num)
            if table_count > 0:
                results['pages_with_tables'].append(page_num)

            if page_num % 50 == 0:
                print(f"Analyzed {page_num}/{results['total_pages']} pages...")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total pages: {results['total_pages']}")
    print(f"Pages with prices: {len(results['pages_with_prices'])}")
    print(f"Pages with models: {len(results['pages_with_models'])}")
    print(f"Pages with tables: {len(results['pages_with_tables'])}")

    # Pages with BOTH prices and models (likely product pages)
    product_pages = set(results['pages_with_prices']) & set(results['pages_with_models'])
    print(f"Pages with BOTH prices AND models: {len(product_pages)}")

    # Save results
    with open('select_page_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)

    return results

if __name__ == "__main__":
    pdf_path = "test_data/pdfs/select-price-book.pdf"
    results = analyze_all_pages(pdf_path)
```

**Run it**:
```bash
python scripts/analyze_select_pages.py
```

**Expected Output**: JSON file showing which pages have products

### 2.2 Sample Different Page Types

Create `scripts/sample_select_pages.py`:

```python
"""Sample different page types to understand table structures."""
import pdfplumber
import camelot
import re

def analyze_page_deep(pdf_path: str, page_num: int):
    print(f"\n{'='*80}")
    print(f"PAGE {page_num}")
    print(f"{'='*80}")

    # pdfplumber extraction
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num - 1]
        text = page.extract_text() or ''
        tables = page.extract_tables()

        print(f"Text length: {len(text)}")
        print(f"Tables found: {len(tables)}")

        # Show first 500 chars
        print(f"\nFirst 500 chars:")
        print(text[:500])

        # Show table structure
        if tables:
            for i, table in enumerate(tables):
                print(f"\nTable {i}: {len(table)} rows × {len(table[0]) if table else 0} cols")
                if len(table) > 0:
                    print(f"Headers: {table[0]}")
                if len(table) > 1:
                    print(f"Sample row: {table[1]}")

# Sample pages from analysis
pages_to_sample = [50, 100, 150, 200]  # Adjust based on analysis
for page in pages_to_sample:
    analyze_page_deep("test_data/pdfs/select-price-book.pdf", page)
```

**Run it**:
```bash
python scripts/sample_select_pages.py
```

---

## Step 3: Identify Table Format Patterns

### 3.1 Look for Different Table Formats

Based on Hager experience, look for:

1. **Standard row tables**:
   - Part Number | Description | Price

2. **Price matrix tables**:
   - Model header at top
   - Size column with multiple finishes per size
   - Example:
     ```
     MODEL123
     Size        Finish  Price
     3" x 3"     US3     $100
                 US4     $95
     4" x 4"     US3     $150
                 US4     $145
     ```

3. **Multiline cell tables**:
   - Single cell contains multiple products separated by newlines

### 3.2 Compare Text Extraction Methods

```python
import pdfplumber
import pymupdf

pdf_path = "test_data/pdfs/select-price-book.pdf"

# Method 1: pdfplumber
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[50]  # Sample page
    text_plumber = page.extract_text() or ''
    print(f"pdfplumber length: {len(text_plumber)}")
    print(text_plumber[:500])

# Method 2: PyMuPDF
doc = pymupdf.open(pdf_path)
page = doc[50]
text_pymupdf = page.get_text()
print(f"\nPyMuPDF length: {len(text_pymupdf)}")
print(text_pymupdf[:500])
```

**Key Question**: Does text extraction method affect how tables are parsed?

---

## Step 4: Implement Missing Format Parsers

### 4.1 Create Matrix Parser (if matrix format exists)

Create `parsers/select/matrix_parser.py`:

```python
"""Parser for SELECT price matrix format."""
import re
import logging
from typing import List, Dict, Any
from decimal import Decimal

from ..shared.provenance import ProvenanceTracker, ParsedItem

logger = logging.getLogger(__name__)

class SelectMatrixParser:
    """Parse SELECT price matrix tables."""

    def __init__(self, provenance_tracker: ProvenanceTracker):
        self.tracker = provenance_tracker

    def extract_matrix_products(self, page_text: str, page_number: int) -> List[ParsedItem]:
        """Extract products from a price matrix page."""
        self.tracker.set_context(section="Price Matrix", page_number=page_number)
        products = []

        # Step 1: Find model number (adjust pattern to SELECT format)
        model_match = re.search(r'\b(MODEL_PATTERN)\b', page_text)
        if not model_match:
            return products

        model = model_match.group(0)

        # Step 2: Extract description
        description = self._extract_description(page_text, model)

        # Step 3: Parse matrix entries
        matrix_entries = self._parse_matrix_entries(page_text)

        # Step 4: Generate products
        for entry in matrix_entries:
            size = entry.get('size')
            finish = entry.get('finish')
            price = entry.get('price')

            if not (size and finish and price):
                continue

            # Generate SKU
            size_code = self._normalize_size(size)
            sku = f"{model}-{size_code}-{finish}"

            product_data = {
                'sku': sku,
                'model': model,
                'description': f"{description} - {size}",
                'size': size,
                'finish': finish,
                'base_price': float(price),
                'specifications': {
                    'size': size,
                    'finish': finish
                },
                'manufacturer': 'select',
                'is_active': True
            }

            item = self.tracker.create_parsed_item(
                value=product_data,
                data_type="product",
                raw_text=f"{model} {size} {finish} ${price}",
                confidence=0.9
            )
            products.append(item)

        logger.info(f"Extracted {len(products)} products from matrix for {model}")
        return products

    def _parse_matrix_entries(self, text: str) -> List[Dict[str, Any]]:
        """Parse size/finish/price entries from matrix format."""
        entries = []
        lines = text.split('\n')

        current_size = None
        current_finish = None

        # Adjust patterns to SELECT format
        size_pattern = r'SIZE_PATTERN'
        finish_pattern = r'^\s*(FINISH_PATTERN)\s*$'
        price_pattern = r'^(\d+\.\d{2})$'

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 2:
                continue

            # Check for size
            size_match = re.search(size_pattern, line)
            if size_match:
                current_size = size_match.group(1).strip()
                logger.debug(f"Found size on line {line_num}: {current_size}")
                continue

            # Check for finish (on its own line - PyMuPDF format)
            finish_only_match = re.match(finish_pattern, line)
            if finish_only_match and current_size:
                current_finish = finish_only_match.group(1)
                logger.debug(f"Found finish on line {line_num}: {current_finish}")
                continue

            # Check for price (on its own line - PyMuPDF format)
            price_only_match = re.match(price_pattern, line)
            if price_only_match and current_size and current_finish:
                try:
                    price = Decimal(price_only_match.group(1))
                    entries.append({
                        'size': current_size,
                        'finish': current_finish,
                        'price': price
                    })
                    logger.debug(f"Extracted: {current_size} {current_finish} ${price}")
                    current_finish = None  # Reset for next entry
                except Exception as e:
                    logger.warning(f"Failed to parse price: {e}")
                continue

        logger.info(f"Parsed {len(entries)} matrix entries")
        return entries

    def _extract_description(self, text: str, model: str) -> str:
        """Extract product description from text."""
        # Customize to SELECT product types
        return f"{model} Product"

    def _normalize_size(self, size: str) -> str:
        """Normalize size for SKU generation."""
        # Customize to SELECT size formats
        return size.replace('"', '').replace(' ', '')

    def is_matrix_page(self, page_text: str) -> bool:
        """Detect if page contains a price matrix."""
        has_model = bool(re.search(r'MODEL_PATTERN', page_text))
        has_finishes = len(re.findall(r'FINISH_PATTERN', page_text)) >= 3
        has_prices = bool(re.search(r'\d+\.\d{2}', page_text))

        is_matrix = has_model and has_finishes and has_prices

        if is_matrix:
            logger.debug(f"Detected matrix page")

        return is_matrix
```

### 4.2 Integrate Matrix Parser into Main Parser

In `parsers/select/parser.py`:

```python
from .matrix_parser import SelectMatrixParser

class SelectParser:
    def __init__(self, pdf_path: str, config: Dict[str, Any] = None):
        # ... existing code ...
        self.matrix_parser = SelectMatrixParser(self.provenance_tracker)

    def _parse_item_tables(self):
        # ... existing code ...

        for page in pages_to_process:
            page_text = page.text or ''

            # Check if this is a price matrix page (NEW)
            if self.matrix_parser.is_matrix_page(page_text):
                matrix_products = self.matrix_parser.extract_matrix_products(
                    page_text, page.page_number
                )
                self.products.extend(matrix_products)
            else:
                # Regular table extraction (existing code)
                # ... existing table parsing logic ...
```

---

## Step 5: Test and Validate

### 5.1 Test Matrix Parser on Sample Page

```python
from parsers.select.matrix_parser import SelectMatrixParser
from parsers.shared.provenance import ProvenanceTracker
import pdfplumber

pdf_path = 'test_data/pdfs/select-price-book.pdf'
tracker = ProvenanceTracker(source_file=pdf_path)
parser = SelectMatrixParser(tracker)

# Test on page identified as matrix
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[50]  # Adjust page number
    text = page.extract_text() or ''

    is_matrix = parser.is_matrix_page(text)
    print(f'Is matrix: {is_matrix}')

    if is_matrix:
        products = parser.extract_matrix_products(text, 51)
        print(f'Products extracted: {len(products)}')

        for i, item in enumerate(products[:3]):
            p = item.value
            print(f'\nProduct {i+1}:')
            print(f'  SKU: {p["sku"]}')
            print(f'  Model: {p["model"]}')
            print(f'  Price: ${p["base_price"]:.2f}')
```

### 5.2 Run Full Parser and Compare

```bash
python -c "
from parsers.select.parser import SelectParser
import logging

logging.basicConfig(level=logging.INFO)

parser = SelectParser('test_data/pdfs/select-price-book.pdf')
result = parser.parse()

print(f'Total products: {len(result[\"products\"])}')
print(f'Improvement: {len(result[\"products\"]) / BASELINE_COUNT * 100 - 100:.1f}%')
"
```

---

## Step 6: Debug Common Issues

### 6.1 Matrix Detected but 0 Products Extracted

**Symptom**: `is_matrix_page()` returns True but `extract_matrix_products()` returns 0 products

**Debugging**:
```python
# Add debug logging to see what's matching
import logging
logging.getLogger('parsers.select.matrix_parser').setLevel(logging.DEBUG)

# Check what text is actually being parsed
print(f"Text length: {len(page_text)}")
print(f"First 500 chars: {page_text[:500]}")

# Test regex patterns individually
import re
size_pattern = r'YOUR_PATTERN'
sizes = re.findall(size_pattern, page_text)
print(f"Sizes found: {sizes}")
```

**Common Fixes**:
1. Text extraction method difference (PyMuPDF vs pdfplumber)
2. Special characters in patterns (curly quotes, em dashes)
3. Pattern too restrictive

### 6.2 PyMuPDF vs pdfplumber Format Differences

**Issue**: Parser works with pdfplumber but not with PyMuPDF text

**Solution**: Support both formats in `_parse_matrix_entries()`:
```python
# Check for finish on its own line (PyMuPDF)
finish_only_match = re.match(r'^\s*(US\d+)\s*$', line)

# Also check for finish with price on same line (pdfplumber)
finish_with_price_match = re.search(r'\b(US\d+)\b.*(\d+\.\d{2})', line)
```

### 6.3 Special Characters Not Matching

**Issue**: Regex patterns don't match because of special characters

**Examples**:
- Curly quotes: `"` (U+201C) and `"` (U+201D) instead of `"`
- Em dash: `—` instead of `-`
- Non-breaking space: ` ` (U+00A0) instead of regular space

**Fix**: Include special characters in patterns:
```python
# Instead of:
size_pattern = r'(\d+"\s*x\s*\d+")'

# Use:
size_pattern = r'(\d+[\"\u201c\u201d]?\s*[xX×]\s*\d+[\"\u201c\u201d]?)'
```

---

## Step 7: Commit and Document

### 7.1 Commit Changes

```bash
git add parsers/select/matrix_parser.py
git add parsers/select/parser.py
git add docs/SELECT_MATRIX_FORMAT.md

git commit -m "feat: Add price matrix parser for SELECT products

Implemented SelectMatrixParser to extract products from price matrix format:
- Handles matrix-style tables (model × size × finish)
- Supports both PyMuPDF and pdfplumber text formats
- Generates unique SKUs from model-size-finish combinations

Key improvements:
- Product count increased from XXX to YYY (ZZZ% improvement)
- Handles special characters (curly quotes, etc.)
- Processes N sizes × M finishes per model

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin your-branch
```

### 7.2 Document Format

Create `docs/SELECT_MATRIX_FORMAT.md`:

```markdown
# SELECT Price Matrix Format

## Discovery
[Document what you found in the PDF]

## Structure
[Show example of matrix format]

## Parsing Strategy
[Explain how the parser works]

## SKU Generation
[Show SKU format]

## Expected Product Count
[Document expected vs actual counts]
```

---

## Summary: Key Lessons from Hager Enhancement

1. **Deep analysis first**: Don't guess - analyze every page to find patterns
2. **Sample different formats**: PDFs often have multiple table structures
3. **Test extraction methods**: PyMuPDF vs pdfplumber can give different results
4. **Handle special characters**: Watch for curly quotes, em dashes, special spaces
5. **Stateful parsing**: Track context (current size, finish) across lines
6. **Debug incrementally**: Test regex patterns individually before full parser
7. **Validate consistency**: Run parser multiple times to ensure stable count

---

## Quick Reference: Hager Results

- **Baseline**: 98 products
- **After enhancement**: 778 products
- **Improvement**: 694%
- **Key insight**: Price matrix format was main product source (714/778 products)
- **Commits**:
  - e21bdea: Parallel extraction + multiline parsing
  - b8c153c: Matrix parser implementation
