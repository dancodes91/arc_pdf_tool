# Universal Parser Accuracy Test Plan

**Date**: 2025-10-23
**Goal**: Achieve and validate accuracy targets across all data types
**Test Dataset**: 100+ PDFs in `test_data/pdfs/`

---

## Accuracy Targets

| Data Type | Target Accuracy | Priority | Rationale |
|-----------|----------------|----------|-----------|
| **Model Numbers/SKUs** | 99%+ | CRITICAL | Core product identifier, must be near-perfect |
| **Pricing Tables** | 98%+ | CRITICAL | Business-critical data, affects revenue |
| **Product Specifications** | 95%+ | HIGH | Important for product differentiation |
| **Add-on Pricing** | 95%+ | HIGH | Affects total pricing accuracy |

---

## Test Dataset Overview

**Available PDFs**: 100+ manufacturer price books
**Location**: `C:\arc_pdf_tool\test_data\pdfs`

### Manufacturers Represented (Sample):

- Hager (2025) - Known manufacturer, custom parser exists
- SELECT Hinges (2025) - Known manufacturer, custom parser exists
- Continental Access (2020) - Universal parser tested
- Lockey (2022) - Universal parser
- Alarm Lock (2024) - Universal parser
- Adams Rite (2025) - Universal parser
- And 90+ more...

### PDF Characteristics:

| Type | Count | Examples |
|------|-------|----------|
| **Digital PDFs** | ~80% | Hager, SELECT, Schlage |
| **Scanned PDFs** | ~15% | Older price books |
| **Mixed** | ~5% | Partial scans + digital |

---

## Testing Methodology

### Phase 1: Baseline Measurement (Current State)

**Goal**: Measure current Universal Parser accuracy against targets

#### Test Process:

1. **Select Representative Sample**:
   - 20 PDFs across different manufacturers
   - Mix of digital, scanned, and complex layouts
   - Include both known (Hager, SELECT) and unknown manufacturers

2. **Manual Ground Truth Creation**:
   - For each PDF, manually extract first 50 products
   - Record:
     - SKU/Model Number
     - Base Price
     - Description/Specifications
     - Add-on options (if applicable)
   - Store in `test_data/ground_truth/[manufacturer]_truth.json`

3. **Run Universal Parser**:
   ```bash
   python scripts/test_universal_accuracy.py \
     --pdf test_data/pdfs/[manufacturer].pdf \
     --ground-truth test_data/ground_truth/[manufacturer]_truth.json \
     --output reports/baseline_accuracy.json
   ```

4. **Calculate Metrics**:
   - Per-field accuracy (SKU, price, specs, add-ons)
   - Overall precision/recall
   - Confidence score distribution
   - Error analysis (what types of errors occurred)

#### Expected Baseline Results:

| Data Type | Current (Estimated) | Target | Gap |
|-----------|---------------------|--------|-----|
| SKUs | 75-80% | 99% | 19-24% |
| Pricing Tables | 70-75% | 98% | 23-28% |
| Specifications | 65-70% | 95% | 25-30% |
| Add-ons | 60-65% | 95% | 30-35% |

---

### Phase 2: Accuracy Improvements (Implementation)

Following the 7-phase plan in `UNIVERSAL_PARSER_98_ACCURACY_PLAN.md`:

#### Priority 1: SKU Accuracy (Target 99%)

**Current Bottlenecks**:
- Pattern matching too restrictive
- OCR errors (O vs 0, I vs 1)
- Missing manufacturer-specific formats

**Improvements**:
1. **Enhanced Pattern Library** (Phase 5):
   ```python
   # Add manufacturer-specific SKU patterns
   patterns = {
       'hager': [r'BB\d{4}', r'EC\d{3,4}', r'TA\d{4}'],
       'select': [r'SL\d{2,3}', r'BB-\d{4}-[A-Z\d]+'],
       'schlage': [r'[A-Z]\d{3}[A-Z]{3}', r'ND\d{2}[A-Z]{3}'],
       # ... 100+ more patterns
   }
   ```

2. **OCR Error Correction** (Phase 6):
   ```python
   def correct_sku_ocr_errors(sku: str) -> str:
       """Context-aware OCR correction for SKUs."""
       corrections = {
           ('O', '0'): r'(?<=\d)O(?=\d)',  # O→0 between digits
           ('I', '1'): r'(?<=\d)I(?=\d)',  # I→1 between digits
           ('l', '1'): r'(?<=\d)l(?=\d)',  # l→1 between digits
       }
       for (old, new), pattern in corrections.items():
           sku = re.sub(pattern, new, sku)
       return sku
   ```

3. **Multi-Source Validation** (Phase 2):
   - If 2+ layers extract same SKU → 99.5% confidence
   - If 3 layers agree → 99.9% confidence

**Target Achievement**:
- Pattern library: 75% → 90% (+15%)
- OCR correction: 90% → 96% (+6%)
- Multi-source validation: 96% → 99%+ (+3%)

---

#### Priority 2: Pricing Table Accuracy (Target 98%)

**Current Bottlenecks**:
- Table structure misdetection
- Price extraction from complex cells
- Handling price ranges ($100-$150)
- Missing currency symbols

**Improvements**:
1. **Enhanced Table Structure Recognition** (Phase 4):
   ```python
   # Use PaddleOCR's table structure module
   from paddleocr import PPStructure

   table_engine = PPStructure()
   result = table_engine(table_image)

   # Get structured cell data with bounding boxes
   for cell in result[0]['res']['cells']:
       text = cell['text']
       confidence = cell['score']
       bbox = cell['bbox']
   ```

2. **Price Normalization** (Phase 6):
   ```python
   def normalize_price(price_text: str) -> float:
       """Robust price extraction and normalization."""
       # Handle multiple formats
       patterns = [
           r'\$\s*(\d+[,\d]*\.?\d{0,2})',  # $123.45
           r'(\d+[,\d]*\.\d{2})',           # 123.45
           r'\$?(\d+)\.00',                 # 100.00
           r'\$?(\d+)',                     # 100
       ]

       for pattern in patterns:
           match = re.search(pattern, price_text)
           if match:
               price_str = match.group(1).replace(',', '')
               return float(price_str)

       return None
   ```

3. **Cell-Level Confidence Scoring** (Phase 3):
   ```python
   # Each price gets field-specific confidence
   price_confidence = calculate_price_confidence(
       value=123.45,
       ocr_score=0.95,
       pattern_match=True,
       reasonable_range=True
   )
   # Returns: 0.98
   ```

**Target Achievement**:
- Table structure: 70% → 85% (+15%)
- Price extraction: 85% → 95% (+10%)
- Validation: 95% → 98%+ (+3%)

---

#### Priority 3: Product Specifications (Target 95%)

**Current Bottlenecks**:
- Multi-line descriptions
- Technical specifications mixed with marketing text
- Inconsistent formatting

**Improvements**:
1. **Multi-Line Text Extraction** (Phase 4):
   ```python
   def extract_multi_line_description(cells: List[Dict]) -> str:
       """Combine cells that span multiple rows."""
       description_parts = []

       for cell in cells:
           if cell['column'] == 'description':
               description_parts.append(cell['text'])

       return ' '.join(description_parts).strip()
   ```

2. **Specification Parsing** (Phase 5):
   ```python
   def parse_specifications(desc: str) -> Dict[str, Any]:
       """Extract structured specs from description."""
       specs = {}

       # Common patterns
       patterns = {
           'dimensions': r'(\d+\.?\d*)\s*x\s*(\d+\.?\d*)',
           'material': r'(stainless steel|brass|bronze|aluminum)',
           'finish': r'(US\d+[A-Z]?|satin|polished)',
           'weight': r'(\d+\.?\d*)\s*(lb|lbs|kg)',
       }

       for key, pattern in patterns.items():
           match = re.search(pattern, desc, re.IGNORECASE)
           if match:
               specs[key] = match.group(0)

       return specs
   ```

3. **Quality Assessment** (Phase 6):
   ```python
   def assess_description_quality(desc: str) -> float:
       """Score description completeness."""
       score = 0.5  # Base

       if len(desc) > 20:
           score += 0.2  # Has content

       if any(keyword in desc.lower() for keyword in ['hinge', 'lock', 'door', 'closer']):
           score += 0.2  # Has domain keywords

       if re.search(r'\d+\.?\d*\s*x\s*\d+\.?\d*', desc):
           score += 0.1  # Has dimensions

       return min(score, 1.0)
   ```

**Target Achievement**:
- Multi-line extraction: 65% → 80% (+15%)
- Spec parsing: 80% → 90% (+10%)
- Quality assessment: 90% → 95%+ (+5%)

---

#### Priority 4: Add-on Pricing (Target 95%)

**Current Bottlenecks**:
- Add-ons in separate sections
- Multiple add-on types (finishes, sizes, options)
- Complex pricing logic (%, fixed, multiplier)

**Improvements**:
1. **Add-On Detection** (Phase 5):
   ```python
   def detect_addon_sections(pdf_text: str) -> List[Dict]:
       """Find add-on sections in PDF."""
       section_markers = [
           'net add',
           'adder',
           'option',
           'finish upcharge',
           'size adjustment',
       ]

       sections = []
       for marker in section_markers:
           pattern = rf'{marker}.*?(?=\n\n|\Z)'
           matches = re.finditer(pattern, pdf_text, re.IGNORECASE | re.DOTALL)
           for match in matches:
               sections.append({
                   'type': marker,
                   'text': match.group(0),
                   'page': get_page_number(match.start())
               })

       return sections
   ```

2. **Add-On Extraction** (Phase 2):
   ```python
   def extract_addon_pricing(section_text: str) -> List[Dict]:
       """Extract add-on options with pricing."""
       addons = []

       # Pattern: OPTION_CODE: $PRICE or OPTION_CODE ... $PRICE
       pattern = r'([A-Z]{2,})\s*(?::|\.{2,})\s*\$?(\d+\.?\d*)'

       for match in re.finditer(pattern, section_text):
           code, price = match.groups()
           addons.append({
               'option_code': code,
               'adder_value': float(price),
               'adder_type': 'net_add',
               'confidence': 0.85
           })

       return addons
   ```

3. **Validation** (Phase 6):
   ```python
   def validate_addons(addons: List[Dict]) -> List[Dict]:
       """Validate add-on pricing logic."""
       validated = []

       for addon in addons:
           # Check price reasonableness
           if 0 < addon['adder_value'] < 10000:
               addon['confidence'] = min(addon['confidence'] + 0.1, 1.0)
               validated.append(addon)
           elif addon['adder_value'] == 0:
               # Might be "no charge"
               addon['confidence'] = 0.7
               validated.append(addon)

       return validated
   ```

**Target Achievement**:
- Section detection: 60% → 80% (+20%)
- Extraction: 80% → 92% (+12%)
- Validation: 92% → 95%+ (+3%)

---

### Phase 3: Validation Testing

**Goal**: Verify accuracy targets are met

#### Test Process:

1. **Expanded Ground Truth**:
   - Create ground truth for 50 PDFs (5000+ products)
   - Cover all manufacturer types
   - Include edge cases

2. **Automated Testing**:
   ```bash
   python scripts/run_accuracy_tests.py \
     --test-set test_data/ground_truth/ \
     --output reports/final_accuracy_report.json \
     --min-sku-accuracy 0.99 \
     --min-price-accuracy 0.98 \
     --min-spec-accuracy 0.95 \
     --min-addon-accuracy 0.95
   ```

3. **Metrics Collection**:
   - Per-field accuracy
   - Per-manufacturer accuracy
   - Confidence distribution
   - Error types and frequencies

4. **Failure Analysis**:
   - Identify remaining error patterns
   - Document edge cases
   - Create improvement backlog

---

## Test Scripts

### Script 1: Ground Truth Creator

**File**: `scripts/create_ground_truth.py`

```python
#!/usr/bin/env python3
"""
Interactive script to create ground truth data for accuracy testing.

Usage:
    python scripts/create_ground_truth.py \\
        --pdf test_data/pdfs/2025-hager-price-book.pdf \\
        --output test_data/ground_truth/hager_2025_truth.json \\
        --num-products 50
"""

import json
import argparse
from pathlib import Path
import pdfplumber

def create_ground_truth():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--num-products', type=int, default=50)
    args = parser.parse_args()

    print(f"Opening PDF: {args.pdf}")
    print(f"Please manually extract {args.num_products} products...")
    print()

    products = []

    for i in range(args.num_products):
        print(f"\n--- Product {i+1}/{args.num_products} ---")
        sku = input("SKU/Model: ").strip()
        price = input("Base Price (numeric only): ").strip()
        description = input("Description: ").strip()

        product = {
            'sku': sku,
            'base_price': float(price) if price else None,
            'description': description,
        }

        # Optional add-ons
        has_addons = input("Add-ons? (y/n): ").strip().lower()
        if has_addons == 'y':
            addons = []
            while True:
                code = input("  Add-on code (or Enter to finish): ").strip()
                if not code:
                    break
                value = input(f"  {code} price: $").strip()
                addons.append({
                    'option_code': code,
                    'adder_value': float(value) if value else 0
                })
            product['addons'] = addons

        products.append(product)

    # Save
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump({
            'pdf': args.pdf,
            'products': products,
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'num_products': len(products)
            }
        }, f, indent=2)

    print(f"\nGround truth saved to: {output_path}")

if __name__ == '__main__':
    create_ground_truth()
```

---

### Script 2: Accuracy Tester

**File**: `scripts/test_universal_accuracy.py`

```python
#!/usr/bin/env python3
"""
Test Universal Parser accuracy against ground truth.

Usage:
    python scripts/test_universal_accuracy.py \\
        --pdf test_data/pdfs/2025-hager-price-book.pdf \\
        --ground-truth test_data/ground_truth/hager_2025_truth.json \\
        --output reports/hager_accuracy.json
"""

import json
import argparse
from pathlib import Path
from parsers.universal import UniversalParser
from typing import Dict, List, Any

def calculate_accuracy(predicted: List[Dict], ground_truth: List[Dict]) -> Dict[str, float]:
    """Calculate accuracy metrics."""

    # Match products by SKU
    sku_matches = 0
    price_matches = 0
    spec_matches = 0
    addon_matches = 0

    total = len(ground_truth)

    # Build SKU index
    pred_by_sku = {p.get('sku'): p for p in predicted if p.get('sku')}

    for truth_product in ground_truth:
        truth_sku = truth_product['sku']

        # SKU accuracy (exact match)
        if truth_sku in pred_by_sku:
            sku_matches += 1
            pred_product = pred_by_sku[truth_sku]

            # Price accuracy (within $0.01)
            truth_price = truth_product.get('base_price')
            pred_price = pred_product.get('base_price')
            if truth_price and pred_price:
                if abs(truth_price - pred_price) <= 0.01:
                    price_matches += 1

            # Spec accuracy (partial match)
            truth_desc = truth_product.get('description', '').lower()
            pred_desc = pred_product.get('description', '').lower()
            if truth_desc and pred_desc:
                # Check if key terms match
                truth_words = set(truth_desc.split())
                pred_words = set(pred_desc.split())
                overlap = len(truth_words & pred_words) / len(truth_words) if truth_words else 0
                if overlap >= 0.7:  # 70% word overlap = match
                    spec_matches += 1

            # Add-on accuracy
            truth_addons = truth_product.get('addons', [])
            pred_addons = pred_product.get('addons', [])
            if truth_addons:
                addon_codes_truth = {a['option_code'] for a in truth_addons}
                addon_codes_pred = {a['option_code'] for a in pred_addons}
                overlap = len(addon_codes_truth & addon_codes_pred) / len(addon_codes_truth)
                if overlap >= 0.8:  # 80% add-on match
                    addon_matches += 1

    return {
        'sku_accuracy': sku_matches / total if total else 0,
        'price_accuracy': price_matches / total if total else 0,
        'spec_accuracy': spec_matches / total if total else 0,
        'addon_accuracy': addon_matches / len([p for p in ground_truth if p.get('addons')]) if any(p.get('addons') for p in ground_truth) else 0,
        'total_products': total,
        'sku_matches': sku_matches,
        'price_matches': price_matches,
        'spec_matches': spec_matches,
        'addon_matches': addon_matches
    }

def test_accuracy():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', required=True)
    parser.add_argument('--ground-truth', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    # Load ground truth
    with open(args.ground_truth) as f:
        truth_data = json.load(f)

    ground_truth = truth_data['products']

    # Run Universal Parser
    print(f"Parsing PDF: {args.pdf}")
    universal_parser = UniversalParser(
        args.pdf,
        config={
            'use_hybrid': True,
            'use_ml_detection': True,
            'confidence_threshold': 0.6
        }
    )

    results = universal_parser.parse()

    # Extract products
    predicted = [item['value'] for item in results.get('products', [])]

    # Calculate accuracy
    metrics = calculate_accuracy(predicted, ground_truth)

    # Generate report
    report = {
        'pdf': args.pdf,
        'ground_truth_file': args.ground_truth,
        'metrics': metrics,
        'targets': {
            'sku_accuracy': 0.99,
            'price_accuracy': 0.98,
            'spec_accuracy': 0.95,
            'addon_accuracy': 0.95
        },
        'passed': {
            'sku': metrics['sku_accuracy'] >= 0.99,
            'price': metrics['price_accuracy'] >= 0.98,
            'spec': metrics['spec_accuracy'] >= 0.95,
            'addon': metrics['addon_accuracy'] >= 0.95
        },
        'parsing_metadata': results.get('parsing_metadata', {})
    }

    # Save report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("\n=== ACCURACY REPORT ===")
    print(f"SKU Accuracy: {metrics['sku_accuracy']:.1%} (Target: 99%)")
    print(f"Price Accuracy: {metrics['price_accuracy']:.1%} (Target: 98%)")
    print(f"Spec Accuracy: {metrics['spec_accuracy']:.1%} (Target: 95%)")
    print(f"Add-on Accuracy: {metrics['addon_accuracy']:.1%} (Target: 95%)")
    print()
    print(f"Report saved to: {output_path}")

if __name__ == '__main__':
    test_accuracy()
```

---

## Expected Timeline

### Week 1: Baseline + Priority 1 (SKU 99%)
- Day 1-2: Create ground truth for 20 PDFs
- Day 3: Run baseline tests
- Day 4-5: Implement SKU improvements

**Deliverable**: SKU accuracy reaches 99%+

### Week 2: Priority 2 & 3 (Pricing 98%, Specs 95%)
- Day 1-3: Table structure improvements
- Day 4-5: Specification extraction

**Deliverable**: Pricing and spec accuracy targets met

### Week 3: Priority 4 & Final Validation (Add-ons 95%)
- Day 1-2: Add-on detection and extraction
- Day 3-4: Create extended ground truth (50 PDFs)
- Day 5: Final validation testing

**Deliverable**: All accuracy targets validated

---

## Success Criteria

### Must-Have (Release Blockers)

- ✅ SKU accuracy ≥ 99% across 50 test PDFs
- ✅ Pricing table accuracy ≥ 98% across 50 test PDFs
- ✅ Product specification accuracy ≥ 95% across 50 test PDFs
- ✅ Add-on pricing accuracy ≥ 95% across 30 test PDFs with add-ons
- ✅ All custom parsers (Hager, SELECT) maintain or exceed 98% accuracy

### Nice-to-Have (Future Improvements)

- 🎯 Finish code accuracy ≥ 95%
- 🎯 Description completeness ≥ 90%
- 🎯 Processing speed < 8 seconds per page
- 🎯 Confidence calibration (predicted confidence matches actual accuracy)

---

## Reporting

### Daily Progress Report

**Template**: `reports/daily/YYYY-MM-DD.md`

```markdown
# Daily Accuracy Progress - [DATE]

## Tests Run
- PDFs tested: [N]
- Products tested: [N]
- Ground truth created: [Y/N]

## Current Accuracy
| Metric | Current | Target | Delta |
|--------|---------|--------|-------|
| SKU | X.X% | 99% | +/- X.X% |
| Price | X.X% | 98% | +/- X.X% |
| Specs | X.X% | 95% | +/- X.X% |
| Add-ons | X.X% | 95% | +/- X.X% |

## Issues Found
1. [Description of issue]
2. [Description of issue]

## Next Steps
1. [Action item]
2. [Action item]
```

### Final Report

**File**: `reports/FINAL_ACCURACY_REPORT.md`

Comprehensive report with:
- Overall accuracy across all metrics
- Per-manufacturer breakdown
- Error analysis
- Confidence calibration
- Performance metrics
- Recommendations for future improvements

---

**Document Version**: 1.0
**Status**: Ready to Execute
**Next Action**: Begin creating ground truth data for baseline testing
