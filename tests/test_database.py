import unittest
import os
import tempfile
from datetime import datetime, date

from database.manager import PriceBookManager
from database.models import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    """Test cases for database manager"""
    
    def setUp(self):
        """Set up test database"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.db_manager = DatabaseManager(f'sqlite:///{self.temp_db.name}')
        self.price_book_manager = PriceBookManager(f'sqlite:///{self.temp_db.name}')
        
        # Initialize database
        self.price_book_manager.initialize_database()
    
    def tearDown(self):
        """Clean up test database"""
        os.unlink(self.temp_db.name)
    
    def test_database_initialization(self):
        """Test database initialization"""
        session = self.db_manager.get_session()
        
        # Check if manufacturers were created
        from database.models import Manufacturer
        manufacturers = session.query(Manufacturer).all()
        
        self.assertGreater(len(manufacturers), 0)
        
        # Check for Hager and SELECT Hinges
        manufacturer_names = [m.name for m in manufacturers]
        self.assertIn('Hager', manufacturer_names)
        self.assertIn('Select Hinges', manufacturer_names)
        
        session.close()
    
    def test_normalize_and_store_data(self):
        """Test data normalization and storage"""
        # Mock parsed data
        parsed_data = {
            'manufacturer': 'hager',
            'effective_date': '2025-01-01',
            'products': [
                {
                    'sku': 'BB1191-US3',
                    'model': 'BB1191',
                    'description': 'Test Hinge',
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
        
        result = self.price_book_manager.normalize_and_store_data(parsed_data)
        
        self.assertEqual(result['status'], 'success')
        self.assertGreater(result['products_created'], 0)
        self.assertGreater(result['finishes_created'], 0)
    
    def test_get_price_book_summary(self):
        """Test price book summary retrieval"""
        # First create a price book
        parsed_data = {
            'manufacturer': 'hager',
            'effective_date': '2025-01-01',
            'products': [
                {
                    'sku': 'BB1191-US3',
                    'model': 'BB1191',
                    'description': 'Test Hinge',
                    'base_price': 145.50,
                    'is_active': True
                }
            ],
            'finishes': [],
            'options': []
        }
        
        result = self.price_book_manager.normalize_and_store_data(parsed_data)
        price_book_id = result['price_book_id']
        
        # Get summary
        summary = self.price_book_manager.get_price_book_summary(price_book_id)
        
        self.assertEqual(summary['manufacturer'], 'Hager')
        self.assertEqual(summary['product_count'], 1)
        self.assertEqual(summary['status'], 'completed')
    
    def test_get_products_by_price_book(self):
        """Test product retrieval by price book"""
        # Create test data
        parsed_data = {
            'manufacturer': 'hager',
            'effective_date': '2025-01-01',
            'products': [
                {
                    'sku': 'BB1191-US3',
                    'model': 'BB1191',
                    'description': 'Test Hinge 1',
                    'base_price': 145.50,
                    'is_active': True
                },
                {
                    'sku': 'BB1192-US4',
                    'model': 'BB1192',
                    'description': 'Test Hinge 2',
                    'base_price': 155.50,
                    'is_active': True
                }
            ],
            'finishes': [],
            'options': []
        }
        
        result = self.price_book_manager.normalize_and_store_data(parsed_data)
        price_book_id = result['price_book_id']
        
        # Get products
        products = self.price_book_manager.get_products_by_price_book(price_book_id)
        
        self.assertEqual(len(products), 2)
        self.assertEqual(products[0]['sku'], 'BB1191-US3')
        self.assertEqual(products[1]['sku'], 'BB1192-US4')
    
    def test_list_price_books(self):
        """Test price book listing"""
        # Create multiple price books
        for i in range(3):
            parsed_data = {
                'manufacturer': 'hager',
                'effective_date': f'2025-0{i+1}-01',
                'products': [
                    {
                        'sku': f'BB119{i}',
                        'model': f'BB119{i}',
                        'description': f'Test Product {i}',
                        'base_price': 100.00 + i * 10,
                        'is_active': True
                    }
                ],
                'finishes': [],
                'options': []
            }
            self.price_book_manager.normalize_and_store_data(parsed_data)
        
        # List price books
        price_books = self.price_book_manager.list_price_books()
        
        self.assertEqual(len(price_books), 3)
        self.assertEqual(price_books[0]['manufacturer'], 'Hager')
    
    def test_parse_date(self):
        """Test date parsing functionality"""
        test_cases = [
            ('2025-01-01', date(2025, 1, 1)),
            ('01/01/2025', date(2025, 1, 1)),
            ('01-01-2025', date(2025, 1, 1)),
            ('1/1/25', date(2025, 1, 1)),
            ('invalid', date.today()),
            ('', None),
            (None, None)
        ]
        
        for date_str, expected in test_cases:
            with self.subTest(date_str=date_str):
                result = self.price_book_manager._parse_date(date_str)
                if expected is None:
                    self.assertIsNone(result)
                else:
                    self.assertEqual(result, expected)
    
    def test_extract_family_name(self):
        """Test family name extraction"""
        test_cases = [
            ({'sku': 'BB1191', 'description': 'Hinge'}, 'BB Series'),
            ({'sku': 'H3A', 'description': 'Hardware'}, 'H Series'),
            ({'sku': 'S123', 'description': 'Lock'}, 'S Series'),
            ({'sku': 'ABC123', 'description': 'Door Handle'}, 'Handles'),
            ({'sku': 'XYZ', 'description': 'Test'}, None)
        ]
        
        for product_data, expected in test_cases:
            with self.subTest(product_data=product_data):
                result = self.price_book_manager._extract_family_name(product_data)
                self.assertEqual(result, expected)
    
    def test_categorize_family(self):
        """Test family categorization"""
        test_cases = [
            ('Hinges', 'Hinges'),
            ('Locks', 'Locks'),
            ('Handles', 'Handles'),
            ('BB Series', 'Hardware'),
            ('Unknown', 'General')
        ]
        
        for family_name, expected in test_cases:
            with self.subTest(family_name=family_name):
                result = self.price_book_manager._categorize_family(family_name)
                self.assertEqual(result, expected)

class TestDatabaseModels(unittest.TestCase):
    """Test cases for database models"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.db_manager = DatabaseManager(f'sqlite:///{self.temp_db.name}')
        self.db_manager.create_tables()
    
    def tearDown(self):
        """Clean up test database"""
        os.unlink(self.temp_db.name)
    
    def test_manufacturer_creation(self):
        """Test manufacturer model creation"""
        from database.models import Manufacturer
        
        session = self.db_manager.get_session()
        
        manufacturer = Manufacturer(
            name='Test Manufacturer',
            code='TEST'
        )
        
        session.add(manufacturer)
        session.commit()
        
        # Verify creation
        retrieved = session.query(Manufacturer).filter(Manufacturer.code == 'TEST').first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, 'Test Manufacturer')
        
        session.close()
    
    def test_price_book_creation(self):
        """Test price book model creation"""
        from database.models import PriceBook, Manufacturer
        
        session = self.db_manager.get_session()
        
        # Create manufacturer first
        manufacturer = Manufacturer(name='Test Manufacturer', code='TEST')
        session.add(manufacturer)
        session.flush()
        
        # Create price book
        price_book = PriceBook(
            manufacturer_id=manufacturer.id,
            edition='2025',
            effective_date=date(2025, 1, 1),
            status='completed'
        )
        
        session.add(price_book)
        session.commit()
        
        # Verify creation
        retrieved = session.query(PriceBook).filter(PriceBook.edition == '2025').first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.manufacturer.name, 'Test Manufacturer')
        
        session.close()
    
    def test_product_creation(self):
        """Test product model creation"""
        from database.models import Product, PriceBook, Manufacturer
        
        session = self.db_manager.get_session()
        
        # Create manufacturer and price book
        manufacturer = Manufacturer(name='Test Manufacturer', code='TEST')
        session.add(manufacturer)
        session.flush()
        
        price_book = PriceBook(
            manufacturer_id=manufacturer.id,
            edition='2025',
            status='completed'
        )
        session.add(price_book)
        session.flush()
        
        # Create product
        product = Product(
            price_book_id=price_book.id,
            sku='TEST123',
            model='TEST',
            description='Test Product',
            base_price=100.00,
            is_active=True
        )
        
        session.add(product)
        session.commit()
        
        # Verify creation
        retrieved = session.query(Product).filter(Product.sku == 'TEST123').first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.base_price, 100.00)
        
        session.close()

if __name__ == '__main__':
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTest(unittest.makeSuite(TestDatabaseManager))
    suite.addTest(unittest.makeSuite(TestDatabaseModels))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\nTests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")
