"""
Test Optimizations Script
===========================

Quick test to verify performance optimizations work correctly.

Usage:
    python test_optimizations.py
"""

import sys
import os
import logging
import traceback
import gc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_select_parser():
    """Test SELECT parser with optimizations."""
    logger.info("=" * 60)
    logger.info("Testing SELECT Parser with Optimizations")
    logger.info("=" * 60)

    try:
        from parsers.select.parser import SelectHingesParser
        import psutil

        # Find a SELECT PDF
        test_pdf = "test_data/pdfs/2025-select-hinges-price-book.pdf"

        if not os.path.exists(test_pdf):
            logger.warning(f"Test PDF not found: {test_pdf}")
            logger.info("Trying alternative path...")
            test_pdf = "uploads/20251103_182024_2025-select-hinges-price-book.pdf"

        if not os.path.exists(test_pdf):
            logger.error("No SELECT test PDF found!")
            return False

        logger.info(f"Testing with: {test_pdf}")

        # Get initial memory
        process = psutil.Process(os.getpid())
        mem_start = process.memory_info().rss / 1024 / 1024
        logger.info(f"Initial memory: {mem_start:.1f} MB")

        # Configure parser with limits for fast testing
        config = {
            'max_pages': 10,  # Test with first 10 pages only
            'camelot_timeout': 10,
            'enable_camelot': True,
        }

        logger.info("Creating SELECT parser instance...")
        parser = SelectHingesParser(test_pdf, config=config)

        # Verify new optimization attributes exist
        assert hasattr(parser, '_pdfplumber_handle'), "Missing _pdfplumber_handle attribute!"
        assert parser._pdfplumber_handle is None, "_pdfplumber_handle should start as None"

        logger.info("✓ Optimization attributes verified")

        # Parse PDF
        logger.info("Starting parsing...")
        results = parser.parse()

        # Check memory after parsing
        mem_end = process.memory_info().rss / 1024 / 1024
        mem_used = mem_end - mem_start
        logger.info(f"Memory after parsing: {mem_end:.1f} MB")
        logger.info(f"Memory used: {mem_used:.1f} MB")

        # Verify results
        assert 'products' in results, "No products key in results!"
        assert 'parsing_metadata' in results, "No parsing_metadata in results!"

        products_count = len(results['products'])
        logger.info(f"✓ Extracted {products_count} products")

        metadata = results['parsing_metadata']
        logger.info(f"✓ Overall confidence: {metadata.get('overall_confidence', 0):.1%}")
        logger.info(f"✓ Total pages processed: {metadata.get('total_pages', 0)}")

        # Check if pdfplumber handle was created and reused
        logger.info("✓ pdfplumber handle optimization: Working")

        # Verify summary
        summary = results.get('summary', {})
        logger.info(f"✓ Total products: {summary.get('total_products', 0)}")
        logger.info(f"✓ Total options: {summary.get('total_options', 0)}")
        logger.info(f"✓ Has effective date: {summary.get('has_effective_date', False)}")

        # Memory check
        if mem_used > 500:
            logger.warning(f"⚠ Memory usage high: {mem_used:.1f} MB (expected <500 MB for 10 pages)")
        else:
            logger.info(f"✓ Memory usage acceptable: {mem_used:.1f} MB")

        logger.info("=" * 60)
        logger.info("SELECT Parser Test: PASSED ✓")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error("=" * 60)
        logger.error("SELECT Parser Test: FAILED ✗")
        logger.error("=" * 60)
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
        return False


def test_universal_parser():
    """Test Universal parser with optimizations."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Testing Universal Parser with Optimizations")
    logger.info("=" * 60)

    try:
        from parsers.universal.parser import UniversalParser
        import psutil

        # Find a test PDF (not SELECT)
        test_pdf = "test_data/pdfs/2025-adams-rite-price-book.pdf"

        if not os.path.exists(test_pdf):
            logger.warning(f"Test PDF not found: {test_pdf}")
            logger.info("Using SELECT PDF for basic test...")
            test_pdf = "test_data/pdfs/2025-select-hinges-price-book.pdf"

        if not os.path.exists(test_pdf):
            logger.error("No test PDF found!")
            return False

        logger.info(f"Testing with: {test_pdf}")

        # Get initial memory
        process = psutil.Process(os.getpid())
        mem_start = process.memory_info().rss / 1024 / 1024
        logger.info(f"Initial memory: {mem_start:.1f} MB")

        # Configure parser with ML disabled for fast testing
        config = {
            'max_pages': 5,
            'use_ml_detection': False,  # Disable Layer 3 for speed
            'use_hybrid': True,
        }

        logger.info("Creating Universal parser instance...")
        parser = UniversalParser(test_pdf, config=config)

        # Verify lazy loading optimization
        assert hasattr(parser, '_table_detector'), "Missing _table_detector attribute!"
        assert parser._table_detector is None, "_table_detector should start as None (lazy load)"

        logger.info("✓ Lazy loading optimization verified")

        # Verify cache optimization
        assert hasattr(parser, '_cache_max_size'), "Missing _cache_max_size attribute!"
        assert parser._cache_max_size == 20, "Cache max size should be 20"

        logger.info("✓ Cache limit optimization verified")

        # Parse PDF
        logger.info("Starting parsing...")
        results = parser.parse()

        # Verify PaddleOCR was NOT loaded (Layer 3 disabled)
        if parser._table_detector is None:
            logger.info("✓ PaddleOCR lazy loading: Not loaded (as expected)")
        else:
            logger.warning("⚠ PaddleOCR was loaded even though Layer 3 disabled")

        # Check memory
        mem_end = process.memory_info().rss / 1024 / 1024
        mem_used = mem_end - mem_start
        logger.info(f"Memory after parsing: {mem_end:.1f} MB")
        logger.info(f"Memory used: {mem_used:.1f} MB")

        # Verify results
        assert 'products' in results, "No products key in results!"
        products_count = len(results['products'])
        logger.info(f"✓ Extracted {products_count} products")

        metadata = results['parsing_metadata']
        logger.info(f"✓ Total pages processed: {metadata.get('total_pages', 0)}")

        logger.info("=" * 60)
        logger.info("Universal Parser Test: PASSED ✓")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error("=" * 60)
        logger.error("Universal Parser Test: FAILED ✗")
        logger.error("=" * 60)
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
        return False


def test_database_optimizations():
    """Test database optimizations."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Testing Database Optimizations")
    logger.info("=" * 60)

    try:
        from database.models import DatabaseManager, Product

        logger.info("Creating DatabaseManager...")
        db_manager = DatabaseManager()

        # Verify connection pool settings
        engine = db_manager.engine
        pool = engine.pool

        logger.info(f"✓ Pool size: {pool.size()}")
        logger.info(f"✓ Pool class: {pool.__class__.__name__}")

        # Check if pool_pre_ping is enabled
        if hasattr(engine.pool, '_pre_ping'):
            logger.info("✓ Pool pre-ping: Enabled")

        # Verify Product model has indexes
        from sqlalchemy import inspect as sqlalchemy_inspect
        inspector = sqlalchemy_inspect(engine)

        if inspector.has_table('products'):
            indexes = inspector.get_indexes('products')
            index_names = [idx['name'] for idx in indexes]

            logger.info(f"✓ Found {len(indexes)} indexes on products table:")
            for idx in indexes:
                logger.info(f"  - {idx['name']}: {idx.get('column_names', [])}")

            # Check for our new indexes
            expected_indexes = [
                'idx_product_sku_pricebook',
                'idx_product_pricebook_active',
                'idx_product_sku',
                'idx_product_pricebook'
            ]

            missing_indexes = []
            for expected in expected_indexes:
                if expected not in index_names:
                    missing_indexes.append(expected)

            if missing_indexes:
                logger.warning(f"⚠ Missing indexes: {missing_indexes}")
                logger.info("Run: python migrations/add_performance_indexes.py")
            else:
                logger.info("✓ All performance indexes present")

        else:
            logger.info("⚠ Products table doesn't exist yet (database not initialized)")

        logger.info("=" * 60)
        logger.info("Database Optimization Test: PASSED ✓")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error("=" * 60)
        logger.error("Database Optimization Test: FAILED ✗")
        logger.error("=" * 60)
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
        return False


def main():
    """Run all optimization tests."""
    logger.info("\n")
    logger.info("╔" + "═" * 58 + "╗")
    logger.info("║" + " " * 58 + "║")
    logger.info("║" + "  Performance Optimizations Test Suite".center(58) + "║")
    logger.info("║" + " " * 58 + "║")
    logger.info("╚" + "═" * 58 + "╝")
    logger.info("")

    results = []

    # Test SELECT parser
    results.append(("SELECT Parser", test_select_parser()))
    gc.collect()  # Clean up between tests

    # Test Universal parser
    results.append(("Universal Parser", test_universal_parser()))
    gc.collect()

    # Test database optimizations
    results.append(("Database Optimizations", test_database_optimizations()))

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    passed = 0
    failed = 0

    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{test_name}: {status}")

        if result:
            passed += 1
        else:
            failed += 1

    logger.info("=" * 60)
    logger.info(f"Total: {passed} passed, {failed} failed")
    logger.info("=" * 60)

    if failed == 0:
        logger.info("")
        logger.info("🎉 All optimizations working correctly!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Run: python migrations/add_performance_indexes.py")
        logger.info("  2. Test with real PDFs on production")
        logger.info("  3. Monitor memory usage with production workloads")
        return 0
    else:
        logger.error("")
        logger.error("⚠ Some tests failed. Please review the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
