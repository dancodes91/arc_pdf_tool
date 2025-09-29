# Parser Architecture Guide

## Overview

ARC PDF Tool uses manufacturer-specific parsers built on shared extraction utilities. Each parser handles unique PDF layouts while leveraging common infrastructure for table extraction, OCR, and data normalization.

## Architecture

```
parsers/
├── hager/
│   ├── parser.py           # Main Hager parser
│   └── sections.py         # Hager-specific extraction
├── select/
│   ├── parser.py           # Main SELECT parser
│   └── sections.py         # SELECT-specific extraction
└── shared/
    ├── pdf_io.py           # PDF extraction (pdfplumber, Camelot)
    ├── confidence.py       # Confidence scoring
    ├── normalization.py    # Data normalization
    ├── provenance.py       # Page tracking
    └── ocr_processor.py    # OCR fallback

```

## Parser Lifecycle

### 1. Initialization
```python
from parsers import HagerParser

parser = HagerParser(
    pdf_path="path/to/pricebook.pdf",
    config={
        'min_confidence': 0.7,
        'enable_ocr': True
    }
)
```

### 2. Parsing
```python
results = parser.parse()
```

**Internal flow**:
1. Extract PDF document (all pages, tables, images)
2. Parse effective date
3. Parse finish symbols
4. Parse price rules
5. Parse options/additions
6. Parse product tables
7. Calculate confidence scores
8. Build results dictionary

### 3. Results Structure
```python
{
    'manufacturer': 'Hager',
    'effective_date': '2025-01-15',
    'products': [
        {
            'sku': 'BB1100-US10B',
            'model': 'BB1100',
            'series': 'BB',
            'finish': 'US10B',
            'base_price': 125.50,
            'description': '4.5" x 4.5" Ball Bearing Hinge',
            'provenance': {'page_number': 45, 'table_index': 2},
            'confidence': 0.95
        }
    ],
    'finishes': [...],
    'options': [...],
    'rules': [...]
}
```

## Shared Utilities

### PDF Extraction (pdf_io.py)

**EnhancedPDFExtractor** - Multi-strategy extraction:

```python
from parsers.shared.pdf_io import EnhancedPDFExtractor

extractor = EnhancedPDFExtractor("path/to/pdf.pdf")
document = extractor.extract_document()

for page in document.pages:
    print(f"Page {page.page_number}: {len(page.tables)} tables")
```

**Strategies**:
1. **pdfplumber** - Fast, text-based extraction
2. **Camelot lattice** - Grid-based tables
3. **Camelot stream** - Line-based tables
4. **OCR fallback** - Scanned/image PDFs

### Table Extraction

**Camelot Integration**:
```python
from parsers.shared.pdf_io import extract_tables_with_camelot

# Lattice mode - for bordered tables
tables = extract_tables_with_camelot(
    pdf_path,
    page_number=10,
    flavor="lattice"
)

# Stream mode - for borderless tables
tables = extract_tables_with_camelot(
    pdf_path,
    page_number=10,
    flavor="stream"
)
```

### Confidence Scoring (confidence.py)

```python
from parsers.shared.confidence import confidence_scorer

score = confidence_scorer.score_price_extraction(
    price_value=125.50,
    source_text="$125.50",
    context="BB1100 Ball Bearing Hinge"
)
# Returns: ConfidenceScore(score=0.95, factors={'exact_match': True, ...})
```

**Scoring Factors**:
- Pattern match quality
- Data completeness
- Cross-validation with context
- Multiple source agreement

### Data Normalization (normalization.py)

```python
from parsers.shared.normalization import data_normalizer

# Normalize price
price = data_normalizer.normalize_price("$125.50")
# Returns: {'value': 125.50, 'currency': 'USD', 'confidence': 0.95}

# Normalize date
date = data_normalizer.normalize_date("Effective January 15, 2025")
# Returns: {'value': '2025-01-15', 'confidence': 0.9}

# Normalize SKU
sku = data_normalizer.normalize_sku("BB 1100 - US10B")
# Returns: 'BB1100-US10B'
```

### Provenance Tracking (provenance.py)

Every extracted item tracks its source:

```python
from parsers.shared.provenance import ProvenanceTracker

tracker = ProvenanceTracker("path/to/pdf.pdf")
tracker.set_context(section="Products", page_number=45, table_index=2)

item = tracker.create_item(
    value={'sku': 'BB1100', 'price': 125.50},
    confidence=0.95,
    raw_text="BB1100 Ball Bearing $125.50",
    source_section="Products"
)
```

**ParsedItem structure**:
```python
{
    'value': {...},
    'confidence': 0.95,
    'provenance': {
        'page_number': 45,
        'table_index': 2,
        'section': 'Products',
        'pdf_path': 'path/to/pdf.pdf'
    },
    'raw_text': '...',
    'extraction_method': 'camelot_lattice'
}
```

## Manufacturer-Specific Parsers

### Hager Parser

**Specializations**:
- BHMA finish codes (US3, US10B, US26D, etc.)
- Product families (BB series, WT series, EC series)
- Price mapping rules (e.g., "US10B use US10A price")
- Hinge additions (EPT, ETW, EMS, HWS, CWP)

**Performance Optimization**:
- Processes only pages with product indicators
- Filters by keywords: BB, WT, ECBB, $, Price, Model
- Reduces 479 pages → ~100-200 pages
- Target: < 2 minutes

**Example**:
```python
from parsers import HagerParser

parser = HagerParser("hager_2025.pdf")
results = parser.parse()

print(f"Products: {len(results['products'])}")
print(f"Finishes: {len(results['finishes'])}")
print(f"Options: {len(results['options'])}")
```

### SELECT Hinges Parser

**Specializations**:
- Embedded SKU format: "SL21 CL HD300" in single cells
- Finish abbreviations: CL (Clear), BR (Bronze), BK (Black)
- Length/duty specifications: HD300, HD600, LL
- Model tables with melt/pivot extraction

**Table Melting**:
```python
# SELECT PDFs have grids: Model × Finish columns
# Parser "melts" table to create one row per combination

# Before (table):
#   Model | CL    | BR    | BK
#   SL21  | 15.00 | 15.50 | 16.00

# After (melted):
# [
#   {sku: 'SL21-CL', price: 15.00},
#   {sku: 'SL21-BR', price: 15.50},
#   {sku: 'SL21-BK', price: 16.00}
# ]
```

**Example**:
```python
from parsers import SelectHingesParser

parser = SelectHingesParser("select_2025.pdf")
results = parser.parse()

# Achieves 130 products in ~43 seconds
```

## Adding a New Manufacturer

### Step 1: Create Parser Structure

```bash
mkdir -p parsers/newvendor
touch parsers/newvendor/__init__.py
touch parsers/newvendor/parser.py
touch parsers/newvendor/sections.py
```

### Step 2: Implement Parser Class

**parsers/newvendor/parser.py**:
```python
from ..shared.pdf_io import EnhancedPDFExtractor
from ..shared.provenance import ProvenanceTracker
from .sections import NewVendorSectionExtractor

class NewVendorParser:
    def __init__(self, pdf_path: str, config: dict = None):
        self.pdf_path = pdf_path
        self.config = config or {}

        self.provenance_tracker = ProvenanceTracker(pdf_path)
        self.section_extractor = NewVendorSectionExtractor(self.provenance_tracker)
        self.pdf_extractor = EnhancedPDFExtractor(pdf_path, config)

        self.products = []
        self.finishes = []
        self.options = []

    def parse(self) -> dict:
        # Extract PDF
        self.document = self.pdf_extractor.extract_document()

        # Parse sections
        self._parse_products()
        self._parse_finishes()
        self._parse_options()

        # Build results
        return {
            'manufacturer': 'NewVendor',
            'products': [self._serialize_item(p) for p in self.products],
            'finishes': [self._serialize_item(f) for f in self.finishes],
            'options': [self._serialize_item(o) for o in self.options]
        }

    def _parse_products(self):
        # Implement product extraction logic
        pass
```

### Step 3: Implement Section Extractors

**parsers/newvendor/sections.py**:
```python
class NewVendorSectionExtractor:
    def __init__(self, provenance_tracker):
        self.tracker = provenance_tracker

    def extract_products(self, text: str, tables: list, page_number: int):
        # Implement product extraction
        self.tracker.set_context(section="Products", page_number=page_number)

        products = []
        for table in tables:
            # Parse table
            # Create ParsedItem for each product
            pass

        return products
```

### Step 4: Register Parser

**parsers/__init__.py**:
```python
from .hager.parser import HagerParser
from .select.parser import SelectHingesParser
from .newvendor.parser import NewVendorParser

__all__ = ['HagerParser', 'SelectHingesParser', 'NewVendorParser']
```

### Step 5: Add Tests

**tests/test_newvendor_parser.py**:
```python
import pytest
from parsers import NewVendorParser

def test_parse_products():
    parser = NewVendorParser("test_data/pdfs/newvendor.pdf")
    results = parser.parse()

    assert len(results['products']) > 0
    assert results['manufacturer'] == 'NewVendor'
```

## Performance Optimization

### 1. Page Filtering
Skip pages without relevant content:
```python
# Filter by keywords
product_indicators = ['Model', 'SKU', 'Price', '$']
pages_to_process = [
    page for page in document.pages
    if any(keyword in page.text for keyword in product_indicators)
]
```

### 2. Lazy Table Extraction
Extract tables only when needed:
```python
# Don't extract all tables upfront
# Extract per-page as needed
for page in pages_to_process:
    tables = extract_tables_with_camelot(pdf_path, page.page_number)
    products = extract_products(tables)
```

### 3. Caching
Cache expensive operations:
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def normalize_sku(sku: str) -> str:
    return re.sub(r'[\s\-_]', '', sku).upper()
```

## Best Practices

1. **Use shared utilities** - Don't reimplement common functionality
2. **Track provenance** - Every item should know its source page
3. **Score confidence** - Low scores go to review queue
4. **Normalize data** - Consistent format across manufacturers
5. **Test extensively** - Add test fixtures for each PDF type
6. **Handle errors gracefully** - Partial extraction is better than failure
7. **Log extraction steps** - Debug performance and quality issues

## Troubleshooting

### Low Extraction Quality

Check confidence scores:
```python
results = parser.parse()
low_conf = [p for p in results['products'] if p['confidence'] < 0.7]
print(f"Low confidence: {len(low_conf)} items")
```

### Missing Products

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

parser = HagerParser("problem.pdf")
results = parser.parse()
# Review logs for extraction steps
```

### OCR Issues

Force OCR for specific pages:
```python
config = {'force_ocr': True, 'ocr_pages': [5, 10, 15]}
parser = HagerParser("scanned.pdf", config=config)
```

## See Also

- [DIFF.md](DIFF.md) - Compare parsed results
- [OPERATIONS.md](OPERATIONS.md) - Production monitoring
- [BASEROW.md](BASEROW.md) - Sync to Baserow