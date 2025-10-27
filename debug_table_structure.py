"""Debug script to see the actual table structure from SELECT PDF."""
import camelot
import pandas as pd

pdf_path = r'C:\Users\Vache\projects\arc_pdf_tool\test_data\pdfs\2025-select-hinges-price-book.pdf'

# Extract table from page 7 (first product page)
print("Extracting tables from page 7...")
tables = camelot.read_pdf(pdf_path, pages='7', flavor='lattice')

print(f"\nFound {tables.n} tables on page 7\n")

for i, table in enumerate(tables):
    df = table.df
    print(f"=== TABLE {i} ===")
    print(f"Shape: {df.shape}")
    print(f"\nColumn headers (first row):")
    print(df.iloc[0].tolist())
    print(f"\nFirst 5 rows:")
    print(df.head(5).to_string())
    print("\n" + "="*80 + "\n")
