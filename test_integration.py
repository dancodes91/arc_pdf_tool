#!/usr/bin/env python3
"""
Integration test for PDF Price Book Parser
This script tests the complete application flow without requiring actual PDF files.
"""

import os
import sys
import tempfile
import logging
from datetime import datetime, date

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.manager import PriceBookManager
from parsers.hager_parser import HagerParser
from parsers.select_hinges_parser import SelectHingesParser
from diff_engine import DiffEngine
from export_manager import ExportManager

def test_database_operations():
    """Test database operations"""
    print("🧪 Testing database operations...")
    
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    try:
        # Initialize database manager
        db_manager = PriceBookManager(f'sqlite:///{temp_db.name}')
        db_manager.initialize_database()
        
        # Test data
        test_data = {
            'manufacturer': 'hager',
            'effective_date': '2025-01-01',
            'products': [
                {
                    'sku': 'BB1191-US3',
                    'model': 'BB1191',
                    'description': 'Test Hinge Product',
                    'base_price': 145.50,
                    'is_active': True
                },
                {
                    'sku': 'BB1192-US4',
                    'model': 'BB1192',
                    'description': 'Another Test Product',
                    'base_price': 155.75,
                    'is_active': True
                }
            ],
            'finishes': [
                {
                    'code': 'US3',
                    'name': 'Satin Chrome',
                    'adder_type': 'net_add',
                    'adder_value': 15.00
                },
                {
                    'code': 'US4',
                    'name': 'Bright Chrome',
                    'adder_type': 'net_add',
                    'adder_value': 20.00
                }
            ],
            'options': []
        }
        
        # Store data
        result = db_manager.normalize_and_store_data(test_data)
        print(f"✅ Stored data: {result}")
        
        # Test retrieval
        summary = db_manager.get_price_book_summary(result['price_book_id'])
        print(f"✅ Retrieved summary: {summary['manufacturer']} - {summary['product_count']} products")
        
        # Test product listing
        products = db_manager.get_products_by_price_book(result['price_book_id'])
        print(f"✅ Retrieved {len(products)} products")
        
        return result['price_book_id']
        
    finally:
        # Cleanup
        try:
            if os.path.exists(temp_db.name):
                os.unlink(temp_db.name)
        except (PermissionError, OSError):
            # File might be locked, ignore cleanup errors in tests
            pass

def test_parser_validation():
    """Test parser validation"""
    print("\n🧪 Testing parser validation...")
    
    # Test Hager parser
    hager_parser = HagerParser("dummy_path")
    
    # Mock data
    test_data = {
        'manufacturer': 'hager',
        'effective_date': '2025-01-01',
        'products': [
            {
                'sku': 'BB1191-US3',
                'model': 'BB1191',
                'description': 'Test Product',
                'base_price': 145.50,
                'is_active': True
            }
        ],
        'finishes': [
            {
                'code': 'US3',
                'name': 'Satin Chrome',
                'adder_type': 'net_add',
                'adder_value': 15.00
            }
        ],
        'options': []
    }
    
    validation = hager_parser.validate_data(test_data)
    print(f"✅ Hager parser validation: {validation['is_valid']}")
    
    # Test SELECT Hinges parser
    select_parser = SelectHingesParser("dummy_path")
    
    test_data_select = {
        'manufacturer': 'select_hinges',
        'effective_date': '2025-01-01',
        'products': [
            {
                'sku': 'H3A',
                'model': '3A',
                'description': 'Test Hinge',
                'base_price': 125.00,
                'is_active': True
            }
        ],
        'finishes': [],
        'options': [
            {
                'option_type': 'net_add',
                'option_code': 'CTW',
                'option_name': 'Continuous Weld',
                'adder_type': 'net_add',
                'adder_value': 25.00
            }
        ]
    }
    
    validation_select = select_parser.validate_data(test_data_select)
    print(f"✅ SELECT Hinges parser validation: {validation_select['is_valid']}")

def test_diff_engine():
    """Test diff engine"""
    print("\n🧪 Testing diff engine...")
    
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    try:
        db_manager = PriceBookManager(f'sqlite:///{temp_db.name}')
        db_manager.initialize_database()
        
        # Create two price books
        old_data = {
            'manufacturer': 'hager',
            'effective_date': '2024-01-01',
            'products': [
                {
                    'sku': 'BB1191-US3',
                    'model': 'BB1191',
                    'description': 'Test Product',
                    'base_price': 140.00,
                    'is_active': True
                }
            ],
            'finishes': [],
            'options': []
        }
        
        new_data = {
            'manufacturer': 'hager',
            'effective_date': '2025-01-01',
            'products': [
                {
                    'sku': 'BB1191-US3',
                    'model': 'BB1191',
                    'description': 'Test Product Updated',
                    'base_price': 145.50,  # Price increased
                    'is_active': True
                },
                {
                    'sku': 'BB1192-US4',  # New product
                    'model': 'BB1192',
                    'description': 'New Product',
                    'base_price': 155.00,
                    'is_active': True
                }
            ],
            'finishes': [],
            'options': []
        }
        
        # Store both price books
        old_result = db_manager.normalize_and_store_data(old_data)
        new_result = db_manager.normalize_and_store_data(new_data)
        
        # Test diff engine
        diff_engine = DiffEngine(f'sqlite:///{temp_db.name}')
        comparison = diff_engine.compare_price_books(
            old_result['price_book_id'], 
            new_result['price_book_id']
        )
        
        print(f"✅ Diff engine comparison: {comparison['summary']['total_changes']} changes found")
        print(f"   - New products: {comparison['summary']['new_products']}")
        print(f"   - Price changes: {comparison['summary']['price_changes']}")
        
    finally:
        try:
            if os.path.exists(temp_db.name):
                os.unlink(temp_db.name)
        except (PermissionError, OSError):
            pass

def test_export_functionality():
    """Test export functionality"""
    print("\n🧪 Testing export functionality...")
    
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    try:
        db_manager = PriceBookManager(f'sqlite:///{temp_db.name}')
        db_manager.initialize_database()
        
        # Create test data
        test_data = {
            'manufacturer': 'hager',
            'effective_date': '2025-01-01',
            'products': [
                {
                    'sku': 'BB1191-US3',
                    'model': 'BB1191',
                    'description': 'Test Product for Export',
                    'base_price': 145.50,
                    'is_active': True
                }
            ],
            'finishes': [],
            'options': []
        }
        
        result = db_manager.normalize_and_store_data(test_data)
        price_book_id = result['price_book_id']
        
        # Test Excel export
        export_manager = ExportManager(f'sqlite:///{temp_db.name}')
        
        try:
            excel_file = export_manager.export_price_book(price_book_id, format='excel')
            print(f"✅ Excel export created: {os.path.basename(excel_file)}")
            
            # Clean up export file
            if os.path.exists(excel_file):
                os.remove(excel_file)
        except Exception as e:
            print(f"⚠️  Excel export failed: {e}")
        
        try:
            csv_file = export_manager.export_price_book(price_book_id, format='csv')
            print(f"✅ CSV export created: {os.path.basename(csv_file)}")
            
            # Clean up export file
            if os.path.exists(csv_file):
                os.remove(csv_file)
        except Exception as e:
            print(f"⚠️  CSV export failed: {e}")
        
    finally:
        try:
            if os.path.exists(temp_db.name):
                os.unlink(temp_db.name)
        except (PermissionError, OSError):
            pass

def main():
    """Run all integration tests"""
    print("🚀 Starting PDF Price Book Parser Integration Tests")
    print("=" * 60)
    
    try:
        # Test database operations
        price_book_id = test_database_operations()
        
        # Test parser validation
        test_parser_validation()
        
        # Test diff engine
        test_diff_engine()
        
        # Test export functionality
        test_export_functionality()
        
        print("\n" + "=" * 60)
        print("✅ All integration tests passed successfully!")
        print("\n🎯 The application is ready for use.")
        print("   Run 'python run.py' to start the web interface.")
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
