"""
Diagnostic script to understand Hager PDF table structures.
"""

import pdfplumber
import camelot


def diagnose_page(pdf_path: str, page_num: int):
    """Diagnose a single page to see table structure."""
    print(f"\n{'='*80}")
    print(f"DIAGNOSING PAGE {page_num}")
    print(f"{'='*80}")

    # Extract with pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        if page_num > len(pdf.pages):
            print(f"Page {page_num} doesn't exist (PDF has {len(pdf.pages)} pages)")
            return

        page = pdf.pages[page_num - 1]  # pdfplumber is 0-indexed

        print(f"\n--- TEXT CONTENT (first 500 chars) ---")
        text = page.extract_text() or ""
        print(text[:500])

        print(f"\n--- TABLES FOUND WITH PDFPLUMBER ---")
        tables = page.extract_tables()
        print(f"Number of tables: {len(tables)}")

        for i, table in enumerate(tables):
            print(f"\nTable {i}:")
            print(f"  Rows: {len(table)}")
            print(f"  Cols: {len(table[0]) if table else 0}")
            print(f"  First few rows:")
            for row_idx, row in enumerate(table[:3]):
                print(f"    Row {row_idx}: {row}")

    # Extract with Camelot
    print(f"\n--- TABLES FOUND WITH CAMELOT (lattice) ---")
    try:
        tables_lattice = camelot.read_pdf(pdf_path, pages=str(page_num), flavor="lattice")
        print(f"Number of tables: {len(tables_lattice)}")

        for i, table in enumerate(tables_lattice):
            df = table.df
            print(f"\nTable {i}:")
            print(f"  Shape: {df.shape}")
            print(f"  Columns: {df.columns.tolist()}")
            print(f"  First few rows:")
            print(df.head(3))

    except Exception as e:
        print(f"Camelot lattice error: {e}")

    print(f"\n--- TABLES FOUND WITH CAMELOT (stream) ---")
    try:
        tables_stream = camelot.read_pdf(pdf_path, pages=str(page_num), flavor="stream")
        print(f"Number of tables: {len(tables_stream)}")

        for i, table in enumerate(tables_stream):
            df = table.df
            print(f"\nTable {i}:")
            print(f"  Shape: {df.shape}")
            print(f"  Columns: {df.columns.tolist()}")
            print(f"  First few rows:")
            print(df.head(3))

    except Exception as e:
        print(f"Camelot stream error: {e}")


def find_product_pages(pdf_path: str, max_pages: int = 50):
    """Find pages likely to contain products."""
    print(f"\n{'='*80}")
    print(f"FINDING PRODUCT PAGES")
    print(f"{'='*80}")

    product_pages = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num in range(1, min(max_pages + 1, len(pdf.pages) + 1)):
            page = pdf.pages[page_num - 1]
            text = page.extract_text() or ""

            # Check for product indicators
            has_price = "$" in text
            has_model = any(pattern in text for pattern in ["BB", "ECBB", "WT"])
            has_finish = any(pattern in text for pattern in ["US3", "US4", "US10", "US26"])

            tables = page.extract_tables()
            has_tables = len(tables) > 0

            if has_tables and has_price and (has_model or has_finish):
                product_pages.append(
                    {
                        "page": page_num,
                        "has_price": has_price,
                        "has_model": has_model,
                        "has_finish": has_finish,
                        "table_count": len(tables),
                    }
                )

    print(f"\nFound {len(product_pages)} pages with potential products:")
    for p in product_pages[:20]:  # Show first 20
        print(
            f"  Page {p['page']}: {p['table_count']} tables, "
            f"price={p['has_price']}, model={p['has_model']}, finish={p['has_finish']}"
        )

    return product_pages


def find_finish_pages(pdf_path: str, max_pages: int = 50):
    """Find pages likely to contain finish symbols."""
    print(f"\n{'='*80}")
    print(f"FINDING FINISH SYMBOL PAGES")
    print(f"{'='*80}")

    finish_pages = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num in range(1, min(max_pages + 1, len(pdf.pages) + 1)):
            page = pdf.pages[page_num - 1]
            text = (page.extract_text() or "").upper()

            if "FINISH" in text and "SYMBOL" in text:
                finish_pages.append(page_num)
                print(f"\nPage {page_num} - FOUND FINISH SYMBOLS")
                print(f"Text excerpt:")
                print(text[:500])

    return finish_pages


if __name__ == "__main__":
    pdf_path = "test_data/pdfs/2025-hager-price-book.pdf"

    # Find key pages
    finish_pages = find_finish_pages(pdf_path, max_pages=20)
    product_pages = find_product_pages(pdf_path, max_pages=100)

    # Diagnose specific pages
    if finish_pages:
        print(f"\n\nDIAGNOSING FINISH PAGE: {finish_pages[0]}")
        diagnose_page(pdf_path, finish_pages[0])

    if product_pages:
        print(f"\n\nDIAGNOSING FIRST PRODUCT PAGE: {product_pages[0]['page']}")
        diagnose_page(pdf_path, product_pages[0]["page"])

        if len(product_pages) > 5:
            print(
                f"\n\nDIAGNOSING MIDDLE PRODUCT PAGE: {product_pages[len(product_pages)//2]['page']}"
            )
            diagnose_page(pdf_path, product_pages[len(product_pages) // 2]["page"])
