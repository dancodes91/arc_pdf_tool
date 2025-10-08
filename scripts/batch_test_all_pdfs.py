#!/usr/bin/env python3
"""
Batch test universal parser on ALL sample PDFs.

Tests all PDFs in test_data/pdfs/ to validate universal parser coverage.
Target: 70%+ success rate (90+ PDFs extract products).
"""

import sys
from pathlib import Path
import json
import time
from typing import Dict, List, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.universal import UniversalParser


def test_single_pdf(pdf_path: Path, max_pages: int = 10) -> Dict[str, Any]:
    """
    Test universal parser on a single PDF.

    Args:
        pdf_path: Path to PDF file
        max_pages: Maximum pages to process

    Returns:
        Dict with results or error info
    """
    print(f"\nTesting: {pdf_path.name}")
    print(f"  Processing first {max_pages} pages...")

    start = time.time()
    try:
        parser = UniversalParser(
            str(pdf_path),
            config={
                "max_pages": max_pages,
                "use_ml_detection": True,
                "confidence_threshold": 0.6,
            }
        )
        results = parser.parse()
        elapsed = time.time() - start

        products = results['summary']['total_products']
        tables = results['parsing_metadata']['tables_detected']
        confidence = results['summary'].get('confidence', 0.0)
        manufacturer = results.get('manufacturer', 'Unknown')

        # Success criteria: at least 5 products with >50% confidence
        success = products >= 5 and confidence > 0.5

        status = "SUCCESS" if success else "REVIEW"
        print(f"  {status}: {products} products, {tables} tables, {confidence:.1%} confidence ({elapsed:.1f}s)")

        return {
            "pdf": pdf_path.name,
            "status": "completed",
            "success": success,
            "products": products,
            "tables": tables,
            "confidence": confidence,
            "manufacturer": manufacturer,
            "time": elapsed,
            "error": None
        }

    except Exception as e:
        elapsed = time.time() - start
        error_msg = str(e)
        print(f"  ERROR: {error_msg} ({elapsed:.1f}s)")

        return {
            "pdf": pdf_path.name,
            "status": "error",
            "success": False,
            "products": 0,
            "tables": 0,
            "confidence": 0.0,
            "manufacturer": "Unknown",
            "time": elapsed,
            "error": error_msg
        }


def main():
    """Run batch testing on all PDFs."""
    print("=" * 100)
    print("BATCH TEST: ALL SAMPLE PDFs")
    print("Testing universal parser coverage across all manufacturers")
    print("Target: 70%+ success rate (90/130 PDFs extract 5+ products with >50% confidence)")
    print("=" * 100)

    # Find all PDFs
    pdf_dir = Path("test_data/pdfs")
    all_pdfs = sorted(pdf_dir.glob("*.pdf"))

    # Exclude known custom parser PDFs from success rate calculation
    # (they have custom parsers, so we test them separately)
    exclude_from_success = {
        "2025-select-hinges-price-book.pdf",
        "2025-select-hinges-price-book (1).pdf",
        "2025-hager-price-book.pdf"
    }

    print(f"\nFound {len(all_pdfs)} PDF files")
    print(f"Excluding {len(exclude_from_success)} known custom parser PDFs from success rate")
    print(f"Testing {len(all_pdfs) - len(exclude_from_success)} unknown manufacturer PDFs\n")

    results = []
    successful = 0
    failed = 0
    errors = 0

    start_time = time.time()

    # Test each PDF
    for i, pdf_path in enumerate(all_pdfs, 1):
        print(f"\n[{i}/{len(all_pdfs)}]", end=" ")

        result = test_single_pdf(pdf_path, max_pages=10)
        results.append(result)

        # Track stats (excluding known custom parser PDFs)
        if pdf_path.name not in exclude_from_success:
            if result["success"]:
                successful += 1
            elif result["error"]:
                errors += 1
            else:
                failed += 1

    total_time = time.time() - start_time

    # Calculate statistics
    unknown_count = len(all_pdfs) - len(exclude_from_success)
    success_rate = (successful / unknown_count * 100) if unknown_count > 0 else 0

    # Print summary
    print("\n" + "=" * 100)
    print("BATCH TEST SUMMARY")
    print("=" * 100)

    print(f"\nTotal PDFs Tested: {len(all_pdfs)}")
    print(f"Unknown Manufacturer PDFs: {unknown_count}")
    print(f"Successful: {successful} ({success_rate:.1f}%)")
    print(f"Failed (< 5 products): {failed}")
    print(f"Errors: {errors}")
    print(f"Total Time: {total_time/60:.1f} minutes")

    # Success/Fail determination
    target_met = success_rate >= 70
    print(f"\nTarget (70%+): {'MET' if target_met else 'NOT MET'}")
    print(f"Overall Status: {'PASS' if target_met else 'FAIL'}")

    # Top performers
    print("\n" + "-" * 100)
    print("TOP 10 PERFORMERS:")
    print("-" * 100)
    successful_results = [r for r in results if r["success"]]
    successful_results.sort(key=lambda x: x["products"], reverse=True)

    print(f"{'PDF':<50} {'Products':<12} {'Tables':<10} {'Confidence':<12} {'Time':<8}")
    print("-" * 100)
    for r in successful_results[:10]:
        print(f"{r['pdf'][:50]:<50} {r['products']:<12} {r['tables']:<10} {r['confidence']:<12.1%} {r['time']:<8.1f}s")

    # Problem files
    problem_results = [r for r in results if not r["success"]]
    if problem_results:
        print("\n" + "-" * 100)
        print(f"PROBLEM FILES ({len(problem_results)}):")
        print("-" * 100)
        print(f"{'PDF':<50} {'Products':<12} {'Error':<40}")
        print("-" * 100)
        for r in problem_results[:20]:  # Show first 20
            error = r['error'][:37] + "..." if r['error'] and len(r['error']) > 40 else (r['error'] or "Low product count")
            print(f"{r['pdf'][:50]:<50} {r['products']:<12} {error:<40}")

        if len(problem_results) > 20:
            print(f"\n... and {len(problem_results) - 20} more problem files")

    # Save detailed results
    output_file = Path("test_results/batch_test_all_pdfs.json")
    output_file.parent.mkdir(exist_ok=True)

    summary = {
        "test_date": datetime.now().isoformat(),
        "total_pdfs": len(all_pdfs),
        "unknown_pdfs": unknown_count,
        "successful": successful,
        "failed": failed,
        "errors": errors,
        "success_rate": success_rate,
        "target_met": target_met,
        "total_time_seconds": total_time,
        "results": results
    }

    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n\nDetailed results saved to: {output_file}")
    print("=" * 100 + "\n")

    # Exit code
    sys.exit(0 if target_met else 1)


if __name__ == "__main__":
    main()
