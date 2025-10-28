"""Test extraction from specific Hager pages."""
import camelot
import pandas as pd

pdf_path = r'C:\Users\Vache\projects\arc_pdf_tool\test_data\pdfs\2025-hager-price-book.pdf'

# Test page 80-85 range (user mentioned around page 80)
for page_num in range(80, 86):
    print(f"\n{'='*80}")
    print(f"PAGE {page_num}")
    print('='*80)

    # Try lattice first
    print(f"\n--- Lattice flavor ---")
    lattice_tables = camelot.read_pdf(pdf_path, pages=str(page_num), flavor='lattice')
    print(f"Found {lattice_tables.n} tables")

    # Try stream
    print(f"\n--- Stream flavor ---")
    stream_tables = camelot.read_pdf(pdf_path, pages=str(page_num), flavor='stream')
    print(f"Found {stream_tables.n} tables")

    if stream_tables.n > 0:
        print(f"\nTable structure from stream:")
        df = stream_tables[0].df
        print(f"Shape: {df.shape}")
        print(f"Header row: {df.iloc[0].tolist()}")
        print(f"\nFirst 3 data rows:")
        print(df.iloc[1:4].to_string())
