#!/usr/bin/env python3
"""
Debug what Camelot actually extracts from the finish symbols page.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from parsers.hager.sections import HagerSectionExtractor
from parsers.shared.provenance import ProvenanceTracker

def debug_camelot_extraction():
    """Debug what Camelot extracts from page 9."""
    print("=== DEBUGGING CAMELOT EXTRACTION ===")

    # Create section extractor
    tracker = ProvenanceTracker("test.pdf")
    extractor = HagerSectionExtractor(tracker)

    # Extract tables from page 9 where finish symbols should be
    page_num = 9
    try:
        tables = extractor.extract_tables_with_camelot(
            'test_data/pdfs/2025-hager-price-book.pdf', page_num
        )
        print(f"Found {len(tables)} tables on page {page_num}")

        for i, table in enumerate(tables):
            print(f"\n--- TABLE {i+1} ---")
            print(f"Shape: {table.shape}")
            print(f"Columns: {list(table.columns)}")
            print("First few rows:")
            print(table.head())

            # Check if it looks like finish symbols
            table_text = str(table).upper()
            print(f"Contains 'FINISH': {'FINISH' in table_text}")
            print(f"Contains 'US': {'US' in table_text}")
            print(f"Contains 'BHMA': {'BHMA' in table_text}")

            # Debug the table scanning logic
            print("\nDetailed cell contents:")
            for row_idx, row in table.iterrows():
                for col_idx, cell in enumerate(row):
                    cell_str = str(cell).strip()
                    if cell_str and cell_str.lower() not in ['nan', 'none'] and len(cell_str) <= 10:
                        print(f"  [{row_idx},{col_idx}]: '{cell_str}'")
                        # Test the finish code detection logic
                        is_finish_code = (
                            cell_str.startswith('US') or
                            (cell_str.isalnum() and any(c.isdigit() for c in cell_str)) or
                            cell_str in ['2C', '3', '3A', '4', '5', '10', '10A', '10B', '15', '26', '26D', '32D']
                        )
                        if is_finish_code:
                            print(f"    -> DETECTED AS FINISH CODE")
                if row_idx > 10:  # Don't print too much
                    print("    ... (truncated)")
                    break

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def debug_text_patterns():
    """Debug text patterns for price rules."""
    print("\n=== DEBUGGING TEXT PATTERNS ===")

    tracker = ProvenanceTracker("test.pdf")
    extractor = HagerSectionExtractor(tracker)

    # Test various price rule patterns
    test_texts = [
        "20% above US10A or US10B price",
        "US10B use US10A price",
        "US26D uses US26 pricing",
        "For US3 use US4",
    ]

    print("Current price rule patterns:")
    for pattern in extractor.price_rule_patterns:
        print(f"  {pattern}")

    print("\nTesting patterns:")
    for text in test_texts:
        print(f"\nText: '{text}'")
        for i, pattern in enumerate(extractor.price_rule_patterns):
            import re
            match = re.search(pattern, text, re.IGNORECASE)
            print(f"  Pattern {i+1}: {'MATCH' if match else 'NO MATCH'}")
            if match:
                print(f"    Groups: {match.groups()}")

if __name__ == "__main__":
    debug_camelot_extraction()
    debug_text_patterns()