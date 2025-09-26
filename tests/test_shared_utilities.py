"""
Test shared parser utilities.
"""
import pytest
import tempfile
import os
from decimal import Decimal
from datetime import date

from parsers.shared.confidence import ConfidenceScorer, ConfidenceLevel
from parsers.shared.normalization import DataNormalizer
from parsers.shared.provenance import ProvenanceTracker, ParsedItem


class TestConfidenceScorer:
    """Test confidence scoring functionality."""

    def setup_method(self):
        self.scorer = ConfidenceScorer()

    def test_price_confidence_valid(self):
        """Test confidence scoring for valid prices."""
        score = self.scorer.score_price_value("$123.45")
        assert score.score > 0.5
        assert score.level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]

    def test_price_confidence_invalid(self):
        """Test confidence scoring for invalid prices."""
        score = self.scorer.score_price_value("invalid")
        assert score.score < 0.5
        assert score.level in [ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW]

    def test_sku_confidence_hager(self):
        """Test SKU confidence for Hager patterns."""
        score = self.scorer.score_sku_value("ABC123", "hager")
        assert score.score > 0.5

    def test_effective_date_confidence(self):
        """Test effective date confidence scoring."""
        score = self.scorer.score_effective_date("EFFECTIVE APRIL 7, 2025")
        assert score.score > 0.8
        # Check that one of the reasons mentions either date format or effective
        reason_text = " ".join(score.reasons).lower()
        assert "date format" in reason_text or "effective" in reason_text


class TestDataNormalizer:
    """Test data normalization functionality."""

    def setup_method(self):
        self.normalizer = DataNormalizer()

    def test_normalize_price_valid(self):
        """Test price normalization with valid inputs."""
        # Test various price formats
        test_cases = [
            ("$123.45", Decimal("123.45")),
            ("123.45", Decimal("123.45")),
            ("$1,234.56", Decimal("1234.56")),
            ("1234", Decimal("1234")),
        ]

        for input_val, expected in test_cases:
            result = self.normalizer.normalize_price(input_val)
            assert result['value'] == expected
            assert not result['errors']

    def test_normalize_price_invalid(self):
        """Test price normalization with invalid inputs."""
        result = self.normalizer.normalize_price("invalid price")
        assert result['value'] is None
        assert result['errors']

    def test_normalize_sku_hager(self):
        """Test SKU normalization for Hager."""
        result = self.normalizer.normalize_sku("ABC123", "hager")
        assert result['value'] == "ABC123"
        assert not result['errors']

    def test_normalize_sku_select(self):
        """Test SKU normalization for SELECT Hinges."""
        result = self.normalizer.normalize_sku("SL11", "select_hinges")
        assert result['value'] == "SL11"
        assert not result['errors']

    def test_normalize_date_effective(self):
        """Test date normalization with effective date."""
        result = self.normalizer.normalize_date("EFFECTIVE APRIL 7, 2025")
        assert result['value'] == date(2025, 4, 7)
        assert not result['errors']

    def test_normalize_finish_code(self):
        """Test finish code normalization."""
        # Test BHMA standard code
        result = self.normalizer.normalize_finish_code("US3")
        assert result['bhma_code'] == "US3"
        assert result['name'] == "Satin Chrome"

        # Test alternative code
        result = self.normalizer.normalize_finish_code("SC")
        assert result['bhma_code'] == "US3"
        assert result['name'] == "Satin Chrome"

    def test_normalize_unit_of_measure(self):
        """Test UOM normalization."""
        result = self.normalizer.normalize_unit_of_measure("each")
        assert result['code'] == "EA"

        result = self.normalizer.normalize_unit_of_measure("dozen")
        assert result['code'] == "DZ"


class TestProvenanceTracker:
    """Test provenance tracking functionality."""

    def test_create_provenance(self):
        """Test basic provenance creation."""
        tracker = ProvenanceTracker("test.pdf")
        tracker.set_context(page_number=1, method="pdfplumber")

        provenance = tracker.create_provenance(
            raw_text="$123.45",
            row_index=1,
            column_index=2
        )

        assert provenance.source_file == "test.pdf"
        assert provenance.page_number == 1
        assert provenance.extraction_method == "pdfplumber"
        assert provenance.row_index == 1
        assert provenance.column_index == 2

    def test_parsed_item_creation(self):
        """Test parsed item with provenance."""
        tracker = ProvenanceTracker("test.pdf")
        tracker.set_context(page_number=1, method="camelot")

        item = tracker.create_parsed_item(
            value=Decimal("123.45"),
            data_type="price",
            raw_text="$123.45",
            confidence=0.95
        )

        assert item.value == Decimal("123.45")
        assert item.data_type == "price"
        assert item.provenance.source_file == "test.pdf"
        assert item.confidence == 0.95

    def test_context_stack(self):
        """Test context stack functionality."""
        tracker = ProvenanceTracker("test.pdf")
        tracker.push_context("Header Section")
        tracker.push_context("Price Table")

        provenance = tracker.create_provenance()
        assert "Header Section > Price Table" in provenance.context_text

        tracker.pop_context()
        provenance = tracker.create_provenance()
        assert provenance.context_text == "Header Section"


class TestIntegration:
    """Integration tests combining all utilities."""

    def test_full_pipeline_simulation(self):
        """Test complete pipeline with all utilities."""
        # Simulate parsing pipeline
        tracker = ProvenanceTracker("sample.pdf")
        normalizer = DataNormalizer()
        scorer = ConfidenceScorer()

        tracker.set_context(page_number=1, method="pdfplumber", section="Price Table")

        # Simulate parsing a table row
        raw_data = ["ABC123", "Widget Description", "$45.99", "US3"]
        parsed_items = []

        # Parse SKU
        sku_result = normalizer.normalize_sku(raw_data[0], "hager")
        if sku_result['value']:
            item = tracker.create_parsed_item(
                value=sku_result['value'],
                data_type="sku",
                raw_text=raw_data[0],
                column_index=0,
                confidence=sku_result['confidence'].score
            )
            parsed_items.append(item)

        # Parse description
        desc_result = normalizer.normalize_description(raw_data[1])
        if desc_result['value']:
            item = tracker.create_parsed_item(
                value=desc_result['cleaned'],
                data_type="description",
                raw_text=raw_data[1],
                column_index=1
            )
            parsed_items.append(item)

        # Parse price
        price_result = normalizer.normalize_price(raw_data[2])
        if price_result['value']:
            item = tracker.create_parsed_item(
                value=price_result['value'],
                data_type="price",
                raw_text=raw_data[2],
                column_index=2,
                confidence=price_result['confidence'].score
            )
            parsed_items.append(item)

        # Parse finish
        finish_result = normalizer.normalize_finish_code(raw_data[3])
        if finish_result['code']:
            item = tracker.create_parsed_item(
                value=finish_result['bhma_code'] or finish_result['code'],
                data_type="finish",
                raw_text=raw_data[3],
                column_index=3
            )
            parsed_items.append(item)

        # Verify results
        assert len(parsed_items) == 4
        assert any(item.data_type == "sku" for item in parsed_items)
        assert any(item.data_type == "price" for item in parsed_items)
        assert any(item.data_type == "finish" for item in parsed_items)

        # All items should have provenance
        for item in parsed_items:
            assert item.provenance is not None
            assert item.provenance.source_file == "sample.pdf"
            assert item.provenance.page_number == 1

    @pytest.mark.integration
    def test_provenance_analysis(self):
        """Test provenance analysis functionality."""
        from parsers.shared.provenance import ProvenanceAnalyzer

        # Create sample parsed items
        tracker = ProvenanceTracker("test.pdf")
        items = []

        # High confidence items
        for i in range(5):
            item = tracker.create_parsed_item(
                value=f"SKU{i}",
                data_type="sku",
                confidence=0.9
            )
            items.append(item)

        # Low confidence items
        for i in range(3):
            item = tracker.create_parsed_item(
                value=f"BadSKU{i}",
                data_type="sku",
                confidence=0.3
            )
            item.validation_errors.append("Low confidence extraction")
            items.append(item)

        analyzer = ProvenanceAnalyzer()
        analysis = analyzer.analyze_extraction_quality(items)

        assert analysis['total_items'] == 8
        assert analysis['confidence_distribution']['high'] == 5
        assert analysis['confidence_distribution']['low'] == 3
        assert len(analysis['issues']) > 0
        assert len(analysis['recommendations']) > 0


if __name__ == "__main__":
    pytest.main([__file__])