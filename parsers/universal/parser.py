"""
Universal Parser - Works with ANY manufacturer price book.

Uses ML-based table detection + pattern extraction to parse unknown formats.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from .table_detector import MLTableDetector
from .pattern_extractor import SmartPatternExtractor
from ..shared.pdf_io import EnhancedPDFExtractor, PDFDocument
from ..shared.provenance import ProvenanceTracker, ParsedItem

logger = logging.getLogger(__name__)


class UniversalParser:
    """
    Universal adaptive parser that works with ANY manufacturer price book.

    Uses 2-step approach:
    1. ML-based table detection (Microsoft TATR)
    2. Smart pattern extraction (regex + heuristics)
    """

    def __init__(self, pdf_path: str, config: Dict[str, Any] = None):
        self.pdf_path = pdf_path
        self.config = config or {}
        self.logger = logging.getLogger(f"{__class__.__name__}")

        # Configuration
        self.max_pages = self.config.get("max_pages", None)
        self.confidence_threshold = self.config.get("confidence_threshold", 0.7)
        self.use_ml_detection = self.config.get("use_ml_detection", True)
        self.extract_structure = self.config.get("extract_structure", False)

        # Initialize components
        self.provenance_tracker = ProvenanceTracker(pdf_path)
        self.pdf_extractor = EnhancedPDFExtractor(pdf_path, config)
        self.pattern_extractor = SmartPatternExtractor()

        # ML detector (lazy loading)
        self.ml_detector = None
        if self.use_ml_detection:
            self.ml_detector = MLTableDetector()

        # Parser results
        self.document: Optional[PDFDocument] = None
        self.detected_tables: List[Dict] = []
        self.products: List[ParsedItem] = []
        self.options: List[ParsedItem] = []
        self.finishes: List[ParsedItem] = []
        self.effective_date: Optional[ParsedItem] = None

    def parse(self) -> Dict[str, Any]:
        """
        Parse PDF using universal adaptive approach.

        Returns:
            Structured data with products, prices, options, etc.
        """
        self.logger.info(f"Starting universal parsing: {self.pdf_path}")

        try:
            # Step 1: Extract PDF document (text + basic tables)
            self.document = self.pdf_extractor.extract_document()
            total_pages = len(self.document.pages)
            self.logger.info(f"Extracted PDF: {total_pages} pages")

            # Step 2: Extract text-based data
            full_text = self._combine_text_content()
            self._parse_from_text(full_text)

            # Step 3: ML-based table detection (if enabled)
            if self.use_ml_detection:
                self.logger.info("Running ML-based table detection...")
                self.detected_tables = self.ml_detector.detect_and_extract_tables(
                    self.pdf_path,
                    max_pages=self.max_pages,
                    extract_structure=self.extract_structure,
                )
                self.logger.info(f"Detected {len(self.detected_tables)} tables")

                # Extract from detected tables
                self._parse_from_ml_tables()
            else:
                self.logger.info("ML detection disabled, using text-only extraction")

            # Build final results
            results = self._build_results()

            self.logger.info(f"Universal parsing complete: {self._get_summary()}")
            return results

        except Exception as e:
            self.logger.error(f"Error during universal parsing: {e}", exc_info=True)
            return self._build_error_results(str(e))

    def _combine_text_content(self) -> str:
        """Combine text from all pages."""
        if not self.document:
            return ""

        text_parts = []
        for page in self.document.pages:
            if page.text:
                text_parts.append(f"--- PAGE {page.page_number} ---\n{page.text}")

        return "\n\n".join(text_parts)

    def _parse_from_text(self, text: str):
        """Parse data from plain text using pattern extraction."""
        self.logger.info("Extracting from text...")

        # Extract effective date
        date_str = self.pattern_extractor.extract_effective_date(text)
        if date_str:
            self.effective_date = self.provenance_tracker.create_parsed_item(
                value=date_str,
                data_type="effective_date",
                raw_text=date_str,
                page_number=1,
                confidence=0.8,
            )
            self.logger.info(f"Found effective date: {date_str}")

        # Extract finishes
        finish_codes = self.pattern_extractor.extract_finishes(text)
        for finish_code in finish_codes[:20]:  # Limit to 20 most common
            finish_item = self.provenance_tracker.create_parsed_item(
                value={"code": finish_code, "name": finish_code},
                data_type="finish",
                raw_text=finish_code,
                page_number=1,
                confidence=0.7,
            )
            self.finishes.append(finish_item)

        self.logger.info(f"Found {len(self.finishes)} finish codes from text")

        # Extract options from text
        options_data = self.pattern_extractor.extract_options(text)
        for option in options_data:
            option_item = self.provenance_tracker.create_parsed_item(
                value=option,
                data_type="option",
                raw_text=str(option),
                page_number=1,
                confidence=0.75,
            )
            self.options.append(option_item)

        self.logger.info(f"Found {len(self.options)} options from text")

    def _parse_from_ml_tables(self):
        """Parse products from ML-detected tables."""
        if not self.detected_tables:
            return

        self.logger.info("Extracting products from ML-detected tables...")

        for table_idx, table in enumerate(self.detected_tables):
            page_num = table.get("page", 0)
            confidence = table.get("confidence", 0)

            # Get table image and try OCR extraction (simplified)
            # In production, would use proper OCR + structure alignment
            # For now, using pattern extraction on available text

            # Try to extract from page text in table region
            page = self._get_page_by_number(page_num)
            if page and page.text:
                # Extract products using pattern matching
                page_products = self.pattern_extractor.extract_products_from_text(
                    page.text, page_num
                )

                # Convert to ParsedItem
                for product_data in page_products:
                    if product_data["confidence"] >= self.confidence_threshold:
                        product_item = self.provenance_tracker.create_parsed_item(
                            value=product_data,
                            data_type="product",
                            raw_text=product_data.get("raw_text", ""),
                            page_number=page_num,
                            confidence=product_data["confidence"],
                        )
                        self.products.append(product_item)

        self.logger.info(f"Extracted {len(self.products)} products from tables")

    def _get_page_by_number(self, page_num: int) -> Optional[Any]:
        """Get page object by page number."""
        if not self.document:
            return None

        for page in self.document.pages:
            if page.page_number == page_num:
                return page
        return None

    def _build_results(self) -> Dict[str, Any]:
        """Build structured results."""
        # Identify manufacturer from text
        manufacturer = self._identify_manufacturer()

        # Calculate overall confidence
        all_items = []
        if self.effective_date:
            all_items.append(self.effective_date)
        all_items.extend(self.products)
        all_items.extend(self.options)
        all_items.extend(self.finishes)

        avg_confidence = (
            sum(item.confidence for item in all_items) / len(all_items)
            if all_items
            else 0.0
        )

        return {
            "manufacturer": manufacturer,
            "source_file": self.pdf_path,
            "parsing_metadata": {
                "parser_version": "1.0_universal",
                "extraction_method": "ml_detection" if self.use_ml_detection else "text_only",
                "total_pages": len(self.document.pages) if self.document else 0,
                "tables_detected": len(self.detected_tables),
                "overall_confidence": avg_confidence,
            },
            "effective_date": self._serialize_item(self.effective_date),
            "products": [self._serialize_item(item) for item in self.products],
            "options": [self._serialize_item(item) for item in self.options],
            "finish_symbols": [self._serialize_item(item) for item in self.finishes],
            "summary": {
                "total_products": len(self.products),
                "total_options": len(self.options),
                "total_finishes": len(self.finishes),
                "has_effective_date": self.effective_date is not None,
                "confidence": avg_confidence,
            },
        }

    def _build_error_results(self, error_message: str) -> Dict[str, Any]:
        """Build error response."""
        return {
            "manufacturer": "Unknown",
            "source_file": self.pdf_path,
            "parsing_metadata": {
                "parser_version": "1.0_universal",
                "status": "failed",
                "error": error_message,
            },
            "products": [],
            "options": [],
            "summary": {
                "total_products": 0,
                "parsing_failed": True,
                "error_message": error_message,
            },
        }

    def _serialize_item(self, item: Optional[ParsedItem]) -> Optional[Dict[str, Any]]:
        """Serialize parsed item for output."""
        if not item:
            return None

        return {
            "value": item.value,
            "data_type": item.data_type,
            "confidence": item.confidence,
            "provenance": item.provenance.to_dict() if item.provenance else None,
        }

    def _identify_manufacturer(self) -> str:
        """Try to identify manufacturer from document text."""
        if not self.document:
            return "Unknown"

        # Get first few pages text
        text = ""
        for page in self.document.pages[:3]:
            if page.text:
                text += page.text.lower()

        # Common manufacturer keywords
        manufacturers = {
            "hager": ["hager", "hager companies", "architectural hardware group"],
            "select_hinges": ["select hinges", "select hardware"],
            "schlage": ["schlage", "allegion schlage"],
            "von_duprin": ["von duprin", "allegion von duprin"],
            "ives": ["ives hardware", "ives by allegion"],
            "lcn": ["lcn closers", "allegion lcn"],
            "rockwood": ["rockwood manufacturing"],
            "adams_rite": ["adams rite"],
            "falcon": ["falcon lock"],
        }

        for mfr, keywords in manufacturers.items():
            if any(keyword in text for keyword in keywords):
                return mfr.replace("_", " ").title()

        return "Unknown"

    def _get_summary(self) -> str:
        """Get parsing summary for logging."""
        return (
            f"{len(self.products)} products, "
            f"{len(self.options)} options, "
            f"{len(self.finishes)} finishes, "
            f"{len(self.detected_tables)} tables detected"
        )
