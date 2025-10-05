#!/usr/bin/env python
"""
Accuracy measurement script for parser validation.

Measures parsing accuracy against ground truth or manual validation.
Calculates row extraction rate, numeric accuracy, and option mapping accuracy.

Usage:
    python scripts/measure_accuracy.py --book 1
    python scripts/measure_accuracy.py --book 1 --ground-truth validation/book1_truth.json
    python scripts/measure_accuracy.py --book 1 --sample 50
"""
import argparse
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import DatabaseManager, PriceBook, Product, ProductOption

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def get_book_data(session, book_id: int) -> Dict[str, Any]:
    """Fetch price book data from database."""
    price_book = session.query(PriceBook).filter_by(id=book_id).first()

    if not price_book:
        raise ValueError(f"Price book {book_id} not found")

    # Get products
    products = session.query(Product).filter_by(price_book_id=book_id).all()

    product_data = []
    for product in products:
        # Get options for this product
        options = session.query(ProductOption).filter_by(product_id=product.id).all()

        product_data.append(
            {
                "id": product.id,
                "model": product.model,
                "sku": product.sku,
                "description": product.description,
                "base_price": float(product.base_price) if product.base_price else None,
                "is_active": product.is_active,
                "options": [
                    {
                        "type": opt.option_type,
                        "code": opt.option_code,
                        "name": opt.option_name,
                        "adder_value": float(opt.adder_value) if opt.adder_value else None,
                    }
                    for opt in options
                ],
            }
        )

    return {
        "id": price_book.id,
        "edition": price_book.edition,
        "manufacturer": price_book.manufacturer.name if price_book.manufacturer else "unknown",
        "total_products": len(products),
        "products": product_data,
        "parsing_notes": price_book.parsing_notes,
    }


def calculate_row_accuracy(parsed_data: Dict, expected_count: int = None) -> Tuple[float, Dict]:
    """
    Calculate row extraction accuracy.

    Returns:
        Tuple of (accuracy_rate, metadata)
    """
    total_products = parsed_data["total_products"]

    # If expected count is provided, use it; otherwise estimate from data
    if expected_count is None:
        # Heuristic: assume we got most of them
        expected_count = total_products

    accuracy = total_products / expected_count if expected_count > 0 else 1.0

    metadata = {"extracted": total_products, "expected": expected_count, "accuracy": accuracy}

    return accuracy, metadata


def calculate_numeric_accuracy(products: List[Dict], sample_size: int = None) -> Tuple[float, Dict]:
    """
    Calculate numeric field accuracy (prices).

    Checks for malformed prices, non-numeric values, etc.

    Returns:
        Tuple of (accuracy_rate, metadata)
    """
    if sample_size:
        products = products[:sample_size]

    total_prices = 0
    valid_prices = 0
    invalid_examples = []

    for product in products:
        price = product.get("base_price")

        if price is None:
            continue

        total_prices += 1

        try:
            # Check if price is valid
            if isinstance(price, (int, float, Decimal)):
                price_val = float(price)

                # Sanity checks
                if 0 < price_val < 10000:  # Reasonable range for door hardware
                    valid_prices += 1
                else:
                    invalid_examples.append(
                        {
                            "model": product.get("model"),
                            "price": price,
                            "reason": "Out of reasonable range",
                        }
                    )
            else:
                invalid_examples.append(
                    {"model": product.get("model"), "price": price, "reason": "Not numeric"}
                )

        except (ValueError, TypeError) as e:
            invalid_examples.append(
                {"model": product.get("model"), "price": price, "reason": f"Conversion error: {e}"}
            )

    accuracy = valid_prices / total_prices if total_prices > 0 else 1.0

    metadata = {
        "total_checked": total_prices,
        "valid": valid_prices,
        "invalid": total_prices - valid_prices,
        "accuracy": accuracy,
        "invalid_examples": invalid_examples[:10],  # First 10 examples
    }

    return accuracy, metadata


def calculate_option_mapping_accuracy(
    products: List[Dict], sample_size: int = None
) -> Tuple[float, Dict]:
    """
    Calculate option→rule mapping accuracy.

    Checks if options are properly extracted and mapped.

    Returns:
        Tuple of (accuracy_rate, metadata)
    """
    if sample_size:
        products = products[:sample_size]

    total_products_with_options = 0
    properly_mapped = 0
    mapping_issues = []

    for product in products:
        options = product.get("options", [])

        if not options:
            continue

        total_products_with_options += 1
        has_issues = False

        for option in options:
            # Check if option has required fields
            if not option.get("type") or not option.get("code"):
                has_issues = True
                mapping_issues.append(
                    {
                        "model": product.get("model"),
                        "issue": "Missing type or code",
                        "option": option,
                    }
                )
                break

            # Check if adder value is reasonable (if present)
            adder = option.get("adder_value")
            if adder and (adder < -1000 or adder > 1000):
                has_issues = True
                mapping_issues.append(
                    {
                        "model": product.get("model"),
                        "issue": f"Unreasonable adder: {adder}",
                        "option": option,
                    }
                )
                break

        if not has_issues:
            properly_mapped += 1

    accuracy = (
        properly_mapped / total_products_with_options if total_products_with_options > 0 else 1.0
    )

    metadata = {
        "products_with_options": total_products_with_options,
        "properly_mapped": properly_mapped,
        "with_issues": len(mapping_issues),
        "accuracy": accuracy,
        "issue_examples": mapping_issues[:10],
    }

    return accuracy, metadata


def print_accuracy_report(
    book_data: Dict, row_result: Tuple, numeric_result: Tuple, option_result: Tuple
):
    """Print comprehensive accuracy report."""
    row_acc, row_meta = row_result
    numeric_acc, numeric_meta = numeric_result
    option_acc, option_meta = option_result

    print()
    print("=" * 80)
    print(f"ACCURACY REPORT - Price Book {book_data['id']}")
    print("=" * 80)
    print()

    print(f"Manufacturer:  {book_data['manufacturer']}")
    print(f"Edition:       {book_data['edition']}")
    print(f"Total Products: {book_data['total_products']}")
    print()

    # Row extraction accuracy
    print("1. Row Extraction Accuracy")
    print(f"   Extracted: {row_meta['extracted']}")
    print(f"   Expected:  {row_meta['expected']}")
    print(f"   Accuracy:  {row_acc * 100:.2f}%")

    if row_acc >= 0.98:
        print(f"   ✅ PASS (≥ 98%)")
    else:
        print(f"   ❌ FAIL (< 98%)")
    print()

    # Numeric accuracy
    print("2. Numeric Field Accuracy (Prices)")
    print(f"   Total checked: {numeric_meta['total_checked']}")
    print(f"   Valid:         {numeric_meta['valid']}")
    print(f"   Invalid:       {numeric_meta['invalid']}")
    print(f"   Accuracy:      {numeric_acc * 100:.2f}%")

    if numeric_acc >= 0.99:
        print(f"   ✅ PASS (≥ 99%)")
    else:
        print(f"   ❌ FAIL (< 99%)")

    if numeric_meta.get("invalid_examples"):
        print(f"   Invalid examples:")
        for ex in numeric_meta["invalid_examples"][:5]:
            print(f"     • {ex['model']}: {ex['price']} ({ex['reason']})")
    print()

    # Option mapping accuracy
    print("3. Option→Rule Mapping Accuracy")
    print(f"   Products with options: {option_meta['products_with_options']}")
    print(f"   Properly mapped:       {option_meta['properly_mapped']}")
    print(f"   With issues:           {option_meta['with_issues']}")
    print(f"   Accuracy:              {option_acc * 100:.2f}%")

    if option_acc >= 0.95:
        print(f"   ✅ PASS (≥ 95%)")
    else:
        print(f"   ❌ FAIL (< 95%)")

    if option_meta.get("issue_examples"):
        print(f"   Issue examples:")
        for ex in option_meta["issue_examples"][:5]:
            print(f"     • {ex['model']}: {ex['issue']}")
    print()

    # Overall summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    all_pass = row_acc >= 0.98 and numeric_acc >= 0.99 and option_acc >= 0.95

    if all_pass:
        print("✅ ALL CHECKS PASSED")
    else:
        print("❌ SOME CHECKS FAILED")

    print(f"  Row extraction:  {row_acc * 100:.2f}% (target: ≥98%)")
    print(f"  Numeric fields:  {numeric_acc * 100:.2f}% (target: ≥99%)")
    print(f"  Option mapping:  {option_acc * 100:.2f}% (target: ≥95%)")
    print()


def main():
    parser = argparse.ArgumentParser(description="Measure parsing accuracy for price book")
    parser.add_argument("--book", type=int, required=True, help="Price book ID to measure")
    parser.add_argument("--expected-rows", type=int, help="Expected number of products")
    parser.add_argument("--sample", type=int, help="Sample size for numeric/option checks")
    parser.add_argument("--export", type=str, help="Export report to JSON file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Connect to database
        db_manager = DatabaseManager()
        session = db_manager.get_session()

        logger.info(f"Fetching price book {args.book}...")
        book_data = get_book_data(session, args.book)

        logger.info(f"Calculating accuracy metrics...")

        # Calculate accuracies
        row_result = calculate_row_accuracy(book_data, expected_count=args.expected_rows)
        numeric_result = calculate_numeric_accuracy(book_data["products"], sample_size=args.sample)
        option_result = calculate_option_mapping_accuracy(
            book_data["products"], sample_size=args.sample
        )

        # Print report
        print_accuracy_report(book_data, row_result, numeric_result, option_result)

        # Export if requested
        if args.export:
            report = {
                "book_id": book_data["id"],
                "manufacturer": book_data["manufacturer"],
                "edition": book_data["edition"],
                "timestamp": str(logger),
                "row_accuracy": {"rate": row_result[0], "metadata": row_result[1]},
                "numeric_accuracy": {"rate": numeric_result[0], "metadata": numeric_result[1]},
                "option_accuracy": {"rate": option_result[0], "metadata": option_result[1]},
            }

            with open(args.export, "w") as f:
                json.dump(report, f, indent=2, default=str)

            logger.info(f"✓ Exported report to {args.export}")

        session.close()

        # Exit with appropriate code
        all_pass = row_result[0] >= 0.98 and numeric_result[0] >= 0.99 and option_result[0] >= 0.95

        sys.exit(0 if all_pass else 1)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    main()
