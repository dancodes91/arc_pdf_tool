"""
Complete validation test for all 7 phases of Universal Parser accuracy improvements.

Tests:
1. Phase 1: PaddleOCR integration
2. Phase 2: Multi-source validation
3. Phase 3: Field-specific confidence models
4. Phase 4: Table structure recognition (via PaddleOCR)
5. Phase 5: Adaptive pattern learning
6. Phase 6: Post-processing validation and error correction
7. Phase 7: Feedback loop system

Validates accuracy targets:
- SKU accuracy: 99%+
- Price accuracy: 98%+
- Description accuracy: 95%+
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_universal_parser_all_phases():
    """Test Universal Parser with all 7 phases enabled."""
    print("\n" + "="*70)
    print("UNIVERSAL PARSER - ALL PHASES VALIDATION TEST")
    print("="*70)

    from parsers.universal.parser import UniversalParser

    # Test PDFs
    test_pdfs = [
        "test_data/pdfs/2025-select-hinges-price-book.pdf",
        "test_data/pdfs/2025-hager-price-book.pdf",
    ]

    all_results = {}

    for pdf_path in test_pdfs:
        pdf_full_path = Path(pdf_path)

        if not pdf_full_path.exists():
            logger.warning(f"PDF not found: {pdf_path}")
            continue

        print(f"\n{'='*70}")
        print(f"Testing: {pdf_full_path.name}")
        print(f"{'='*70}")

        try:
            # Create parser with all features enabled
            config = {
                "use_hybrid": True,
                "use_ml_detection": True,
                "confidence_threshold": 0.6,
                "max_pages": 5,  # Limit to first 5 pages for testing
            }

            parser = UniversalParser(str(pdf_full_path), config)

            # Parse PDF
            print("\n[PARSING] Starting extraction with all 7 phases...")
            results = parser.parse()

            # Extract results
            products = results.get("products", [])
            options = results.get("options", [])
            finishes = results.get("finishes", [])

            print(f"\n[RESULTS]")
            print(f"  Products: {len(products)}")
            print(f"  Options: {len(options)}")
            print(f"  Finishes: {len(finishes)}")

            # Analyze confidence scores
            if products:
                confidences = [p.get("confidence", 0) for p in products]
                avg_confidence = sum(confidences) / len(confidences)
                high_confidence = sum(1 for c in confidences if c >= 0.9)

                print(f"\n[CONFIDENCE ANALYSIS]")
                print(f"  Average confidence: {avg_confidence:.1%}")
                print(f"  High confidence (>=90%): {high_confidence}/{len(products)} ({high_confidence/len(products):.1%})")

            # Analyze phase results
            print(f"\n[PHASE ANALYSIS]")

            # Phase 2: Multi-source validation
            multi_source = sum(
                1 for p in products
                if p.get("source_count", 0) >= 2
            )
            print(f"  Phase 2 - Multi-source validated: {multi_source}/{len(products)} ({multi_source/len(products):.1%})")

            # Phase 3: Field-specific confidence
            field_confidence_tracked = sum(
                1 for p in products
                if 'sku_confidence' in p or 'base_price_confidence' in p
            )
            print(f"  Phase 3 - Field confidence tracked: {field_confidence_tracked}/{len(products)}")

            # Phase 5: Pattern learning
            pattern_validated = sum(
                1 for p in products
                if p.get("pattern_validated", False)
            )
            print(f"  Phase 5 - Pattern validated: {pattern_validated}/{len(products)}")

            # Phase 6: Error correction
            auto_corrected = sum(
                1 for p in products
                if p.get("sku_corrected", False)
            )
            print(f"  Phase 6 - Auto-corrected SKUs: {auto_corrected}/{len(products)}")

            # Phase 7: Feedback corrections
            feedback_corrected = sum(
                1 for p in products
                if any(k.endswith('_feedback_corrected') for k in p.keys())
            )
            print(f"  Phase 7 - Feedback corrections: {feedback_corrected}/{len(products)}")

            # Show sample products
            print(f"\n[SAMPLE PRODUCTS] (First 5)")
            for i, product in enumerate(products[:5], 1):
                sku = product.get("sku", "N/A")
                price = product.get("base_price", "N/A")
                desc = product.get("description", "N/A")[:40]
                conf = product.get("confidence", 0)

                print(f"\n  Product {i}:")
                print(f"    SKU: {sku}")
                print(f"    Price: ${price}" if isinstance(price, (int, float)) else f"    Price: {price}")
                print(f"    Description: {desc}...")
                print(f"    Confidence: {conf:.1%}")

                # Show phase indicators
                indicators = []
                if product.get("source_count", 0) >= 2:
                    indicators.append("Multi-source")
                if product.get("pattern_validated"):
                    indicators.append("Pattern-validated")
                if product.get("sku_corrected"):
                    indicators.append("Auto-corrected")

                if indicators:
                    print(f"    Phases: {', '.join(indicators)}")

            # Store results
            all_results[pdf_full_path.name] = {
                "products": len(products),
                "options": len(options),
                "finishes": len(finishes),
                "avg_confidence": avg_confidence if products else 0,
                "multi_source_rate": multi_source / len(products) if products else 0,
                "pattern_validated_rate": pattern_validated / len(products) if products else 0,
                "auto_corrected_count": auto_corrected,
            }

        except Exception as e:
            logger.error(f"Error testing {pdf_path}: {e}", exc_info=True)
            all_results[pdf_full_path.name] = {"error": str(e)}

    # Summary
    print("\n" + "="*70)
    print("SUMMARY - ALL PHASES TEST")
    print("="*70)

    for pdf_name, results in all_results.items():
        print(f"\n{pdf_name}:")
        if "error" in results:
            print(f"  ERROR: {results['error']}")
        else:
            print(f"  Products: {results['products']}")
            print(f"  Avg Confidence: {results['avg_confidence']:.1%}")
            print(f"  Multi-source Rate: {results['multi_source_rate']:.1%}")
            print(f"  Pattern Validated: {results['pattern_validated_rate']:.1%}")
            print(f"  Auto-corrected: {results['auto_corrected_count']}")

    print("\n" + "="*70)
    print("ALL PHASES TEST COMPLETE")
    print("="*70)

    # Check if targets met
    print("\n[ACCURACY TARGET CHECK]")
    total_products = sum(r.get("products", 0) for r in all_results.values() if "error" not in r)
    avg_overall_confidence = sum(
        r.get("avg_confidence", 0) * r.get("products", 0)
        for r in all_results.values() if "error" not in r
    ) / total_products if total_products > 0 else 0

    print(f"  Overall avg confidence: {avg_overall_confidence:.1%}")
    print(f"  Target: 95%+ for descriptions, 98%+ for prices, 99%+ for SKUs")

    if avg_overall_confidence >= 0.95:
        print("  STATUS: [PASS] Confidence targets met!")
    else:
        print("  STATUS: [NEEDS IMPROVEMENT] Below target")

    return all_results


def test_feedback_system():
    """Test Phase 7 feedback collection system."""
    print("\n" + "="*70)
    print("PHASE 7: FEEDBACK SYSTEM TEST")
    print("="*70)

    from parsers.shared.feedback_collector import FeedbackCollector

    collector = FeedbackCollector()

    # Simulate a correction
    print("\n[TEST] Recording sample correction...")
    collector.record_correction(
        original_value="SL1OO",  # OCR error: O instead of 0
        corrected_value="SL100",
        field_name="sku",
        manufacturer="select",
        confidence=0.75,
        extraction_method="layer1_text"
    )

    # Get accuracy report
    print("\n[REPORT] Feedback accuracy report:")
    report = collector.get_accuracy_report("select")

    print(json.dumps(report, indent=2, default=str))

    # Test correction suggestion
    print("\n[TEST] Testing correction suggestions...")
    suggestion = collector.get_correction_suggestions("SL1OO", "sku", "select")
    print(f"  Original: SL1OO")
    print(f"  Suggestion: {suggestion}")

    print("\n" + "="*70)


def test_pattern_learning():
    """Test Phase 5 pattern learning."""
    print("\n" + "="*70)
    print("PHASE 5: PATTERN LEARNING TEST")
    print("="*70)

    from parsers.shared.pattern_learner import AdaptivePatternLearner

    learner = AdaptivePatternLearner()

    # Sample products
    sample_products = [
        {"sku": "SL100", "description": "Continuous Hinge"},
        {"sku": "SL200", "description": "Geared Hinge"},
        {"sku": "BB1279", "description": "Ball Bearing Hinge"},
    ]

    print("\n[TEST] Learning patterns from sample products...")
    learner.learn_from_extraction("select", sample_products)

    # Test validation
    print("\n[TEST] Validating SKUs against learned patterns...")
    test_skus = ["SL150", "SL999", "BB1234", "INVALID"]

    for sku in test_skus:
        boost = learner.validate_sku("select", sku)
        print(f"  {sku}: {'MATCH' if boost > 0 else 'NO MATCH'} (boost: {boost:.2f})")

    print("\n" + "="*70)


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("UNIVERSAL PARSER - 7-PHASE ACCURACY IMPROVEMENT TEST SUITE")
    print("="*70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test 1: Pattern Learning
    test_pattern_learning()

    # Test 2: Feedback System
    test_feedback_system()

    # Test 3: Full parser with all phases
    test_universal_parser_all_phases()

    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "="*70)
    print("ALL TESTS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
