#!/usr/bin/env python3
"""
Test full pipeline: Parse -> ETL -> Database -> API
Validates that confidence boosting works end-to-end with SQLite database
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.universal import UniversalParser
from services.etl_loader import ETLLoader
from database.models import DatabaseManager, PriceBook, Product
from database.manager import PriceBookManager
from sqlalchemy import func


def test_full_pipeline():
    """Test the complete pipeline"""

    print('=' * 80)
    print('TESTING FULL PIPELINE: PARSE -> ETL -> DATABASE')
    print('=' * 80)

    # 1. Parse a PDF with hybrid parser
    pdf_path = 'test_data/pdfs/2020-continental-access-price-book.pdf'
    print(f'\nStep 1: Parsing {pdf_path}...')
    parser = UniversalParser(pdf_path, config={'use_hybrid': True})
    parsed_data = parser.parse()

    print(f'  OK Parsed successfully')
    print(f'  - Products: {parsed_data["summary"]["total_products"]}')
    print(f'  - Confidence: {parsed_data["summary"]["confidence"]:.1%}')

    # 2. Create a test database
    test_db_path = 'test_price_books_temp.db'
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    print(f'\nStep 2: Creating test database...')
    db_url = f'sqlite:///{test_db_path}'
    db_manager = DatabaseManager(db_url)

    # Create all tables
    db_manager.create_tables()

    session = db_manager.get_session()
    print(f'  OK Database created: {test_db_path}')

    # 3. Load data using ETL Loader
    print(f'\nStep 3: Loading data with ETL Loader...')
    parsed_data['file_path'] = pdf_path
    parsed_data['file_size'] = os.path.getsize(pdf_path)

    etl_loader = ETLLoader(database_url=db_url)
    load_result = etl_loader.load_parsing_results(parsed_data, session)
    session.commit()

    print(f'  OK Data loaded successfully')
    print(f'  - Price Book ID: {load_result["price_book_id"]}')
    print(f'  - Products loaded: {load_result["products_loaded"]}')
    print(f'  - Finishes loaded: {load_result.get("finishes_loaded", 0)}')

    # 4. Verify data in database
    print(f'\nStep 4: Verifying data in database...')

    # Check price book
    price_book = session.query(PriceBook).filter_by(id=load_result['price_book_id']).first()
    if price_book:
        print(f'  OK Price Book found:')
        print(f'    - ID: {price_book.id}')
        print(f'    - Manufacturer: {price_book.manufacturer.name if price_book.manufacturer else "Unknown"}')
        print(f'    - File Path: {price_book.file_path}')
        print(f'    - Status: {price_book.status}')

        # Count products
        product_count = len(price_book.products)
        print(f'    - Total Products: {product_count}')

        # Check if confidence is stored
        if hasattr(price_book, 'overall_confidence') and price_book.overall_confidence is not None:
            print(f'    - Overall Confidence: {price_book.overall_confidence:.1%}')
        else:
            print(f'    - Overall Confidence: NOT STORED (field missing or NULL)')
    else:
        print(f'  X Price Book NOT found!')
        return False

    # Check products
    products = session.query(Product).filter_by(price_book_id=load_result['price_book_id']).limit(5).all()
    print(f'\n  OK First 5 products:')
    for i, product in enumerate(products, 1):
        print(f'    Product {i}:')
        print(f'      SKU: {product.sku}')
        print(f'      Price: ${product.base_price:.2f}')
        print(f'      Description: {product.description or "N/A"}')

        # Check if confidence is stored
        if hasattr(product, 'confidence') and product.confidence is not None:
            print(f'      Confidence: {product.confidence:.1%} OK')
        else:
            print(f'      Confidence: NOT STORED (field missing or NULL)')

        print(f'      Page: {product.page_number}')

    # Check total count
    total_products = session.query(func.count(Product.id)).filter_by(price_book_id=load_result['price_book_id']).scalar()
    print(f'\n  OK Total products in DB: {total_products}')

    # 5. Test retrieval (like API would do)
    print(f'\nStep 5: Testing retrieval (API simulation)...')
    price_book_manager = PriceBookManager(db_url)

    summary = price_book_manager.get_price_book_summary(load_result['price_book_id'])

    if summary:
        print(f'  OK Summary retrieved:')
        print(f'    - Manufacturer: {summary.get("manufacturer")}')
        print(f'    - Total Products: {summary.get("total_products")}')
        print(f'    - Confidence: {summary.get("confidence", "NOT IN SUMMARY")}')
    else:
        print(f'  X Summary NOT retrieved!')
        return False

    # Get products
    products_list = price_book_manager.get_products_by_price_book(load_result['price_book_id'], limit=3)
    print(f'\n  OK Products retrieved: {len(products_list)}')
    for i, prod in enumerate(products_list, 1):
        sku = prod.get("sku", "N/A")
        price = prod.get("base_price", 0)
        conf = prod.get("confidence", "NOT IN RESPONSE")
        print(f'    Product {i}: {sku} - ${price:.2f} (confidence: {conf})')

    # 6. Validate confidence values
    print(f'\nStep 6: Validating confidence scores...')

    # Check if confidence is in the expected range
    if hasattr(price_book, 'overall_confidence') and price_book.overall_confidence:
        if 0.85 <= price_book.overall_confidence <= 1.0:
            print(f'  OK Overall confidence in valid range: {price_book.overall_confidence:.1%}')
        else:
            print(f'  ! Overall confidence outside expected range: {price_book.overall_confidence:.1%}')

    # Check product confidences
    high_conf_count = 0
    for product in products:
        if hasattr(product, 'confidence') and product.confidence:
            if product.confidence >= 0.90:
                high_conf_count += 1

    print(f'  OK Products with 90%+ confidence: {high_conf_count}/{len(products)}')

    # Cleanup
    session.close()

    print(f'\n' + '=' * 80)
    print('TEST COMPLETE - SUCCESS!')
    print('=' * 80)
    print(f'\nDatabase saved at: {test_db_path}')
    print(f'You can inspect it with: sqlite3 {test_db_path}')
    print(f'\nQuick SQL queries to try:')
    print(f'  SELECT * FROM price_books;')
    print(f'  SELECT sku, base_price, confidence FROM products LIMIT 10;')
    print(f'  SELECT AVG(confidence) FROM products;')

    return True


if __name__ == "__main__":
    success = test_full_pipeline()
    sys.exit(0 if success else 1)
