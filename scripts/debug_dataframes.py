#!/usr/bin/env python3
"""
Debug script to see what's in the extracted DataFrames.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.universal.img2table_detector import Img2TableDetector

print("Extracting tables from SELECT PDF...")
detector = Img2TableDetector({
    "lang": "en",
    "min_confidence": 50,
    "implicit_rows": True,
    "borderless_tables": True
})

tables = detector.extract_tables_from_pdf(
    "test_data/pdfs/2025-select-hinges-price-book.pdf",
    max_pages=5
)

print(f"\nFound {len(tables)} tables")

for i, table in enumerate(tables, 1):
    df = table['dataframe']
    print(f"\n{'='*80}")
    print(f"TABLE {i} (Page {table['page']}, {table['num_rows']} rows x {table['num_cols']} cols)")
    print(f"{'='*80}")
    print(df.head(10))
    print(f"\nFirst row values: {df.iloc[0].tolist() if not df.empty else 'Empty'}")
