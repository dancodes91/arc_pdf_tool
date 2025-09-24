import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock
import pandas as pd

from parsers.hager_parser import HagerParser
from parsers.select_hinges_parser import SelectHingesParser

class TestHagerParser(unittest.TestCase):
    """Test cases for Hager parser"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.sample_pdf_path = "test_data/hager_sample.pdf"
        self.parser = HagerParser(self.sample_pdf_path)
    
    def test_identify_manufacturer(self):
        """Test manufacturer identification"""
        # Mock text content
        self.parser.text_content = "Hager Companies Price Book 2025"
        
        manufacturer = self.parser.identify_manufacturer()
        self.assertEqual(manufacturer, 'hager')
    
    def test_clean_price(self):
        """Test price cleaning functionality"""
        # Test various price formats
        test_cases = [
            ("$145.50", 145.50),
            ("145.50", 145.50),
            ("1,234.56", 1234.56),
            ("1,234", 1234.0),
            ("invalid", None),
            ("", None),
            (None, None)
        ]
        
        for input_price, expected in test_cases:
            with self.subTest(input_price=input_price):
                result = self.parser.clean_price(input_price)
                self.assertEqual(result, expected)
    
    def test_clean_sku(self):
        """Test SKU cleaning functionality"""
        test_cases = [
            ("BB1191-US3", "BB1191-US3"),
            ("  bb1191-us3  ", "BB1191-US3"),
            ("BB1191", "BB1191"),
            ("", ""),
            (None, "")
        ]
        
        for input_sku, expected in test_cases:
            with self.subTest(input_sku=input_sku):
                result = self.parser.clean_sku(input_sku)
                self.assertEqual(result, expected)
    
    def test_extract_model_from_sku(self):
        """Test model extraction from SKU"""
        test_cases = [
            ("BB1191-US3", "BB1191"),
            ("BBH1234-US4", "BBH1234"),
            ("BB1191", "BB1191"),
            ("H3A-US10B", "H3A")
        ]
        
        for sku, expected in test_cases:
            with self.subTest(sku=sku):
                result = self.parser._extract_model_from_sku(sku)
                self.assertEqual(result, expected)
    
    def test_extract_finish_from_sku(self):
        """Test finish code extraction from SKU"""
        test_cases = [
            ("BB1191-US3", "US3"),
            ("BBH1234-US4", "US4"),
            ("BB1191", None),
            ("H3A-US10B", "US10B")
        ]
        
        for sku, expected in test_cases:
            with self.subTest(sku=sku):
                result = self.parser._extract_finish_from_sku(sku)
                self.assertEqual(result, expected)
    
    def test_looks_like_sku(self):
        """Test SKU pattern recognition"""
        test_cases = [
            ("BB1191", True),
            ("BBH1234", True),
            ("H3A", True),
            ("123", False),
            ("ABC", False),
            ("", False)
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                result = self.parser._looks_like_sku(text)
                self.assertEqual(result, expected)
    
    def test_looks_like_price(self):
        """Test price pattern recognition"""
        test_cases = [
            ("$145.50", True),
            ("145.50", True),
            ("1,234.56", True),
            ("invalid", False),
            ("", False)
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                result = self.parser._looks_like_price(text)
                self.assertEqual(result, expected)
    
    @patch('parsers.hager_parser.pdfplumber.open')
    def test_extract_tables_pdfplumber(self, mock_pdfplumber):
        """Test table extraction with pdfplumber"""
        # Mock pdfplumber response
        mock_page = MagicMock()
        mock_page.extract_tables.return_value = [
            [['SKU', 'Description', 'Price'], ['BB1191', 'Test Product', '$145.50']]
        ]
        
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf
        
        tables = self.parser._extract_with_pdfplumber()
        
        self.assertEqual(len(tables), 1)
        self.assertIsInstance(tables[0], pd.DataFrame)
        self.assertEqual(tables[0].iloc[0, 0], 'BB1191')
    
    def test_parse_finish_adders(self):
        """Test finish adder parsing"""
        self.parser.text_content = """
        Finish Adders:
        US3 Satin Chrome $15.00
        US4 Bright Chrome $20.00
        US10B Satin Bronze $25.00
        """
        
        finishes = self.parser._parse_finish_adders()
        
        self.assertGreater(len(finishes), 0)
        self.assertEqual(finishes[0]['code'], 'US3')
        self.assertEqual(finishes[0]['adder_value'], 15.00)

class TestSelectHingesParser(unittest.TestCase):
    """Test cases for SELECT Hinges parser"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.sample_pdf_path = "test_data/select_hinges_sample.pdf"
        self.parser = SelectHingesParser(self.sample_pdf_path)
    
    def test_identify_manufacturer(self):
        """Test manufacturer identification"""
        self.parser.text_content = "SELECT Hinges Price Book 2025"
        
        manufacturer = self.parser.identify_manufacturer()
        self.assertEqual(manufacturer, 'select_hinges')
    
    def test_net_add_options(self):
        """Test net-add options configuration"""
        expected_options = ['CTW', 'EPT', 'EMS', 'TIPIT', 'Hospital Tip', 'UL FR3']
        
        for option in expected_options:
            self.assertIn(option, self.parser.net_add_options)
    
    def test_option_rules(self):
        """Test option rules configuration"""
        # Test CTW rules
        self.assertEqual(self.parser.option_rules['CTW']['requires'], [])
        self.assertEqual(self.parser.option_rules['CTW']['excludes'], [])
        
        # Test EPT rules
        self.assertEqual(self.parser.option_rules['EPT']['excludes'], ['CTW'])
        
        # Test TIPIT vs Hospital Tip
        self.assertEqual(self.parser.option_rules['TIPIT']['excludes'], ['Hospital Tip'])
        self.assertEqual(self.parser.option_rules['Hospital Tip']['excludes'], ['TIPIT'])
    
    def test_looks_like_sku_select(self):
        """Test SKU pattern recognition for SELECT Hinges"""
        test_cases = [
            ("H3A", True),
            ("S123", True),
            ("ABC123", True),
            ("123", False),
            ("", False)
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                result = self.parser._looks_like_sku(text)
                self.assertEqual(result, expected)
    
    def test_extract_model_from_sku_select(self):
        """Test model extraction for SELECT Hinges"""
        test_cases = [
            ("H3A", "3A"),
            ("S123", "123"),
            ("ABC123", "123"),
            ("H3A-OPT", "3A")
        ]
        
        for sku, expected in test_cases:
            with self.subTest(sku=sku):
                result = self.parser._extract_model_from_sku(sku)
                self.assertEqual(result, expected)
    
    def test_parse_net_add_options(self):
        """Test net-add options parsing"""
        self.parser.text_content = """
        Net Add Options:
        CTW Continuous Weld $25.00
        EPT Electroplated $30.00
        EMS Electromagnetic Shielding $35.00
        TIPIT Tip It $15.00
        Hospital Tip $20.00
        UL FR3 Fire Rated $40.00
        """
        
        options = self.parser._parse_net_add_options()
        
        self.assertGreater(len(options), 0)
        
        # Check that all expected options are found
        option_codes = [opt['option_code'] for opt in options]
        for expected_option in ['CTW', 'EPT', 'EMS', 'TIPIT', 'Hospital Tip', 'UL FR3']:
            self.assertIn(expected_option, option_codes)

class TestParserIntegration(unittest.TestCase):
    """Integration tests for parsers"""
    
    def test_parser_validation(self):
        """Test parser data validation"""
        # Mock parsed data
        mock_data = {
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
        
        parser = HagerParser("dummy_path")
        validation = parser.validate_data(mock_data)
        
        self.assertTrue(validation['is_valid'])
        self.assertEqual(len(validation['errors']), 0)
    
    def test_parser_validation_errors(self):
        """Test parser validation with errors"""
        # Mock invalid data
        mock_data = {
            'manufacturer': 'hager',
            'effective_date': None,
            'products': [],  # No products
            'finishes': [],
            'options': []
        }
        
        parser = HagerParser("dummy_path")
        validation = parser.validate_data(mock_data)
        
        self.assertFalse(validation['is_valid'])
        self.assertGreater(len(validation['errors']), 0)

if __name__ == '__main__':
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTest(unittest.makeSuite(TestHagerParser))
    suite.addTest(unittest.makeSuite(TestSelectHingesParser))
    suite.addTest(unittest.makeSuite(TestParserIntegration))
    
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
