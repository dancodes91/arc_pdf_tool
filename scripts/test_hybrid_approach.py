"""
TEST SCRIPT: Hybrid 3-Layer Extraction Approach

This is a STANDALONE test script that does NOT modify existing code.
Tests the hybrid strategy on sample PDFs to validate near-100% accuracy.

Compare results against current Universal Parser to see improvement.
"""

import sys
import json
import time
import re
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import existing parser for comparison
from parsers.universal.parser import UniversalParser


class HybridTestParser:
    """
    Standalone hybrid parser for testing.

    Does NOT modify existing code - purely for validation.
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.products = []
        self.layer1_products = []
        self.layer2_products = []
        self.layer3_products = []
        self.stats = {
            'layer1_time': 0,
            'layer2_time': 0,
            'layer3_time': 0,
            'layer1_count': 0,
            'layer2_count': 0,
            'layer3_count': 0,
        }

    def parse(self) -> Dict[str, Any]:
        """Run hybrid extraction."""
        print(f"\n{'='*80}")
        print(f"HYBRID TEST: {Path(self.pdf_path).name}")
        print(f"{'='*80}")

        # LAYER 1: Fast text extraction
        print("\n[Layer 1] Fast text extraction (pdfplumber)...")
        start = time.time()
        self.layer1_products = self._layer1_text_extraction()
        self.stats['layer1_time'] = time.time() - start
        self.stats['layer1_count'] = len(self.layer1_products)
        print(f"  → Found {len(self.layer1_products)} products in {self.stats['layer1_time']:.1f}s")

        # LAYER 2: Camelot (conditional)
        if self._should_use_layer2():
            print("\n[Layer 2] Structured table extraction (camelot)...")
            start = time.time()
            self.layer2_products = self._layer2_camelot_extraction()
            self.stats['layer2_time'] = time.time() - start
            self.stats['layer2_count'] = len(self.layer2_products)
            print(f"  → Found {len(self.layer2_products)} additional products in {self.stats['layer2_time']:.1f}s")
        else:
            print("\n[Layer 2] SKIPPED (Layer 1 sufficient)")

        # LAYER 3: ML (last resort)
        if self._should_use_layer3():
            print("\n[Layer 3] Deep ML scan (img2table + PaddleOCR)...")
            start = time.time()
            self.layer3_products = self._layer3_ml_extraction()
            self.stats['layer3_time'] = time.time() - start
            self.stats['layer3_count'] = len(self.layer3_products)
            print(f"  → Found {len(self.layer3_products)} additional products in {self.stats['layer3_time']:.1f}s")
        else:
            print("\n[Layer 3] SKIPPED (not needed)")

        # Merge & deduplicate
        print("\n[Merge] Combining and deduplicating...")
        self.products = self._merge_and_deduplicate()

        total_time = self.stats['layer1_time'] + self.stats['layer2_time'] + self.stats['layer3_time']
        print(f"\n{'='*80}")
        print(f"HYBRID RESULT: {len(self.products)} total products in {total_time:.1f}s")
        print(f"{'='*80}")

        return {
            'total_products': len(self.products),
            'layer1_products': len(self.layer1_products),
            'layer2_products': len(self.layer2_products),
            'layer3_products': len(self.layer3_products),
            'products': self.products,
            'stats': self.stats,
            'total_time': total_time
        }

    def _layer1_text_extraction(self) -> List[Dict]:
        """Layer 1: Fast text extraction with pdfplumber."""
        try:
            import pdfplumber
        except ImportError:
            print("  ✗ pdfplumber not available")
            return []

        products = []
        seen_skus = set()

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract text
                    text = page.extract_text() or ""

                    # Extract simple tables (pdfplumber native)
                    tables = page.extract_tables()

                    # Parse tables
                    for table in tables:
                        if table and len(table) > 1:
                            try:
                                # Convert to DataFrame
                                df = pd.DataFrame(table[1:], columns=table[0])
                                table_products = self._extract_from_dataframe(df, page_num)

                                # Add non-duplicate products
                                for p in table_products:
                                    if p['sku'] not in seen_skus:
                                        products.append(p)
                                        seen_skus.add(p['sku'])
                            except Exception as e:
                                pass  # Skip bad tables

                    # Parse text line-by-line
                    text_products = self._extract_from_text_lines(text, page_num)
                    for p in text_products:
                        if p['sku'] not in seen_skus:
                            products.append(p)
                            seen_skus.add(p['sku'])

        except Exception as e:
            print(f"  ✗ Layer 1 error: {e}")

        return products

    def _extract_from_dataframe(self, df: pd.DataFrame, page_num: int) -> List[Dict]:
        """Extract products from DataFrame."""
        products = []

        # Clean DataFrame
        df = df.fillna('')
        df = df.replace(r'^\s*$', '', regex=True)

        if df.empty:
            return products

        # Identify columns
        sku_col = None
        price_col = None
        desc_col = None

        # Try to find SKU column
        for idx, col in enumerate(df.columns):
            col_str = str(col).lower()
            sample = ' '.join(str(v) for v in df.iloc[:3, idx]).lower()

            if any(kw in col_str or kw in sample for kw in ['sku', 'model', 'part', 'item', 'catalog']):
                sku_col = idx
            elif any(kw in col_str or kw in sample for kw in ['price', 'list', 'cost', '$']):
                price_col = idx
            elif any(kw in col_str for kw in ['desc', 'description', 'name']):
                desc_col = idx

        # Fallback: first column is SKU, find numeric column for price
        if sku_col is None:
            sku_col = 0

        if price_col is None:
            for idx in range(len(df.columns)):
                if idx == sku_col:
                    continue
                # Check if column has numbers
                sample = df.iloc[:5, idx].astype(str)
                if sample.str.contains(r'\d').sum() >= 3:
                    price_col = idx
                    break

        if price_col is None:
            return products

        # Extract products from rows
        for idx, row in df.iterrows():
            sku = str(row.iloc[sku_col]).strip()
            price_str = str(row.iloc[price_col]).strip()

            # Validate SKU
            if not sku or sku.lower() in ['nan', 'none', '']:
                continue

            # Extract price
            price = self._extract_price_from_text(price_str)
            if not price or price <= 0:
                continue

            # Get description
            desc = ''
            if desc_col is not None:
                desc = str(row.iloc[desc_col]).strip()

            products.append({
                'sku': sku,
                'price': price,
                'description': desc[:200],
                'page': page_num,
                'source': 'layer1_table',
                'confidence': 0.85
            })

        return products

    def _extract_from_text_lines(self, text: str, page_num: int) -> List[Dict]:
        """Extract products from text line-by-line."""
        products = []
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue

            # Look for SKU pattern (flexible)
            sku_match = re.search(
                r'\b([A-Z]{2,}[-.]?[A-Z0-9]{2,}[-.]?[A-Z0-9]*)\b',
                line,
                re.IGNORECASE
            )

            # Look for price pattern
            price_match = re.search(
                r'\$\s*(\d{1,6}(?:[,\.]\d{2,3})?)|(?:^|\s)(\d{2,5}\.\d{2})(?:\s|$)',
                line
            )

            if sku_match and price_match:
                sku = sku_match.group(1)
                price_str = price_match.group(1) or price_match.group(2)
                price = self._extract_price_from_text(price_str)

                if price and price > 0:
                    # Extract description (text between SKU and price)
                    desc = line[sku_match.end():price_match.start()].strip()

                    products.append({
                        'sku': sku,
                        'price': price,
                        'description': desc[:200],
                        'page': page_num,
                        'source': 'layer1_text',
                        'confidence': 0.80
                    })

        return products

    def _extract_price_from_text(self, text: str) -> float:
        """Extract price from string."""
        if not text:
            return 0.0

        # Clean text
        text = str(text).replace(',', '').replace('$', '').strip()

        # Try to parse as float
        try:
            price = float(text)
            if 0.01 <= price <= 1000000:
                return price
        except (ValueError, TypeError):
            pass

        # Try to find any number
        match = re.search(r'(\d+(?:\.\d{1,2})?)', text)
        if match:
            try:
                price = float(match.group(1))
                if 1 <= price <= 1000000:
                    return price
            except ValueError:
                pass

        return 0.0

    def _layer2_camelot_extraction(self) -> List[Dict]:
        """Layer 2: Camelot table extraction."""
        try:
            import camelot
        except ImportError:
            print("  ✗ camelot-py not available")
            return []

        products = []
        seen_skus = set(p['sku'] for p in self.layer1_products)

        try:
            # Try lattice (bordered tables)
            tables = camelot.read_pdf(self.pdf_path, pages='all', flavor='lattice')

            print(f"  → Camelot lattice found {len(tables)} tables")

            for table in tables:
                df = table.df
                page_num = table.page

                table_products = self._extract_from_dataframe(df, page_num)

                # Only add products not found in Layer 1
                for p in table_products:
                    if p['sku'] not in seen_skus:
                        p['source'] = 'layer2_lattice'
                        p['confidence'] = 0.90
                        products.append(p)
                        seen_skus.add(p['sku'])

            # If lattice didn't find much, try stream (borderless)
            if len(products) < 5:
                stream_tables = camelot.read_pdf(self.pdf_path, pages='all', flavor='stream')
                print(f"  → Camelot stream found {len(stream_tables)} tables")

                for table in stream_tables:
                    df = table.df
                    page_num = table.page

                    table_products = self._extract_from_dataframe(df, page_num)

                    for p in table_products:
                        if p['sku'] not in seen_skus:
                            p['source'] = 'layer2_stream'
                            p['confidence'] = 0.85
                            products.append(p)
                            seen_skus.add(p['sku'])

        except Exception as e:
            print(f"  ✗ Layer 2 error: {e}")

        return products

    def _layer3_ml_extraction(self) -> List[Dict]:
        """Layer 3: Use existing Universal Parser (ML-based)."""
        products = []
        seen_skus = set(p['sku'] for p in self.layer1_products + self.layer2_products)

        try:
            # Use your existing Universal Parser
            parser = UniversalParser(
                self.pdf_path,
                config={'use_ml_detection': True, 'confidence_threshold': 0.6}
            )
            results = parser.parse()

            # Extract products from results
            for product_item in results.get('products', []):
                if isinstance(product_item, dict):
                    value = product_item.get('value', {})
                else:
                    value = product_item.value if hasattr(product_item, 'value') else {}

                sku = value.get('sku', '')
                price = value.get('base_price', 0)

                if sku and price and sku not in seen_skus:
                    products.append({
                        'sku': sku,
                        'price': price,
                        'description': value.get('description', ''),
                        'page': value.get('page', 0),
                        'source': 'layer3_ml',
                        'confidence': product_item.get('confidence', 0.7)
                    })
                    seen_skus.add(sku)

        except Exception as e:
            print(f"  ✗ Layer 3 error: {e}")

        return products

    def _should_use_layer2(self) -> bool:
        """Decide if Layer 2 is needed."""
        if not self.layer1_products:
            return True

        # If Layer 1 found very few products, use Layer 2
        return len(self.layer1_products) < 20

    def _should_use_layer3(self) -> bool:
        """Decide if Layer 3 is needed."""
        total = len(self.layer1_products) + len(self.layer2_products)

        # Use Layer 3 only if still very low yield
        return total < 10

    def _merge_and_deduplicate(self) -> List[Dict]:
        """Merge results from all layers and remove duplicates."""
        all_products = []
        seen_skus = set()

        # Priority order: Layer 3 (most accurate) > Layer 2 > Layer 1
        for product_list in [self.layer3_products, self.layer2_products, self.layer1_products]:
            for product in product_list:
                sku = product['sku']
                if sku not in seen_skus:
                    all_products.append(product)
                    seen_skus.add(sku)

        return all_products


def compare_parsers(pdf_path: str) -> Dict[str, Any]:
    """Compare Hybrid Test Parser vs Current Universal Parser."""
    print(f"\n{'#'*80}")
    print(f"COMPARISON TEST: {Path(pdf_path).name}")
    print(f"{'#'*80}")

    # Test 1: Current Universal Parser
    print(f"\n[TEST 1] Current Universal Parser (ML-only)")
    print(f"-" * 80)
    start = time.time()
    try:
        current_parser = UniversalParser(
            pdf_path,
            config={'use_ml_detection': True, 'confidence_threshold': 0.6}
        )
        current_results = current_parser.parse()
        current_time = time.time() - start
        current_products = len(current_results.get('products', []))
        current_confidence = current_results.get('summary', {}).get('confidence', 0)
        print(f"✓ Result: {current_products} products, {current_confidence:.1%} confidence, {current_time:.1f}s")
    except Exception as e:
        current_products = 0
        current_time = 0
        current_confidence = 0
        print(f"✗ Error: {e}")

    # Test 2: Hybrid Parser
    print(f"\n[TEST 2] Hybrid 3-Layer Parser")
    print(f"-" * 80)
    start = time.time()
    try:
        hybrid_parser = HybridTestParser(pdf_path)
        hybrid_results = hybrid_parser.parse()
        hybrid_time = time.time() - start
        hybrid_products = hybrid_results['total_products']
    except Exception as e:
        hybrid_products = 0
        hybrid_time = 0
        print(f"✗ Error: {e}")

    # Comparison
    print(f"\n{'='*80}")
    print(f"COMPARISON RESULTS:")
    print(f"{'='*80}")
    print(f"{'Metric':<30} {'Current':<20} {'Hybrid':<20} {'Improvement'}")
    print(f"-" * 80)
    print(f"{'Total Products':<30} {current_products:<20} {hybrid_products:<20} {hybrid_products - current_products:+d}")
    print(f"{'Extraction Time':<30} {current_time:<20.1f} {hybrid_time:<20.1f} {((current_time - hybrid_time) / current_time * 100) if current_time > 0 else 0:+.0f}%")

    if hybrid_products > 0:
        print(f"{'Layer 1 (text)':<30} {'':<20} {hybrid_results['layer1_products']:<20} {hybrid_results['layer1_products'] / hybrid_products * 100:.0f}%")
        print(f"{'Layer 2 (camelot)':<30} {'':<20} {hybrid_results['layer2_products']:<20} {hybrid_results['layer2_products'] / hybrid_products * 100:.0f}%")
        print(f"{'Layer 3 (ML)':<30} {'':<20} {hybrid_results['layer3_products']:<20} {hybrid_results['layer3_products'] / hybrid_products * 100:.0f}%")

    improvement = ((hybrid_products - current_products) / current_products * 100) if current_products > 0 else 0
    print(f"{'='*80}")
    print(f"Overall Improvement: {improvement:+.1f}% more products")
    print(f"{'='*80}\n")

    return {
        'pdf': Path(pdf_path).name,
        'current_products': current_products,
        'hybrid_products': hybrid_products,
        'improvement_percent': improvement,
        'current_time': current_time,
        'hybrid_time': hybrid_time
    }


def main():
    """Run comparison test on sample PDFs."""
    # Test PDFs
    test_pdfs = [
        "test_data/pdfs/2020-continental-access-price-book.pdf",  # Currently gets 29, should get 40+
        "test_data/pdfs/2023-pbb-price-book.pdf",  # Currently FAILS (0 products)
        "test_data/pdfs/2024-alarm-lock-price-book.pdf",  # Currently successful (506 products)
        "test_data/pdfs/2022-lockey-price-book.pdf",  # Currently successful (461 products)
    ]

    results = []

    for pdf in test_pdfs:
        pdf_path = Path(pdf)
        if not pdf_path.exists():
            print(f"\n✗ Skipping {pdf_path.name} (not found)")
            continue

        result = compare_parsers(str(pdf_path))
        results.append(result)

    # Summary
    print(f"\n{'#'*80}")
    print(f"FINAL SUMMARY")
    print(f"{'#'*80}\n")
    print(f"{'PDF':<50} {'Current':<15} {'Hybrid':<15} {'Improvement'}")
    print(f"-" * 80)

    for r in results:
        print(f"{r['pdf']:<50} {r['current_products']:<15} {r['hybrid_products']:<15} {r['improvement_percent']:+.0f}%")

    avg_improvement = sum(r['improvement_percent'] for r in results) / len(results) if results else 0
    print(f"-" * 80)
    print(f"{'AVERAGE':<50} {'':<15} {'':<15} {avg_improvement:+.1f}%")
    print(f"{'='*80}\n")

    # Save results
    output_file = Path("test_results/hybrid_comparison.json")
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to: {output_file}\n")


if __name__ == "__main__":
    main()
