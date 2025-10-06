# Universal Adaptive Parser - Plan & Architecture

**Goal**: Build ONE parser that works with ANY manufacturer price book without custom code per manufacturer

**Status**: Research Complete → Design Phase
**Date**: 2025-10-05

---

## 🔬 Research Findings (2024-2025 State of the Art)

### Modern Approaches for Universal PDF Parsing:

#### 1. **LLM-Based Vision Models** (RECOMMENDED ✅)
**Tools**:
- **GPT-4o Vision** (OpenAI) - Best for complex tables
- **LlamaParse** (LlamaIndex) - GenAI-native, industry-leading table extraction
- **Gemini Pro Vision** (Google)

**Capabilities**:
- ✅ Zero-shot learning (no training data needed)
- ✅ Understands document layout AND semantics
- ✅ Handles complex tables (merged cells, nested tables)
- ✅ Adaptive to new formats automatically
- ✅ Extracts structured JSON from any format

**Pricing**:
- GPT-4o Vision: ~$0.01-0.03 per page
- LlamaParse: $0.003/page (free tier: 7,000 pages/week)

---

#### 2. **Deep Learning Models** (GOOD ✅)
**Tools**:
- **Microsoft Table Transformer (TATR)** - Open source, free
- **LayoutLM v3** (Microsoft) - Document understanding
- **PdfTable Toolkit** (2024)

**Capabilities**:
- ✅ Pre-trained on millions of documents
- ✅ Detects tables automatically
- ✅ Recognizes table structure
- ✅ Outputs to HTML/CSV
- ✅ Works offline (no API costs)

**Limitations**:
- ⚠️ Requires setup/configuration
- ⚠️ Less adaptive than LLMs
- ⚠️ May struggle with unusual formats

---

#### 3. **Hybrid Approach** (BEST ✅✅✅)
**Combination**:
1. Use **Microsoft Table Transformer** for table detection
2. Use **LlamaParse/GPT-4o** for complex table parsing
3. Use **existing SELECT/Hager parsers** for known manufacturers
4. Fallback cascade: Known parser → TATR → LLM

**Benefits**:
- ✅ Cost-effective (use free TATR first)
- ✅ Accurate (LLM fallback for edge cases)
- ✅ Fast (known parsers are fastest)
- ✅ Scalable

---

## 🏗️ Proposed Architecture: Universal Adaptive Parser

### **3-Tier Intelligent Routing System**

```
┌─────────────────────────────────────────────────────┐
│           PDF Upload (Any Manufacturer)              │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │  TIER 1: Manufacturer         │
        │  Detection & Known Parsers    │
        │  (Fast, Free, Accurate)       │
        └──────────────┬─────────────────┘
                       │
            ┌──────────┴──────────┐
            │                     │
        Known MFR?          Unknown MFR?
            │                     │
            ▼                     ▼
    ┌─────────────────┐   ┌─────────────────────┐
    │ SELECT Parser   │   │  TIER 2: ML-Based    │
    │ Hager Parser    │   │  Table Detection     │
    │ (Future: +10)   │   │  (TATR + LayoutLM)   │
    └─────────────────┘   └──────────┬──────────┘
                                     │
                          ┌──────────┴──────────┐
                          │                     │
                    Tables Found?        No Tables?
                          │                     │
                          ▼                     ▼
               ┌──────────────────┐    ┌──────────────────┐
               │ Pattern-Based     │    │  TIER 3: LLM      │
               │ Extraction        │    │  Vision Parsing   │
               │ (Smart Heuristics)│    │  (GPT-4o/LlamaParse)│
               └──────────────────┘    └──────────────────┘
                          │                     │
                          └──────────┬──────────┘
                                     ▼
                          ┌──────────────────────┐
                          │  Structured Output    │
                          │  (Products, Prices,   │
                          │   Options, Metadata)  │
                          └──────────────────────┘
```

---

## 📐 Detailed Implementation Plan

### **TIER 1: Known Manufacturer Parsers** ✅ (Already Built)

**Current State**:
- SELECT Hinges parser (working)
- Hager parser (working)

**How it Works**:
```python
# parsers/universal/dispatcher.py
def detect_manufacturer(pdf_path: str) -> str:
    """Auto-detect manufacturer from first 3 pages."""
    with pdfplumber.open(pdf_path) as pdf:
        text = " ".join(p.extract_text() for p in pdf.pages[:3]).lower()

        # Check known patterns
        if "select hinges" in text:
            return "select_hinges"
        elif "hager" in text:
            return "hager"
        # ... add more as we build them

        return "unknown"

def route_to_parser(pdf_path: str):
    """Route to appropriate parser."""
    manufacturer = detect_manufacturer(pdf_path)

    if manufacturer == "select_hinges":
        from parsers.select import SelectHingesParser
        return SelectHingesParser(pdf_path)
    elif manufacturer == "hager":
        from parsers.hager import HagerParser
        return HagerParser(pdf_path)
    else:
        # Route to Tier 2: Universal parser
        from parsers.universal import UniversalParser
        return UniversalParser(pdf_path)
```

**Benefits**:
- ✅ Fastest (optimized)
- ✅ Most accurate (custom logic)
- ✅ Free (no API costs)

---

### **TIER 2: ML-Based Table Detection** ⏳ (To Build)

**Technology Stack**:
1. **Microsoft Table Transformer (TATR)** - Table detection
2. **LayoutLM** - Document layout understanding
3. **Pattern-based extraction** - Smart heuristics for SKUs, prices

**Implementation**:

```python
# parsers/universal/ml_detector.py
import torch
from transformers import AutoModelForObjectDetection
from PIL import Image
import pdf2image

class MLTableDetector:
    """ML-based table detection using Microsoft TATR."""

    def __init__(self):
        # Load pre-trained models
        self.table_model = AutoModelForObjectDetection.from_pretrained(
            "microsoft/table-transformer-detection"
        )
        self.structure_model = AutoModelForObjectDetection.from_pretrained(
            "microsoft/table-transformer-structure-recognition"
        )

    def detect_tables(self, pdf_path: str) -> List[Dict]:
        """Detect all tables in PDF."""
        # Convert PDF to images
        images = pdf2image.convert_from_path(pdf_path)

        tables = []
        for page_num, img in enumerate(images, 1):
            # Detect table regions
            table_boxes = self._detect_table_regions(img)

            for box in table_boxes:
                # Crop table region
                table_img = img.crop(box)

                # Recognize table structure
                structure = self._recognize_structure(table_img)

                tables.append({
                    "page": page_num,
                    "bbox": box,
                    "structure": structure,
                    "confidence": structure.get("score", 0)
                })

        return tables

    def _detect_table_regions(self, image: Image) -> List:
        """Detect table bounding boxes using TATR."""
        # Run TATR table detection
        outputs = self.table_model(image)
        # Return bounding boxes with confidence > 0.7
        return [box for box in outputs if box["score"] > 0.7]

    def _recognize_structure(self, table_img: Image) -> Dict:
        """Recognize table structure (rows, columns, cells)."""
        # Run TATR structure recognition
        outputs = self.structure_model(table_img)
        return outputs
```

**Then, smart pattern extraction**:

```python
# parsers/universal/pattern_extractor.py
import re
from typing import List, Dict

class SmartPatternExtractor:
    """Intelligent pattern-based extraction for common price book elements."""

    def __init__(self):
        # Common price patterns
        self.price_patterns = [
            r"\$\s*(\d+[\d,]*\.?\d{0,2})",  # $123.45
            r"(\d+[\d,]*\.?\d{2})\s*USD",   # 123.45 USD
            r"Price:\s*(\d+[\d,]*\.?\d{2})", # Price: 123.45
        ]

        # Common SKU patterns
        self.sku_patterns = [
            r"[A-Z]{2,}\d{2,}[A-Z]*",  # SL100, BB1279
            r"\d{3,}-[A-Z0-9-]+",      # 123-ABC-45
            r"[A-Z]+\s*\d+\s*[A-Z]*",  # SL 100 HD
        ]

        # Finish code patterns
        self.finish_patterns = [
            r"US\s*\d+[A-Z]?",  # US26D, US10B
            r"[A-Z]{2,3}\s*\d*", # BR, CL, ORB
        ]

    def extract_from_table(self, table_data: pd.DataFrame) -> List[Dict]:
        """Extract products from detected table."""
        products = []

        for idx, row in table_data.iterrows():
            # Convert row to text
            row_text = " ".join(str(cell) for cell in row)

            # Extract SKU
            sku = self._extract_sku(row_text)
            if not sku:
                continue  # Skip rows without SKU

            # Extract price
            price = self._extract_price(row_text)

            # Extract finish
            finish = self._extract_finish(row_text)

            # Build product
            product = {
                "sku": sku,
                "base_price": price,
                "finish_code": finish,
                "raw_text": row_text,
                "confidence": self._calculate_confidence(sku, price, finish)
            }

            products.append(product)

        return products

    def _extract_sku(self, text: str) -> Optional[str]:
        """Extract SKU using patterns."""
        for pattern in self.sku_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0).strip()
        return None

    def _extract_price(self, text: str) -> Optional[float]:
        """Extract price using patterns."""
        for pattern in self.price_patterns:
            match = re.search(pattern, text)
            if match:
                price_str = match.group(1).replace(",", "")
                try:
                    return float(price_str)
                except ValueError:
                    continue
        return None

    def _extract_finish(self, text: str) -> Optional[str]:
        """Extract finish code using patterns."""
        for pattern in self.finish_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0).strip()
        return None

    def _calculate_confidence(self, sku, price, finish) -> float:
        """Calculate extraction confidence."""
        confidence = 0.0
        if sku:
            confidence += 0.4
        if price and price > 0:
            confidence += 0.4
        if finish:
            confidence += 0.2
        return confidence
```

**Benefits**:
- ✅ Free (open-source models)
- ✅ Works offline
- ✅ Handles 60-70% of unknown manufacturers
- ✅ Fast (GPU accelerated)

**Limitations**:
- ⚠️ Requires GPU for speed (CPU is slow)
- ⚠️ May struggle with very unusual formats

---

### **TIER 3: LLM Vision Parsing** ⏳ (To Build - Fallback)

**Technology**: LlamaParse or GPT-4o Vision

**When to Use**:
- TATR fails to detect tables
- Confidence < 70%
- User requests "high accuracy mode"
- Scanned/poor quality PDFs

**Implementation Option A: LlamaParse** (RECOMMENDED)

```python
# parsers/universal/llm_parser.py
from llama_parse import LlamaParse

class LLMUniversalParser:
    """LLM-based universal parser using LlamaParse."""

    def __init__(self, api_key: str):
        self.parser = LlamaParse(
            api_key=api_key,
            result_type="markdown",  # or "json"
            num_workers=4,
            verbose=True,
            language="en"
        )

    def parse_pdf(self, pdf_path: str) -> Dict:
        """Parse PDF using LlamaParse."""
        # Parse PDF to markdown
        documents = self.parser.load_data(pdf_path)

        # Extract structured data using LLM
        extracted_data = self._extract_with_llm_prompt(documents)

        return extracted_data

    def _extract_with_llm_prompt(self, documents) -> Dict:
        """Use LLM to extract structured data from parsed content."""
        from openai import OpenAI

        client = OpenAI()

        # Combine all document text
        full_text = "\n\n".join(doc.text for doc in documents)

        # Craft extraction prompt
        prompt = f"""
You are analyzing a manufacturer price book PDF. Extract the following structured data:

1. **Manufacturer Name**: The company name
2. **Effective Date**: The price book effective date
3. **Products**: List of products with:
   - SKU/Model number
   - Description
   - Base price (numeric)
   - Finish code (if applicable)
   - Size/dimensions (if applicable)

4. **Options/Adders**: List of options with:
   - Option code
   - Option name
   - Adder value (price adjustment)
   - Adder type (net_add, percent, etc.)

5. **Finishes**: List of finish codes with:
   - Code (e.g., US26D)
   - Name/description
   - BHMA code (if applicable)

Return ONLY valid JSON in this exact format:
{{
  "manufacturer": "string",
  "effective_date": "YYYY-MM-DD",
  "products": [
    {{
      "sku": "string",
      "description": "string",
      "base_price": float,
      "finish_code": "string",
      "size": "string"
    }}
  ],
  "options": [
    {{
      "option_code": "string",
      "option_name": "string",
      "adder_value": float,
      "adder_type": "string"
    }}
  ],
  "finishes": [
    {{
      "code": "string",
      "name": "string",
      "bhma_code": "string"
    }}
  ]
}}

PDF Content:
{full_text[:15000]}  # Limit to avoid token limits

Extract the data now:
"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a precise data extraction assistant. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0
        )

        import json
        return json.loads(response.choices[0].message.content)
```

**Pricing Estimate**:
- LlamaParse: $0.003/page (7,000 free/week)
- GPT-4o: ~$0.02/page
- **For 100-page PDF**: $0.30-$2.00

**Benefits**:
- ✅ Handles ANY format (100% adaptive)
- ✅ Highest accuracy
- ✅ Understands context/semantics
- ✅ No training needed

**Limitations**:
- ⚠️ API costs (but reasonable)
- ⚠️ Requires internet connection
- ⚠️ Slower than local methods

---

## 🎯 Final Universal Parser Architecture

```python
# parsers/universal/parser.py
class UniversalParser:
    """
    Universal adaptive parser that works with ANY manufacturer price book.

    Uses 3-tier routing:
    1. Known manufacturer → custom parser (fastest, free, accurate)
    2. Unknown manufacturer → ML detection (free, good accuracy)
    3. Low confidence/fallback → LLM parsing (paid, highest accuracy)
    """

    def __init__(self, pdf_path: str, config: Dict = None):
        self.pdf_path = pdf_path
        self.config = config or {}

        # Configuration
        self.use_llm_fallback = config.get("use_llm_fallback", True)
        self.llm_api_key = config.get("llm_api_key", os.getenv("OPENAI_API_KEY"))
        self.confidence_threshold = config.get("confidence_threshold", 0.7)

        # Initialize components
        self.ml_detector = MLTableDetector()
        self.pattern_extractor = SmartPatternExtractor()
        if self.use_llm_fallback:
            self.llm_parser = LLMUniversalParser(self.llm_api_key)

    def parse(self) -> Dict[str, Any]:
        """Parse PDF using adaptive 3-tier approach."""
        logger.info(f"Starting universal parsing: {self.pdf_path}")

        # TIER 1: Try known manufacturer parser
        manufacturer = detect_manufacturer(self.pdf_path)
        if manufacturer != "unknown":
            logger.info(f"Known manufacturer detected: {manufacturer}")
            parser = route_to_parser(self.pdf_path)
            results = parser.parse()
            results["parsing_method"] = "known_parser"
            return results

        # TIER 2: ML-based table detection
        logger.info("Unknown manufacturer - using ML table detection")
        tables = self.ml_detector.detect_tables(self.pdf_path)

        if tables:
            # Extract using pattern-based methods
            products = []
            for table in tables:
                table_products = self.pattern_extractor.extract_from_table(table)
                products.extend(table_products)

            # Calculate overall confidence
            avg_confidence = sum(p["confidence"] for p in products) / len(products) if products else 0

            if avg_confidence >= self.confidence_threshold:
                logger.info(f"ML extraction successful (confidence: {avg_confidence:.2f})")
                results = self._build_results_from_ml(products, tables)
                results["parsing_method"] = "ml_detection"
                return results

        # TIER 3: LLM fallback
        if self.use_llm_fallback:
            logger.info("Using LLM fallback for highest accuracy")
            results = self.llm_parser.parse_pdf(self.pdf_path)
            results["parsing_method"] = "llm_vision"
            return results
        else:
            logger.warning("No LLM fallback configured - returning partial results")
            results = self._build_results_from_ml(products, tables) if tables else {}
            results["parsing_method"] = "ml_detection_low_confidence"
            return results

    def _build_results_from_ml(self, products, tables) -> Dict:
        """Build structured results from ML extraction."""
        return {
            "manufacturer": "Unknown",
            "products": products,
            "total_products": len(products),
            "total_tables_detected": len(tables),
            "parsing_metadata": {
                "method": "ml_detection",
                "confidence": sum(p["confidence"] for p in products) / len(products) if products else 0
            }
        }
```

---

## 💰 Cost-Benefit Analysis

### Cost Per PDF Parse:

| Method | Cost/Page | 100-Page PDF | 417-Page Hager | Accuracy | Speed |
|--------|-----------|--------------|-----------------|----------|-------|
| **Known Parser** | $0 | $0 | $0 | 95-98% | 10-30s |
| **ML Detection (TATR)** | $0 | $0 | $0 | 70-85% | 30-60s |
| **LlamaParse** | $0.003 | $0.30 | $1.25 | 90-95% | 60-120s |
| **GPT-4o Vision** | $0.02 | $2.00 | $8.34 | 95-98% | 90-180s |

### Hybrid Approach Savings:

If 50% of PDFs use known parsers, 30% use ML, 20% use LLM:
- **Average cost per 100-page PDF**: (0.5 × $0) + (0.3 × $0) + (0.2 × $0.30) = **$0.06**
- **vs LLM-only**: $0.30 → **80% cost savings**

---

## 🚀 Implementation Timeline

### **Week 1: Foundation**
- ✅ Research (done)
- ⏳ Design universal parser interface
- ⏳ Install Microsoft Table Transformer
- ⏳ Set up LlamaParse API

### **Week 2: Core Implementation**
- ⏳ Build Tier 1 dispatcher (manufacturer detection)
- ⏳ Implement ML table detector (TATR)
- ⏳ Build pattern extractor

### **Week 3: LLM Integration**
- ⏳ Integrate LlamaParse
- ⏳ Build prompt templates
- ⏳ Add confidence scoring

### **Week 4: Testing & Validation**
- ⏳ Test on 20+ manufacturer PDFs
- ⏳ Measure accuracy vs known parsers
- ⏳ Optimize thresholds and routing logic

**Total**: **4 weeks** to production-ready universal parser

---

## 📊 Success Metrics

### Target Accuracy (compared to manual extraction):
- ≥95% for known manufacturers (Tier 1)
- ≥80% for unknown manufacturers (Tier 2 ML)
- ≥90% for LLM fallback (Tier 3)

### Coverage:
- **Month 1**: 7 known parsers + universal ML
- **Month 2**: 15 known parsers + universal
- **Month 3**: 25 known parsers + universal
- **Goal**: 80%+ coverage with hybrid approach

---

## ✅ Recommendation

### **BUILD THE HYBRID 3-TIER SYSTEM**:

**Why**:
1. ✅ Best of all worlds (speed + accuracy + cost)
2. ✅ Scales automatically (works with ANY PDF)
3. ✅ Cost-effective (80% savings vs LLM-only)
4. ✅ Proven technology (2024 state-of-the-art)
5. ✅ Future-proof (can add more known parsers over time)

**Next Steps**:
1. Install Microsoft Table Transformer (1-2 hours)
2. Set up LlamaParse account (free tier: 7,000 pages/week)
3. Build universal parser dispatcher (2-3 days)
4. Test on 10 random manufacturer PDFs (1 day)
5. Deploy and iterate

**Want me to start building this NOW?**
