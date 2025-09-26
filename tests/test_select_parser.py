"""
Test SELECT Hinges parser with golden data validation.
"""
import pytest
import tempfile
import os
from datetime import date
from unittest.mock import Mock, patch
import pandas as pd

from parsers.select.parser import SelectHingesParser
from parsers.select.sections import SelectSectionExtractor
from parsers.shared.provenance import ProvenanceTracker


class TestSelectSectionExtractor:
    """Test SELECT section extraction functionality."""

    def setup_method(self):
        self.tracker = ProvenanceTracker("test.pdf")
        self.extractor = SelectSectionExtractor(self.tracker)

    def test_extract_effective_date(self):
        """Test effective date extraction."""
        test_text = """
        SELECT HINGES PRICE BOOK
        EFFECTIVE APRIL 7, 2025

        All prices listed are net prices.
        """

        result = self.extractor.extract_effective_date(test_text)
        assert result is not None
        assert result.value == date(2025, 4, 7)
        assert result.data_type == "effective_date"
        assert result.confidence > 0.8

    def test_extract_effective_date_alternate_format(self):
        """Test effective date extraction with alternate format."""
        test_text = "PRICES EFFECTIVE JANUARY 15, 2024"

        result = self.extractor.extract_effective_date(test_text)
        assert result is not None
        assert result.value == date(2024, 1, 15)

    def test_extract_net_add_options(self):
        """Test net add options extraction."""
        test_text = """
        NET ADD OPTIONS:

        CTW-4 $108
        CTW-5 $113
        CTW-8 $126
        CTW-10 $137
        CTW-12 $156

        EPT prep $41
        EMS $46

        ATW-4 $176
        ATW-8 $188
        ATW-12 $204

        Hospital Tip $34
        TIPIT Left $25
        TIPIT Right $25

        FR3 $18
        """

        options = self.extractor.extract_net_add_options(test_text)

        # Should find multiple options
        assert len(options) >= 10

        # Check specific options
        option_codes = [opt.value['option_code'] for opt in options if isinstance(opt.value, dict)]
        assert 'CTW' in option_codes
        assert 'EPT' in option_codes
        assert 'EMS' in option_codes
        assert 'ATW' in option_codes
        assert 'HT' in option_codes
        assert 'FR3' in option_codes

        # Check pricing
        ctw_options = [opt for opt in options
                      if isinstance(opt.value, dict) and opt.value.get('option_code') == 'CTW']
        assert len(ctw_options) >= 1

        # Verify CTW-4 pricing
        ctw_4 = next((opt for opt in ctw_options
                     if opt.value.get('size_variant') == '4'), None)
        if ctw_4:
            assert ctw_4.value['adder_value'] == 108.0

    def test_extract_model_tables_from_dataframe(self):
        """Test model table extraction from DataFrame."""
        # Create sample model table
        sample_data = {
            'Model': ['SL11CL24', 'SL11BR24', 'SL11BK24', 'SL11CL30', 'SL11BR30'],
            'Description': ['Light Duty 24"', 'Light Duty 24"', 'Light Duty 24"',
                           'Light Duty 30"', 'Light Duty 30"'],
            'Price': ['$45.50', '$48.25', '$52.75', '$52.25', '$55.00'],
            'Length': ['24"', '24"', '24"', '30"', '30"'],
            'Duty': ['Light', 'Light', 'Light', 'Light', 'Light']
        }

        test_table = pd.DataFrame(sample_data)
        products = self.extractor.extract_model_tables("", [test_table])

        assert len(products) == 5

        # Check first product
        first_product = products[0]
        assert isinstance(first_product.value, dict)
        assert first_product.value['sku'] == 'SL11CL24'
        assert first_product.value['model'] == 'SL11'
        assert first_product.value['base_price'] == 45.50
        assert first_product.value['finish_code'] == 'CL'

    def test_extract_model_tables_from_text(self):
        """Test model table extraction from text patterns."""
        test_text = """
        SL11 SERIES - LIGHT DUTY
        CL24 $45.50
        BR24 $48.25
        BK24 $52.75
        CL30 $52.25

        SL24 SERIES - MEDIUM DUTY
        CL24 $78.50
        BR24 $82.25
        """

        products = self.extractor.extract_model_tables(test_text, [])

        # Should find products from both series
        assert len(products) >= 4

        # Check SL11 products
        sl11_products = [p for p in products
                        if isinstance(p.value, dict) and p.value.get('model') == 'SL11']
        assert len(sl11_products) >= 4

    def test_option_constraints(self):
        """Test option constraint extraction."""
        test_text = "CTW-4 $108"
        options = self.extractor.extract_net_add_options(test_text)

        ctw_option = next((opt for opt in options
                          if isinstance(opt.value, dict) and opt.value.get('option_code') == 'CTW'), None)

        assert ctw_option is not None
        assert 'constraints' in ctw_option.value
        assert ctw_option.value['constraints'].get('requires_handing') is True


class TestSelectHingesParser:
    """Test complete SELECT Hinges parser functionality."""

    def setup_method(self):
        # Create a temporary test file path
        self.test_pdf_path = "test_select.pdf"

    @patch('parsers.select.parser.EnhancedPDFExtractor')
    def test_parser_initialization(self, mock_extractor_class):
        """Test parser initialization."""
        mock_extractor_class.return_value = Mock()

        parser = SelectHingesParser(self.test_pdf_path)

        assert parser.pdf_path == self.test_pdf_path
        assert parser.provenance_tracker is not None
        assert parser.section_extractor is not None

    @patch('parsers.select.parser.EnhancedPDFExtractor')
    def test_parse_success_flow(self, mock_extractor_class):
        """Test successful parsing flow."""
        # Mock PDF extraction
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor

        # Mock document
        mock_page = Mock()
        mock_page.page_number = 1
        mock_page.text = """
        SELECT HINGES PRICE BOOK
        EFFECTIVE APRIL 7, 2025

        CTW-4 $108
        EPT prep $41
        EMS $46
        """
        mock_page.tables = []

        mock_document = Mock()
        mock_document.pages = [mock_page]
        mock_extractor.extract_document.return_value = mock_document

        parser = SelectHingesParser(self.test_pdf_path)
        results = parser.parse()

        # Verify basic structure
        assert 'manufacturer' in results
        assert results['manufacturer'] == 'SELECT Hinges'
        assert 'effective_date' in results
        assert 'net_add_options' in results
        assert 'products' in results
        assert 'summary' in results
        assert 'validation' in results

    @patch('parsers.select.parser.EnhancedPDFExtractor')
    def test_parse_with_products(self, mock_extractor_class):
        """Test parsing with product data."""
        # Mock PDF extraction with product table
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor

        # Create mock table with products
        product_data = {
            'Model': ['SL11CL24', 'SL11BR24'],
            'Price': ['$45.50', '$48.25'],
            'Description': ['Light Duty 24"', 'Light Duty 24"']
        }
        mock_table = pd.DataFrame(product_data)

        mock_page = Mock()
        mock_page.page_number = 1
        mock_page.text = "EFFECTIVE APRIL 7, 2025"
        mock_page.tables = [mock_table]

        mock_document = Mock()
        mock_document.pages = [mock_page]
        mock_extractor.extract_document.return_value = mock_document

        parser = SelectHingesParser(self.test_pdf_path)
        results = parser.parse()

        # Should have products
        assert len(results['products']) >= 2
        assert results['summary']['total_products'] >= 2

    @patch('parsers.select.parser.EnhancedPDFExtractor')
    def test_parse_error_handling(self, mock_extractor_class):
        """Test error handling during parsing."""
        # Mock PDF extraction failure
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract_document.side_effect = Exception("PDF extraction failed")

        parser = SelectHingesParser(self.test_pdf_path)
        results = parser.parse()

        # Should return error results
        assert 'error' in results['parsing_metadata']
        assert results['summary']['parsing_failed'] is True
        assert not results['validation']['is_valid']

    @patch('parsers.select.parser.EnhancedPDFExtractor')
    def test_validation_logic(self, mock_extractor_class):
        """Test result validation logic."""
        mock_extractor_class.return_value = Mock()
        parser = SelectHingesParser(self.test_pdf_path)

        # Test validation with good results
        good_results = {
            'effective_date': {'value': date(2025, 4, 7)},
            'net_add_options': [
                {'confidence': 0.9}, {'confidence': 0.8}
            ],
            'products': [
                {'confidence': 0.9}, {'confidence': 0.85}, {'confidence': 0.8}
            ]
        }

        validation = parser._validate_results(good_results)
        assert validation['is_valid']
        assert validation['accuracy_metrics']['overall_quality'] == 'good'

        # Test validation with poor results
        poor_results = {
            'effective_date': None,
            'net_add_options': [],
            'products': []
        }

        validation = parser._validate_results(poor_results)
        assert not validation['is_valid']
        assert len(validation['errors']) > 0

    @patch('parsers.select.parser.EnhancedPDFExtractor')
    def test_golden_data_export(self, mock_extractor_class):
        """Test golden data export functionality."""
        mock_extractor_class.return_value = Mock()
        parser = SelectHingesParser(self.test_pdf_path)

        # Add some mock data
        from parsers.shared.provenance import ParsedItem, ProvenanceInfo

        mock_provenance = ProvenanceInfo(
            source_file="test.pdf",
            page_number=1,
            extraction_method="test"
        )

        parser.effective_date = ParsedItem(
            value=date(2025, 4, 7),
            data_type="effective_date",
            provenance=mock_provenance,
            confidence=0.95
        )

        option_data = {
            'option_code': 'CTW',
            'adder_value': 108.0,
            'option_name': 'Continuous Weld'
        }
        parser.net_add_options = [
            ParsedItem(
                value=option_data,
                data_type="net_add_option",
                provenance=mock_provenance,
                confidence=0.9
            )
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            files_created = parser.export_golden_data(temp_dir)

            assert 'effective_date' in files_created
            assert 'options' in files_created
            assert 'provenance' in files_created

            # Verify files exist
            for file_path in files_created.values():
                assert os.path.exists(file_path)


class TestSelectParserIntegration:
    """Integration tests for SELECT parser."""

    def test_complete_parsing_simulation(self):
        """Test complete parsing with realistic data."""
        test_text = """
        SELECT DOOR HARDWARE
        PRICE BOOK 2025

        EFFECTIVE APRIL 7, 2025

        NET ADD OPTIONS:
        CTW-4 $108.00
        CTW-5 $113.00
        EPT prep $41.00
        EMS $46.00
        Hospital Tip $34.00
        FR3 $18.00

        SL11 SERIES - LIGHT DUTY HINGES
        Model CL24: $45.50
        Model BR24: $48.25
        Model BK24: $52.75
        """

        # This would be a full integration test with actual PDF processing
        # For now, we'll test the section extraction components

        tracker = ProvenanceTracker("test.pdf")
        extractor = SelectSectionExtractor(tracker)

        # Test effective date
        effective_date = extractor.extract_effective_date(test_text)
        assert effective_date is not None
        assert effective_date.value == date(2025, 4, 7)

        # Test options
        options = extractor.extract_net_add_options(test_text)
        assert len(options) >= 6

        # Verify option details
        option_codes = [opt.value['option_code'] for opt in options
                       if isinstance(opt.value, dict)]
        assert 'CTW' in option_codes
        assert 'EPT' in option_codes
        assert 'EMS' in option_codes
        assert 'HT' in option_codes
        assert 'FR3' in option_codes


if __name__ == "__main__":
    pytest.main([__file__])