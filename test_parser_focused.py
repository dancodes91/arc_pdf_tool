#!/usr/bin/env python3
"""
Focused test of Hager parser with real PDF data.
Tests each section individually to identify issues.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from parsers.hager.parser import HagerParser
from parsers.shared.pdf_io import EnhancedPDFExtractor

def test_effective_date():
    """Test effective date extraction."""
    print("=== TESTING EFFECTIVE DATE ===")

    # Extract first page only for speed
    extractor = EnhancedPDFExtractor('test_data/pdfs/2025-hager-price-book.pdf')
    doc = extractor.extract_document()

    # Test with just first page (has "Effective 3/31/2025")
    first_page_text = doc.pages[0].text or ''
    print(f"First page text contains 'Effective': {'Effective' in first_page_text}")
    print(f"First 200 chars: {first_page_text[:200]}")

    # Test parsing using the data normalizer directly
    from parsers.shared.normalization import data_normalizer
    result = data_normalizer.normalize_date(first_page_text)
    print(f"Extracted date: {result}")
    return result and result.get('value') is not None

def test_finish_symbols():
    """Test finish symbols extraction."""
    print("\n=== TESTING FINISH SYMBOLS ===")
    parser = HagerParser('test_data/pdfs/2025-hager-price-book.pdf')

    # Use pages 9-10 where we found finish symbols
    extractor = EnhancedPDFExtractor('test_data/pdfs/2025-hager-price-book.pdf')
    doc = extractor.extract_document()

    for page_num in [9, 10]:
        page = doc.pages[page_num - 1]
        page_text = page.text or ''
        print(f"\nPage {page_num}:")
        print(f"  Contains 'ARCHITECTURAL FINISH': {'ARCHITECTURAL FINISH' in page_text.upper()}")
        print(f"  Contains 'US10': {'US10' in page_text}")
        print(f"  Contains 'BHMA': {'BHMA' in page_text}")

        # Try to extract tables with Camelot (just this page)
        try:
            tables = parser.section_extractor.extract_tables_with_camelot(
                'test_data/pdfs/2025-hager-price-book.pdf', page_num
            )
            print(f"  Camelot found {len(tables)} tables")

            # Try to extract finish symbols
            symbols = parser.section_extractor.extract_finish_symbols(
                page_text, tables, page_num
            )
            print(f"  Extracted {len(symbols)} finish symbols")

            if symbols:
                for i, symbol in enumerate(symbols[:3]):
                    print(f"    {i+1}: {symbol.value}")
                return True
        except Exception as e:
            print(f"  Error: {e}")

    return False

def test_price_rules():
    """Test price rules extraction."""
    print("\n=== TESTING PRICE RULES ===")
    parser = HagerParser('test_data/pdfs/2025-hager-price-book.pdf')

    # Test with a page that has "20% above US10A or US10B price"
    test_text = "20% above US10A or US10B price"
    print(f"Testing with text: '{test_text}'")

    try:
        rules = parser.section_extractor.extract_price_rules(test_text, [], 9)
        print(f"Extracted {len(rules)} price rules")
        if rules:
            for rule in rules:
                print(f"  Rule: {rule.value}")
            return True
    except Exception as e:
        print(f"Error: {e}")

    return False

def main():
    """Run focused tests."""
    print("FOCUSED HAGER PARSER TEST")
    print("Testing individual sections to identify issues...")

    results = {
        'effective_date': test_effective_date(),
        'finish_symbols': test_finish_symbols(),
        'price_rules': test_price_rules()
    }

    print(f"\nRESULTS:")
    for section, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"  {section}: {status}")

    if all(results.values()):
        print("\nAll sections working - parser should extract non-zero data!")
    else:
        print("\nSome sections need fixes")

if __name__ == "__main__":
    main()