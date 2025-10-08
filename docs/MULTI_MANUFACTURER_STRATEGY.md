# Multi-Manufacturer Parser Strategy

**Date**: 2025-10-05
**Status**: ANALYSIS & RECOMMENDATIONS

---

## Current Situation

You have **130+ manufacturer PDF price books** in `test_data/pdfs/`:

### Major Manufacturers (20MB+ PDFs):
- Schlage (37MB) - Major lock manufacturer
- McKinney (27MB) - Hinges
- Dorma Kaba (multiple books, 19-25MB) - Access control
- Medeco (22MB) - High-security locks
- Von Duprin (13MB) - Exit devices
- Allegion (20MB) - Multi-family hardware
- Master Lock (18MB)
- Hager (20MB) - ✅ **Parser exists** (with optimization)

### Medium Manufacturers (5-15MB):
- Best (multiple books) - Locks, cores, hinges
- Falcon (13MB)
- IVES (12MB)
- LCN (14MB)
- Marks (12MB)
- RCI (19MB)
- SDC (14MB)
- And 50+ others...

### Small Manufacturers (<5MB):
- SELECT Hinges (6MB) - ✅ **Parser exists** (working perfectly)
- Adams Rite, Arrow, Detex, HES, Securitron, Trimco, Zero
- And 60+ others...

---

## Question: Should We Build a "Universal Parser"?

### ❌ **NO** - Universal parser is NOT recommended

**Why?**
1. **Each manufacturer has unique formats**:
   - Hager: Matrix-style tables (Model × Finish × Size)
   - SELECT: Row-based tables with net-add options
   - Schlage: Likely different again
   - Von Duprin: Exit devices have different pricing structure

2. **Accuracy would suffer**:
   - Universal parser = compromise = lower accuracy
   - Requirements demand ≥98% row accuracy, ≥99% numeric accuracy
   - Can only achieve this with manufacturer-specific logic

3. **Maintenance nightmare**:
   - One change breaks all manufacturers
   - Hard to debug which manufacturer is failing

---

## ✅ **RECOMMENDED APPROACH**: Hybrid Architecture

### 1. Shared Framework (60% reusable) ✅ **Already Built**

**What's Shared** (works for ALL manufacturers):
```
parsers/shared/
├── pdf_io.py              # PDF extraction (pdfplumber + Camelot)
├── ocr.py                 # OCR fallback for scanned PDFs
├── table_processor.py     # Table cleaning, header merging
├── page_classifier.py     # Detect scanned vs digital pages
├── normalization.py       # Price/date/text normalization
├── provenance.py          # Track data source (page, cell)
├── parallel_extractor.py  # Parallel table extraction
```

**Benefits**:
- ✅ 60% of code is reusable
- ✅ OCR works for ALL manufacturers
- ✅ Table extraction works for ALL manufacturers
- ✅ Provenance tracking works for ALL manufacturers

---

### 2. Manufacturer-Specific Parsers (40% custom)

**What's Custom** (per manufacturer):
```
parsers/{manufacturer}/
├── __init__.py
├── parser.py              # Main parser orchestration
├── sections.py            # Extract products, options, finishes
└── [matrix_parser.py]     # Optional: For matrix-style tables
```

**Custom Logic Needed**:
1. **Table Detection**: Which tables contain products?
2. **SKU Format**: How to generate SKU from model/finish/size?
3. **Price Extraction**: Where are prices in the table?
4. **Options/Adders**: How are options represented?

**Effort Per Manufacturer**:
- Similar format (e.g., SELECT-like): **4-8 hours**
- Different format (e.g., Schlage, Von Duprin): **1-3 days**
- Complex/messy PDF: **3-5 days**

---

## Strategy for Your 130+ Manufacturers

### Phase 1: Group by Format Type ✅ **RECOMMENDED FIRST**

Before building parsers, **analyze PDF structures** to group manufacturers by format similarity:

#### Step 1: Rapid Analysis (2-3 hours)
Run `analyze_pdf_chunked.py` on 10-15 representative PDFs:

```bash
# Small manufacturers (likely similar to SELECT)
uv run python scripts/analyze_pdf_chunked.py "test_data/pdfs/2025-rockwood-price-book.pdf"
uv run python scripts/analyze_pdf_chunked.py "test_data/pdfs/2025-ives-price-book.pdf"
uv run python scripts/analyze_pdf_chunked.py "test_data/pdfs/2025-trimco-price-book.pdf"

# Medium manufacturers
uv run python scripts/analyze_pdf_chunked.py "test_data/pdfs/2025-schlage-price-book.pdf"
uv run python scripts/analyze_pdf_chunked.py "test_data/pdfs/2025-von-duprin-price-book.pdf"
uv run python scripts/analyze_pdf_chunked.py "test_data/pdfs/2025-best-hinges-door-accessories-price-book.pdf"

# Large manufacturers
uv run python scripts/analyze_pdf_chunked.py "test_data/pdfs/2025-allegion-multi-family-price-book.pdf"
uv run python scripts/analyze_pdf_chunked.py "test_data/pdfs/2025-medeco-price-book.pdf"
```

#### Step 2: Categorize by Format (1 hour)
Group manufacturers into format types:

| Format Type | Characteristics | Example Manufacturers | Effort |
|------------|-----------------|----------------------|--------|
| **Row-Based** | One product per row, columns for attributes | SELECT, Rockwood, IVES | 4-8 hrs |
| **Matrix-Style** | Rows=Models, Cols=Finishes/Sizes, Cells=Prices | Hager, McKinney (likely) | 4-8 hrs |
| **Nested Tables** | Multiple table types per page | Schlage (likely) | 1-3 days |
| **Catalog Style** | Products with images, descriptions, then prices | Master Lock (likely) | 1-3 days |

---

### Phase 2: Build Template Parsers (1-2 weeks)

Create **4 template parsers** (one per format type):

#### Template 1: Row-Based Parser ✅ **Already Done**
- **Base**: SELECT Hinges parser
- **Works for**: Rockwood, IVES, Trimco, Zero, etc. (40+ manufacturers)
- **Customization**: 2-4 hours per manufacturer

#### Template 2: Matrix-Style Parser ✅ **Already Done**
- **Base**: Hager parser
- **Works for**: McKinney, possibly Best Hinges, etc. (10+ manufacturers)
- **Customization**: 2-4 hours per manufacturer

#### Template 3: Nested Tables Parser (NEW)
- **Base**: Build from SELECT + custom logic
- **Works for**: Schlage, Von Duprin, Falcon, etc. (30+ manufacturers)
- **Effort**: 2-3 days to build template
- **Customization**: 1-2 days per manufacturer

#### Template 4: Catalog Style Parser (NEW)
- **Base**: Build with OCR + pattern matching
- **Works for**: Master Lock, possibly others (20+ manufacturers)
- **Effort**: 3-5 days to build template
- **Customization**: 1-2 days per manufacturer

---

### Phase 3: Automated Manufacturer Detection

Build a **dispatcher** that auto-detects manufacturer and routes to correct parser:

```python
# parsers/dispatcher.py
def detect_manufacturer(pdf_path: str) -> str:
    """Auto-detect manufacturer from PDF content."""
    with pdfplumber.open(pdf_path) as pdf:
        first_page_text = pdf.pages[0].extract_text().lower()

        # Check for manufacturer keywords
        if "hager" in first_page_text:
            return "hager"
        elif "select hinges" in first_page_text:
            return "select_hinges"
        elif "schlage" in first_page_text:
            return "schlage"
        elif "von duprin" in first_page_text:
            return "von_duprin"
        # ... add more manufacturers

        return "unknown"

def get_parser_for_manufacturer(manufacturer: str, pdf_path: str):
    """Return appropriate parser instance."""
    if manufacturer == "hager":
        from parsers.hager import HagerParser
        return HagerParser(pdf_path)
    elif manufacturer == "select_hinges":
        from parsers.select import SelectHingesParser
        return SelectHingesParser(pdf_path)
    elif manufacturer == "schlage":
        from parsers.schlage import SchlageParser
        return SchlageParser(pdf_path)
    # ... add more
```

**Integration into app.py**:
```python
# app.py
from parsers.dispatcher import detect_manufacturer, get_parser_for_manufacturer

@app.post("/upload")
async def upload_file(file: UploadFile):
    # Save PDF
    pdf_path = save_uploaded_file(file)

    # Auto-detect manufacturer
    manufacturer = detect_manufacturer(pdf_path)

    # Get appropriate parser
    parser = get_parser_for_manufacturer(manufacturer, pdf_path)

    # Parse
    results = parser.parse()

    return results
```

---

## Prioritization Strategy

### Tier 1: High-Value Manufacturers (Build First)
These are likely your most common price books:

1. **Schlage** (37MB) - Major lock manufacturer
2. **Allegion** (20MB) - Multi-family hardware
3. **Von Duprin** (13MB) - Exit devices
4. **LCN** (14MB) - Door closers
5. **Best** (multiple books) - Locks, cores, hinges

**Why?** These 5 manufacturers probably cover 60-70% of your real-world usage.

**Effort**: 1-2 weeks (2-3 days per manufacturer)

---

### Tier 2: Medium-Value Manufacturers (Build Next)
Fill in common gaps:

6. **Medeco** (22MB) - High-security locks
7. **Falcon** (13MB)
8. **IVES** (12MB)
9. **McKinney** (27MB) - Hinges (likely similar to Hager)
10. **Marks** (12MB)

**Effort**: 1-2 weeks

---

### Tier 3: Long-Tail Manufacturers (Build As Needed)
The remaining 120+ manufacturers - build on-demand:

- When a customer requests a specific manufacturer
- When you get a new PDF that needs parsing
- Use existing templates (4-8 hours per manufacturer)

**Effort**: Ongoing, as needed

---

## Recommended Immediate Next Steps

### Option A: Build 5 High-Value Parsers (RECOMMENDED)
**Time**: 2 weeks
**Coverage**: 60-70% of real-world usage
**ROI**: High

1. ✅ SELECT (done)
2. ✅ Hager (done, needs testing with optimization)
3. ⏳ Schlage (2-3 days)
4. ⏳ Von Duprin (2-3 days)
5. ⏳ LCN (2-3 days)

**After 2 weeks**: You can parse PDFs from 5 major manufacturers covering most use cases.

---

### Option B: Build Analysis + Detection System (FASTER MVP)
**Time**: 1 week
**Coverage**: Identify ALL manufacturers, parse 2
**ROI**: Better visibility

1. ✅ SELECT parser (done)
2. ✅ Hager parser (done)
3. ⏳ Rapid PDF analysis script (batch analyze all 130 PDFs) - 1 day
4. ⏳ Manufacturer detection system - 1 day
5. ⏳ Format classification (group by table type) - 1 day
6. ⏳ Report: Which manufacturers need custom parsers vs templates - 1 day

**After 1 week**: You know exactly which manufacturers need what, and have a roadmap.

---

## Cost-Benefit Analysis

### If You Build ALL 130 Parsers:
- **Effort**: 130 manufacturers × 6 hours (avg) = **780 hours** = **19 weeks** (full-time)
- **Cost**: Very high
- **Benefit**: Complete coverage
- **Recommendation**: ❌ **NOT RECOMMENDED** - too expensive

### If You Build 5-10 Parsers (Recommended):
- **Effort**: 10 manufacturers × 1.5 days (avg) = **15 days** = **3 weeks**
- **Cost**: Reasonable
- **Benefit**: Covers 70-80% of real-world usage
- **Recommendation**: ✅ **RECOMMENDED**

### If You Build Template System + On-Demand:
- **Effort**:
  - 4 templates: 2 weeks
  - Each new manufacturer: 4-8 hours (using templates)
- **Cost**: Low ongoing cost
- **Benefit**: Scalable, flexible
- **Recommendation**: ✅ **HIGHLY RECOMMENDED**

---

## Summary

### What You Have Now:
- ✅ 60% reusable framework (shared utilities)
- ✅ 2 working parsers: SELECT, Hager
- ✅ 130+ test PDFs
- ✅ Clear documentation (ADDING_NEW_MANUFACTURER.md)

### What You Need:
1. **Rapid PDF analysis** of 10-15 representative manufacturers (3 hours)
2. **Format classification** - group manufacturers by table structure (1 day)
3. **Build 2-3 more template parsers** (Nested Tables, Catalog Style) - 1 week
4. **Manufacturer detection system** - 1 day
5. **Build 5 high-value parsers** (Schlage, Von Duprin, LCN, Allegion, Best) - 2 weeks

### Total Effort to 70% Coverage:
**4 weeks** (80 hours)

### My Recommendation:
**Option B + Top 5 Parsers**:
1. Week 1: Analysis, classification, detection system
2. Week 2-3: Build 5 high-value parsers (Schlage, Von Duprin, LCN, Allegion, Best)
3. Week 4: Testing, accuracy validation, documentation

**Result**: Parse 7 manufacturers (SELECT, Hager + 5 new) covering 70% of real-world usage.

---

## Next Action

**Which approach do you prefer?**

A. Build 5 high-value parsers immediately (Schlage, Von Duprin, LCN, Allegion, Best)
B. Analyze all 130 PDFs first, then decide priority
C. Build template system, then cherry-pick manufacturers as needed
D. Focus on completing Hager/SELECT accuracy validation first, then expand

**Let me know and I'll proceed with your choice!**
