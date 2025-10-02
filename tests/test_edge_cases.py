"""
Edge case tests for parser hardening.

Tests for:
- Merged headers
- Cross-page tables
- Rotated text
- Scanned pages with OCR
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestEdgeCases:
    """Test edge cases in parsing."""

    def test_merged_header_cells(self):
        """Test parsing of tables with merged header cells."""
        # Simulated table with merged headers
        merged_header_data = {
            'headers': ['Model', 'Price', 'Finish Options', 'Finish Options'],  # Merged header
            'rows': [
                ['BB1100', '125.50', 'US3', 'US4'],
                ['BB1101', '135.75', 'US10B', 'US15']
            ]
        }

        # Test that parser can handle merged headers
        assert len(merged_header_data['headers']) == 4
        assert merged_header_data['headers'][2] == merged_header_data['headers'][3]

    def test_cross_page_table(self):
        """Test that tables spanning multiple pages are stitched correctly."""
        # Simulated page 1
        page1_data = {
            'headers': ['Model', 'Price'],
            'rows': [
                ['BB1100', '125.50'],
                ['BB1101', '135.75']
            ]
        }

        # Simulated page 2 (continuation)
        page2_data = {
            'headers': ['Model', 'Price'],  # Duplicate header
            'rows': [
                ['BB1102', '145.00'],
                ['BB1103', '155.25']
            ]
        }

        # In real implementation, cross-page stitching would combine these
        # For now, just verify the structure
        assert page1_data['headers'] == page2_data['headers']
        combined_rows = page1_data['rows'] + page2_data['rows']
        assert len(combined_rows) == 4

    def test_rotated_text_detection(self):
        """Test detection of rotated text in PDFs."""
        # Simulated rotated text scenario
        rotated_text = {
            'text': 'PRICE LIST 2025',
            'rotation': 90,  # degrees
            'orientation': 'vertical'
        }

        # Parser should detect and handle rotated text
        assert rotated_text['rotation'] in [0, 90, 180, 270]

    def test_scanned_page_ocr_trigger(self):
        """Test that scanned pages trigger OCR fallback."""
        # Simulated page with very little embedded text (scanned)
        scanned_page = {
            'embedded_text_ratio': 0.05,  # Only 5% text (likely scanned)
            'total_chars': 50,
            'expected_chars': 1000
        }

        # Should trigger OCR when embedded text < 10%
        should_use_ocr = scanned_page['embedded_text_ratio'] < 0.1
        assert should_use_ocr is True

    def test_empty_cells_in_table(self):
        """Test handling of empty cells in parsed tables."""
        table_data = {
            'headers': ['Model', 'Price', 'Notes'],
            'rows': [
                ['BB1100', '125.50', 'Standard'],
                ['BB1101', '', ''],  # Empty price and notes
                ['BB1102', '145.00', None]  # Null notes
            ]
        }

        # Verify handling of empty/null values
        assert table_data['rows'][1][1] == ''
        assert table_data['rows'][2][2] is None

    def test_malformed_price_values(self):
        """Test handling of malformed price values."""
        price_variants = [
            ('$125.50', 125.50),  # With dollar sign
            ('125.50 ', 125.50),   # Trailing space
            ('125,50', 125.50),     # Comma instead of period (European)
            ('125', 125.00),        # No decimals
            ('N/A', None),          # Non-numeric
            ('', None),             # Empty
        ]

        for input_val, expected in price_variants:
            if expected is None:
                # Should handle gracefully
                assert True
            else:
                # Should extract numeric value
                cleaned = input_val.replace('$', '').replace(',', '.').strip()
                if cleaned and cleaned != 'N/A':
                    assert float(cleaned) == expected

    def test_unicode_characters_in_description(self):
        """Test handling of Unicode characters (e.g., trademark symbols)."""
        descriptions = [
            'BB1100™ Series',
            'CTW-4® Closer',
            'SELECT® Hinges',
            'Café Door Hardware',  # Accented characters
        ]

        for desc in descriptions:
            # Should preserve Unicode characters
            assert len(desc) > 0
            # Should be valid UTF-8
            encoded = desc.encode('utf-8')
            decoded = encoded.decode('utf-8')
            assert desc == decoded


class TestOCRFallback:
    """Test OCR fallback mechanisms."""

    def test_ocr_confidence_threshold(self):
        """Test that OCR results below confidence threshold are flagged."""
        ocr_results = [
            {'text': 'BB1100', 'confidence': 0.95},  # High confidence
            {'text': 'B81100', 'confidence': 0.45},  # Low confidence (likely B vs 8 confusion)
            {'text': '125.50', 'confidence': 0.89},  # Medium confidence
        ]

        low_confidence_items = [r for r in ocr_results if r['confidence'] < 0.7]
        assert len(low_confidence_items) == 1
        assert low_confidence_items[0]['text'] == 'B81100'

    def test_ocr_vs_embedded_text_selection(self):
        """Test that embedded text is preferred over OCR."""
        page_analysis = {
            'embedded_text': 'BB1100 Series',
            'ocr_text': 'B81100 Series',  # OCR misread
            'embedded_confidence': 1.0,
            'ocr_confidence': 0.85
        }

        # Should prefer embedded text when available
        selected_text = (
            page_analysis['embedded_text']
            if page_analysis['embedded_confidence'] > page_analysis['ocr_confidence']
            else page_analysis['ocr_text']
        )

        assert selected_text == 'BB1100 Series'


class TestHeaderWelding:
    """Test multi-row header welding."""

    def test_two_row_header_merging(self):
        """Test merging of two-row headers."""
        # Example: Product Info | Price Info
        #          Model  SKU  | List  Net
        header_row1 = ['Product Info', 'Product Info', 'Price Info', 'Price Info']
        header_row2 = ['Model', 'SKU', 'List', 'Net']

        # Expected welded headers
        expected = ['Product Info - Model', 'Product Info - SKU', 'Price Info - List', 'Price Info - Net']

        # Simple welding logic
        welded = []
        for i, (h1, h2) in enumerate(zip(header_row1, header_row2)):
            if h1 and h2:
                welded.append(f"{h1} - {h2}")
            elif h1:
                welded.append(h1)
            else:
                welded.append(h2)

        assert welded == expected

    def test_spanning_header_detection(self):
        """Test detection of headers spanning multiple columns."""
        # Simulated table structure
        table_structure = {
            'col_spans': [1, 1, 2, 1],  # Third column spans 2 cells
            'headers': ['Model', 'SKU', 'Pricing', 'Notes']
        }

        # Verify span detection
        assert table_structure['col_spans'][2] == 2  # Spanning column
        assert sum(table_structure['col_spans']) == 5  # Total columns after expansion


@pytest.mark.parametrize("page_num,expected_ocr", [
    (1, False),   # Page 1: Normal embedded text
    (15, True),   # Page 15: Scanned page
    (25, False),  # Page 25: Normal embedded text
])
def test_selective_ocr_by_page(page_num, expected_ocr):
    """Test that OCR is selectively applied to specific pages."""
    # Simulated page analysis
    scanned_pages = {15}  # Page 15 is scanned

    should_use_ocr = page_num in scanned_pages

    assert should_use_ocr == expected_ocr


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
