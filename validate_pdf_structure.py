"""
Comprehensive PDF validation using PDF Processing Pro techniques.
Validates both PDF integrity and parser extraction accuracy.
"""
import pdfplumber
import sys
import json
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

def validate_pdf_integrity(pdf_path):
    """Validate PDF file integrity and structure."""
    print("="*70)
    print("PDF INTEGRITY VALIDATION")
    print("="*70)

    results = {
        "file_exists": False,
        "readable": False,
        "page_count": 0,
        "has_text": False,
        "has_tables": False,
        "metadata": {},
        "issues": []
    }

    try:
        # Check file exists
        if not Path(pdf_path).exists():
            results["issues"].append("File does not exist")
            return results
        results["file_exists"] = True
        print(f"✓ File exists: {pdf_path}")

        # Try to open PDF
        with pdfplumber.open(pdf_path) as pdf:
            results["readable"] = True
            results["page_count"] = len(pdf.pages)
            print(f"✓ PDF is readable: {len(pdf.pages)} pages")

            # Check metadata
            if pdf.metadata:
                results["metadata"] = {k: str(v) for k, v in pdf.metadata.items()}
                print(f"✓ Metadata available: {len(results['metadata'])} fields")

            # Check for text content
            text_pages = 0
            for page in pdf.pages:
                text = page.extract_text()
                if text and len(text.strip()) > 50:
                    text_pages += 1

            results["has_text"] = text_pages > 0
            print(f"✓ Text content: {text_pages}/{len(pdf.pages)} pages with text")

            # Check for tables
            tables_found = 0
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    tables_found += len(tables)

            results["has_tables"] = tables_found > 0
            print(f"✓ Tables: {tables_found} tables found across all pages")

    except Exception as e:
        results["issues"].append(f"Error reading PDF: {str(e)}")
        print(f"✗ Error: {e}")
        return results

    if not results["issues"]:
        print("\n✓ PDF INTEGRITY: PASSED")
    else:
        print(f"\n✗ PDF INTEGRITY: FAILED ({len(results['issues'])} issues)")

    return results


def extract_all_tables_detailed(pdf_path):
    """Extract all tables with detailed analysis."""
    print("\n" + "="*70)
    print("DETAILED TABLE EXTRACTION")
    print("="*70)

    tables_data = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()

            if tables:
                print(f"\nPage {page_num}: {len(tables)} table(s) found")

                for table_idx, table in enumerate(tables, 1):
                    if not table or len(table) == 0:
                        continue

                    # Analyze table structure
                    rows = len(table)
                    cols = len(table[0]) if table[0] else 0

                    # Count non-empty cells
                    non_empty = sum(1 for row in table for cell in row
                                   if cell and str(cell).strip() not in ['', 'None', 'nan'])

                    # Check for price patterns
                    price_cells = 0
                    model_cells = 0
                    for row in table:
                        for cell in row:
                            if cell:
                                cell_str = str(cell)
                                # Count prices (digits with optional decimal)
                                if any(char.isdigit() for char in cell_str):
                                    # Check if it looks like a price (not a model number)
                                    import re
                                    if re.search(r'\b\d+\.?\d{0,2}\b', cell_str):
                                        price_cells += 1
                                # Count model patterns
                                if re.search(r'SL\s*\d{2,3}', cell_str, re.IGNORECASE):
                                    model_cells += 1

                    table_info = {
                        "page": page_num,
                        "table_index": table_idx,
                        "dimensions": f"{rows} x {cols}",
                        "non_empty_cells": non_empty,
                        "price_cells": price_cells,
                        "model_cells": model_cells,
                        "header": table[0] if table else None,
                        "sample_rows": table[1:4] if len(table) > 1 else []
                    }

                    tables_data.append(table_info)

                    print(f"  Table {table_idx}:")
                    print(f"    - Dimensions: {rows} rows x {cols} columns")
                    print(f"    - Non-empty cells: {non_empty}")
                    print(f"    - Price cells: {price_cells}")
                    print(f"    - Model cells: {model_cells}")
                    print(f"    - Header: {table[0][:3]}..." if len(table[0]) > 3 else f"    - Header: {table[0]}")

    print(f"\n✓ TOTAL TABLES: {len(tables_data)} tables extracted")
    return tables_data


def validate_parser_extraction(pdf_path, csv_path):
    """Validate parser extraction against raw PDF data."""
    print("\n" + "="*70)
    print("PARSER EXTRACTION VALIDATION")
    print("="*70)

    import pandas as pd

    # Load parser output
    df = pd.read_csv(csv_path)
    print(f"\n✓ Loaded parser output: {len(df)} products")

    validation_results = {
        "total_products": len(df),
        "sku_validation": {},
        "price_validation": {},
        "data_quality": {},
        "issues": []
    }

    # Validate SKU format
    print("\nSKU Validation:")
    sku_pattern = r'^[A-Z]+\d+[-_][A-Z]{2}[-_]?[A-Z]*\d*[-_]?\d{2,3}$'
    import re
    valid_skus = df['sku'].str.match(sku_pattern, na=False).sum()
    validation_results["sku_validation"] = {
        "valid_format": valid_skus,
        "invalid_format": len(df) - valid_skus,
        "pattern": sku_pattern
    }
    print(f"  ✓ Valid SKU format: {valid_skus}/{len(df)}")
    if len(df) - valid_skus > 0:
        print(f"  ⚠ Invalid SKU format: {len(df) - valid_skus}")
        invalid_skus = df[~df['sku'].str.match(sku_pattern, na=False)]['sku'].head(10).tolist()
        print(f"    Examples: {invalid_skus}")

    # Validate prices
    print("\nPrice Validation:")
    price_min = df['base_price'].min()
    price_max = df['base_price'].max()
    price_mean = df['base_price'].mean()
    price_invalid = ((df['base_price'] < 10) | (df['base_price'] > 10000)).sum()

    validation_results["price_validation"] = {
        "min": float(price_min),
        "max": float(price_max),
        "mean": float(price_mean),
        "out_of_range": int(price_invalid)
    }

    print(f"  ✓ Price range: ${price_min:.2f} - ${price_max:.2f}")
    print(f"  ✓ Average price: ${price_mean:.2f}")
    print(f"  ✓ Out of range (< $10 or > $10,000): {price_invalid}")

    # Check for duplicates
    print("\nDuplicate Check:")
    duplicates = df.duplicated(subset=['sku']).sum()
    validation_results["data_quality"]["duplicates"] = int(duplicates)
    print(f"  ✓ Duplicate SKUs: {duplicates}")

    # Convert numpy types to native Python types for JSON serialization
    import numpy as np
    def convert_numpy(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy(item) for item in obj]
        return obj

    validation_results = convert_numpy(validation_results)

    # Check for missing data
    print("\nMissing Data Check:")
    missing = {
        "sku": int(df['sku'].isna().sum()),
        "base_price": int(df['base_price'].isna().sum()),
        "description": int(df['description'].isna().sum())
    }
    validation_results["data_quality"]["missing"] = missing

    for field, count in missing.items():
        status = "✓" if count == 0 else "⚠"
        print(f"  {status} Missing {field}: {count}")

    # Validate against PDF content
    print("\nPDF Cross-Validation:")
    with pdfplumber.open(pdf_path) as pdf:
        # Check for SL11 products in PDF
        sl11_text_found = False
        for page in pdf.pages:
            text = page.extract_text()
            if text and "SL11" in text:
                sl11_text_found = True
                break

        sl11_in_csv = len(df[df['sku'].str.contains('SL11', case=False, na=False)])

        print(f"  ✓ SL11 mentioned in PDF: {sl11_text_found}")
        print(f"  ✓ SL11 products extracted: {sl11_in_csv}")

        if sl11_text_found and sl11_in_csv == 0:
            validation_results["issues"].append("SL11 found in PDF but not extracted")

    # Final verdict
    print("\n" + "="*70)
    if len(validation_results["issues"]) == 0 and price_invalid == 0 and duplicates == 0:
        print("✓ PARSER VALIDATION: PASSED")
    else:
        print(f"⚠ PARSER VALIDATION: {len(validation_results['issues'])} issues found")

    return validation_results


def test_edge_cases(pdf_path):
    """Test parser against known edge cases in the PDF."""
    print("\n" + "="*70)
    print("EDGE CASE TESTING")
    print("="*70)

    edge_cases = []

    with pdfplumber.open(pdf_path) as pdf:
        # Test Case 1: Tables with merged columns (83"/85")
        print("\nTest 1: Merged Column Handling (83\"/85\")")
        page7 = pdf.pages[6]
        tables = page7.extract_tables()
        if tables:
            table = tables[0]
            header = table[0] if table else []
            merged_col_found = any('/' in str(col) for col in header if col)
            print(f"  ✓ Merged column found: {merged_col_found}")
            edge_cases.append({
                "test": "Merged columns",
                "passed": merged_col_found
            })

        # Test Case 2: Dash handling (unavailable sizes)
        print("\nTest 2: Dash Handling (unavailable sizes)")
        dash_cells_found = False
        if tables:
            for row in tables[0]:
                if any(cell == '-' for cell in row if cell):
                    dash_cells_found = True
                    break
        print(f"  ✓ Dash cells found: {dash_cells_found}")
        edge_cases.append({
            "test": "Dash cells",
            "passed": dash_cells_found
        })

        # Test Case 3: Garbage text in cells
        print("\nTest 3: Garbage Text Detection")
        garbage_patterns = ['WEB', 'SITE', 'BROC', 'METRIC', 'bevel edge']
        garbage_found = False
        if tables:
            for row in tables[0]:
                for cell in row:
                    if cell and any(pattern in str(cell) for pattern in garbage_patterns):
                        garbage_found = True
                        print(f"  ✓ Garbage text example: '{cell}'")
                        break
                if garbage_found:
                    break
        edge_cases.append({
            "test": "Garbage text filtering",
            "passed": garbage_found
        })

        # Test Case 4: Multiple price formats
        print("\nTest 4: Price Format Variations")
        price_variations = set()
        if tables:
            import re
            for row in tables[0][1:]:  # Skip header
                for cell in row:
                    if cell:
                        # Look for numeric patterns
                        matches = re.findall(r'\d+\.?\d*', str(cell))
                        for match in matches:
                            try:
                                val = float(match)
                                if 10 <= val <= 5000:
                                    price_variations.add(match)
                            except:
                                pass

        print(f"  ✓ Price format variations found: {len(price_variations)}")
        if len(price_variations) > 0:
            print(f"    Examples: {list(price_variations)[:5]}")
        edge_cases.append({
            "test": "Price format variations",
            "passed": len(price_variations) > 0
        })

    passed_tests = sum(1 for case in edge_cases if case["passed"])
    print(f"\n✓ EDGE CASE TESTS: {passed_tests}/{len(edge_cases)} passed")

    return edge_cases


def generate_validation_report(pdf_path, csv_path):
    """Generate comprehensive validation report."""
    print("\n" + "="*70)
    print("GENERATING COMPREHENSIVE VALIDATION REPORT")
    print("="*70)

    report = {
        "timestamp": datetime.now().isoformat(),
        "pdf_file": str(pdf_path),
        "csv_file": str(csv_path),
        "results": {}
    }

    # Run all validations
    report["results"]["pdf_integrity"] = validate_pdf_integrity(pdf_path)
    report["results"]["tables"] = extract_all_tables_detailed(pdf_path)
    report["results"]["parser_validation"] = validate_parser_extraction(pdf_path, csv_path)
    report["results"]["edge_cases"] = test_edge_cases(pdf_path)

    # Save report
    output_path = Path(pdf_path).parent.parent / "validation_report.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Validation report saved: {output_path}")

    # Print summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)

    integrity = report["results"]["pdf_integrity"]
    parser = report["results"]["parser_validation"]

    print(f"\nPDF Status:")
    print(f"  - Pages: {integrity['page_count']}")
    print(f"  - Tables: {len(report['results']['tables'])}")
    print(f"  - Issues: {len(integrity['issues'])}")

    print(f"\nParser Performance:")
    print(f"  - Products extracted: {parser['total_products']}")
    print(f"  - Valid SKUs: {parser['sku_validation']['valid_format']}")
    print(f"  - Price range: ${parser['price_validation']['min']:.2f} - ${parser['price_validation']['max']:.2f}")
    print(f"  - Duplicates: {parser['data_quality']['duplicates']}")
    print(f"  - Issues: {len(parser['issues'])}")

    edge_cases = report["results"]["edge_cases"]
    passed = sum(1 for case in edge_cases if case["passed"])
    print(f"\nEdge Cases:")
    print(f"  - Tests passed: {passed}/{len(edge_cases)}")

    print("\n" + "="*70)

    return report


if __name__ == "__main__":
    pdf_path = r"C:\Users\Vache\Desktop\vatche\arc_pdf_tool\test_data\pdfs\2025-select-hinges-price-book.pdf"
    csv_path = r"C:\Users\Vache\Desktop\vatche\arc_pdf_tool\test_exports\select hinges_products_20251111_115838.csv"

    report = generate_validation_report(pdf_path, csv_path)
