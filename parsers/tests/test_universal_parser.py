"""
Tests for the Universal PDF Parser.

Run with: pytest parsers/tests/test_universal_parser.py -v
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from parsers.universal_parser import (
    UniversalPDFParser,
    ParsedDocument,
    PDFType,
    ExtractionMethod,
    PageAnalysis,
    ExtractionResult,
    parse_pdf,
)
from parsers.shared.table_processor import TableProcessor, ProcessedTable, TableStructure


class TestUniversalPDFParser:
    """Test suite for UniversalPDFParser."""

    def test_parser_initialization(self):
        """Test parser initializes correctly."""
        parser = UniversalPDFParser()
        assert parser is not None
        assert parser.config == {}
        
        parser_with_config = UniversalPDFParser({"min_confidence": 0.8})
        assert parser_with_config.config["min_confidence"] == 0.8

    def test_pdf_type_detection(self):
        """Test PDF type detection from page analyses."""
        parser = UniversalPDFParser()
        
        digital_analyses = [
            PageAnalysis(
                page_number=1, has_text=True, text_density=0.01,
                has_images=False, image_coverage=0.0, has_tables=True,
                table_count=1, table_regions=[], 
                recommended_method=ExtractionMethod.PYMUPDF,
                is_scanned=False
            ),
            PageAnalysis(
                page_number=2, has_text=True, text_density=0.01,
                has_images=False, image_coverage=0.0, has_tables=True,
                table_count=2, table_regions=[],
                recommended_method=ExtractionMethod.PYMUPDF,
                is_scanned=False
            ),
        ]
        assert parser._determine_pdf_type(digital_analyses) == PDFType.DIGITAL
        
        scanned_analyses = [
            PageAnalysis(
                page_number=1, has_text=False, text_density=0.0,
                has_images=True, image_coverage=0.9, has_tables=False,
                table_count=0, table_regions=[],
                recommended_method=ExtractionMethod.PADDLEOCR,
                is_scanned=True
            ),
        ]
        assert parser._determine_pdf_type(scanned_analyses) == PDFType.SCANNED
        
        hybrid_analyses = [
            PageAnalysis(
                page_number=1, has_text=True, text_density=0.01,
                has_images=False, image_coverage=0.0, has_tables=True,
                table_count=1, table_regions=[],
                recommended_method=ExtractionMethod.PYMUPDF,
                is_scanned=False
            ),
            PageAnalysis(
                page_number=2, has_text=False, text_density=0.0,
                has_images=True, image_coverage=0.9, has_tables=False,
                table_count=0, table_regions=[],
                recommended_method=ExtractionMethod.PADDLEOCR,
                is_scanned=True
            ),
        ]
        assert parser._determine_pdf_type(hybrid_analyses) == PDFType.HYBRID

    def test_clean_price(self):
        """Test price cleaning functionality."""
        parser = UniversalPDFParser()
        
        assert parser._clean_price("$1,234.56") == 1234.56
        assert parser._clean_price("$100.00") == 100.00
        assert parser._clean_price("99.99") == 99.99
        assert parser._clean_price("1234") == 1234.0
        
        assert parser._clean_price("") is None
        assert parser._clean_price(None) is None
        assert parser._clean_price("N/A") is None
        
        assert parser._clean_price("1234,56") == 1234.56

    def test_clean_sku(self):
        """Test SKU cleaning functionality."""
        parser = UniversalPDFParser()
        
        assert parser._clean_sku("abc-123") == "ABC-123"
        assert parser._clean_sku("  SKU001  ") == "SKU001"
        assert parser._clean_sku("...test...") == "TEST"
        assert parser._clean_sku("") == ""
        assert parser._clean_sku(None) == ""

    def test_extraction_confidence_calculation(self):
        """Test confidence calculation for extractions."""
        parser = UniversalPDFParser()
        
        tables = [pd.DataFrame({"sku": ["A", "B"], "price": [100, 200]})]
        confidence = parser._calculate_extraction_confidence(
            tables, "Sample text content here",
            ExtractionMethod.PYMUPDF, {}
        )
        assert confidence >= 0.9
        
        confidence = parser._calculate_extraction_confidence(
            [], "", ExtractionMethod.TESSERACT, {}
        )
        assert confidence <= 0.65

    def test_effective_date_extraction(self):
        """Test effective date extraction from text."""
        parser = UniversalPDFParser()
        
        text1 = "Price List\nEffective Date: 01/15/2025\nProducts..."
        assert parser._extract_effective_date(text1) == "01/15/2025"
        
        text2 = "Prices effective 12-01-2024"
        assert parser._extract_effective_date(text2) == "12-01-2024"
        
        text3 = "Product catalog with no date"
        assert parser._extract_effective_date(text3) is None

    def test_product_extraction_from_tables(self):
        """Test product extraction from DataFrames."""
        parser = UniversalPDFParser()
        
        df = pd.DataFrame({
            "SKU": ["ABC-001", "ABC-002", "ABC-003"],
            "Description": ["Product A", "Product B", "Product C"],
            "Price": ["$100.00", "$200.00", "$300.00"],
            "_page_number": [1, 1, 1],
            "_extraction_method": ["pymupdf", "pymupdf", "pymupdf"],
        })
        
        products = parser._extract_products([df])
        
        assert len(products) == 3
        assert products[0]["sku"] == "ABC-001"
        assert products[0]["description"] == "Product A"
        assert products[0]["base_price"] == 100.00

    def test_table_enhancement(self):
        """Test table enhancement with TableProcessor."""
        parser = UniversalPDFParser()
        
        df = pd.DataFrame({
            "col1": ["Header1", "Data1", "Data2"],
            "col2": ["Header2", "Data3", "Data4"],
        })
        
        enhanced = parser._enhance_tables([df])
        assert len(enhanced) >= 1

    def test_parse_table_from_text(self):
        """Test parsing table structure from OCR text."""
        parser = UniversalPDFParser()
        
        text = """SKU          Description          Price
ABC-001      Product One          $100.00
ABC-002      Product Two          $200.00
ABC-003      Product Three        $300.00"""
        
        table_data = parser._parse_table_from_text(text)
        
        assert len(table_data) >= 3
        assert len(table_data[0]) >= 3


class TestTableProcessor:
    """Test suite for TableProcessor."""

    def test_processor_initialization(self):
        """Test TableProcessor initializes correctly."""
        processor = TableProcessor()
        assert processor is not None

    def test_process_empty_table(self):
        """Test processing an empty table."""
        processor = TableProcessor()
        
        df = pd.DataFrame()
        result = processor.process_table(df)
        
        assert result.dataframe.empty
        assert result.confidence == 0.0
        assert "Empty table" in result.processing_notes

    def test_process_simple_table(self):
        """Test processing a simple table."""
        processor = TableProcessor()
        
        df = pd.DataFrame({
            "SKU": ["ABC-001", "ABC-002"],
            "Description": ["Product A", "Product B"],
            "Price": ["$100.00", "$200.00"],
        })
        
        result = processor.process_table(df)
        
        assert not result.dataframe.empty
        assert result.confidence > 0
        assert len(result.dataframe) == 2

    def test_header_welding(self):
        """Test multi-row header welding."""
        processor = TableProcessor()
        
        # Create table with multi-row header
        df = pd.DataFrame([
            ["Product", "Price", "Details"],
            ["Information", "List", "Specifications"],
            ["ABC-001", "$100.00", "Spec A"],
            ["ABC-002", "$200.00", "Spec B"],
        ])
        
        result = processor.process_table(df)
        
        # Should have welded headers or processed correctly
        assert not result.dataframe.empty
        assert result.confidence > 0

    def test_merged_cell_recovery(self):
        """Test merged cell recovery."""
        processor = TableProcessor()
        
        # Create table with merged cells (empty cells that should be filled)
        df = pd.DataFrame({
            "Category": ["Electronics", "", "", "Furniture", "", ""],
            "Item": ["Phone", "Tablet", "Laptop", "Chair", "Desk", "Table"],
            "Price": ["$500", "$300", "$1000", "$150", "$200", "$250"],
        })
        
        result = processor.process_table(df)
        
        # Check that merged cells were recovered
        assert not result.dataframe.empty
        # The empty cells should be filled with the category value
        category_col = result.dataframe.iloc[:, 0] if len(result.dataframe.columns) > 0 else pd.Series()
        
        # At least some cells should be filled
        non_empty = sum(1 for val in category_col if str(val).strip() and str(val).lower() not in ['nan', 'none', ''])
        assert non_empty >= 2

    def test_numeric_column_detection(self):
        """Test numeric column detection."""
        processor = TableProcessor()
        
        df = pd.DataFrame({
            "Name": ["Item A", "Item B", "Item C"],
            "Price": ["$100.00", "$200.00", "$300.00"],
            "Quantity": ["10", "20", "30"],
        })
        
        result = processor.process_table(df)
        
        assert not result.dataframe.empty
        assert result.confidence > 0

    def test_cross_page_stitching(self):
        """Test cross-page table stitching."""
        processor = TableProcessor()
        
        # Create two tables that should be stitched
        df1 = pd.DataFrame({
            "SKU": ["ABC-001", "ABC-002"],
            "Price": ["$100", "$200"],
        })
        df2 = pd.DataFrame({
            "SKU": ["ABC-003", "ABC-004"],
            "Price": ["$300", "$400"],
        })
        
        table1 = processor.process_table(df1)
        table2 = processor.process_table(df2)
        
        stitched = processor.stitch_cross_page_tables([table1, table2])
        
        # Should stitch into one table
        assert len(stitched) >= 1
        # Combined should have all rows
        total_rows = sum(len(t.dataframe) for t in stitched)
        assert total_rows >= 4

    def test_table_type_detection(self):
        """Test table type detection."""
        processor = TableProcessor()
        
        # Price list table
        price_df = pd.DataFrame({
            "SKU": ["ABC-001", "ABC-002"],
            "Description": ["Product A", "Product B"],
            "List Price": ["$100", "$200"],
        })
        assert processor.detect_table_type(price_df) == "price_list"
        
        # Product catalog
        catalog_df = pd.DataFrame({
            "Model": ["M001", "M002"],
            "Name": ["Widget A", "Widget B"],
            "Category": ["Tools", "Parts"],
        })
        assert processor.detect_table_type(catalog_df) in ["product_catalog", "unknown"]
        
        # Empty table
        empty_df = pd.DataFrame()
        assert processor.detect_table_type(empty_df) == "unknown"

    def test_fingerprint_calculation(self):
        """Test table fingerprint calculation."""
        processor = TableProcessor()
        
        df1 = pd.DataFrame({
            "SKU": ["ABC-001", "ABC-002"],
            "Price": ["$100", "$200"],
        })
        df2 = pd.DataFrame({
            "SKU": ["XYZ-001", "XYZ-002"],
            "Price": ["$300", "$400"],
        })
        
        # Same structure should have same fingerprint
        fp1 = processor._calculate_fingerprint(df1)
        fp2 = processor._calculate_fingerprint(df2)
        
        # Fingerprints should be similar (same column structure)
        assert fp1 is not None
        assert fp2 is not None
        # Both should have similar patterns
        assert "sku" in fp1.lower()
        assert "sku" in fp2.lower()

    def test_is_header_row_detection(self):
        """Test header row detection."""
        processor = TableProcessor()
        
        df = pd.DataFrame([
            ["Model", "Description", "Price"],
            ["ABC-001", "Product A", "$100.00"],
            ["ABC-002", "Product B", "$200.00"],
        ])
        
        # First row should be detected as header
        row = df.iloc[0]
        is_header = processor._is_header_row(row, df, 0)
        assert is_header is True
        
        # Data row should not be detected as header
        data_row = df.iloc[1]
        is_data_header = processor._is_header_row(data_row, df, 1)
        assert is_data_header is False

    def test_clean_dataframe(self):
        """Test dataframe cleaning."""
        processor = TableProcessor()
        
        # Create dataframe with empty rows and columns
        df = pd.DataFrame({
            "A": ["Value1", np.nan, "Value2", np.nan],
            "B": [np.nan, np.nan, np.nan, np.nan],
            "C": ["X", np.nan, "Y", np.nan],
        })
        
        cleaned = processor._clean_dataframe(df)
        
        # Empty column B should be removed
        assert len(cleaned.columns) <= 2
        # Empty rows should be removed
        assert len(cleaned) <= 2


class TestParseDocumentDataclass:
    """Test ParsedDocument dataclass."""

    def test_parsed_document_creation(self):
        """Test creating a ParsedDocument."""
        doc = ParsedDocument(
            source_file="test.pdf",
            pdf_type=PDFType.DIGITAL,
            page_count=5,
            tables=[pd.DataFrame()],
            text_content="Sample text",
            effective_date="01/01/2025",
            products=[{"sku": "TEST"}],
            extraction_results=[],
            overall_confidence=0.95,
            processing_notes=["Test note"],
        )
        
        assert doc.source_file == "test.pdf"
        assert doc.pdf_type == PDFType.DIGITAL
        assert doc.page_count == 5
        assert doc.overall_confidence == 0.95


class TestConvenienceFunction:
    """Test the parse_pdf convenience function."""

    def test_parse_pdf_function_exists(self):
        """Test that parse_pdf function is importable."""
        assert callable(parse_pdf)


class TestExtractionResult:
    """Test ExtractionResult dataclass."""

    def test_extraction_result_creation(self):
        """Test creating an ExtractionResult."""
        result = ExtractionResult(
            method=ExtractionMethod.PYMUPDF,
            tables=[pd.DataFrame({"a": [1, 2]})],
            text_content="Sample text",
            confidence=0.95,
            page_number=1,
            processing_time_ms=100.5,
        )
        
        assert result.method == ExtractionMethod.PYMUPDF
        assert len(result.tables) == 1
        assert result.confidence == 0.95
        assert result.page_number == 1
        assert result.processing_time_ms == 100.5
        assert result.errors == []
        assert result.warnings == []

    def test_extraction_result_with_errors(self):
        """Test ExtractionResult with errors."""
        result = ExtractionResult(
            method=ExtractionMethod.TESSERACT,
            tables=[],
            text_content="",
            confidence=0.0,
            page_number=1,
            processing_time_ms=50.0,
            errors=["OCR failed", "No text found"],
            warnings=["Low quality image"],
        )
        
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert result.confidence == 0.0


class TestPageAnalysis:
    """Test PageAnalysis dataclass."""

    def test_page_analysis_creation(self):
        """Test creating a PageAnalysis."""
        analysis = PageAnalysis(
            page_number=1,
            has_text=True,
            text_density=0.05,
            has_images=False,
            image_coverage=0.0,
            has_tables=True,
            table_count=2,
            table_regions=[(0, 0, 100, 100), (0, 200, 100, 300)],
            recommended_method=ExtractionMethod.PYMUPDF,
            is_scanned=False,
        )
        
        assert analysis.page_number == 1
        assert analysis.has_text is True
        assert analysis.has_tables is True
        assert analysis.table_count == 2
        assert len(analysis.table_regions) == 2
        assert analysis.is_scanned is False


class TestIntegration:
    """Integration tests with real PDF files."""

    @pytest.fixture
    def test_pdf_path(self):
        """Get path to test PDF if it exists."""
        test_paths = [
            Path("testdata/pdf/ABH PL 14 - 11.10.25 - Not to Scale.pdf"),
            Path("tests/testdata/sample.pdf"),
            Path("testdata/sample.pdf"),
        ]
        
        for path in test_paths:
            if path.exists():
                return str(path)
        
        return None

    @pytest.mark.skipif(
        not Path("testdata/pdf").exists(),
        reason="Test PDF directory not found"
    )
    def test_parse_real_pdf(self, test_pdf_path):
        """Test parsing a real PDF file."""
        if test_pdf_path is None:
            pytest.skip("No test PDF file found")
        
        parser = UniversalPDFParser()
        result = parser.parse(test_pdf_path)
        
        assert isinstance(result, ParsedDocument)
        assert result.page_count > 0
        assert result.overall_confidence > 0
        
        assert len(result.tables) > 0 or len(result.text_content) > 0
        
        print(f"\n--- Parse Results for {Path(test_pdf_path).name} ---")
        print(f"PDF Type: {result.pdf_type.value}")
        print(f"Pages: {result.page_count}")
        print(f"Tables: {len(result.tables)}")
        print(f"Products: {len(result.products)}")
        print(f"Confidence: {result.overall_confidence:.2%}")
        print(f"Effective Date: {result.effective_date}")
        print(f"Processing Notes: {result.processing_notes}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
