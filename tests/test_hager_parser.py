"""
Test Hager parser with golden data validation.
"""
import pytest
import tempfile
import os
from datetime import date
from unittest.mock import Mock, patch
import pandas as pd

from parsers.hager.parser import HagerParser
from parsers.hager.sections import HagerSectionExtractor
from parsers.shared.provenance import ProvenanceTracker


class TestHagerSectionExtractor:
    """Test Hager section extraction functionality."""

    def setup_method(self):
        self.tracker = ProvenanceTracker("test.pdf")
        self.extractor = HagerSectionExtractor(self.tracker)

    def test_extract_finish_symbols(self):
        """Test finish symbols extraction."""
        test_text = """
        FINISH SYMBOLS

        US3     Satin Chrome            $12.50
        US4     Bright Chrome           $15.75
        US10B   Satin Bronze            $18.25
        US15    Satin Brass             $20.50
        US26D   Oil Rubbed Bronze       $22.75
        """

        finishes = self.extractor.extract_finish_symbols_legacy(test_text)

        # Should find multiple finishes
        assert len(finishes) >= 4

        # Check specific finishes
        finish_codes = [f.value['code'] for f in finishes if isinstance(f.value, dict)]
        assert 'US3' in finish_codes
        assert 'US10B' in finish_codes
        assert 'US26D' in finish_codes

        # Check pricing
        us3_finish = next((f for f in finishes
                          if isinstance(f.value, dict) and f.value.get('code') == 'US3'), None)
        if us3_finish:
            assert us3_finish.value['base_price'] == 12.50
            assert us3_finish.value['name'] == 'Satin Chrome'

    def test_extract_price_rules(self):
        """Test price rule extraction."""
        test_text = """
        PRICING RULES:

        US10B use US10A price
        For US33D use US32D
        US5 uses US4 pricing
        """

        rules = self.extractor.extract_price_rules_legacy(test_text)

        # Should find multiple rules
        assert len(rules) >= 2

        # Check specific rules
        rule_data = [(r.value['source_finish'], r.value['target_finish'])
                    for r in rules if isinstance(r.value, dict)]

        assert ('US10B', 'US10A') in rule_data or ('US33D', 'US32D') in rule_data

    def test_extract_hinge_additions(self):
        """Test hinge additions extraction."""
        test_text = """
        HINGE ADDITIONS:

        EPT preparation add $25.00
        EMS electromagnetic shielding add $35.50
        ETW electric thru-wire add $45.75
        HWS heavy weight stainless add $55.25
        """

        additions = self.extractor.extract_hinge_additions_legacy(test_text)

        # Should find additions
        assert len(additions) >= 3

        # Check specific additions
        addition_codes = [a.value['option_code'] for a in additions if isinstance(a.value, dict)]
        assert 'EPT' in addition_codes
        assert 'EMS' in addition_codes

        # Check pricing
        ept_addition = next((a for a in additions
                           if isinstance(a.value, dict) and a.value.get('option_code') == 'EPT'), None)
        if ept_addition:
            assert ept_addition.value['adder_value'] == 25.00

    def test_extract_item_tables_from_dataframe(self):
        """Test item table extraction from DataFrame."""
        # Create sample Hager table
        sample_data = {
            'Model': ['BB1100US3', 'BB1100US4', 'BB1100US10B', 'BB1279US3', 'BB1279US10B'],
            'Description': ['Ball Bearing Heavy', 'Ball Bearing Heavy', 'Ball Bearing Heavy',
                          'Ball Bearing Standard', 'Ball Bearing Standard'],
            'Price': ['$125.50', '$128.75', '$135.25', '$98.25', '$102.00'],
            'Series': ['BB1100', 'BB1100', 'BB1100', 'BB1279', 'BB1279'],
            'Duty': ['Heavy', 'Heavy', 'Heavy', 'Standard', 'Standard']
        }

        test_table = pd.DataFrame(sample_data)
        products = self.extractor.extract_item_tables_legacy("", [test_table])

        assert len(products) == 5

        # Check first product
        first_product = products[0]
        assert isinstance(first_product.value, dict)
        assert first_product.value['sku'] == 'BB1100US3'
        assert first_product.value['model'] == 'BB1100'
        assert first_product.value['base_price'] == 125.50
        assert first_product.value['manufacturer'] == 'hager'

    def test_extract_item_tables_from_text(self):
        """Test item table extraction from text patterns."""
        test_text = """
        BB1100 SERIES - BALL BEARING HEAVY DUTY
        US3 $125.50
        US4 $128.75
        US10B $135.25

        BB1279 SERIES - BALL BEARING STANDARD
        US3 $98.25
        US10B $102.00
        """

        products = self.extractor.extract_item_tables_legacy(test_text, [])

        # Should find products from both series
        assert len(products) >= 3

        # Check BB1100 products
        bb1100_products = [p for p in products
                          if isinstance(p.value, dict) and p.value.get('model') == 'BB1100']
        assert len(bb1100_products) >= 2

    def test_hager_finish_mapping(self):
        """Test Hager-specific finish code mapping."""
        test_text = "US26D Oil Rubbed Bronze $22.75"
        finishes = self.extractor.extract_finish_symbols_legacy(test_text)

        us26d_finish = next((f for f in finishes
                           if isinstance(f.value, dict) and f.value.get('code') == 'US26D'), None)

        assert us26d_finish is not None
        assert us26d_finish.value['code'] == 'US26D'
        assert 'Oil Rubbed Bronze' in us26d_finish.value['name']


class TestHagerParser:
    """Test complete Hager parser functionality."""

    def setup_method(self):
        # Create a temporary test file path
        self.test_pdf_path = "test_hager.pdf"

    @patch('parsers.hager.parser.EnhancedPDFExtractor')
    def test_parser_initialization(self, mock_extractor_class):
        """Test parser initialization."""
        mock_extractor_class.return_value = Mock()

        parser = HagerParser(self.test_pdf_path)

        assert parser.pdf_path == self.test_pdf_path
        assert parser.provenance_tracker is not None
        assert parser.section_extractor is not None

    @patch('parsers.hager.parser.EnhancedPDFExtractor')
    def test_parse_success_flow(self, mock_extractor_class):
        """Test successful parsing flow."""
        # Mock PDF extraction
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor

        # Mock document
        mock_page = Mock()
        mock_page.page_number = 1
        mock_page.text = """
        HAGER PRICE BOOK 2025

        FINISH SYMBOLS:
        US3 Satin Chrome $12.50
        US10B Satin Bronze $18.25

        EPT preparation add $25.00
        EMS electromagnetic add $35.50
        """
        mock_page.tables = []

        mock_document = Mock()
        mock_document.pages = [mock_page]
        mock_extractor.extract_document.return_value = mock_document

        parser = HagerParser(self.test_pdf_path)
        results = parser.parse()

        # Verify basic structure
        assert 'manufacturer' in results
        assert results['manufacturer'] == 'Hager'
        assert 'finish_symbols' in results
        assert 'hinge_additions' in results
        assert 'products' in results
        assert 'summary' in results
        assert 'validation' in results

    @patch('parsers.hager.sections.HagerSectionExtractor.extract_tables_with_camelot')
    @patch('parsers.hager.parser.EnhancedPDFExtractor')
    def test_parse_with_products(self, mock_extractor_class, mock_camelot):
        """Test parsing with product data."""
        # Mock PDF extraction with product table
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor

        # Create mock table with products
        product_data = {
            'Model': ['BB1100US3', 'BB1100US4'],
            'Price': ['$125.50', '$128.75'],
            'Description': ['Ball Bearing Heavy', 'Ball Bearing Heavy']
        }
        mock_table = pd.DataFrame(product_data)

        # Mock Camelot extraction to return the product table
        mock_camelot.return_value = [mock_table]

        mock_page = Mock()
        mock_page.page_number = 1
        mock_page.text = "US3 Satin Chrome $12.50"
        mock_page.tables = [mock_table]

        mock_document = Mock()
        mock_document.pages = [mock_page]
        mock_extractor.extract_document.return_value = mock_document

        parser = HagerParser(self.test_pdf_path)
        results = parser.parse()

        # Should have products
        assert len(results['products']) >= 2
        assert results['summary']['total_products'] >= 2

    @patch('parsers.hager.parser.EnhancedPDFExtractor')
    def test_parse_error_handling(self, mock_extractor_class):
        """Test error handling during parsing."""
        # Mock PDF extraction failure
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract_document.side_effect = Exception("PDF extraction failed")

        parser = HagerParser(self.test_pdf_path)
        results = parser.parse()

        # Should return error results
        assert 'error' in results['parsing_metadata']
        assert results['summary']['parsing_failed'] is True
        assert not results['validation']['is_valid']

    @patch('parsers.hager.parser.EnhancedPDFExtractor')
    def test_validation_logic(self, mock_extractor_class):
        """Test result validation logic."""
        mock_extractor_class.return_value = Mock()
        parser = HagerParser(self.test_pdf_path)

        # Test validation with good results
        good_results = {
            'finish_symbols': [
                {'confidence': 0.9}, {'confidence': 0.8}, {'confidence': 0.85}
            ],
            'products': [
                {'confidence': 0.9}, {'confidence': 0.85}, {'confidence': 0.8}
            ],
            'price_rules': [
                {'confidence': 0.95}
            ],
            'hinge_additions': [
                {'confidence': 0.9}
            ]
        }

        validation = parser._validate_results(good_results)
        assert validation['is_valid']
        assert validation['accuracy_metrics']['overall_quality'] == 'good'

        # Test validation with poor results
        poor_results = {
            'finish_symbols': [],
            'products': [],
            'price_rules': [],
            'hinge_additions': []
        }

        validation = parser._validate_results(poor_results)
        assert not validation['is_valid']
        assert len(validation['errors']) > 0

    @patch('parsers.hager.parser.EnhancedPDFExtractor')
    def test_golden_data_export(self, mock_extractor_class):
        """Test golden data export functionality."""
        mock_extractor_class.return_value = Mock()
        parser = HagerParser(self.test_pdf_path)

        # Add some mock data
        from parsers.shared.provenance import ParsedItem, ProvenanceInfo

        mock_provenance = ProvenanceInfo(
            source_file="test.pdf",
            page_number=1,
            extraction_method="test"
        )

        finish_data = {
            'code': 'US3',
            'bhma_code': 'US3',
            'name': 'Satin Chrome',
            'base_price': 12.50
        }
        parser.finish_symbols = [
            ParsedItem(
                value=finish_data,
                data_type="finish",
                provenance=mock_provenance,
                confidence=0.9
            )
        ]

        addition_data = {
            'option_code': 'EPT',
            'adder_value': 25.00,
            'option_name': 'Electroplated Preparation'
        }
        parser.hinge_additions = [
            ParsedItem(
                value=addition_data,
                data_type="hinge_addition",
                provenance=mock_provenance,
                confidence=0.9
            )
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            files_created = parser.export_golden_data(temp_dir)

            assert 'finishes' in files_created
            assert 'additions' in files_created
            assert 'provenance' in files_created

            # Verify files exist
            for file_path in files_created.values():
                assert os.path.exists(file_path)


class TestHagerParserIntegration:
    """Integration tests for Hager parser."""

    def test_complete_parsing_simulation(self):
        """Test complete parsing with realistic data."""
        test_text = """
        HAGER HARDWARE PRICE BOOK 2025

        FINISH SYMBOLS:
        US3 Satin Chrome $12.50
        US4 Bright Chrome $15.75
        US10B Satin Bronze $18.25
        US26D Oil Rubbed Bronze $22.75

        PRICING RULES:
        US10B use US10A price
        US33D use US32D price

        HINGE ADDITIONS:
        EPT preparation add $25.00
        EMS electromagnetic shielding add $35.50
        ETW electric thru-wire add $45.75

        BB1100 SERIES:
        US3 $125.50
        US4 $128.75
        US10B $135.25
        """

        # This would be a full integration test with actual PDF processing
        # For now, we'll test the section extraction components

        tracker = ProvenanceTracker("test.pdf")
        extractor = HagerSectionExtractor(tracker)

        # Test finishes
        finishes = extractor.extract_finish_symbols_legacy(test_text)
        assert len(finishes) >= 4

        # Test rules
        rules = extractor.extract_price_rules_legacy(test_text)
        assert len(rules) >= 2

        # Test additions
        additions = extractor.extract_hinge_additions_legacy(test_text)
        assert len(additions) >= 3

        # Verify finish details
        finish_codes = [f.value['code'] for f in finishes if isinstance(f.value, dict)]
        assert 'US3' in finish_codes
        assert 'US10B' in finish_codes
        assert 'US26D' in finish_codes


if __name__ == "__main__":
    pytest.main([__file__])