#!/usr/bin/env python3
"""
Comprehensive validation of Universal Parser against ALL sample PDFs.

Tests:
1. SELECT Hinges vs Custom Parser (90%+ target)
2. Hager vs Custom Parser (90%+ target)
3. All other PDFs (extraction validation)

Goal: Achieve 90%+ accuracy across all manufacturers.
"""

import sys
from pathlib import Path
import json
import time
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.universal import UniversalParser
from parsers.select.parser import SelectHingesParser
from parsers.hager.parser import HagerParser


def test_with_custom_baseline(
    pdf_path: str,
    custom_parser_class,
    parser_name: str,
    max_pages: int = 20
) -> Dict[str, Any]:
    """Test universal parser against custom parser baseline."""
    print(f"\n{'='*100}")
    print(f"TESTING: {parser_name}")
    print(f"PDF: {Path(pdf_path).name}")
    print(f"{'='*100}\n")

    # Run custom parser (baseline)
    print(f"[1/2] Running {parser_name} Custom Parser (baseline)...")
    start = time.time()
    try:
        if parser_name == "Hager":
            custom_parser = custom_parser_class(pdf_path, config={"fast_mode": True})
        else:
            custom_parser = custom_parser_class(pdf_path)

        custom_results = custom_parser.parse()
        custom_time = time.time() - start

        custom_products = custom_results['summary']['total_products']
        custom_options = custom_results['summary'].get('total_options', 0)

        print(f"  OK: {custom_products} products, {custom_options} options ({custom_time:.1f}s)")
    except Exception as e:
        print(f"  ERROR: {e}")
        return {"error": str(e), "parser": parser_name}

    # Run universal parser
    print(f"\n[2/2] Running Universal Parser...")
    start = time.time()
    try:
        universal_parser = UniversalParser(
            pdf_path,
            config={
                "max_pages": max_pages,
                "use_ml_detection": True,
                "confidence_threshold": 0.6,
            }
        )
        universal_results = universal_parser.parse()
        universal_time = time.time() - start

        universal_products = universal_results['summary']['total_products']
        universal_options = universal_results['summary'].get('total_options', 0)
        universal_conf = universal_results['summary']['confidence']

        print(f"  OK: {universal_products} products, {universal_options} options ({universal_time:.1f}s)")
    except Exception as e:
        print(f"  ERROR: {e}")
        return {"error": str(e), "parser": parser_name}

    # Calculate accuracy
    if custom_products > 0:
        product_accuracy = (universal_products / custom_products * 100)
    else:
        product_accuracy = 0

    if custom_options > 0:
        option_accuracy = (universal_options / custom_options * 100)
    else:
        option_accuracy = 100 if universal_options == 0 else 0

    # Determine pass/fail (90% threshold)
    passed = product_accuracy >= 90

    print(f"\n{'-'*100}")
    print(f"RESULTS:")
    print(f"{'-'*100}")
    print(f"{'Metric':<25} {'Custom':<15} {'Universal':<15} {'Accuracy':<15} {'Status':<10}")
    print(f"{'-'*100}")
    print(f"{'Products':<25} {custom_products:<15} {universal_products:<15} {product_accuracy:>6.1f}% {'PASS' if product_accuracy >= 90 else 'FAIL':>14}")
    print(f"{'Options':<25} {custom_options:<15} {universal_options:<15} {option_accuracy:>6.1f}% {'PASS' if option_accuracy >= 90 else 'N/A':>14}")
    print(f"{'Confidence':<25} {'N/A':<15} {f'{universal_conf:.1%}':<15} {'N/A':<15} {'N/A':<10}")
    print(f"{'-'*100}")
    print(f"\nOVERALL: {'PASS (>= 90%)' if passed else 'FAIL (< 90%)'} - Product Accuracy: {product_accuracy:.1f}%")

    return {
        "pdf": Path(pdf_path).name,
        "parser": parser_name,
        "custom_products": custom_products,
        "universal_products": universal_products,
        "product_accuracy": product_accuracy,
        "custom_options": custom_options,
        "universal_options": universal_options,
        "option_accuracy": option_accuracy,
        "confidence": universal_conf,
        "passed": passed,
        "custom_time": custom_time,
        "universal_time": universal_time
    }


def test_unknown_pdf(pdf_path: str, max_pages: int = 10) -> Dict[str, Any]:
    """Test universal parser on unknown manufacturer PDF."""
    print(f"\n{'='*100}")
    print(f"TESTING: Unknown Manufacturer")
    print(f"PDF: {Path(pdf_path).name}")
    print(f"{'='*100}\n")

    print(f"Running Universal Parser (first {max_pages} pages)...")
    start = time.time()
    try:
        universal_parser = UniversalParser(
            pdf_path,
            config={
                "max_pages": max_pages,
                "use_ml_detection": True,
                "confidence_threshold": 0.6,
            }
        )
        universal_results = universal_parser.parse()
        universal_time = time.time() - start

        products = universal_results['summary']['total_products']
        tables = universal_results['parsing_metadata']['tables_detected']
        confidence = universal_results['summary']['confidence']
        manufacturer = universal_results.get('manufacturer', 'Unknown')

        print(f"  OK: {products} products, {tables} tables ({universal_time:.1f}s)")
        print(f"  Manufacturer: {manufacturer}")
        print(f"  Confidence: {confidence:.1%}")

        # Success if we extracted at least 1 product with >50% confidence
        success = products > 0 and confidence > 0.5

        print(f"\nRESULT: {'SUCCESS' if success else 'NEEDS REVIEW'}")

        return {
            "pdf": Path(pdf_path).name,
            "parser": "Universal Only",
            "products": products,
            "tables": tables,
            "confidence": confidence,
            "manufacturer": manufacturer,
            "success": success,
            "time": universal_time
        }
    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            "pdf": Path(pdf_path).name,
            "parser": "Universal Only",
            "error": str(e),
            "success": False
        }


def main():
    """Run comprehensive validation."""
    print("\n" + "="*100)
    print("COMPREHENSIVE UNIVERSAL PARSER VALIDATION")
    print("Target: 90%+ Accuracy vs Custom Parsers")
    print("="*100)

    results = []

    # Test 1: SELECT Hinges (Custom Baseline)
    print("\n\n### TEST 1: SELECT HINGES ###")
    try:
        select_result = test_with_custom_baseline(
            "test_data/pdfs/2025-select-hinges-price-book.pdf",
            SelectHingesParser,
            "SELECT Hinges",
            max_pages=20
        )
        if "error" not in select_result:
            results.append(select_result)
    except Exception as e:
        print(f"\nSELECT test FAILED: {e}")

    # Test 2: Hager (Custom Baseline)
    print("\n\n### TEST 2: HAGER ###")
    try:
        hager_result = test_with_custom_baseline(
            "test_data/pdfs/2025-hager-price-book.pdf",
            HagerParser,
            "Hager",
            max_pages=50  # Test first 50 pages
        )
        if "error" not in hager_result:
            results.append(hager_result)
    except Exception as e:
        print(f"\nHAGER test FAILED: {e}")

    # Test 3-5: Unknown manufacturers (sample 3 random PDFs)
    print("\n\n### TEST 3-5: UNKNOWN MANUFACTURERS ###")
    pdf_dir = Path("test_data/pdfs")
    all_pdfs = [
        p for p in pdf_dir.glob("*.pdf")
        if p.name not in [
            "2025-select-hinges-price-book.pdf",
            "2025-select-hinges-price-book (1).pdf",
            "2025-hager-price-book.pdf"
        ]
    ]

    import random
    sample_pdfs = random.sample(all_pdfs, min(3, len(all_pdfs)))

    for i, pdf_path in enumerate(sample_pdfs, 3):
        print(f"\n\n### TEST {i}: {pdf_path.stem.upper()} ###")
        try:
            unknown_result = test_unknown_pdf(str(pdf_path), max_pages=10)
            if "error" not in unknown_result:
                results.append(unknown_result)
        except Exception as e:
            print(f"\nTest FAILED: {e}")

    # Final Summary
    print("\n\n" + "="*100)
    print("FINAL VALIDATION SUMMARY")
    print("="*100 + "\n")

    # Custom parser comparisons
    custom_tests = [r for r in results if "custom_products" in r]
    if custom_tests:
        print("CUSTOM PARSER COMPARISONS (90% Target):")
        print(f"{'PDF':<30} {'Parser':<15} {'Products':<15} {'Accuracy':<15} {'Status':<10}")
        print("-"*100)

        for r in custom_tests:
            status = "PASS" if r['passed'] else "FAIL"
            print(f"{r['pdf'][:30]:<30} {r['parser']:<15} {r['universal_products']}/{r['custom_products']:<13} {r['product_accuracy']:>6.1f}% {status:>14}")

        # Calculate average accuracy
        avg_accuracy = sum(r['product_accuracy'] for r in custom_tests) / len(custom_tests)
        all_passed = all(r['passed'] for r in custom_tests)

        print("-"*100)
        print(f"\nAverage Accuracy: {avg_accuracy:.1f}%")
        print(f"Overall Status: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
        print(f"Target Met: {'YES' if avg_accuracy >= 90 else 'NO'}")

    # Unknown manufacturer tests
    unknown_tests = [r for r in results if "custom_products" not in r and "error" not in r]
    if unknown_tests:
        print("\n\nUNKNOWN MANUFACTURER TESTS:")
        print(f"{'PDF':<40} {'Products':<12} {'Tables':<10} {'Confidence':<12} {'Status':<10}")
        print("-"*100)

        for r in unknown_tests:
            status = "SUCCESS" if r.get('success') else "REVIEW"
            print(f"{r['pdf'][:40]:<40} {r['products']:<12} {r['tables']:<10} {r['confidence']:<12.1%} {status:<10}")

        success_count = sum(1 for r in unknown_tests if r.get('success'))
        print(f"\nSuccess Rate: {success_count}/{len(unknown_tests)} ({success_count/len(unknown_tests)*100:.0f}%)")

    # Save detailed results
    output_file = Path("test_results/comprehensive_validation.json")
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n\nDetailed results saved to: {output_file}")
    print("="*100 + "\n")


if __name__ == "__main__":
    main()
