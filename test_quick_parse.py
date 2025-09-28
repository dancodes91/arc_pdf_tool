#!/usr/bin/env python3
"""
Quick test of Hager parser - process just key pages for speed.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from parsers.hager.parser import HagerParser
from parsers.shared.pdf_io import EnhancedPDFExtractor

def test_quick_parse():
    """Test parser with key pages only."""
    print("=== QUICK HAGER PARSER TEST ===")

    # Extract just first 15 pages for speed
    extractor = EnhancedPDFExtractor('test_data/pdfs/2025-hager-price-book.pdf')
    doc = extractor.extract_document()

    # Create parser but limit pages
    parser = HagerParser('test_data/pdfs/2025-hager-price-book.pdf')

    # Process key pages manually
    key_pages = doc.pages[:15]  # First 15 pages should have finishes and rules

    finish_symbols = []
    price_rules = []
    hinge_additions = []
    products = []

    for page in key_pages:
        page_text = page.text or ''
        page_num = page.page_number

        # Extract tables for this page
        try:
            tables = parser.section_extractor.extract_tables_with_camelot(
                'test_data/pdfs/2025-hager-price-book.pdf', page_num
            )
        except:
            tables = []

        # Extract data from this page
        page_finishes = parser.section_extractor.extract_finish_symbols(
            page_text, tables, page_num
        )
        page_rules = parser.section_extractor.extract_price_rules(
            page_text, tables, page_num
        )
        page_additions = parser.section_extractor.extract_hinge_additions(
            page_text, tables, page_num
        )
        page_products = parser.section_extractor.extract_item_tables(
            page_text, tables, page_num
        )

        finish_symbols.extend(page_finishes)
        price_rules.extend(page_rules)
        hinge_additions.extend(page_additions)
        products.extend(page_products)

        print(f"Page {page_num}: {len(page_finishes)} finishes, {len(page_rules)} rules, {len(page_additions)} additions, {len(page_products)} products")

    print(f"\n=== RESULTS (First 15 pages) ===")
    print(f"Finish Symbols: {len(finish_symbols)}")
    print(f"Price Rules: {len(price_rules)}")
    print(f"Hinge Additions: {len(hinge_additions)}")
    print(f"Products: {len(products)}")

    if finish_symbols:
        print(f"\nSample finish symbols:")
        for i, fs in enumerate(finish_symbols[:3]):
            print(f"  {i+1}: {fs.value}")

    if price_rules:
        print(f"\nSample price rules:")
        for i, pr in enumerate(price_rules[:3]):
            print(f"  {i+1}: {pr.value}")

    return len(finish_symbols) > 0, len(price_rules) > 0, len(hinge_additions) > 0

if __name__ == "__main__":
    test_quick_parse()