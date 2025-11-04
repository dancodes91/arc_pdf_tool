# Adding a New Manufacturer Parser

## Overview

Each manufacturer pricing book requires a **custom parser** due to unique formats, table structures, and product naming conventions.

**Effort Required**: 4-8 hours for similar formats, 1-3 days for completely different formats.

---

## Step-by-Step Process

### 1. Analyze the PDF (1-2 hours)

First, understand the structure of the new pricing book:

```bash
# Run analysis script
uv run python scripts/analyze_pdf_chunked.py "path/to/new-manufacturer.pdf"
```

**Questions to Answer**:
- How many pages?
- Where are pricing tables located?
- What's the table structure? (matrix, row-based, hybrid?)
- How are products identified? (model codes, SKUs, descriptions?)
- Are there finish codes, options, rules?
- What's the effective date format?

**Create**: `docs/{manufacturer}_pdf_analysis.md` with findings

---

### 2. Create Parser Directory Structure (15 mins)

```bash
mkdir -p parsers/{manufacturer_name}
touch parsers/{manufacturer_name}/__init__.py
touch parsers/{manufacturer_name}/parser.py
touch parsers/{manufacturer_name}/sections.py
```

**Example for "Acme Hinges"**:
```
parsers/
└── acme/
    ├── __init__.py
    ├── parser.py       # Main parser orchestration
    └── sections.py     # Section-specific extraction logic
```

---

### 3. Copy Template from Similar Parser (30 mins)

**If table-based like SELECT**, copy from SELECT:
```bash
cp parsers/select/parser.py parsers/acme/parser.py
cp parsers/select/sections.py parsers/acme/sections.py
```

**If matrix-based like Hager**, copy from Hager:
```bash
cp parsers/hager/parser.py parsers/acme/parser.py
cp parsers/hager/sections.py parsers/acme/sections.py
```

---

### 4. Update `__init__.py` (5 mins)

Edit `parsers/acme/__init__.py`:

```python
from .parser import AcmeParser

__all__ = ["AcmeParser"]
```

---

### 5. Customize `parser.py` (1-2 hours)

Edit `parsers/acme/parser.py`:

```python
"""
Enhanced Acme parser using shared utilities.
"""
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from ..shared.pdf_io import EnhancedPDFExtractor, PDFDocument
from ..shared.provenance import ProvenanceTracker, ParsedItem, ProvenanceAnalyzer
from .sections import AcmeSectionExtractor


logger = logging.getLogger(__name__)


class AcmeParser:
    """Enhanced Acme parser with comprehensive extraction capabilities."""

    def __init__(self, pdf_path: str, config: Dict[str, Any] = None):
        self.pdf_path = pdf_path
        self.config = config or {}
        self.logger = logging.getLogger(f"{__class__.__name__}")

        # Initialize utilities
        self.provenance_tracker = ProvenanceTracker(pdf_path)
        self.section_extractor = AcmeSectionExtractor(self.provenance_tracker)
        self.pdf_extractor = EnhancedPDFExtractor(pdf_path, config)

        # Parser results
        self.document: Optional[PDFDocument] = None
        self.effective_date: Optional[ParsedItem] = None
        self.products: List[ParsedItem] = []
        self.finishes: List[ParsedItem] = []
        self.options: List[ParsedItem] = []

    def parse(self) -> Dict[str, Any]:
        """Parse Acme PDF with comprehensive extraction."""
        self.logger.info(f"Starting Acme parsing: {self.pdf_path}")

        try:
            # Extract PDF document
            self.document = self.pdf_extractor.extract_document()
            self.logger.info(f"Extracted PDF with {len(self.document.pages)} pages")

            # Combine all text and tables
            full_text = self._combine_text_content()
            all_tables = self._combine_all_tables()

            # Parse sections (customize based on your analysis)
            self._parse_effective_date(full_text)
            self._parse_finishes(full_text)
            self._parse_options(full_text)
            self._parse_products(full_text, all_tables)

            # Build final results
            results = self._build_results()

            self.logger.info(f"Acme parsing completed: {self._get_summary()}")
            return results

        except Exception as e:
            self.logger.error(f"Error during Acme parsing: {e}")
            return self._build_error_results(str(e))

    # Add custom methods here based on your PDF structure
    # ... (see SELECT/Hager parsers for examples)

    def identify_manufacturer(self) -> str:
        """Identify manufacturer from PDF content."""
        # Look for Acme indicators in text
        text = self._combine_text_content().lower() if self.document else ""

        acme_indicators = ["acme", "acme hinges", "acme hardware"]
        for indicator in acme_indicators:
            if indicator in text:
                return "acme"

        return "acme"  # Default
```

---

### 6. Customize `sections.py` (2-4 hours)

This is the **most important** file - it contains the extraction logic specific to your manufacturer's format.

Edit `parsers/acme/sections.py`:

```python
"""
Acme-specific section extraction logic.

Customize these methods based on your PDF analysis.
"""
import re
from typing import List, Dict, Any, Optional
import pandas as pd

from ..shared.provenance import ProvenanceTracker, ParsedItem


class AcmeSectionExtractor:
    """Extracts sections from Acme pricing PDFs."""

    def __init__(self, provenance_tracker: ProvenanceTracker):
        self.provenance = provenance_tracker

    def extract_products(self, text: str, tables: List, page_num: int) -> List[ParsedItem]:
        """
        Extract products from Acme tables.

        CUSTOMIZE THIS based on your table structure!
        """
        products = []

        for table in tables:
            # Example: Acme uses a specific table header
            if self._is_product_table(table):
                products.extend(self._extract_from_product_table(table, page_num))

        return products

    def _is_product_table(self, table) -> bool:
        """Detect if table contains product data."""
        # CUSTOMIZE: Look for specific headers
        if isinstance(table, pd.DataFrame):
            headers = table.columns.tolist() if hasattr(table, 'columns') else []
            # Example: Acme tables have "Model", "Price", "Finish" columns
            required_headers = ["model", "price"]
            return any(header.lower() in str(headers).lower() for header in required_headers)
        return False

    def _extract_from_product_table(self, table, page_num: int) -> List[ParsedItem]:
        """Extract products from a product table."""
        products = []

        # CUSTOMIZE: Extract based on your table structure
        if isinstance(table, pd.DataFrame):
            for idx, row in table.iterrows():
                # Example extraction logic
                product_data = {
                    "sku": self._generate_sku(row),
                    "model": row.get("Model", ""),
                    "base_price": self._clean_price(row.get("Price", "")),
                    "finish": row.get("Finish", ""),
                    # Add more fields as needed
                }

                if product_data["sku"] and product_data["base_price"]:
                    products.append(
                        self.provenance.create_parsed_item(
                            value=product_data,
                            data_type="product",
                            raw_text=str(row.to_dict()),
                            page_number=page_num,
                            confidence=0.85,
                        )
                    )

        return products

    def _generate_sku(self, row) -> str:
        """Generate SKU based on Acme's naming convention."""
        # CUSTOMIZE: Acme's SKU format
        # Example: {MODEL}_{FINISH}_{SIZE}
        model = row.get("Model", "").strip()
        finish = row.get("Finish", "").strip()
        size = row.get("Size", "").strip()

        if model:
            parts = [model]
            if finish:
                parts.append(finish)
            if size:
                parts.append(size)
            return "_".join(parts)
        return ""

    def _clean_price(self, price_str) -> Optional[float]:
        """Clean price string to float."""
        if not price_str:
            return None

        # Remove currency symbols and commas
        cleaned = re.sub(r'[^\d.]', '', str(price_str))
        try:
            return float(cleaned)
        except ValueError:
            return None
```

**Key Customization Points**:
1. `_is_product_table()` - How to detect pricing tables
2. `_extract_from_product_table()` - How to parse rows
3. `_generate_sku()` - SKU format for this manufacturer
4. Add manufacturer-specific methods as needed

---

### 7. Register Parser in Main System (10 mins)

Edit `parsers/__init__.py`:

```python
try:
    from .hager.parser import HagerParser
    from .select.parser import SelectHingesParser
    from .acme.parser import AcmeParser  # ADD THIS

    __all__ = ["HagerParser", "SelectHingesParser", "AcmeParser"]  # ADD TO LIST

except ImportError as e:
    # Fallback logic...
```

---

### 8. Update Manufacturer Detection (15 mins)

Edit `app.py` or your main router to detect the new manufacturer:

```python
def detect_manufacturer(pdf_path: str) -> str:
    """Detect manufacturer from PDF content."""
    with pdfplumber.open(pdf_path) as pdf:
        first_page_text = pdf.pages[0].extract_text().lower()

        if "hager" in first_page_text:
            return "hager"
        elif "select" in first_page_text or "select hinges" in first_page_text:
            return "select_hinges"
        elif "acme" in first_page_text:  # ADD THIS
            return "acme"

        return "unknown"
```

---

### 9. Test the Parser (1-2 hours)

Create test file `tests/test_acme_parser.py`:

```python
import pytest
from parsers.acme.parser import AcmeParser

def test_acme_parser_initialization():
    """Test parser can be initialized."""
    parser = AcmeParser("test_data/pdfs/acme-sample.pdf")
    assert parser is not None

def test_acme_parser_extracts_products():
    """Test parser extracts products."""
    parser = AcmeParser("test_data/pdfs/acme-sample.pdf")
    results = parser.parse()

    assert results["manufacturer"] == "Acme"
    assert len(results["products"]) > 0
    assert results["summary"]["total_products"] > 0

# Add more tests...
```

Run tests:
```bash
uv run python -m pytest tests/test_acme_parser.py -v
```

---

### 10. Validate Results (30 mins)

Run the parser and check output:

```bash
uv run python scripts/parse_and_export.py "test_data/pdfs/acme-price-book.pdf"
```

**Check**:
- [ ] Products extracted correctly
- [ ] Prices are accurate
- [ ] SKUs match expected format
- [ ] Finishes/options captured
- [ ] Effective date found
- [ ] CSV exports are valid

---

## Common Customization Patterns

### Pattern 1: Matrix-Style Tables (like Hager)

If your manufacturer uses a matrix where:
- **Rows** = Models
- **Columns** = Finishes or Sizes
- **Cells** = Prices

Copy from `parsers/hager/matrix_parser.py` and adapt.

### Pattern 2: Row-Based Tables (like SELECT)

If your manufacturer uses rows where:
- Each row = One product variant
- Columns = Attributes (Model, Finish, Size, Price)

Copy from `parsers/select/sections.py` and adapt the `extract_model_tables()` method.

### Pattern 3: Hybrid (Matrix + Rows)

If tables vary by section:
- Detect table type first
- Route to appropriate extraction method
- Combine results

---

## Testing Checklist

Before declaring a new parser complete:

- [ ] Parses all pages without errors
- [ ] Extracts ≥90% of expected products
- [ ] SKU format is consistent
- [ ] Prices are accurate (spot check 10+ items)
- [ ] Effective date extracted correctly
- [ ] Finishes/options captured (if applicable)
- [ ] CSV exports match expected schema
- [ ] Parser tests pass
- [ ] No timeout issues (completes in <5 min for <100 pages)

---

## Troubleshooting

### Low Product Count

**Symptom**: Parser only extracts 10% of expected products

**Fixes**:
1. Check table detection logic in `_is_product_table()`
2. Verify regex patterns for model codes
3. Check if tables are being skipped due to filters
4. Add debug logging to see which pages are processed

### Wrong SKU Format

**Symptom**: SKUs don't match expected pattern

**Fix**: Update `_generate_sku()` method with correct format

### Missing Prices

**Symptom**: Products extracted but prices are null

**Fixes**:
1. Check `_clean_price()` regex patterns
2. Verify column names in `_extract_from_product_table()`
3. Check for currency symbols or formatting

### Parser Timeout

**Symptom**: Parser takes >5 minutes on 100-page PDF

**Fixes**:
1. Add page range filtering (like Hager parser)
2. Optimize table extraction (use Camelot with specific pages)
3. Add caching for repeated operations

---

## Example: Adding "Baldwin Hardware"

```bash
# 1. Analyze PDF
uv run python scripts/analyze_pdf_chunked.py "test_data/pdfs/baldwin-2025.pdf"

# 2. Create parser
mkdir -p parsers/baldwin
touch parsers/baldwin/{__init__.py,parser.py,sections.py}

# 3. Copy template (assuming row-based like SELECT)
cp parsers/select/parser.py parsers/baldwin/parser.py
cp parsers/select/sections.py parsers/baldwin/sections.py

# 4. Customize (2-4 hours of editing)
# - Update class names: SelectHingesParser → BaldwinParser
# - Update manufacturer: "SELECT Hinges" → "Baldwin"
# - Customize SKU format in sections.py
# - Update table detection logic

# 5. Register
# Edit parsers/__init__.py to add BaldwinParser

# 6. Test
uv run python scripts/parse_and_export.py "test_data/pdfs/baldwin-2025.pdf"
```

---

## Summary

**Short Answer**: No, not automatic. Each manufacturer needs custom code.

**Good News**: You have a **reusable framework**:
- ✅ Shared utilities (PDF extraction, table processing, OCR)
- ✅ Two working examples (Hager, SELECT)
- ✅ Clear template to follow
- ✅ 60% of code is reusable

**Effort Per New Manufacturer**:
- **Similar format**: 4-8 hours
- **Different format**: 1-3 days
- **Complex/messy PDF**: 3-5 days

**Recommendation**: Start with similar manufacturers first to build experience, then tackle more complex formats.
