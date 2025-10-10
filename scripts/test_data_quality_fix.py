#!/usr/bin/env python3
"""
Test the data quality fixes on Continental Access PDF.

Tests:
1. Header detection (skip title rows)
2. Price cleaning (handle "$ 1 ,145.00")
3. Effective date extraction ("AS OF MARCH 9 2020")
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.universal import UniversalParser


def main():
    """Test data quality fixes on Continental Access."""

    pdf_path = "test_data/pdfs/2020-continental-access-price-book.pdf"

    print("=" * 100)
    print("TESTING DATA QUALITY FIXES")
    print("PDF: Continental Access (2020)")
    print("=" * 100)

    print("\nRunning Universal Parser with fixes...")

    parser = UniversalParser(
        pdf_path,
        config={
            "max_pages": 3,  # First 3 pages
            "use_ml_detection": False,  # Use pdfplumber only (faster)
            "use_hybrid": True,
        }
    )

    results = parser.parse()

    # Extract results
    products = results.get('products', [])
    effective_date = results.get('effective_date')
    summary = results.get('summary', {})

    print(f"\n{'='*100}")
    print("RESULTS:")
    print(f"{'='*100}\n")

    print(f"Total Products: {len(products)}")
    print(f"Effective Date: {effective_date or 'NOT FOUND'}")
    print(f"Confidence: {summary.get('confidence', 0):.1%}\n")

    if len(products) > 0:
        print(f"{'='*100}")
        print(f"FIRST 10 PRODUCTS (Quality Check):")
        print(f"{'='*100}\n")

        for i, product in enumerate(products[:10], 1):
            # Handle multiple product formats:
            # 1. ParsedItem object with .value attribute
            # 2. Dict with 'value' key (hybrid parser format)
            # 3. Plain dict (legacy format)
            if hasattr(product, 'value'):
                # ParsedItem object
                product_data = product.value
            elif isinstance(product, dict) and 'value' in product:
                # Dict with 'value' key
                product_data = product['value']
            else:
                # Plain dict
                product_data = product

            sku = product_data.get('sku', 'N/A')
            model = product_data.get('model', 'N/A')
            price = product_data.get('base_price', 0)
            description = product_data.get('description', 'N/A')
            if description and len(description) > 60:
                description = description[:60]

            print(f"{i}.")
            print(f"   SKU: {sku}")
            print(f"   Model: {model}")
            print(f"   Price: ${price:.2f}")
            print(f"   Description: {description}...")
            print()

        # Quality checks
        print(f"{'='*100}")
        print(f"QUALITY CHECKS:")
        print(f"{'='*100}\n")

        # Check for garbage SKUs
        garbage_skus = []
        for p in products:
            # Handle multiple formats (same as above)
            if hasattr(p, 'value'):
                product_data = p.value
            elif isinstance(p, dict) and 'value' in p:
                product_data = p['value']
            else:
                product_data = p

            sku = product_data.get('sku', '')
            if sku.lower() in ['per', 'of', 'to', 'lock', 'pin', 'bag', 'box']:
                garbage_skus.append(sku)

        if garbage_skus:
            print(f"X Found {len(garbage_skus)} garbage SKUs: {garbage_skus}")
        else:
            print(f"OK - No garbage SKUs found")

        # Check for valid prices
        invalid_prices = []
        for p in products:
            # Handle multiple formats (same as above)
            if hasattr(p, 'value'):
                product_data = p.value
            elif isinstance(p, dict) and 'value' in p:
                product_data = p['value']
            else:
                product_data = p

            price = product_data.get('base_price', 0)
            if not price or price < 1:
                invalid_prices.append(product_data)

        if invalid_prices:
            print(f"X Found {len(invalid_prices)} invalid prices")
        else:
            print(f"OK - All prices valid (>= $1.00)")

        # Check effective date
        if effective_date:
            print(f"OK - Effective date found: {effective_date}")
        else:
            print(f"X Effective date NOT found (should be 'MARCH 9 2020')")

        # Success criteria
        print(f"\n{'='*100}")
        print(f"SUCCESS CRITERIA:")
        print(f"{'='*100}\n")

        # Expected: 10-15 clean products (not 27 garbage)
        clean_products = len(products) - len(garbage_skus)
        expected_min = 10
        expected_max = 20

        if expected_min <= clean_products <= expected_max:
            print(f"OK - Product count: {clean_products} (expected {expected_min}-{expected_max})")
        else:
            print(f"X Product count: {clean_products} (expected {expected_min}-{expected_max})")

        # All prices should be valid
        if len(invalid_prices) == 0:
            print(f"OK - Price quality: All prices valid")
        else:
            print(f"X Price quality: {len(invalid_prices)} invalid prices")

        # Effective date should be found
        date_str = effective_date.get('value') if isinstance(effective_date, dict) else effective_date
        if date_str:
            print(f"OK - Date extraction: '{date_str}' found")
        else:
            print(f"X Date extraction: Date not found")

        # Overall verdict
        print(f"\n{'='*100}")
        if (expected_min <= clean_products <= expected_max and
            len(invalid_prices) == 0 and
            date_str):
            print(f"OK - ALL FIXES WORKING - DATA QUALITY: EXCELLENT")
        else:
            print(f"WARNING - SOME ISSUES REMAIN - SEE DETAILS ABOVE")
        print(f"{'='*100}\n")

    else:
        print("X NO PRODUCTS EXTRACTED - PARSER FAILED\n")


if __name__ == "__main__":
    main()
