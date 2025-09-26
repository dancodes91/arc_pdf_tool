#!/usr/bin/env python3
"""
Test the enhanced Hager parser with real PDF data.
"""
import sys
import json
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from parsers.hager.parser import HagerParser

def main():
    print("=== Testing Enhanced Hager Parser ===")

    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Test with real PDF
    pdf_path = "D:\%BkUP_DntRmvMe!\MyDocDrvD\Desktop\projects\arc_pdf_tool\test_data\pdfs\2025-hager-price-book.pdf"

    if not Path(pdf_path).exists():
        print(f"ERROR: PDF file not found: {pdf_path}")
        return False

    print(f"Testing with PDF: {pdf_path}")

    try:
        # Parse with enhanced parser
        parser = HagerParser(pdf_path)
        results = parser.parse()

        # Display results summary
        print("\n📊 PARSING RESULTS:")
        print(f"   Products: {len(results.get('products', []))}")
        print(f"   Finish Symbols: {len(results.get('finish_symbols', []))}")
        print(f"   Price Rules: {len(results.get('price_rules', []))}")
        print(f"   Hinge Additions: {len(results.get('hinge_additions', []))}")
        print(f"   Effective Date: {results.get('effective_date', 'Not found')}")

        # Check for improvement
        products_count = len(results.get('products', []))
        finishes_count = len(results.get('finish_symbols', []))
        rules_count = len(results.get('price_rules', []))
        additions_count = len(results.get('hinge_additions', []))

        print("\n🎯 ENHANCEMENT STATUS:")
        if finishes_count > 0:
            print(f"   ✅ Finish symbols extraction: IMPROVED ({finishes_count} found)")
        else:
            print(f"   ⚠️  Finish symbols extraction: Still needs work (0 found)")

        if additions_count > 0:
            print(f"   ✅ Hinge additions extraction: IMPROVED ({additions_count} found)")
        else:
            print(f"   ⚠️  Hinge additions extraction: Still needs work (0 found)")

        if rules_count > 0:
            print(f"   ✅ Price rules extraction: IMPROVED ({rules_count} found)")
        else:
            print(f"   ⚠️  Price rules extraction: Still needs work (0 found)")

        print(f"   📦 Product extraction: {products_count} products")

        # Export results for inspection
        output_file = "enhanced_parser_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Results exported to: {output_file}")

        # Success criteria
        total_non_product_items = finishes_count + rules_count + additions_count
        if total_non_product_items > 0:
            print(f"\n🎉 SUCCESS: Enhanced parser extracted {total_non_product_items} non-product items!")
            print("   This is a significant improvement over the previous 0 count.")
            return True
        else:
            print(f"\n⚠️  NEEDS MORE WORK: Still extracting 0 finish symbols, rules, and additions")
            return False

    except Exception as e:
        print(f"❌ Error during parsing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)