"""
Deep analysis of Hager PDF to find all product tables and understand why we're missing 568+ products.
"""

import pdfplumber
import camelot
import json
import re


def analyze_page_deep(pdf_path: str, page_num: int):
    """Deep analysis of a single page."""
    print(f"\n{'='*80}")
    print(f"DEEP ANALYSIS - PAGE {page_num}")
    print(f"{'='*80}")

    # Get text content
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num - 1]
        text = page.extract_text() or ""

        print(f"\n--- TEXT INDICATORS ---")
        print(f"Has $: {('$' in text)}")
        price_pattern = r"\$\d+\.\d{2}"
        model_pattern = r"\b(BB|ECBB|WT)\d+"
        finish_pattern = r"US\d+[A-Z]?"
        print(f"Has price numbers: {bool(re.search(price_pattern, text))}")
        print(f"Has model codes (BB/ECBB/WT): {bool(re.search(model_pattern, text))}")
        print(f"Has finish codes (US): {bool(re.search(finish_pattern, text))}")
        print(f"Text length: {len(text)}")

        # Extract pdfplumber tables
        print(f"\n--- PDFPLUMBER TABLES ---")
        plumber_tables = page.extract_tables()
        print(f"Number of tables: {len(plumber_tables)}")

        for i, table in enumerate(plumber_tables):
            if table:
                print(f"\nTable {i}: {len(table)} rows × {len(table[0]) if table else 0} cols")
                # Show first 3 rows
                for row_idx, row in enumerate(table[:3]):
                    print(f"  Row {row_idx}: {row}")

                # Check for prices in table
                table_text = str(table)
                has_prices = "$" in table_text
                has_multiline = "\n" in table_text
                print(f"  Contains prices: {has_prices}")
                print(f"  Has multiline cells: {has_multiline}")

    # Extract Camelot tables
    print(f"\n--- CAMELOT LATTICE TABLES ---")
    try:
        camelot_tables = camelot.read_pdf(pdf_path, pages=str(page_num), flavor="lattice")
        print(f"Number of tables: {camelot_tables.n}")

        for i, table in enumerate(camelot_tables):
            df = table.df
            print(f"\nTable {i}:")
            print(f"  Shape: {df.shape}")
            print(f"  Accuracy: {table.accuracy:.2f}%")
            print(f"  Whitespace: {table.whitespace:.2f}%")
            print(f"  Columns: {list(df.columns)}")
            print(f"  First 3 rows:")
            print(df.head(3).to_string())

            # Analyze column content
            for col_idx in range(len(df.columns)):
                col_sample = " ".join(str(df.iloc[i, col_idx]) for i in range(min(3, len(df))))
                has_price = "$" in col_sample
                has_model = bool(re.search(r"\b(BB|ECBB|WT)\d+", col_sample))
                if has_price or has_model:
                    print(f"  Column {col_idx}: price={has_price}, model={has_model}")
    except Exception as e:
        print(f"Camelot lattice failed: {e}")

    # Try stream flavor
    print(f"\n--- CAMELOT STREAM TABLES ---")
    try:
        camelot_stream = camelot.read_pdf(
            pdf_path, pages=str(page_num), flavor="stream", edge_tol=500, row_tol=10
        )
        print(f"Number of tables: {camelot_stream.n}")

        for i, table in enumerate(camelot_stream):
            df = table.df
            print(f"\nTable {i}:")
            print(f"  Shape: {df.shape}")
            print(f"  Accuracy: {table.accuracy:.2f}%")
            print(f"  First 3 rows:")
            print(df.head(3).to_string())
    except Exception as e:
        print(f"Camelot stream failed: {e}")


def find_product_pages_comprehensive(pdf_path: str, output_file: str = "hager_page_analysis.json"):
    """Comprehensively analyze all pages to categorize them."""
    print("=" * 80)
    print("COMPREHENSIVE PAGE ANALYSIS")
    print("=" * 80)

    results = {
        "total_pages": 0,
        "pages_with_prices": [],
        "pages_with_models": [],
        "pages_with_tables": [],
        "pages_with_multiline_prices": [],
        "page_details": {},
    }

    with pdfplumber.open(pdf_path) as pdf:
        results["total_pages"] = len(pdf.pages)

        for page_num in range(1, len(pdf.pages) + 1):
            page = pdf.pages[page_num - 1]
            text = page.extract_text() or ""
            tables = page.extract_tables()

            # Analyze page
            has_price = "$" in text
            model_pat = r"\b(BB|ECBB|WT|EC)\d+"
            finish_pat = r"US\d+[A-Z]?"
            multiline_price_pat = r"\$\d+\.\d{2}\s*\n\s*\$\d+\.\d{2}"
            has_model = bool(re.search(model_pat, text))
            has_finish = bool(re.search(finish_pat, text))
            has_list_price = "list" in text.lower() and "$" in text
            table_count = len(tables)

            # Check for multiline price cells
            has_multiline_prices = False
            if tables:
                for table in tables:
                    table_str = str(table)
                    if "$" in table_str and "\n" in table_str:
                        # Look for pattern: $123.45\n$456.78
                        if re.search(multiline_price_pat, table_str):
                            has_multiline_prices = True
                            break

            page_info = {
                "page": page_num,
                "has_price": has_price,
                "has_model": has_model,
                "has_finish": has_finish,
                "has_list_price": has_list_price,
                "table_count": table_count,
                "has_multiline_prices": has_multiline_prices,
                "text_length": len(text),
            }

            results["page_details"][page_num] = page_info

            if has_price:
                results["pages_with_prices"].append(page_num)
            if has_model:
                results["pages_with_models"].append(page_num)
            if table_count > 0:
                results["pages_with_tables"].append(page_num)
            if has_multiline_prices:
                results["pages_with_multiline_prices"].append(page_num)

            # Progress indicator
            if page_num % 50 == 0:
                print(f"Analyzed {page_num}/{results['total_pages']} pages...")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total pages: {results['total_pages']}")
    print(f"Pages with prices: {len(results['pages_with_prices'])}")
    print(f"Pages with model codes: {len(results['pages_with_models'])}")
    print(f"Pages with tables: {len(results['pages_with_tables'])}")
    print(f"Pages with multiline prices: {len(results['pages_with_multiline_prices'])}")

    # Pages with prices AND models (likely product pages)
    product_pages = set(results["pages_with_prices"]) & set(results["pages_with_models"])
    print(f"Pages with BOTH prices AND models: {len(product_pages)}")
    print(f"  Sample: {sorted(product_pages)[:20]}")

    # Save results
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results saved to: {output_file}")

    return results


def sample_different_table_types(pdf_path: str, analysis_results: dict):
    """Sample pages from different categories to understand table structures."""
    print(f"\n{'='*80}")
    print("SAMPLING DIFFERENT TABLE TYPES")
    print(f"{'='*80}")

    # Get pages with prices and models
    product_pages = set(analysis_results["pages_with_prices"]) & set(
        analysis_results["pages_with_models"]
    )
    product_pages = sorted(product_pages)

    # Sample: beginning, middle, end of product section
    samples = []
    if len(product_pages) > 0:
        samples.append(("First product page", product_pages[0]))
    if len(product_pages) > 10:
        samples.append(("Early product page", product_pages[10]))
    if len(product_pages) > len(product_pages) // 2:
        samples.append(("Middle product page", product_pages[len(product_pages) // 2]))
    if len(product_pages) > 0:
        samples.append(
            (
                "Late product page",
                product_pages[-10] if len(product_pages) > 10 else product_pages[-1],
            )
        )

    # Add multiline price pages
    if analysis_results["pages_with_multiline_prices"]:
        samples.append(("Multiline price page", analysis_results["pages_with_multiline_prices"][0]))

    # Analyze each sample
    for label, page_num in samples:
        print(f"\n{label}: PAGE {page_num}")
        analyze_page_deep(pdf_path, page_num)


if __name__ == "__main__":
    pdf_path = "test_data/pdfs/2025-hager-price-book.pdf"

    print("Starting comprehensive Hager PDF analysis...")
    print("This will take a few minutes...\n")

    # Step 1: Comprehensive page analysis
    results = find_product_pages_comprehensive(pdf_path)

    # Step 2: Sample different table types
    sample_different_table_types(pdf_path, results)

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nReview hager_page_analysis.json for full page-by-page breakdown")
    print("Look for patterns in the sampled pages above")
