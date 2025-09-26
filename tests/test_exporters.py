"""
Test data exporters.
"""
import pytest
import tempfile
import json
import csv
import os
from datetime import datetime, date
from unittest.mock import Mock, MagicMock
import pandas as pd

from services.exporters import DataExporter, QuickExporter
from database.models import Manufacturer, PriceBook, Product, Finish, ProductOption


class TestDataExporter:
    """Test DataExporter functionality."""

    def setup_method(self):
        self.session = Mock()
        self.exporter = DataExporter(self.session)

    def test_gather_price_book_data(self):
        """Test gathering price book data."""
        # Mock price book
        manufacturer = Mock()
        manufacturer.name = "Test Manufacturer"
        manufacturer.id = 1

        price_book = Mock()
        price_book.id = 1
        price_book.manufacturer = manufacturer
        price_book.manufacturer_id = 1
        price_book.edition = "2025 Edition"
        price_book.effective_date = date(2025, 1, 1)
        price_book.upload_date = datetime(2025, 1, 1, 12, 0)
        price_book.status = "processed"
        price_book.file_path = "test.pdf"

        # Mock products
        mock_product = Mock()
        mock_product.id = 1
        mock_product.sku = "TEST123"
        mock_product.model = "TEST"
        mock_product.description = "Test Product"
        mock_product.base_price = 125.50
        mock_product.family = None
        mock_product.is_active = True
        mock_product.effective_date = date(2025, 1, 1)
        mock_product.created_at = datetime(2025, 1, 1, 12, 0)

        # Mock finishes
        mock_finish = Mock()
        mock_finish.id = 1
        mock_finish.code = "US3"
        mock_finish.name = "Satin Chrome"
        mock_finish.bhma_code = "US3"
        mock_finish.description = "Satin Chrome Finish"
        mock_finish.created_at = datetime(2025, 1, 1, 12, 0)

        # Mock options
        mock_option = Mock()
        mock_option.id = 1
        mock_option.option_type = "preparation"
        mock_option.option_code = "EPT"
        mock_option.option_name = "Electroplated Preparation"
        mock_option.adder_type = "net_add"
        mock_option.adder_value = 25.00
        mock_option.is_required = False
        mock_option.created_at = datetime(2025, 1, 1, 12, 0)

        # Configure mocks
        self.session.query.return_value.filter_by.return_value.all.return_value = [mock_product]

        def mock_query(model):
            query_mock = Mock()
            filter_mock = Mock()
            filter_mock.all.return_value = []

            if model == Product:
                filter_mock.all.return_value = [mock_product]
            elif model == Finish:
                filter_mock.all.return_value = [mock_finish]
            elif model == ProductOption:
                filter_mock.all.return_value = [mock_option]

            query_mock.filter_by.return_value = filter_mock
            query_mock.filter.return_value = filter_mock
            return query_mock

        self.session.query.side_effect = mock_query

        # Test data gathering
        data = self.exporter._gather_price_book_data(price_book)

        # Verify structure
        assert 'products' in data
        assert 'finishes' in data
        assert 'options' in data
        assert 'price_book_info' in data

        # Verify price book info
        assert data['price_book_info']['manufacturer'] == "Test Manufacturer"
        assert data['price_book_info']['edition'] == "2025 Edition"

        # Verify products
        assert len(data['products']) == 1
        product_data = data['products'][0]
        assert product_data['sku'] == "TEST123"
        assert product_data['base_price'] == 125.50

        # Verify finishes
        assert len(data['finishes']) == 1
        finish_data = data['finishes'][0]
        assert finish_data['code'] == "US3"
        assert finish_data['name'] == "Satin Chrome"

        # Verify options
        assert len(data['options']) == 1
        option_data = data['options'][0]
        assert option_data['option_code'] == "EPT"
        assert option_data['adder_value'] == 25.00

    def test_export_to_json(self):
        """Test JSON export functionality."""
        # Mock price book
        price_book = Mock()
        price_book.edition = "test_edition"

        # Test data
        test_data = {
            'products': [
                {'sku': 'TEST123', 'price': 125.50}
            ],
            'finishes': [
                {'code': 'US3', 'name': 'Satin Chrome'}
            ],
            'options': [],
            'price_book_info': {
                'manufacturer': 'Test',
                'edition': 'test_edition'
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = temp_dir
            json_file = self.exporter._export_to_json(test_data, output_path, price_book)

            # Verify file was created
            assert os.path.exists(json_file)
            assert json_file.endswith('test_edition_complete.json')

            # Verify content
            with open(json_file, 'r') as f:
                exported_data = json.load(f)

            assert 'price_book_info' in exported_data
            assert 'products' in exported_data
            assert 'export_metadata' in exported_data
            assert exported_data['products'][0]['sku'] == 'TEST123'

    def test_export_to_csv(self):
        """Test CSV export functionality."""
        # Mock price book
        price_book = Mock()
        price_book.edition = "test_edition"

        # Test data
        test_data = {
            'products': [
                {'sku': 'TEST123', 'price': 125.50, 'model': 'TEST'}
            ],
            'finishes': [
                {'code': 'US3', 'name': 'Satin Chrome', 'price': 12.50}
            ],
            'options': [
                {'code': 'EPT', 'price': 25.00, 'name': 'Preparation'}
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = temp_dir
            csv_files = self.exporter._export_to_csv(test_data, output_path, price_book)

            # Verify files were created
            assert 'products_csv' in csv_files
            assert 'finishes_csv' in csv_files
            assert 'options_csv' in csv_files

            # Verify products CSV
            products_file = csv_files['products_csv']
            assert os.path.exists(products_file)

            with open(products_file, 'r') as f:
                reader = csv.DictReader(f)
                products = list(reader)
                assert len(products) == 1
                assert products[0]['sku'] == 'TEST123'

    def test_export_to_xlsx(self):
        """Test Excel export functionality."""
        # Mock price book
        price_book = Mock()
        price_book.edition = "test_edition"

        # Test data
        test_data = {
            'products': [
                {'sku': 'TEST123', 'price': 125.50}
            ],
            'finishes': [
                {'code': 'US3', 'name': 'Satin Chrome'}
            ],
            'options': [],
            'price_book_info': {
                'id': 1,
                'manufacturer': 'Test',
                'edition': 'test_edition',
                'effective_date': '2025-01-01',
                'upload_date': '2025-01-01T12:00:00',
                'status': 'processed',
                'file_path': 'test.pdf'
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = temp_dir
            xlsx_file = self.exporter._export_to_xlsx(test_data, output_path, price_book)

            # Verify file was created
            assert os.path.exists(xlsx_file)
            assert xlsx_file.endswith('test_edition_complete.xlsx')

            # Verify we can read it back
            excel_data = pd.read_excel(xlsx_file, sheet_name=None)
            assert 'Products' in excel_data
            assert 'Finishes' in excel_data
            assert 'Info' in excel_data

            # Verify products sheet
            products_df = excel_data['Products']
            assert len(products_df) == 1
            assert products_df.iloc[0]['sku'] == 'TEST123'

    def test_export_price_book_data_integration(self):
        """Test complete price book export integration."""
        # Mock price book
        price_book = Mock()
        price_book.id = 1
        price_book.edition = "test_edition"

        self.session.get.return_value = price_book

        # Mock _gather_price_book_data method
        test_data = {
            'products': [{'sku': 'TEST123', 'price': 125.50}],
            'finishes': [{'code': 'US3', 'name': 'Satin Chrome'}],
            'options': [],
            'price_book_info': {'manufacturer': 'Test', 'edition': 'test_edition'}
        }
        self.exporter._gather_price_book_data = Mock(return_value=test_data)

        with tempfile.TemporaryDirectory() as temp_dir:
            files_created = self.exporter.export_price_book_data(
                price_book_id=1,
                output_dir=temp_dir,
                formats=['json', 'csv']
            )

            # Verify files were created
            assert 'json' in files_created
            assert 'products_csv' in files_created
            assert 'finishes_csv' in files_created

            # Verify files exist
            for file_path in files_created.values():
                assert os.path.exists(file_path)


class TestQuickExporter:
    """Test QuickExporter functionality."""

    def test_export_products_to_csv(self):
        """Test quick CSV export for products."""
        products = [
            {'sku': 'TEST123', 'price': 125.50, 'model': 'TEST'},
            {'sku': 'TEST456', 'price': 150.25, 'model': 'TEST2'}
        ]

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            temp_file = f.name

        try:
            QuickExporter.export_products_to_csv(products, temp_file)

            # Verify file was created
            assert os.path.exists(temp_file)

            # Read back and verify
            with open(temp_file, 'r') as f:
                reader = csv.DictReader(f)
                exported_products = list(reader)

            assert len(exported_products) == 2
            assert exported_products[0]['sku'] == 'TEST123'
            assert float(exported_products[0]['price']) == 125.50

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_export_to_json(self):
        """Test quick JSON export."""
        test_data = {
            'products': [
                {'sku': 'TEST123', 'price': 125.50}
            ],
            'manufacturer': 'Test'
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name

        try:
            QuickExporter.export_to_json(test_data, temp_file)

            # Verify file was created
            assert os.path.exists(temp_file)

            # Read back and verify
            with open(temp_file, 'r') as f:
                exported_data = json.load(f)

            assert exported_data['manufacturer'] == 'Test'
            assert len(exported_data['products']) == 1
            assert exported_data['products'][0]['sku'] == 'TEST123'

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_export_parsing_results(self):
        """Test exporting raw parsing results."""
        parsing_results = {
            'manufacturer': 'Test',
            'products': [
                {
                    'value': {
                        'sku': 'TEST123',
                        'model': 'TEST',
                        'base_price': 125.50,
                        'description': 'Test Product',
                        'manufacturer': 'Test',
                        'is_active': True
                    }
                }
            ],
            'finish_symbols': [
                {
                    'value': {
                        'code': 'US3',
                        'name': 'Satin Chrome',
                        'bhma_code': 'US3',
                        'description': 'Chrome finish',
                        'base_price': 12.50
                    }
                }
            ],
            'summary': {
                'total_products': 1,
                'total_finishes': 1
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            files_created = QuickExporter.export_parsing_results(parsing_results, temp_dir)

            # Verify files were created
            assert 'results_json' in files_created
            assert 'products_csv' in files_created
            assert 'finishes_csv' in files_created

            # Verify JSON file
            json_file = files_created['results_json']
            assert os.path.exists(json_file)

            with open(json_file, 'r') as f:
                data = json.load(f)
                assert data['manufacturer'] == 'Test'

            # Verify products CSV
            products_file = files_created['products_csv']
            assert os.path.exists(products_file)

            with open(products_file, 'r') as f:
                reader = csv.DictReader(f)
                products = list(reader)
                assert len(products) == 1
                assert products[0]['sku'] == 'TEST123'

            # Verify finishes CSV
            finishes_file = files_created['finishes_csv']
            assert os.path.exists(finishes_file)

            with open(finishes_file, 'r') as f:
                reader = csv.DictReader(f)
                finishes = list(reader)
                assert len(finishes) == 1
                assert finishes[0]['code'] == 'US3'

    def test_export_empty_products(self):
        """Test exporting empty product list."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            temp_file = f.name

        try:
            QuickExporter.export_products_to_csv([], temp_file)

            # File should still be created but empty (or header only)
            assert os.path.exists(temp_file)

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_export_parsing_results_no_products(self):
        """Test exporting parsing results with no products."""
        parsing_results = {
            'manufacturer': 'Test',
            'products': [],
            'finish_symbols': [],
            'summary': {
                'total_products': 0,
                'total_finishes': 0
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            files_created = QuickExporter.export_parsing_results(parsing_results, temp_dir)

            # Should still create JSON file
            assert 'results_json' in files_created
            json_file = files_created['results_json']
            assert os.path.exists(json_file)

            # Should not create CSV files for empty data
            assert 'products_csv' not in files_created
            assert 'finishes_csv' not in files_created


if __name__ == "__main__":
    pytest.main([__file__])