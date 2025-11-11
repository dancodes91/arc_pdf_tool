"""
Comprehensive Hager PDF and Parser Validation using PDF Processing Pro.
Validates the Hager parser against the 2025 Hager Price Book PDF.
"""
import pdfplumber
import sys
import json
from pathlib import Path
from datetime import datetime
import time

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None


def analyze_hager_pdf_structure(pdf_path):
    """Analyze Hager PDF structure and product organization."""
    print("="*70)
    print("HAGER PDF STRUCTURE ANALYSIS")
    print("="*70)

    results = {
        "file_info": {},
        "product_families": {},
        "sample_pages": [],
        "table_distribution": {}
    }

    with pdfplumber.open(pdf_path) as pdf:
        print(f"\nBasic Info:")
        print(f"  - Pages: {len(pdf.pages)}")
        print(f"  - File size: {Path(pdf_path).stat().st_size / 1024 / 1024:.2f} MB")

        results["file_info"] = {
            "total_pages": len(pdf.pages),
            "file_size_mb": Path(pdf_path).stat().st_size / 1024 / 1024
        }

        # Sample pages to understand product organization
        sample_page_numbers = [20, 50, 100, 150, 200, 250]
        print(f"\nSampling pages: {sample_page_numbers}")

        for page_num in sample_page_numbers:
            if page_num < len(pdf.pages):
                page = pdf.pages[page_num]
                text = page.extract_text() or ""
                tables = page.extract_tables()

                # Extract product family from page header
                first_line = text.split('\n')[0] if text else ""

                sample_info = {
                    "page": page_num + 1,
                    "header": first_line[:100],
                    "tables": len(tables),
                    "has_prices": "$" in text,
                    "has_finish_codes": any(code in text for code in ["US3", "US4", "US10", "US26", "US32"]),
                    "product_indicators": []
                }

                # Detect product families
                if "BB" in text and "Hinge" in text:
                    sample_info["product_indicators"].append("Ball Bearing Hinges")
                if "WT" in text:
                    sample_info["product_indicators"].append("Wide Throw Hinges")
                if "ECBB" in text:
                    sample_info["product_indicators"].append("Electric Hinges")
                if "Exit Device" in text:
                    sample_info["product_indicators"].append("Exit Devices")
                if "Door Control" in text or "Closer" in text:
                    sample_info["product_indicators"].append("Door Controls")
                if "Lock" in text:
                    sample_info["product_indicators"].append("Locks")

                results["sample_pages"].append(sample_info)

                print(f"\n  Page {page_num + 1}: {first_line[:60]}...")
                print(f"    - Tables: {len(tables)}")
                print(f"    - Products: {', '.join(sample_info['product_indicators']) if sample_info['product_indicators'] else 'None detected'}")

        # Count tables by section
        print(f"\nScanning table distribution...")
        sections = {
            "front_matter": (1, 20),
            "main_catalog": (21, 300),
            "supplementary": (301, len(pdf.pages))
        }

        for section_name, (start, end) in sections.items():
            table_count = 0
            for i in range(start - 1, min(end, len(pdf.pages))):
                tables = pdf.pages[i].extract_tables()
                table_count += len(tables)

            results["table_distribution"][section_name] = {
                "page_range": f"{start}-{end}",
                "tables": table_count
            }
            print(f"  {section_name}: {table_count} tables (pages {start}-{end})")

    return results


def validate_hager_parser_output(csv_path, pdf_path):
    """Validate Hager parser output against PDF."""
    print("\n" + "="*70)
    print("HAGER PARSER OUTPUT VALIDATION")
    print("="*70)

    try:
        import pandas as pd
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print("\n⚠ CSV file not found - parser may still be running")
        return {"status": "pending", "message": "CSV file not found"}
    except Exception as e:
        print(f"\n✗ Error reading CSV: {e}")
        return {"status": "error", "message": str(e)}

    validation = {
        "total_products": len(df),
        "price_range": {},
        "product_families": {},
        "finish_codes": {},
        "data_quality": {}
    }

    print(f"\n✓ Loaded parser output: {len(df)} products")

    # Price validation
    if 'base_price' in df.columns:
        price_min = df['base_price'].min()
        price_max = df['base_price'].max()
        price_mean = df['base_price'].mean()

        validation["price_range"] = {
            "min": float(price_min),
            "max": float(price_max),
            "mean": float(price_mean)
        }

        print(f"\nPrice Range:")
        print(f"  - Min: ${price_min:.2f}")
        print(f"  - Max: ${price_max:.2f}")
        print(f"  - Average: ${price_mean:.2f}")

    # Product family distribution
    if 'series' in df.columns:
        series_counts = df['series'].value_counts().head(10)
        validation["product_families"] = series_counts.to_dict()

        print(f"\nTop Product Families:")
        for series, count in series_counts.items():
            print(f"  - {series}: {count} products")

    # Finish code distribution
    if 'finish_code' in df.columns:
        finish_counts = df['finish_code'].value_counts().head(10)
        validation["finish_codes"] = finish_counts.to_dict()

        print(f"\nTop Finish Codes:")
        for finish, count in finish_counts.items():
            print(f"  - {finish}: {count} products")

    # Data quality checks
    print(f"\nData Quality:")
    duplicates = df.duplicated(subset=['sku']).sum() if 'sku' in df.columns else 0
    missing_sku = df['sku'].isna().sum() if 'sku' in df.columns else 0
    missing_price = df['base_price'].isna().sum() if 'base_price' in df.columns else 0

    validation["data_quality"] = {
        "duplicates": int(duplicates),
        "missing_sku": int(missing_sku),
        "missing_price": int(missing_price)
    }

    print(f"  ✓ Duplicates: {duplicates}")
    print(f"  ✓ Missing SKU: {missing_sku}")
    print(f"  ✓ Missing Price: {missing_price}")

    # Cross-validation with PDF
    print(f"\nPDF Cross-Validation:")
    with pdfplumber.open(pdf_path) as pdf:
        # Check for BB hinges (most common Hager product)
        bb_in_pdf = False
        for page in pdf.pages[20:30]:  # Check sample pages
            text = page.extract_text() or ""
            if "BB" in text and "Hinge" in text:
                bb_in_pdf = True
                break

        bb_in_csv = len(df[df['sku'].str.contains('BB', case=False, na=False)]) if 'sku' in df.columns else 0

        print(f"  - BB Hinges in PDF: {'Yes' if bb_in_pdf else 'No'}")
        print(f"  - BB Hinges extracted: {bb_in_csv}")

        validation["cross_validation"] = {
            "bb_hinges_in_pdf": bb_in_pdf,
            "bb_hinges_extracted": int(bb_in_csv)
        }

    return validation


def test_hager_edge_cases(pdf_path):
    """Test Hager-specific edge cases."""
    print("\n" + "="*70)
    print("HAGER EDGE CASE TESTING")
    print("="*70)

    edge_cases = []

    with pdfplumber.open(pdf_path) as pdf:
        # Test 1: Finish code matrix tables (common in Hager)
        print("\nTest 1: Finish Code Matrix Detection")
        page_51 = pdf.pages[50]  # BB hinge page
        text_51 = page_51.extract_text() or ""

        finish_codes_found = []
        for code in ["US3", "US4", "US10", "US10B", "US26", "US26D", "US32", "US32D"]:
            if code in text_51:
                finish_codes_found.append(code)

        print(f"  ✓ Finish codes found: {len(finish_codes_found)}")
        print(f"    Examples: {', '.join(finish_codes_found[:5])}")
        edge_cases.append({
            "test": "Finish code matrix",
            "passed": len(finish_codes_found) >= 5
        })

        # Test 2: Multiple products per model (size variations)
        print("\nTest 2: Size Variation Handling")
        size_patterns = ['4-1/2"', '5"', '5-1/2"', '6"']
        sizes_found = sum(1 for pattern in size_patterns if pattern in text_51)
        print(f"  ✓ Size variations found: {sizes_found}")
        edge_cases.append({
            "test": "Size variations",
            "passed": sizes_found >= 2
        })

        # Test 3: Box/Case quantity columns
        print("\nTest 3: Quantity Column Detection")
        has_box_qty = "Box" in text_51 and "Qty" in text_51
        has_case_qty = "Case" in text_51 and "Qty" in text_51
        print(f"  ✓ Box Qty column: {has_box_qty}")
        print(f"  ✓ Case Qty column: {has_case_qty}")
        edge_cases.append({
            "test": "Quantity columns",
            "passed": has_box_qty or has_case_qty
        })

        # Test 4: Price variations by finish
        print("\nTest 4: Finish Price Variations")
        tables_51 = page_51.extract_tables()
        has_price_matrix = False
        if tables_51:
            # Check if table has multiple price columns
            for table in tables_51:
                if len(table) > 1 and len(table[0]) >= 4:
                    has_price_matrix = True
                    break
        print(f"  ✓ Price matrix structure: {has_price_matrix}")
        edge_cases.append({
            "test": "Price variations by finish",
            "passed": has_price_matrix
        })

    passed = sum(1 for case in edge_cases if case["passed"])
    print(f"\n✓ EDGE CASE TESTS: {passed}/{len(edge_cases)} passed")

    return edge_cases


def generate_hager_validation_report(pdf_path, csv_path=None):
    """Generate comprehensive validation report for Hager parser."""
    print("\n" + "="*70)
    print("GENERATING HAGER VALIDATION REPORT")
    print("="*70)

    report = {
        "timestamp": datetime.now().isoformat(),
        "pdf_file": str(pdf_path),
        "csv_file": str(csv_path) if csv_path else None,
        "results": {}
    }

    # Analyze PDF structure
    report["results"]["pdf_structure"] = analyze_hager_pdf_structure(pdf_path)

    # Validate parser output (if available)
    if csv_path and Path(csv_path).exists():
        report["results"]["parser_validation"] = validate_hager_parser_output(csv_path, pdf_path)
    else:
        print("\n⚠ Parser output not available - skipping validation")
        report["results"]["parser_validation"] = {
            "status": "pending",
            "message": "CSV file not found - parser may still be running"
        }

    # Test edge cases
    report["results"]["edge_cases"] = test_hager_edge_cases(pdf_path)

    # Save report
    output_dir = Path(pdf_path).parent
    output_path = output_dir / "hager_validation_report.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n✓ Validation report saved: {output_path}")

    # Print summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)

    pdf_struct = report["results"]["pdf_structure"]
    print(f"\nHager PDF:")
    print(f"  - Pages: {pdf_struct['file_info']['total_pages']}")
    print(f"  - File size: {pdf_struct['file_info']['file_size_mb']:.2f} MB")

    tables_dist = pdf_struct["table_distribution"]
    total_tables = sum(section["tables"] for section in tables_dist.values())
    print(f"  - Total tables: {total_tables}")

    if "parser_validation" in report["results"]:
        parser_val = report["results"]["parser_validation"]
        if parser_val.get("status") != "pending":
            print(f"\nParser Output:")
            print(f"  - Products extracted: {parser_val.get('total_products', 0)}")
            if "price_range" in parser_val:
                print(f"  - Price range: ${parser_val['price_range']['min']:.2f} - ${parser_val['price_range']['max']:.2f}")

    edge_cases = report["results"]["edge_cases"]
    passed = sum(1 for case in edge_cases if case["passed"])
    print(f"\nEdge Cases:")
    print(f"  - Tests passed: {passed}/{len(edge_cases)}")

    print("\n" + "="*70)

    return report


if __name__ == "__main__":
    pdf_path = r"C:\Users\Vache\Desktop\vatche\arc_pdf_tool\test_data\pdfs\2025-hager-price-book.pdf"

    # Try to find parser output
    csv_path = None
    export_dir = Path(r"C:\Users\Vache\Desktop\vatche\arc_pdf_tool\test_exports_hager")
    if export_dir.exists():
        csv_files = list(export_dir.glob("*products*.csv"))
        if csv_files:
            csv_path = str(csv_files[0])
            print(f"Found parser output: {csv_path}")
        else:
            print("No parser output found - will validate PDF structure only")

    report = generate_hager_validation_report(pdf_path, csv_path)
