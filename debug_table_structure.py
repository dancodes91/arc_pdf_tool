"""Debug script to inspect specific rows of table 0 on page 7."""

import camelot
import pandas as pd

pdf_path = r"test_data\pdfs\2025-select-hinges-price-book.pdf"
page = 7

print("Extracting page 7, table 0 with lattice...")
tables = camelot.read_pdf(pdf_path, pages=str(page), flavor="lattice")

if tables.n > 0:
    df = tables[0].df
    print(f"\nTable shape: {df.shape}")
    print(f"\nHeader row (row 0):")
    print(f"  {list(df.iloc[0])}")

    print(f"\nInspecting specific rows:")
    for row_idx in [25, 26, 27, 28, 29, 30, 31, 32, 33, 34]:
        if row_idx < len(df):
            row = df.iloc[row_idx]
            print(f"\nRow {row_idx}:")
            for col_idx, value in enumerate(row):
                print(f"  Col {col_idx}: '{value}'")
