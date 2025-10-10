#!/usr/bin/env python3
"""
Analyze PDF structure to understand exact table layouts.

This script examines multiple sample PDFs to identify:
- Table structure patterns
- Column configurations
- Multi-line cell behavior
- Header detection challenges
"""

import sys
from pathlib import Path
import pdfplumber
import pandas as pd
from tabulate import tabulate

sys.path.insert(0, str(Path(__file__).parent.parent))


def analyze_pdf_tables(pdf_path: str, max_pages: int = 3):
    """Analyze table structure in a PDF."""

    print(f"\n{'='*100}")
    print(f"ANALYZING: {Path(pdf_path).name}")
    print(f"{'='*100}\n")

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        pages_to_check = min(max_pages, total_pages)

        print(f"Total pages: {total_pages}")
        print(f"Analyzing first {pages_to_check} pages\n")

        for page_num in range(pages_to_check):
            page = pdf.pages[page_num]
            print(f"\n--- PAGE {page_num + 1} ---\n")

            # Extract text
            text = page.extract_text() or ""
            lines = text.split('\n')[:15]  # First 15 lines

            print("FIRST 15 LINES OF TEXT:")
            print("-" * 80)
            for i, line in enumerate(lines, 1):
                print(f"{i:2d}: {line[:100]}")  # Truncate long lines

            # Extract tables using pdfplumber
            tables = page.extract_tables()

            if tables:
                print(f"\n\nFOUND {len(tables)} TABLE(S) ON PAGE {page_num + 1}:\n")

                for table_idx, table in enumerate(tables, 1):
                    print(f"\nTable {table_idx}:")
                    print(f"  Rows: {len(table)}")
                    print(f"  Columns: {len(table[0]) if table else 0}")

                    if len(table) > 0:
                        # Show first 10 rows
                        print(f"\n  First 10 rows (raw data):")
                        print("  " + "-" * 90)

                        for row_idx, row in enumerate(table[:10]):
                            # Clean None values
                            cleaned_row = [str(cell) if cell else '' for cell in row]
                            print(f"  Row {row_idx}: {cleaned_row}")

                        # Try to convert to DataFrame
                        try:
                            if len(table) > 1:
                                df = pd.DataFrame(table[1:], columns=table[0])

                                print(f"\n  DataFrame Preview (first 5 rows):")
                                print("  " + "-" * 90)

                                # Show as table
                                for idx, row in df.head(5).iterrows():
                                    print(f"  {idx}: {row.to_dict()}")

                                # Column analysis
                                print(f"\n  Column Analysis:")
                                print("  " + "-" * 90)
                                for col_idx, col_name in enumerate(df.columns):
                                    sample_vals = df[col_name].head(3).tolist()
                                    print(f"  Col {col_idx} ({col_name}): {sample_vals}")

                        except Exception as e:
                            print(f"  ERROR converting to DataFrame: {e}")
            else:
                print(f"\nNO TABLES FOUND ON PAGE {page_num + 1}")
                print("(Page may have borderless tables or complex formatting)")

            print("\n" + "="*100)


def main():
    """Run structure analysis on sample PDFs."""

    # Test PDFs with known issues
    test_pdfs = [
        "test_data/pdfs/2025-select-hinges-price-book.pdf",
        "test_data/pdfs/2025-hager-price-book.pdf",
        "test_data/pdfs/2020-continental-access-price-book.pdf",
        "test_data/pdfs/2022-lockey-price-book.pdf",
    ]

    for pdf_path in test_pdfs:
        if Path(pdf_path).exists():
            try:
                analyze_pdf_tables(pdf_path, max_pages=2)
            except Exception as e:
                print(f"\nERROR analyzing {pdf_path}: {e}\n")
        else:
            print(f"\nSKIPPING (not found): {pdf_path}\n")

    print("\n" + "="*100)
    print("ANALYSIS COMPLETE")
    print("="*100)


if __name__ == "__main__":
    main()
