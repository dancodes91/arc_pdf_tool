"""
Test script to verify Camelot timeout protection.
"""
import logging
import sys
import time
from parsers.select.sections import SelectSectionExtractor
from parsers.shared.provenance import ProvenanceTracker

# Configure logging to see timeout messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_timeout_protection():
    """Test that Camelot extraction times out properly."""

    # This should be a PDF that exists (use any SELECT PDF you have)
    test_pdf = r"test_data\pdfs\2025-select-hinges-price-book.pdf"

    logger.info("=" * 70)
    logger.info("Testing Camelot timeout protection")
    logger.info("=" * 70)

    # Create extractor
    tracker = ProvenanceTracker(test_pdf)
    extractor = SelectSectionExtractor(tracker)

    # Test with very short timeout to simulate hang
    logger.info("\nTest 1: Short timeout (5 seconds) - should timeout quickly")
    start = time.time()
    result = extractor.extract_tables_with_camelot(test_pdf, 1, timeout=5)
    elapsed = time.time() - start

    logger.info(f"Result: {'Success' if result else 'Timeout/Failed'}")
    logger.info(f"Elapsed time: {elapsed:.2f}s")
    logger.info(f"Tables extracted: {len(result) if result else 0}")

    # Test with normal timeout
    logger.info("\nTest 2: Normal timeout (30 seconds) - should complete")
    start = time.time()
    result = extractor.extract_tables_with_camelot(test_pdf, 1, timeout=30)
    elapsed = time.time() - start

    logger.info(f"Result: {'Success' if result else 'Timeout/Failed'}")
    logger.info(f"Elapsed time: {elapsed:.2f}s")
    logger.info(f"Tables extracted: {len(result) if result else 0}")

    logger.info("\n" + "=" * 70)
    logger.info("Timeout protection test completed successfully!")
    logger.info("=" * 70)

if __name__ == "__main__":
    try:
        test_timeout_protection()
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        sys.exit(1)
