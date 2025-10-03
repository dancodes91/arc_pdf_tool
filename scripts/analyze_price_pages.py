"""Analyze the 99 pages with prices to understand table structures."""
import json
import pdfplumber
import re

# Load analysis
with open('hager_page_analysis.json') as f:
    analysis = json.load(f)

price_pages = analysis['pages_with_prices']
print(f"Analyzing {len(price_pages)} pages with prices...")

# Sample pages from different sections
samples = [
    price_pages[0],   # First
    price_pages[10],  # Early
    price_pages[len(price_pages)//2],  # Middle
    price_pages[-10], # Late
    price_pages[-1],  # Last
]

pdf_path = "test_data/pdfs/2025-hager-price-book.pdf"

with pdfplumber.open(pdf_path) as pdf:
    for page_num in samples:
        print(f"\n{'='*80}")
        print(f"PAGE {page_num}")
        print(f"{'='*80}")

        page = pdf.pages[page_num - 1]
        text = page.extract_text() or ""
        tables = page.extract_tables()

        # Look for product patterns
        bb_pat = r'\bBB\d+'
        ecbb_pat = r'\bECBB\d+'
        wt_pat = r'\bWT\d+'
        price_pat = r'\$\d+\.\d{2}'
        print(f"\nProduct Indicators:")
        print(f"  BB models: {len(re.findall(bb_pat, text))}")
        print(f"  ECBB models: {len(re.findall(ecbb_pat, text))}")
        print(f"  WT models: {len(re.findall(wt_pat, text))}")
        print(f"  Prices ($X.XX): {len(re.findall(price_pat, text))}")
        print(f"  'List' mentions: {text.lower().count('list')}")

        print(f"\nTables: {len(tables)}")
        for i, table in enumerate(tables):
            if not table or len(table) < 2:
                continue

            print(f"\n  Table {i}: {len(table)} rows x {len(table[0]) if table else 0} cols")

            # Check headers
            header = table[0] if len(table) > 0 else []
            print(f"    Headers: {header}")

            # Check if has prices
            table_str = str(table)
            has_price = '$' in table_str
            price_pattern = r'\$\d+\.\d{2}'
            price_count = len(re.findall(price_pattern, table_str))

            # Check if has part numbers
            part_pattern = r'\d{1,2}-\d{3}-\d{4}'
            has_part_num = bool(re.search(part_pattern, table_str))
            part_count = len(re.findall(part_pattern, table_str))

            print(f"    Has prices: {has_price} (count: {price_count})")
            print(f"    Has part numbers: {has_part_num} (count: {part_count})")

            # Sample a data row
            if len(table) > 1:
                data_row = table[1]
                print(f"    Sample row: {data_row}")
