#!/usr/bin/env python3
"""
Quick test of hybrid parser integration on sample PDFs.
Validates that hybrid approach is working correctly.
"""

import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.universal import UniversalParser


def test_pdf(pdf_path: str, name: str):
    """Test a single PDF with hybrid parser."""
    print(f"\n{'='*80}")
    print(f"Testing: {name}")
    print('='*80)

    start = time.time()
    parser = UniversalParser(
        pdf_path,
        config={
            'max_pages': None,  # Process all pages
            'use_hybrid': True,  # Enable hybrid approach
            'use_ml_detection': True,
            'confidence_threshold': 0.6,
        }
    )
    results = parser.parse()
    elapsed = time.time() - start

    products = results['summary']['total_products']
    confidence = results['summary'].get('confidence', 0)
    tables = results['parsing_metadata']['tables_detected']

    print(f"Products: {products}")
    print(f"Confidence: {confidence:.1%}")
    print(f"Tables: {tables}")
    print(f"Time: {elapsed:.2f}s")

    return {
        'name': name,
        'products': products,
        'confidence': confidence,
        'time': elapsed,
        'success': products > 0
    }


def main():
    """Run quick hybrid test on sample PDFs."""
    print("\n" + "="*80)
    print("QUICK HYBRID PARSER TEST")
    print("Testing integrated 3-layer hybrid approach")
    print("="*80)

    # Test a variety of PDFs
    test_cases = [
        ("test_data/pdfs/2020-continental-access-price-book.pdf", "Continental Access (previous: 12)"),
        ("test_data/pdfs/2022-lockey-price-book.pdf", "Lockey (previous: 461)"),
        ("test_data/pdfs/2024-alarm-lock-price-book.pdf", "Alarm Lock (previous: 506)"),
    ]

    results = []
    for pdf_path, name in test_cases:
        if not Path(pdf_path).exists():
            print(f"\nSkipping {name}: File not found")
            continue

        try:
            result = test_pdf(pdf_path, name)
            results.append(result)
        except Exception as e:
            print(f"\nERROR: {e}")
            results.append({
                'name': name,
                'products': 0,
                'confidence': 0,
                'time': 0,
                'success': False
            })

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    successful = sum(1 for r in results if r['success'])
    total = len(results)

    print(f"\nSuccess Rate: {successful}/{total} ({successful/total*100:.1f}%)")
    print(f"\nResults:")
    print(f"{'PDF':<45} {'Products':<12} {'Confidence':<12} {'Time':<8}")
    print("-"*80)
    for r in results:
        print(f"{r['name']:<45} {r['products']:<12} {r['confidence']:<12.1%} {r['time']:<8.2f}s")

    print("\n" + "="*80)
    print("Hybrid integration test complete!")
    print("="*80)


if __name__ == "__main__":
    main()
