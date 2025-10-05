#!/usr/bin/env python3
"""
Accuracy Validation Script

Validates parser accuracy against golden datasets to meet requirements:
- ≥98% accuracy on extracted rows (products + options)
- ≥99% accuracy on numeric values (prices)

Usage:
    uv run python scripts/validate_accuracy.py --manufacturer select
    uv run python scripts/validate_accuracy.py --manufacturer hager
    uv run python scripts/validate_accuracy.py --all
"""

import sys
import csv
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from decimal import Decimal
from datetime import datetime
import argparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.select.parser import SelectHingesParser
from parsers.hager.parser import HagerParser

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class AccuracyValidator:
    """Validates parser accuracy against golden datasets."""

    def __init__(self, manufacturer: str):
        self.manufacturer = manufacturer.upper()
        self.golden_dir = Path("test_data/golden")
        self.results = {
            "manufacturer": manufacturer,
            "timestamp": datetime.now().isoformat(),
            "row_accuracy": 0.0,
            "numeric_accuracy": 0.0,
            "product_matches": [],
            "option_matches": [],
            "price_errors": [],
            "missing_items": [],
            "extra_items": [],
            "metadata_checks": {},
        }

    def load_golden_products(self) -> List[Dict[str, Any]]:
        """Load golden product dataset."""
        golden_file = self.golden_dir / f"{self.manufacturer}_golden_products.csv"
        if not golden_file.exists():
            raise FileNotFoundError(f"Golden dataset not found: {golden_file}")

        products = []
        with open(golden_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                products.append(row)

        logger.info(f"Loaded {len(products)} golden products")
        return products

    def load_golden_options(self) -> List[Dict[str, Any]]:
        """Load golden options dataset."""
        golden_file = self.golden_dir / f"{self.manufacturer}_golden_options.csv"
        if not golden_file.exists():
            logger.warning(f"No golden options found: {golden_file}")
            return []

        options = []
        with open(golden_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                options.append(row)

        logger.info(f"Loaded {len(options)} golden options")
        return options

    def load_golden_metadata(self) -> Dict[str, Any]:
        """Load golden metadata expectations."""
        golden_file = self.golden_dir / f"{self.manufacturer}_golden_metadata.csv"
        if not golden_file.exists():
            logger.warning(f"No golden metadata found: {golden_file}")
            return {}

        metadata = {}
        with open(golden_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                field = row["field"]
                value = row["expected_value"]
                data_type = row.get("data_type", "string")

                # Convert to appropriate type
                if data_type == "integer":
                    metadata[field] = int(value)
                elif data_type == "float":
                    metadata[field] = float(value)
                elif data_type == "date":
                    metadata[field] = value
                else:
                    metadata[field] = value

        logger.info(f"Loaded {len(metadata)} metadata expectations")
        return metadata

    def parse_pdf(self) -> Dict[str, Any]:
        """Parse the PDF using appropriate parser."""
        if self.manufacturer == "SELECT":
            pdf_path = "test_data/pdfs/2025-select-hinges-price-book.pdf"
            parser = SelectHingesParser(pdf_path)
        elif self.manufacturer == "HAGER":
            pdf_path = "test_data/pdfs/2025-hager-price-book.pdf"
            # Use fast mode for validation (90%+ coverage, faster)
            parser = HagerParser(pdf_path, config={"fast_mode": True})
        else:
            raise ValueError(f"Unknown manufacturer: {self.manufacturer}")

        logger.info(f"Parsing {pdf_path}...")
        results = parser.parse()
        logger.info(
            f"Parsed {len(results.get('products', []))} products, "
            f"{len(results.get('net_add_options', []))} options"
        )
        return results

    def validate_products(
        self, golden: List[Dict], parsed: List[Dict]
    ) -> Tuple[float, List[Dict]]:
        """
        Validate product extraction accuracy.

        Returns:
            (accuracy_rate, match_details)
        """
        matches = []
        total_golden = len(golden)

        for golden_product in golden:
            golden_sku = golden_product["sku"]
            golden_price = Decimal(golden_product["base_price"])

            # Find matching product in parsed results
            parsed_product = self._find_product_by_sku(parsed, golden_sku)

            if parsed_product:
                parsed_price = Decimal(str(parsed_product.get("base_price", 0)))
                price_match = abs(parsed_price - golden_price) < Decimal("0.01")

                match = {
                    "sku": golden_sku,
                    "found": True,
                    "price_match": price_match,
                    "expected_price": float(golden_price),
                    "actual_price": float(parsed_price),
                    "price_diff": float(abs(parsed_price - golden_price)),
                }
                matches.append(match)

                if not price_match:
                    self.results["price_errors"].append(match)
            else:
                matches.append({"sku": golden_sku, "found": False})
                self.results["missing_items"].append(golden_sku)

        found_count = sum(1 for m in matches if m["found"])
        accuracy = (found_count / total_golden) * 100 if total_golden > 0 else 0

        return accuracy, matches

    def validate_options(
        self, golden: List[Dict], parsed: List[Dict]
    ) -> Tuple[float, List[Dict]]:
        """Validate option extraction accuracy."""
        if not golden:
            return 100.0, []  # No golden data to validate against

        matches = []
        total_golden = len(golden)

        for golden_option in golden:
            option_code = golden_option["option_code"]
            golden_adder = Decimal(golden_option["adder_value"])

            # Find matching option
            parsed_option = self._find_option_by_code(parsed, option_code)

            if parsed_option:
                parsed_adder = Decimal(str(parsed_option.get("adder_value", 0)))
                adder_match = abs(parsed_adder - golden_adder) < Decimal("0.01")

                match = {
                    "option_code": option_code,
                    "found": True,
                    "adder_match": adder_match,
                    "expected_adder": float(golden_adder),
                    "actual_adder": float(parsed_adder),
                    "adder_diff": float(abs(parsed_adder - golden_adder)),
                }
                matches.append(match)

                if not adder_match:
                    self.results["price_errors"].append(match)
            else:
                matches.append({"option_code": option_code, "found": False})
                self.results["missing_items"].append(option_code)

        found_count = sum(1 for m in matches if m["found"])
        accuracy = (found_count / total_golden) * 100 if total_golden > 0 else 0

        return accuracy, matches

    def validate_numeric_accuracy(self) -> float:
        """
        Calculate numeric accuracy (prices must be ≥99% accurate).

        Checks all price values against golden dataset.
        """
        total_prices = 0
        correct_prices = 0

        # Check product prices
        for match in self.results["product_matches"]:
            if match.get("found") and "price_match" in match:
                total_prices += 1
                if match["price_match"]:
                    correct_prices += 1

        # Check option adders
        for match in self.results["option_matches"]:
            if match.get("found") and "adder_match" in match:
                total_prices += 1
                if match["adder_match"]:
                    correct_prices += 1

        accuracy = (correct_prices / total_prices * 100) if total_prices > 0 else 0
        return accuracy

    def validate_metadata(self, golden_meta: Dict, parsed: Dict) -> Dict[str, bool]:
        """Validate metadata expectations."""
        checks = {}

        for field, expected_value in golden_meta.items():
            if field == "manufacturer":
                actual = parsed.get("manufacturer", "")
                checks[field] = expected_value.lower() in actual.lower()

            elif field == "effective_date":
                # Parse date from parsed results
                eff_date = parsed.get("effective_date", {})
                if isinstance(eff_date, dict):
                    actual_date = eff_date.get("value")
                else:
                    actual_date = eff_date
                # Compare dates (allow some flexibility in format)
                checks[field] = str(expected_value) in str(actual_date)

            elif field.endswith("_min"):
                # Minimum count checks (e.g., total_products_min)
                base_field = field.replace("_min", "")
                summary = parsed.get("summary", {})

                if base_field == "total_products":
                    actual = summary.get("total_products", 0)
                elif base_field == "total_options":
                    actual = summary.get("total_options", 0)
                elif base_field == "total_finishes":
                    actual = summary.get("total_finishes", 0)
                else:
                    actual = 0

                checks[field] = actual >= expected_value

        return checks

    def _find_product_by_sku(self, products: List[Dict], sku: str) -> Dict:
        """Find product by SKU in parsed results."""
        for product in products:
            if isinstance(product, dict):
                value = product.get("value", {})
                if isinstance(value, dict) and value.get("sku") == sku:
                    return value
        return None

    def _find_option_by_code(self, options: List[Dict], code: str) -> Dict:
        """Find option by code in parsed results."""
        for option in options:
            if isinstance(option, dict):
                value = option.get("value", {})
                if isinstance(value, dict):
                    option_code = value.get("option_code", "")
                    # Allow partial matches (e.g., "CTW" in "CTW - Center to Center")
                    if code.upper() in option_code.upper() or option_code.upper() in code.upper():
                        return value
        return None

    def run_validation(self) -> Dict[str, Any]:
        """Run complete validation."""
        logger.info(f"\n{'='*60}")
        logger.info(f"ACCURACY VALIDATION: {self.manufacturer}")
        logger.info(f"{'='*60}\n")

        # Load golden datasets
        golden_products = self.load_golden_products()
        golden_options = self.load_golden_options()
        golden_metadata = self.load_golden_metadata()

        # Parse PDF
        parsed_results = self.parse_pdf()

        # Extract parsed items
        parsed_products = parsed_results.get("products", [])
        parsed_options = parsed_results.get("net_add_options", [])

        # Validate products
        logger.info("\nValidating products...")
        product_accuracy, product_matches = self.validate_products(
            golden_products, parsed_products
        )
        self.results["product_matches"] = product_matches

        # Validate options
        logger.info("Validating options...")
        option_accuracy, option_matches = self.validate_options(golden_options, parsed_options)
        self.results["option_matches"] = option_matches

        # Calculate overall row accuracy
        total_rows = len(golden_products) + len(golden_options)
        found_rows = sum(1 for m in product_matches if m["found"]) + sum(
            1 for m in option_matches if m["found"]
        )
        row_accuracy = (found_rows / total_rows * 100) if total_rows > 0 else 0
        self.results["row_accuracy"] = row_accuracy

        # Calculate numeric accuracy
        numeric_accuracy = self.validate_numeric_accuracy()
        self.results["numeric_accuracy"] = numeric_accuracy

        # Validate metadata
        logger.info("Validating metadata...")
        metadata_checks = self.validate_metadata(golden_metadata, parsed_results)
        self.results["metadata_checks"] = metadata_checks

        return self.results

    def print_report(self):
        """Print validation report."""
        print(f"\n{'='*60}")
        print(f"ACCURACY VALIDATION REPORT: {self.manufacturer}")
        print(f"{'='*60}\n")

        # Requirements thresholds
        ROW_THRESHOLD = 98.0
        NUMERIC_THRESHOLD = 99.0

        row_acc = self.results["row_accuracy"]
        num_acc = self.results["numeric_accuracy"]

        print(f"Row Accuracy:     {row_acc:.2f}% (threshold: >={ROW_THRESHOLD}%)")
        print(f"Numeric Accuracy: {num_acc:.2f}% (threshold: >={NUMERIC_THRESHOLD}%)")
        print()

        # Pass/Fail
        row_pass = row_acc >= ROW_THRESHOLD
        num_pass = num_acc >= NUMERIC_THRESHOLD

        print("RESULTS:")
        print(f"  Row Accuracy:     {'PASS' if row_pass else 'FAIL'} {'+' if row_pass else 'X'}")
        print(
            f"  Numeric Accuracy: {'PASS' if num_pass else 'FAIL'} {'+' if num_pass else 'X'}"
        )
        print()

        overall_pass = row_pass and num_pass
        print(f"OVERALL: {'PASS +' if overall_pass else 'FAIL X'}")
        print()

        # Details
        print(f"Products:")
        print(f"  Found:   {sum(1 for m in self.results['product_matches'] if m['found'])}")
        print(f"  Missing: {len(self.results['missing_items'])}")
        print()

        print(f"Options:")
        print(f"  Found:   {sum(1 for m in self.results['option_matches'] if m['found'])}")
        print()

        if self.results["price_errors"]:
            print(f"Price Errors ({len(self.results['price_errors'])}):")
            for error in self.results["price_errors"][:5]:  # Show first 5
                if "sku" in error:
                    print(
                        f"  {error['sku']}: expected ${error['expected_price']}, "
                        f"got ${error['actual_price']}"
                    )
                elif "option_code" in error:
                    print(
                        f"  {error['option_code']}: expected ${error['expected_adder']}, "
                        f"got ${error['actual_adder']}"
                    )
            print()

        print(f"Metadata Checks:")
        for field, passed in self.results["metadata_checks"].items():
            status = "PASS +" if passed else "FAIL X"
            print(f"  {field}: {status}")
        print()

        print(f"{'='*60}\n")

    def export_report(self, output_path: str):
        """Export detailed JSON report."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, default=str)
        logger.info(f"Detailed report exported to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Validate parser accuracy")
    parser.add_argument(
        "--manufacturer",
        choices=["select", "hager", "all"],
        default="select",
        help="Manufacturer to validate",
    )
    parser.add_argument(
        "--export", type=str, help="Export detailed report to JSON file"
    )
    args = parser.parse_args()

    manufacturers = (
        ["select", "hager"] if args.manufacturer == "all" else [args.manufacturer]
    )

    all_pass = True
    for mfr in manufacturers:
        validator = AccuracyValidator(mfr)
        results = validator.run_validation()
        validator.print_report()

        if args.export:
            export_path = args.export.replace(".json", f"_{mfr}.json")
            validator.export_report(export_path)

        # Check if passed
        if results["row_accuracy"] < 98.0 or results["numeric_accuracy"] < 99.0:
            all_pass = False

    # Exit code
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
