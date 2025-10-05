#!/usr/bin/env python3
"""
Quick test script to validate Hager parsing with limited pages for Milestone 1 validation.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.hager.parser import HagerParser
from services.exporters import QuickExporter


def main():
    pdf_path = "test_data/pdfs/2025-hager-price-book.pdf"

    print(f"Testing Hager parser with limited pages: {pdf_path}")

    # Initialize parser
    parser = HagerParser()

    # Parse with limited pages for quick validation
    print("Parsing PDF (limited pages for testing)...")
    results = parser.parse(pdf_path, max_pages=50)  # Limit to first 50 pages

    print("\nSUMMARY")
    print(f"  Manufacturer: {results.get('manufacturer', 'Unknown')}")
    print(f"  Effective Date: {results.get('effective_date', 'Not found')}")
    print(f"  Total Finishes: {len(results.get('finishes', []))}")
    print(f"  Total Options: {len(results.get('options', []))}")
    print(f"  Total Items: {len(results.get('items', []))}")
    print(f"  Total Rules: {len(results.get('rules', []))}")

    # Export results
    print("\nExporting results...")
    base_name = "hager_2025_test"

    try:
        # Use QuickExporter for fast validation
        exporter = QuickExporter(output_dir="exports")
        export_paths = exporter.export_all(results, base_name)

        print("\nExports Written:")
        for path in export_paths:
            print(f"  {path}")

        print(f"\n[OK] Test complete! Limited parsing successful.")

        # Quick validation of exports
        print("\nQuick validation:")
        items_csv = Path("exports") / f"{base_name}_items.csv"
        if items_csv.exists():
            with open(items_csv, "r") as f:
                lines = f.readlines()
                print(f"  items.csv: {len(lines)-1} data rows (plus header)")

        options_csv = Path("exports") / f"{base_name}_options.csv"
        if options_csv.exists():
            with open(options_csv, "r") as f:
                lines = f.readlines()
                print(f"  options.csv: {len(lines)-1} data rows (plus header)")

    except Exception as e:
        print(f"Export error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
