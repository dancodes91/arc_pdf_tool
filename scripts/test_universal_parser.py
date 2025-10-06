#!/usr/bin/env python3
"""
Quick test script for Universal Parser.

Tests ML-based table detection on random manufacturer PDFs.
"""

import sys
from pathlib import Path
import logging
import json
import random

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.universal import UniversalParser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_single_pdf(pdf_path: str, output_dir: str = None):
    """Test universal parser on a single PDF."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing: {pdf_path}")
    logger.info(f"{'='*60}\n")

    # Parse with universal parser
    parser = UniversalParser(
        pdf_path,
        config={
            "max_pages": 10,  # Limit to first 10 pages for quick test
            "use_ml_detection": True,
            "extract_structure": False,  # Skip structure for speed
            "confidence_threshold": 0.6,
        }
    )

    results = parser.parse()

    # Print summary
    print(f"\nRESULTS:")
    print(f"  Manufacturer: {results.get('manufacturer', 'Unknown')}")
    print(f"  Products found: {results['summary']['total_products']}")
    print(f"  Options found: {results['summary']['total_options']}")
    print(f"  Finishes found: {results['summary']['total_finishes']}")
    print(f"  Tables detected: {results['parsing_metadata']['tables_detected']}")
    print(f"  Confidence: {results['summary']['confidence']:.2%}")

    # Show sample products
    if results['products']:
        print(f"\nSample Products:")
        for i, product in enumerate(results['products'][:5], 1):
            p = product['value']
            print(f"  {i}. SKU: {p.get('sku', 'N/A')}, Price: ${p.get('base_price', 0):.2f}, Confidence: {product['confidence']:.2%}")

    # Save results if output_dir specified
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        pdf_name = Path(pdf_path).stem
        output_file = output_path / f"{pdf_name}_universal_results.json"

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"Results saved to: {output_file}")

    return results


def test_multiple_pdfs(pdf_dir: str, num_samples: int = 10):
    """Test universal parser on multiple random PDFs."""
    pdf_path = Path(pdf_dir)

    # Get all PDFs
    all_pdfs = list(pdf_path.glob("*.pdf"))
    logger.info(f"Found {len(all_pdfs)} PDF files in {pdf_dir}")

    # Sample random PDFs
    sample_pdfs = random.sample(all_pdfs, min(num_samples, len(all_pdfs)))

    logger.info(f"\nTesting {len(sample_pdfs)} random PDFs...\n")

    results_summary = []

    for i, pdf_file in enumerate(sample_pdfs, 1):
        logger.info(f"\n[{i}/{len(sample_pdfs)}] Testing: {pdf_file.name}")

        try:
            results = test_single_pdf(str(pdf_file))

            results_summary.append({
                "file": pdf_file.name,
                "manufacturer": results.get('manufacturer', 'Unknown'),
                "products": results['summary']['total_products'],
                "options": results['summary']['total_options'],
                "finishes": results['summary']['total_finishes'],
                "tables": results['parsing_metadata']['tables_detected'],
                "confidence": results['summary']['confidence'],
                "status": "success"
            })

        except Exception as e:
            logger.error(f"Failed to parse {pdf_file.name}: {e}")
            results_summary.append({
                "file": pdf_file.name,
                "status": "failed",
                "error": str(e)
            })

    # Print summary
    print(f"\n\n{'='*80}")
    print(f"UNIVERSAL PARSER TEST SUMMARY")
    print(f"{'='*80}\n")

    success_count = sum(1 for r in results_summary if r['status'] == 'success')
    print(f"Total PDFs tested: {len(results_summary)}")
    print(f"Successful parses: {success_count}/{len(results_summary)} ({success_count/len(results_summary)*100:.1f}%)")

    print(f"\nDetailed Results:")
    for r in results_summary:
        if r['status'] == 'success':
            print(f"  {r['file'][:50]:50s} | {r['manufacturer']:20s} | Products: {r['products']:3d} | Tables: {r['tables']:2d} | Conf: {r['confidence']:.2%}")
        else:
            print(f"  {r['file'][:50]:50s} | FAILED: {r.get('error', 'Unknown error')}")

    return results_summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Universal Parser")
    parser.add_argument(
        "--pdf",
        type=str,
        help="Single PDF file to test"
    )
    parser.add_argument(
        "--dir",
        type=str,
        default="test_data/pdfs",
        help="Directory of PDFs to test (default: test_data/pdfs)"
    )
    parser.add_argument(
        "--num",
        type=int,
        default=10,
        help="Number of random PDFs to test (default: 10)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output directory for results"
    )

    args = parser.parse_args()

    if args.pdf:
        # Test single PDF
        test_single_pdf(args.pdf, args.output)
    else:
        # Test multiple random PDFs
        test_multiple_pdfs(args.dir, args.num)
