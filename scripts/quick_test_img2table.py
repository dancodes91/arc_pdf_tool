#!/usr/bin/env python3
"""
Quick test of img2table + PaddleOCR integration.
Tests table extraction directly on one PDF.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("Importing UniversalParser...")
from parsers.universal import UniversalParser

print("Testing on SELECT Hinges PDF...")
pdf_path = "test_data/pdfs/2025-select-hinges-price-book.pdf"

parser = UniversalParser(
    pdf_path,
    config={
        "max_pages": 5,  # Only test 5 pages for speed
        "use_ml_detection": True,
        "confidence_threshold": 0.6,
    }
)

print("Parsing PDF...")
results = parser.parse()

print("\n" + "="*80)
print("RESULTS:")
print("="*80)
print(f"Manufacturer: {results.get('manufacturer', 'Unknown')}")
print(f"Tables detected: {results['parsing_metadata']['tables_detected']}")
print(f"Products found: {results['summary']['total_products']}")
print(f"Options found: {results['summary']['total_options']}")
print(f"Finishes found: {results['summary']['total_finishes']}")
print(f"Confidence: {results['summary']['confidence']:.2%}")
print("="*80)

if results['summary']['total_products'] > 0:
    print("\nSUCCESS: img2table + PaddleOCR WORKING!")
    print(f"Extracted {results['summary']['total_products']} products from tables.")
else:
    print("\nWARNING: No products extracted.")
    print(f"Tables detected: {results['parsing_metadata']['tables_detected']}")
    print("Check if OCR is working correctly.")
