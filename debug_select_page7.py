"""Debug script to inspect SELECT PDF page 7 table extraction."""

import camelot
import pandas as pd

pdf_path = r"test_data\pdfs\2025-select-hinges-price-book.pdf"
page = 7

print(f"=== Extracting tables from page {page} using Camelot ===\n")

# Try both flavors
for flavor in ["lattice", "stream"]:
    print(f"\n{'='*60}")
    print(f"FLAVOR: {flavor}")
    print('='*60)

    try:
        tables = camelot.read_pdf(pdf_path, pages=str(page), flavor=flavor)
        print(f"Found {tables.n} tables\n")

        for i, table in enumerate(tables):
            print(f"\n--- Table {i+1} ---")
            df = table.df
            print(f"Shape: {df.shape}")
            print(f"\nFirst 15 rows:")
            try:
                print(df.head(15).to_string())
            except Exception as e:
                print(f"Error displaying table: {e}")
                # Try without unicode chars
                try:
                    print(df.head(15).to_string(encoding='utf-8', errors='replace'))
                except:
                    print("Could not display table")

            # Look specifically for SL11, SL12, SL14 rows
            print(f"\n\nSearching for SL11/SL12/SL14 rows...")
            for idx, row in df.iterrows():
                try:
                    row_text = " ".join(str(cell) for cell in row)
                    if any(model in row_text.upper() for model in ["SL11", "SL12", "SL14"]):
                        print(f"\nRow {idx}: {list(row)[:6]}")  # First 6 columns only
                except Exception as e:
                    print(f"Error processing row {idx}: {e}")

    except Exception as e:
        print(f"Error with {flavor}: {e}")

print("\n\n" + "="*60)
print("DONE")
print("="*60)
