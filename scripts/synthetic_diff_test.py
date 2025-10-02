#!/usr/bin/env python
"""
Synthetic diff test script for validating rename detection.

Creates synthetic price books with controlled renames to test
fuzzy matching accuracy and confidence scoring.

Usage:
    python scripts/synthetic_diff_test.py --rename --pct 0.2
    python scripts/synthetic_diff_test.py --rename --pct 0.15 --threshold 0.95
"""
import argparse
import sys
import random
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.diff_engine_v2 import DiffEngineV2, ChangeType

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def create_base_products(count: int = 100) -> List[Dict[str, Any]]:
    """Create a base set of realistic products."""
    products = []

    families = ['bb1100', 'bb1200', 'ctw', 'hinge', 'lever']
    finishes = ['US3', 'US4', 'US10B', 'US15', 'US26D']
    sizes = ['3', '4', '4.5', '5', '6']

    for i in range(count):
        family = random.choice(families)
        finish = random.choice(finishes)
        size = random.choice(sizes)

        model = f"{family.upper()}-{i:04d}"

        products.append({
            'model': model,
            'manufacturer': 'hager',
            'family': family,
            'finish': finish,
            'size': size,
            'price': round(random.uniform(25.0, 250.0), 2),
            'description': f'{family.upper()} Series Door Hardware'
        })

    return products


def apply_renames(products: List[Dict[str, Any]], pct: float) -> tuple[List[Dict[str, Any]], List[tuple]]:
    """
    Apply realistic renames to a percentage of products.

    Returns:
        Tuple of (renamed_products, rename_map)
    """
    renamed_products = []
    rename_map = []

    # Calculate how many to rename
    rename_count = int(len(products) * pct)
    indices_to_rename = random.sample(range(len(products)), rename_count)

    rename_patterns = [
        lambda m: m.replace('-', ''),           # CTW-4 -> CTW4
        lambda m: m.replace('-', '_'),          # BB-1100 -> BB_1100
        lambda m: m + 'A',                      # BB1100-1 -> BB1100-1A
        lambda m: m.replace('0', 'O') if '0' in m else m,  # BB1100 -> BB11OO
        lambda m: m[:-1] + 'X' if m else m     # CTW-4 -> CTW-X
    ]

    for i, product in enumerate(products):
        new_product = product.copy()

        if i in indices_to_rename:
            old_model = product['model']
            pattern = random.choice(rename_patterns)
            new_model = pattern(old_model)

            new_product['model'] = new_model
            rename_map.append((old_model, new_model))

            logger.debug(f"Renamed: {old_model} -> {new_model}")

        renamed_products.append(new_product)

    return renamed_products, rename_map


def apply_price_changes(products: List[Dict[str, Any]], pct: float = 0.3) -> List[Dict[str, Any]]:
    """Apply price changes to simulate realistic diff."""
    changed_products = []

    change_count = int(len(products) * pct)
    indices_to_change = random.sample(range(len(products)), change_count)

    for i, product in enumerate(products):
        new_product = product.copy()

        if i in indices_to_change:
            # Apply realistic price change (+/- 5-15%)
            change_factor = random.uniform(0.85, 1.15)
            new_product['price'] = round(product['price'] * change_factor, 2)

        changed_products.append(new_product)

    return changed_products


def run_synthetic_test(rename_pct: float, required_accuracy: float = 0.95, product_count: int = 100) -> bool:
    """
    Run synthetic diff test with rename detection.

    Args:
        rename_pct: Percentage of products to rename (0.0-1.0)
        required_accuracy: Required match accuracy (0.0-1.0)
        product_count: Number of products to generate

    Returns:
        True if test passes, False otherwise
    """
    logger.info(f"🧪 Synthetic Diff Test")
    logger.info(f"=" * 60)
    logger.info(f"Product count: {product_count}")
    logger.info(f"Rename percentage: {rename_pct * 100:.1f}%")
    logger.info(f"Required accuracy: {required_accuracy * 100:.1f}%")
    logger.info("")

    # Create base products
    base_products = create_base_products(product_count)

    # Create old book
    old_book = {
        'id': 'old_synthetic',
        'manufacturer': 'hager',
        'effective_date': datetime(2024, 1, 1),
        'products': base_products
    }

    # Create new book with renames and price changes
    renamed_products, rename_map = apply_renames(base_products, rename_pct)
    new_products = apply_price_changes(renamed_products, pct=0.3)

    new_book = {
        'id': 'new_synthetic',
        'manufacturer': 'hager',
        'effective_date': datetime(2024, 6, 1),
        'products': new_products
    }

    logger.info(f"✓ Created synthetic books")
    logger.info(f"  Old products: {len(base_products)}")
    logger.info(f"  New products: {len(new_products)}")
    logger.info(f"  Applied renames: {len(rename_map)}")
    logger.info("")

    # Run diff engine
    diff_engine = DiffEngineV2({
        'enable_fuzzy_matching': True,
        'fuzzy_threshold': 70,
        'review_threshold': 0.6
    })

    logger.info(f"🔍 Running diff engine...")
    diff_result = diff_engine.create_diff(old_book, new_book)

    # Analyze results
    fuzzy_matches = [m for m in diff_result.matches if m.match_method == 'fuzzy']
    exact_matches = [m for m in diff_result.matches if m.match_method == 'exact_key']

    detected_renames = len(fuzzy_matches)
    expected_renames = len(rename_map)

    if expected_renames > 0:
        accuracy = detected_renames / expected_renames
    else:
        accuracy = 1.0

    logger.info(f"")
    logger.info(f"📊 Results:")
    logger.info(f"=" * 60)
    logger.info(f"Exact matches:     {len(exact_matches)}")
    logger.info(f"Fuzzy matches:     {len(fuzzy_matches)}")
    logger.info(f"Expected renames:  {expected_renames}")
    logger.info(f"Detected renames:  {detected_renames}")
    logger.info(f"Accuracy:          {accuracy * 100:.1f}%")
    logger.info(f"")

    # Check if test passes
    passed = accuracy >= required_accuracy

    if passed:
        logger.info(f"✅ TEST PASSED - Accuracy {accuracy * 100:.1f}% >= {required_accuracy * 100:.1f}%")
    else:
        logger.info(f"❌ TEST FAILED - Accuracy {accuracy * 100:.1f}% < {required_accuracy * 100:.1f}%")

    # Show sample fuzzy matches
    if fuzzy_matches:
        logger.info(f"")
        logger.info(f"Sample fuzzy matches:")
        for match in fuzzy_matches[:5]:
            old_model = match.old_item.get('model', 'N/A')
            new_model = match.new_item.get('model', 'N/A') if match.new_item else 'N/A'
            confidence = match.confidence
            logger.info(f"  {old_model:20s} -> {new_model:20s} ({confidence * 100:.1f}% confidence)")

    # Show review queue
    if diff_result.review_queue:
        logger.info(f"")
        logger.info(f"⚠️  Review queue ({len(diff_result.review_queue)} items need review):")
        for match in diff_result.review_queue[:5]:
            old_model = match.old_item.get('model', 'N/A') if match.old_item else 'N/A'
            new_model = match.new_item.get('model', 'N/A') if match.new_item else 'N/A'
            logger.info(f"  {old_model:20s} -> {new_model:20s} ({match.confidence * 100:.1f}%)")

    return passed


def main():
    parser = argparse.ArgumentParser(description='Run synthetic diff test with rename detection')
    parser.add_argument('--rename', action='store_true', help='Enable rename testing')
    parser.add_argument('--pct', type=float, default=0.2, help='Percentage to rename (0.0-1.0, default: 0.2)')
    parser.add_argument('--threshold', type=float, default=0.95, help='Required accuracy (0.0-1.0, default: 0.95)')
    parser.add_argument('--count', type=int, default=100, help='Number of products (default: 100)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.rename:
        print("Error: --rename flag is required")
        print("Usage: python scripts/synthetic_diff_test.py --rename --pct 0.2")
        sys.exit(1)

    # Validate inputs
    if not (0.0 <= args.pct <= 1.0):
        print(f"Error: --pct must be between 0.0 and 1.0, got {args.pct}")
        sys.exit(1)

    if not (0.0 <= args.threshold <= 1.0):
        print(f"Error: --threshold must be between 0.0 and 1.0, got {args.threshold}")
        sys.exit(1)

    # Run test
    success = run_synthetic_test(
        rename_pct=args.pct,
        required_accuracy=args.threshold,
        product_count=args.count
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
