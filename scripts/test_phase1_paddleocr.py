#!/usr/bin/env python3
"""
Quick test of Phase 1 PaddleOCR integration with real PDFs.

Tests:
1. PaddleOCR availability
2. Universal Parser with PaddleOCR enabled
3. Extraction quality metrics
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.universal import UniversalParser
from parsers.shared.paddleocr_processor import PaddleOCRProcessor

def test_paddleocr_availability():
    """Test if PaddleOCR is installed and working."""
    print("=" * 60)
    print("TEST 1: PaddleOCR Availability")
    print("=" * 60)

    processor = PaddleOCRProcessor()

    if processor.is_available():
        print("[OK] PaddleOCR is installed and available")
        return True
    else:
        print("[FAIL] PaddleOCR is NOT available")
        print("   Install with: pip install paddleocr")
        return False


def test_universal_parser_with_pdf(pdf_path: str):
    """Test Universal Parser with a real PDF."""
    print("\n" + "=" * 60)
    print(f"TEST 2: Universal Parser with PaddleOCR")
    print(f"PDF: {Path(pdf_path).name}")
    print("=" * 60)

    # Create parser
    parser = UniversalParser(
        pdf_path,
        config={
            'use_hybrid': True,
            'use_ml_detection': True,
            'confidence_threshold': 0.6,
            'max_pages': 5  # Test first 5 pages only
        }
    )

    print("\n[PARSING] PDF (first 5 pages)...")
    results = parser.parse()

    # Extract metrics
    metadata = results.get('parsing_metadata', {})
    products = results.get('products', [])
    summary = results.get('summary', {})

    print("\n[RESULTS]")
    print(f"   Total Products: {len(products)}")
    print(f"   Overall Confidence: {metadata.get('overall_confidence', 0):.1%}")

    # Count by extraction method
    layer1_count = sum(1 for p in products if p.get('provenance', {}).get('extraction_method') == 'layer1_text')
    layer2_count = sum(1 for p in products if p.get('provenance', {}).get('extraction_method') == 'layer2_camelot')
    layer3_count = sum(1 for p in products if p.get('provenance', {}).get('extraction_method') == 'layer3_ml')
    layer3_paddle_count = sum(1 for p in products if p.get('provenance', {}).get('extraction_method') == 'layer3_paddleocr')

    print(f"\n[EXTRACTION METHODS]")
    print(f"   Layer 1 (pdfplumber): {layer1_count} products")
    print(f"   Layer 2 (camelot): {layer2_count} products")
    print(f"   Layer 3 (img2table): {layer3_count} products")
    print(f"   Layer 3 (PaddleOCR): {layer3_paddle_count} products **NEW**")

    # Show sample products
    if products:
        print(f"\n[SAMPLE PRODUCTS] (first 3):")
        for i, product in enumerate(products[:3], 1):
            value = product.get('value', {})
            provenance = product.get('provenance', {})
            print(f"\n   Product {i}:")
            print(f"      SKU: {value.get('sku', 'N/A')}")
            print(f"      Price: ${value.get('base_price', 0):.2f}")
            print(f"      Description: {value.get('description', 'N/A')[:50]}...")
            print(f"      Confidence: {product.get('confidence', 0):.1%}")
            print(f"      Method: {provenance.get('extraction_method', 'unknown')}")

    # Check if PaddleOCR was actually used
    if layer3_paddle_count > 0:
        print(f"\n[SUCCESS] PaddleOCR extracted {layer3_paddle_count} products!")
        improvement = (layer3_paddle_count / len(products) * 100) if products else 0
        print(f"   PaddleOCR contribution: {improvement:.1f}% of total products")
    else:
        print(f"\n[NOTE] PaddleOCR was not used (all pages succeeded in Layers 1+2)")
        print(f"   This is OK - PaddleOCR only activates for failed pages")

    return results


def test_multiple_pdfs():
    """Test with multiple PDFs to validate PaddleOCR integration."""
    test_pdfs = [
        "test_data/pdfs/2025-hager-price-book.pdf",
        "test_data/pdfs/2025-select-hinges-price-book.pdf",
        "test_data/pdfs/2020-continental-access-price-book.pdf",
    ]

    print("\n" + "=" * 60)
    print("TEST 3: Multiple PDF Validation")
    print("=" * 60)

    results_summary = []

    for pdf_path in test_pdfs:
        if not Path(pdf_path).exists():
            print(f"\n[SKIP] {Path(pdf_path).name} (not found)")
            continue

        try:
            results = test_universal_parser_with_pdf(pdf_path)
            products = results.get('products', [])
            layer3_paddle = sum(
                1 for p in products
                if p.get('provenance', {}).get('extraction_method') == 'layer3_paddleocr'
            )

            results_summary.append({
                'pdf': Path(pdf_path).name,
                'total_products': len(products),
                'paddleocr_products': layer3_paddle,
                'confidence': results.get('parsing_metadata', {}).get('overall_confidence', 0)
            })

        except Exception as e:
            print(f"\n[ERROR] testing {Path(pdf_path).name}: {e}")
            continue

        print("\n" + "-" * 60)

    # Summary table
    if results_summary:
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"\n{'PDF':<40} {'Products':<12} {'PaddleOCR':<12} {'Confidence'}")
        print("-" * 80)
        for r in results_summary:
            print(f"{r['pdf']:<40} {r['total_products']:<12} {r['paddleocr_products']:<12} {r['confidence']:.1%}")


if __name__ == '__main__':
    print("\n>>> Phase 1 PaddleOCR Integration Test\n")

    # Test 1: Check PaddleOCR availability
    paddleocr_available = test_paddleocr_availability()

    if not paddleocr_available:
        print("\n[!] PaddleOCR not available. Install to enable enhanced accuracy:")
        print("   pip install paddleocr")
        print("\nContinuing test with fallback extraction...")

    # Test 2: Single PDF test
    test_pdf = "test_data/pdfs/2025-hager-price-book.pdf"
    if Path(test_pdf).exists():
        test_universal_parser_with_pdf(test_pdf)
    else:
        print(f"\n[!] Test PDF not found: {test_pdf}")

    # Test 3: Multiple PDFs
    test_multiple_pdfs()

    print("\n[DONE] Testing complete!")
