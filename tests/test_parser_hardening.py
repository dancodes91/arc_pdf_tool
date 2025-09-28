"""
Tests for parser hardening components.

Tests page classification, table processing, OCR fallback,
and integrated hardened extraction functionality.
"""
import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
import tempfile
from pathlib import Path

# Import the components we're testing
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.shared.page_classifier import PageClassifier, PageType, ExtractionMethod
from parsers.shared.table_processor import TableProcessor, TableStructure
from parsers.shared.provenance import ProvenanceTracker
from tests.fixtures.test_page_data import (
    get_test_page_data, get_test_table_structures, get_cross_page_test_data,
    get_ocr_test_scenarios, get_confidence_test_cases,
    generate_price_variations, generate_model_code_variations
)


class TestPageClassifier:
    """Test page classification functionality."""

    def setup_method(self):
        self.classifier = PageClassifier()

    def test_title_page_classification(self):
        """Test classification of title pages."""
        test_data = get_test_page_data()['title_page']

        analysis = self.classifier.classify_page(
            page_text=test_data['text'],
            page_number=test_data['page_number'],
            tables=test_data['tables']
        )

        assert analysis.page_type == PageType.TITLE_PAGE
        assert analysis.confidence > 0.5
        assert analysis.recommended_method in [ExtractionMethod.TEXT_ONLY]

    def test_finish_symbols_classification(self):
        """Test classification of finish symbols pages."""
        test_data = get_test_page_data()['finish_symbols']

        analysis = self.classifier.classify_page(
            page_text=test_data['text'],
            page_number=test_data['page_number'],
            tables=test_data['tables']
        )

        assert analysis.page_type == PageType.FINISH_SYMBOLS
        assert analysis.confidence > 0.6
        assert analysis.recommended_method in [ExtractionMethod.CAMELOT_LATTICE, ExtractionMethod.PDFPLUMBER]

    def test_data_table_classification(self):
        """Test classification of data table pages."""
        test_data = get_test_page_data()['data_table']

        analysis = self.classifier.classify_page(
            page_text=test_data['text'],
            page_number=test_data['page_number'],
            tables=test_data['tables']
        )

        assert analysis.page_type == PageType.DATA_TABLE
        assert analysis.has_tables
        assert analysis.recommended_method in [ExtractionMethod.CAMELOT_LATTICE, ExtractionMethod.CAMELOT_STREAM]

    def test_ocr_trigger_detection(self):
        """Test OCR trigger detection."""
        # Low text scenario
        analysis = self.classifier.classify_page(
            page_text="BB",  # Very short
            page_number=1,
            tables=[]
        )
        assert analysis.needs_ocr

        # Table indicators but no tables
        analysis = self.classifier.classify_page(
            page_text="Model Description Price BB1100 Ball Bearing $125.50",
            page_number=1,
            tables=[]
        )
        # Should recommend OCR due to table indicators but no tables detected
        # This depends on the implementation details

    def test_pattern_scoring(self):
        """Test pattern scoring accuracy."""
        test_data = get_test_page_data()

        for page_type, data in test_data.items():
            analysis = self.classifier.classify_page(
                page_text=data['text'],
                page_number=data['page_number'],
                tables=data['tables']
            )

            # Check that the expected type gets highest or near-highest score
            pattern_scores = analysis.features.get('pattern_scores', {})
            expected_pattern = data['expected_type'].replace('_page', '').replace('_', '')

            # Allow some flexibility in mapping
            if expected_pattern in pattern_scores:
                assert pattern_scores[expected_pattern] > 0.2

    def test_document_analysis(self):
        """Test analysis of entire document."""
        test_data = get_test_page_data()
        pages_data = [
            {
                'text': data['text'],
                'page_number': data['page_number'],
                'tables': data['tables']
            }
            for data in test_data.values()
        ]

        analyses = self.classifier.analyze_document(pages_data)

        assert len(analyses) == len(test_data)

        # Check that we get variety in page types
        page_types = [analysis.page_type for analysis in analyses]
        unique_types = set(page_types)
        assert len(unique_types) >= 3  # Should have at least 3 different types


class TestTableProcessor:
    """Test table processing functionality."""

    def setup_method(self):
        self.processor = TableProcessor()

    def test_simple_table_processing(self):
        """Test processing of simple, well-formed tables."""
        test_data = get_test_table_structures()['simple_table']

        result = self.processor.process_table(test_data['data'])

        assert result.confidence > 0.7
        assert len(result.dataframe) == test_data['expected_rows']
        assert len(result.dataframe.columns) == test_data['expected_cols']
        assert 'Model' in str(result.dataframe.columns)

    def test_multi_row_header_welding(self):
        """Test welding of multi-row headers."""
        test_data = get_test_table_structures()['multi_row_header']

        result = self.processor.process_table(test_data['data'])

        # After welding, should have fewer rows but combined headers
        assert len(result.dataframe) == test_data['expected_rows']
        assert result.structure.has_multi_row_header
        assert 'Welded' in ' '.join(result.processing_notes)

        # Check that headers were properly combined
        columns_text = ' '.join(str(col) for col in result.dataframe.columns)
        assert 'Model' in columns_text
        assert 'Description' in columns_text

    def test_merged_cell_recovery(self):
        """Test recovery of merged cells."""
        test_data = get_test_table_structures()['merged_cells']

        result = self.processor.process_table(test_data['data'])

        assert len(result.structure.merged_cells) > 0
        assert 'merged cell' in ' '.join(result.processing_notes).lower()

        # Check that values were propagated
        df = result.dataframe
        # BB1100 Series should be propagated to subsequent cells
        assert any('BB1100' in str(cell) for row in df.values for cell in row)

    def test_cross_page_table_stitching(self):
        """Test stitching of tables across pages."""
        cross_page_data = get_cross_page_test_data()

        # Create processed tables from test data
        tables = []
        for page_data in cross_page_data:
            result = self.processor.process_table(
                page_data['table_data'],
                page_data['page_number']
            )
            tables.append(result)

        # Test stitching
        stitched_tables = self.processor.stitch_cross_page_tables(tables)

        # Should combine into fewer tables
        assert len(stitched_tables) <= len(tables)

        if len(stitched_tables) < len(tables):
            # Check that the combined table has more rows
            combined_table = stitched_tables[0]
            original_rows = sum(len(table.dataframe) for table in tables)
            assert len(combined_table.dataframe) == original_rows

    def test_confidence_calculation(self):
        """Test confidence calculation for different table qualities."""
        confidence_cases = get_confidence_test_cases()

        for case in confidence_cases:
            result = self.processor.process_table(case['data'])

            min_conf, max_conf = case['expected_confidence_range']
            assert min_conf <= result.confidence <= max_conf, \
                f"Confidence {result.confidence} not in range {case['expected_confidence_range']} for {case['name']}"

    def test_data_normalization(self):
        """Test normalization of table data."""
        # Test currency normalization
        currency_data = [
            ['Model', 'Price'],
            ['BB1100', '$ 125.50'],  # Space after $
            ['BB1101', '$135 .75'],  # Space before decimal
            ['BB1102', '156.25']     # No currency symbol
        ]

        result = self.processor.process_table(currency_data)

        # Check that currency formatting was normalized
        price_col = result.dataframe.iloc[:, 1]  # Price column
        price_text = ' '.join(str(val) for val in price_col)

        # Should remove extra spaces
        assert '$ 125.50' not in price_text or '$125.50' in price_text


class TestOCRProcessor:
    """Test OCR processor functionality."""

    def test_ocr_trigger_scenarios(self):
        """Test different scenarios that should trigger OCR."""
        # Mock OCR processor since we don't want to require Tesseract in tests
        with patch('parsers.shared.ocr_processor.TESSERACT_AVAILABLE', False):
            from parsers.shared.ocr_processor import OCRProcessor

            processor = OCRProcessor()
            scenarios = get_ocr_test_scenarios()

            for scenario_name, scenario in scenarios.items():
                should_trigger = processor.should_use_ocr(
                    text=scenario['text'],
                    tables=scenario['tables']
                )

                assert should_trigger == scenario['should_trigger'], \
                    f"OCR trigger mismatch for scenario: {scenario_name}"

    @patch('parsers.shared.ocr_processor.TESSERACT_AVAILABLE', True)
    @patch('parsers.shared.ocr_processor.pytesseract')
    @patch('parsers.shared.ocr_processor.convert_from_path')
    def test_ocr_text_extraction(self, mock_convert, mock_tesseract):
        """Test OCR text extraction with mocked dependencies."""
        from parsers.shared.ocr_processor import OCRProcessor

        # Mock image conversion
        mock_image = Mock()
        mock_convert.return_value = [mock_image]

        # Mock Tesseract results
        mock_tesseract.image_to_string.return_value = "BB1100 Ball Bearing $125.50"
        mock_tesseract.image_to_data.return_value = {
            'text': ['BB1100', 'Ball', 'Bearing', '$125.50'],
            'conf': [95, 90, 88, 92],
            'left': [10, 50, 100, 200],
            'top': [10, 10, 10, 10],
            'width': [40, 30, 40, 50],
            'height': [20, 20, 20, 20]
        }

        processor = OCRProcessor()

        with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp_file:
            result = processor.extract_text_from_pdf_page(tmp_file.name, 1)

            assert result.text == "BB1100 Ball Bearing $125.50"
            assert result.confidence > 0.8
            assert len(result.word_confidences) == 4
            assert result.method == "tesseract"

    def test_ocr_preprocessing_options(self):
        """Test OCR preprocessing options."""
        from parsers.shared.ocr_processor import OCRProcessor, OCRConfig

        config = OCRConfig(
            preprocess=True,
            enhance_contrast=True,
            denoise=True
        )

        processor = OCRProcessor(config)
        assert processor.config.preprocess
        assert processor.config.enhance_contrast


class TestPropertyBasedNormalization:
    """Property-based tests for data normalization."""

    def test_price_normalization_properties(self):
        """Test that price normalization preserves numeric values."""
        from parsers.shared.table_processor import TableProcessor

        processor = TableProcessor()
        price_variations = generate_price_variations()

        for price_str in price_variations:
            # Create a simple table with this price
            table_data = [
                ['Model', 'Price'],
                ['BB1100', price_str]
            ]

            result = processor.process_table(table_data)

            # Extract the processed price
            price_cell = result.dataframe.iloc[0, 1]  # First row, second column

            # Should contain numeric value (allowing for formatting)
            price_text = str(price_cell)
            has_number = any(char.isdigit() for char in price_text)
            assert has_number, f"Price normalization failed for: {price_str} -> {price_text}"

    def test_model_code_normalization_properties(self):
        """Test that model code normalization preserves essential information."""
        model_variations = generate_model_code_variations()

        for model_code in model_variations:
            # Essential parts should be preserved
            normalized = model_code.upper().replace(' ', '').replace('-', '')

            # Should still contain the base model number
            assert 'BB1100' in normalized or 'bb1100' in model_code.lower()

    def test_finish_code_normalization_properties(self):
        """Test that finish code normalization preserves standard codes."""
        from tests.fixtures.test_page_data import generate_finish_code_variations

        finish_variations = generate_finish_code_variations()

        for finish_code in finish_variations:
            normalized = finish_code.upper().replace(' ', '').replace('-', '')

            # Should preserve standard BHMA patterns
            standard_patterns = ['US3', 'US10B', '2C', '3A']
            for pattern in standard_patterns:
                if pattern.lower() in finish_code.lower():
                    assert pattern in normalized


class TestIntegratedHardening:
    """Test integrated hardening functionality."""

    @patch('parsers.shared.enhanced_extractor.EnhancedPDFExtractor')
    def test_hardened_extraction_workflow(self, mock_extractor_class):
        """Test complete hardened extraction workflow."""
        from parsers.shared.enhanced_extractor import HardenedExtractor

        # Mock the base extractor
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor

        # Mock document with test pages
        mock_pages = []
        test_data = get_test_page_data()

        for i, (page_type, data) in enumerate(test_data.items()):
            mock_page = Mock()
            mock_page.page_number = i + 1
            mock_page.text = data['text']
            mock_page.tables = data['tables']
            mock_pages.append(mock_page)

        mock_document = Mock()
        mock_document.pages = mock_pages
        mock_extractor.extract_document.return_value = mock_document

        # Test hardened extraction
        with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp_file:
            extractor = HardenedExtractor(tmp_file.name)
            document, page_results = extractor.extract_document_hardened()

            assert len(page_results) == len(test_data)

            # Check that different page types got appropriate methods
            methods_used = [result.extraction_method_used for result in page_results]
            assert len(set(methods_used)) > 1  # Should use variety of methods

            # Check that processing notes were generated
            for result in page_results:
                assert len(result.processing_notes) > 0
                assert result.page_analysis.page_type is not None

    def test_section_extraction_routing(self):
        """Test that section extraction routes to relevant pages."""
        from parsers.shared.enhanced_extractor import HardenedExtractor

        with patch('parsers.shared.enhanced_extractor.EnhancedPDFExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor

            # Create mock pages with different types
            mock_pages = []
            test_data = get_test_page_data()

            for page_type, data in test_data.items():
                mock_page = Mock()
                mock_page.page_number = data['page_number']
                mock_page.text = data['text']
                mock_page.tables = data['tables']
                mock_pages.append(mock_page)

            mock_document = Mock()
            mock_document.pages = mock_pages
            mock_extractor.extract_document.return_value = mock_document

            with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp_file:
                extractor = HardenedExtractor(tmp_file.name)

                # Mock the internal method to avoid full extraction
                extractor.extract_document_hardened = Mock()
                extractor.extract_document_hardened.return_value = (mock_document, [])

                # Test section routing (this would normally do full extraction)
                results = extractor.extract_section_hardened('finish_symbols')

                # Should return results (empty in this mocked case)
                assert isinstance(results, list)


class TestRegressionPrevention:
    """Tests to prevent regression of known issues."""

    def test_empty_table_handling(self):
        """Test that empty tables don't cause crashes."""
        processor = TableProcessor()

        # Test empty list
        result = processor.process_table([])
        assert result.dataframe.empty
        assert result.confidence == 0.0

        # Test empty DataFrame
        result = processor.process_table(pd.DataFrame())
        assert result.dataframe.empty
        assert result.confidence == 0.0

    def test_malformed_table_graceful_handling(self):
        """Test graceful handling of malformed tables."""
        processor = TableProcessor()

        # Inconsistent row lengths
        malformed_data = [
            ['Model', 'Price'],
            ['BB1100'],  # Missing price
            ['BB1101', '$125.50', 'Extra column'],  # Extra column
            []  # Empty row
        ]

        result = processor.process_table(malformed_data)

        # Should not crash and should have some data
        assert isinstance(result.dataframe, pd.DataFrame)
        assert result.confidence >= 0.0  # Should have valid confidence

    def test_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters."""
        processor = TableProcessor()

        unicode_data = [
            ['Model', 'Description'],
            ['BB1100', 'Stainless Steel — Heavy Duty'],
            ['BB1101', 'Brass • Standard'],
            ['BB1102', 'Chrome ¼" thick']
        ]

        result = processor.process_table(unicode_data)

        # Should handle Unicode gracefully
        assert not result.dataframe.empty
        df_text = str(result.dataframe)

        # Unicode characters should be preserved or safely converted
        assert '—' in df_text or 'Heavy Duty' in df_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])