"""
Enhanced PDF extractor that integrates page classification, table processing,
and OCR fallback for robust parsing.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import pandas as pd

from .page_classifier import PageClassifier, PageAnalysis, route_extraction
from .table_processor import TableProcessor, ProcessedTable
from .ocr_processor import OCRProcessor, OCRConfig, extract_with_ocr_fallback
from .pdf_io import EnhancedPDFExtractor, PDFDocument
from .provenance import ProvenanceTracker

logger = logging.getLogger(__name__)


@dataclass
class EnhancedExtractionResult:
    """Result of enhanced extraction process."""

    text: str
    tables: List[ProcessedTable]
    page_analysis: PageAnalysis
    ocr_result: Optional[Any] = None
    extraction_method_used: str = ""
    processing_notes: List[str] = None


class HardenedExtractor:
    """
    Hardened PDF extractor with intelligent routing and fallbacks.

    Combines page classification, advanced table processing, and OCR
    fallback for maximum extraction reliability across different layouts.
    """

    def __init__(self, pdf_path: str, config: Dict[str, Any] = None):
        self.pdf_path = pdf_path
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.page_classifier = PageClassifier()
        self.table_processor = TableProcessor()
        self.ocr_processor = OCRProcessor(OCRConfig(**self.config.get("ocr", {})))
        self.base_extractor = EnhancedPDFExtractor(pdf_path, config)
        self.provenance_tracker = ProvenanceTracker(pdf_path)

        # Hardening thresholds
        self.ocr_text_threshold = self.config.get("ocr_text_threshold", 50)
        self.table_confidence_threshold = self.config.get("table_confidence_threshold", 0.3)
        self.cross_page_stitch = self.config.get("cross_page_stitch", True)

    def extract_document_hardened(self) -> Tuple[PDFDocument, List[EnhancedExtractionResult]]:
        """
        Extract document with hardening techniques.

        Returns:
            Tuple of (PDFDocument, per_page_results)
        """
        self.logger.info(f"Starting hardened extraction: {self.pdf_path}")

        # Extract base document
        document = self.base_extractor.extract_document()
        per_page_results = []

        # Process each page with intelligent routing
        for page in document.pages:
            page_result = self._extract_page_hardened(page)
            per_page_results.append(page_result)

        # Apply cross-page processing if enabled
        if self.cross_page_stitch:
            per_page_results = self._apply_cross_page_processing(per_page_results)

        self.logger.info(f"Hardened extraction completed: {len(per_page_results)} pages processed")
        return document, per_page_results

    def _extract_page_hardened(self, page) -> EnhancedExtractionResult:
        """
        Extract a single page with hardening techniques.

        Args:
            page: Page object from base extraction

        Returns:
            EnhancedExtractionResult for the page
        """
        page_number = page.page_number
        base_text = page.text or ""
        base_tables = page.tables or []

        self.logger.debug(f"Processing page {page_number} with hardening")

        # Step 1: Classify page and get routing recommendation
        page_analysis = self.page_classifier.classify_page(
            page_text=base_text, page_number=page_number, tables=base_tables, page_features={}
        )

        extraction_config = route_extraction(
            page_analysis, {"text": base_text, "tables": base_tables}
        )
        processing_notes = [f"Page classified as: {page_analysis.page_type.value}"]

        # Step 2: Apply method-specific extraction
        final_text = base_text
        final_tables = []
        ocr_result = None
        method_used = extraction_config["method"]

        try:
            if extraction_config["ocr_fallback"] or method_used == "ocr_fallback":
                # OCR fallback path
                final_text, raw_tables, ocr_result = extract_with_ocr_fallback(
                    self.pdf_path, page_number, base_text, base_tables, self.ocr_processor.config
                )
                method_used = "ocr_fallback"
                processing_notes.append("OCR fallback applied")

                # Process OCR tables
                for table in raw_tables:
                    processed_table = self.table_processor.process_table(
                        table, page_number, len(final_tables)
                    )
                    final_tables.append(processed_table)

            elif method_used in ["camelot_lattice", "camelot_stream"]:
                # Enhanced Camelot extraction with processing
                raw_tables = self._extract_tables_camelot(page_number, extraction_config)
                processing_notes.append(
                    f"Camelot {extraction_config.get('camelot_flavor', 'lattice')} extraction"
                )

                # Process each table with hardening
                for table in raw_tables:
                    processed_table = self.table_processor.process_table(
                        table, page_number, len(final_tables)
                    )
                    final_tables.append(processed_table)

            elif method_used == "pdfplumber":
                # Enhanced pdfplumber extraction
                if base_tables:
                    for table in base_tables:
                        processed_table = self.table_processor.process_table(
                            table, page_number, len(final_tables)
                        )
                        final_tables.append(processed_table)
                processing_notes.append("PDFplumber extraction with processing")

            else:
                # Text-only extraction
                processing_notes.append("Text-only extraction")

        except Exception as e:
            self.logger.error(f"Enhanced extraction failed for page {page_number}: {e}")
            # Fallback to base extraction
            for table in base_tables:
                processed_table = self.table_processor.process_table(
                    table, page_number, len(final_tables)
                )
                final_tables.append(processed_table)
            processing_notes.append(f"Fallback to base extraction due to: {str(e)}")

        # Step 3: Apply rotated text handling if needed
        if page_analysis.features.get("needs_rotation_detection", False):
            final_text = self._handle_rotated_text(final_text, page_number)
            processing_notes.append("Rotated text handling applied")

        # Step 4: Normalize units and currency
        final_text = self._normalize_units_currency(final_text)
        for table in final_tables:
            table.dataframe = self._normalize_table_currency(table.dataframe)

        return EnhancedExtractionResult(
            text=final_text,
            tables=final_tables,
            page_analysis=page_analysis,
            ocr_result=ocr_result,
            extraction_method_used=method_used,
            processing_notes=processing_notes or [],
        )

    def _extract_tables_camelot(self, page_number: int, config: Dict) -> List[pd.DataFrame]:
        """Extract tables using Camelot with specified configuration."""
        try:
            import camelot

            flavor = config.get("camelot_flavor", "lattice")
            kwargs = {}

            if flavor == "lattice":
                kwargs.update(
                    {
                        "edge_tol": config.get("edge_tol", 50),
                        "row_tol": config.get("row_tol", 2),
                    }
                )
            else:  # stream
                kwargs.update(
                    {
                        "row_tol": config.get("row_tol", 2),
                        "col_tol": config.get("col_tol", 0),
                    }
                )

            # Extract tables
            tables = camelot.read_pdf(
                self.pdf_path, pages=str(page_number), flavor=flavor, **kwargs
            )

            return [table.df for table in tables]

        except Exception as e:
            self.logger.error(f"Camelot extraction failed for page {page_number}: {e}")
            return []

    def _apply_cross_page_processing(
        self, page_results: List[EnhancedExtractionResult]
    ) -> List[EnhancedExtractionResult]:
        """
        Apply cross-page processing like table stitching.

        Args:
            page_results: Results from individual page processing

        Returns:
            Updated results with cross-page processing applied
        """
        self.logger.info("Applying cross-page processing")

        # Extract all processed tables for stitching
        all_tables = []
        page_table_counts = []

        for result in page_results:
            page_table_counts.append(len(result.tables))
            all_tables.extend(result.tables)

        # Apply table stitching
        if all_tables:
            stitched_tables = self.table_processor.stitch_cross_page_tables(all_tables)

            # Redistribute stitched tables back to pages
            if len(stitched_tables) != len(all_tables):
                self.logger.info(
                    f"Table stitching: {len(all_tables)} -> {len(stitched_tables)} tables"
                )

                # Simple redistribution - assign stitched tables to first relevant page
                table_idx = 0
                for i, result in enumerate(page_results):
                    original_count = page_table_counts[i]
                    new_tables = []

                    # Take next stitched tables up to original count
                    for _ in range(min(original_count, len(stitched_tables) - table_idx)):
                        if table_idx < len(stitched_tables):
                            new_tables.append(stitched_tables[table_idx])
                            table_idx += 1

                    result.tables = new_tables
                    if len(new_tables) != original_count:
                        result.processing_notes.append(
                            f"Cross-page stitching applied: {original_count} -> {len(new_tables)} tables"
                        )

        return page_results

    def _handle_rotated_text(self, text: str, page_number: int) -> str:
        """
        Handle rotated text detection and normalization.

        Args:
            text: Input text
            page_number: Page number for context

        Returns:
            Text with rotation issues addressed
        """
        # This is a placeholder for rotation detection/correction
        # In a full implementation, this would use PyMuPDF or similar
        # to detect and correct text rotation

        # Simple heuristic: if text has unusual patterns, try to fix
        lines = text.split("\n")

        # Look for patterns that suggest rotation issues
        unusual_patterns = 0
        for line in lines:
            # Very short lines might indicate rotation
            if len(line.strip()) == 1:
                unusual_patterns += 1
            # Lines with only numbers might be rotated headers
            if line.strip().isdigit() and len(line.strip()) < 3:
                unusual_patterns += 1

        if unusual_patterns > len(lines) * 0.3:
            self.logger.warning(f"Page {page_number} may have rotation issues")
            # For now, just log the issue
            # TODO: Implement actual rotation correction

        return text

    def _normalize_units_currency(self, text: str) -> str:
        """
        Normalize currency and unit representations.

        Args:
            text: Input text

        Returns:
            Text with normalized currency/units
        """
        import re

        # Normalize currency symbols
        text = re.sub(r"\$\s+", "$", text)  # Remove space after $
        text = re.sub(r"(\d)\s*,\s*(\d{3})", r"\1,\2", text)  # Fix comma spacing in numbers
        text = re.sub(r"(\d)\s+\.(\d{2})", r"\1.\2", text)  # Fix decimal spacing

        # Normalize common units
        unit_normalizations = {
            r"\binches?\b": "in",
            r"\bfeet\b": "ft",
            r"\bpounds?\b": "lbs",
            r"\bkilograms?\b": "kg",
        }

        for pattern, replacement in unit_normalizations.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def _normalize_table_currency(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize currency in table data.

        Args:
            df: Input DataFrame

        Returns:
            DataFrame with normalized currency
        """
        if df.empty:
            return df

        new_df = df.copy()

        for col_idx in range(len(new_df.columns)):
            column = new_df.iloc[:, col_idx]

            # Check if column contains prices
            sample_text = " ".join(str(val) for val in column.head(5))
            if "$" in sample_text:
                # Normalize price formatting in this column
                def normalize_price(val):
                    if pd.isna(val):
                        return val

                    val_str = str(val)
                    # Remove extra spaces around currency
                    val_str = re.sub(r"\$\s+", "$", val_str)
                    # Fix decimal spacing
                    val_str = re.sub(r"(\d)\s+\.(\d{2})", r"\1.\2", val_str)
                    return val_str

                new_df.iloc[:, col_idx] = column.apply(normalize_price)

        return new_df

    def extract_section_hardened(
        self, section_type: str, page_range: Optional[Tuple[int, int]] = None
    ) -> List[Any]:
        """
        Extract a specific section with hardening techniques.

        Args:
            section_type: Type of section (finish_symbols, price_rules, etc.)
            page_range: Optional range of pages to process

        Returns:
            List of extracted items for the section
        """
        document, page_results = self.extract_document_hardened()

        # Filter to relevant pages
        if page_range:
            start_page, end_page = page_range
            relevant_results = [
                result
                for result in page_results
                if start_page <= result.page_analysis.page_number <= end_page
            ]
        else:
            # Filter by page type relevance
            type_mapping = {
                "finish_symbols": ["finish_symbols", "mixed_content"],
                "price_rules": ["price_rules", "mixed_content"],
                "products": ["data_table", "mixed_content"],
                "options": ["option_list", "mixed_content"],
            }

            relevant_types = type_mapping.get(section_type, ["mixed_content"])
            relevant_results = [
                result
                for result in page_results
                if result.page_analysis.page_type.value in relevant_types
            ]

        self.logger.info(
            f"Section {section_type}: processing {len(relevant_results)} relevant pages"
        )
        return relevant_results
