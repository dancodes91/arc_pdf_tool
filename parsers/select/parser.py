"""
Enhanced SELECT Hinges parser using shared utilities.
"""
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from ..shared.pdf_io import EnhancedPDFExtractor, PDFDocument
from ..shared.confidence import confidence_scorer, ConfidenceScore
from ..shared.normalization import data_normalizer
from ..shared.provenance import ProvenanceTracker, ParsedItem, ProvenanceAnalyzer
from .sections import SelectSectionExtractor


logger = logging.getLogger(__name__)


class SelectHingesParser:
    """Enhanced SELECT Hinges parser with comprehensive extraction capabilities."""

    def __init__(self, pdf_path: str, config: Dict[str, Any] = None):
        self.pdf_path = pdf_path
        self.config = config or {}
        self.logger = logging.getLogger(f"{__class__.__name__}")

        # Initialize utilities
        self.provenance_tracker = ProvenanceTracker(pdf_path)
        self.section_extractor = SelectSectionExtractor(self.provenance_tracker)
        self.pdf_extractor = EnhancedPDFExtractor(pdf_path, config)

        # Parser results
        self.document: Optional[PDFDocument] = None
        self.effective_date: Optional[ParsedItem] = None
        self.net_add_options: List[ParsedItem] = []
        self.products: List[ParsedItem] = []
        self.finishes: List[ParsedItem] = []

    def parse(self) -> Dict[str, Any]:
        """Parse SELECT Hinges PDF with comprehensive extraction."""
        self.logger.info(f"Starting enhanced SELECT Hinges parsing: {self.pdf_path}")

        try:
            # Extract PDF document
            self.document = self.pdf_extractor.extract_document()
            self.logger.info(f"Extracted PDF with {len(self.document.pages)} pages")

            # Combine all text content
            full_text = self._combine_text_content()

            # Extract all tables
            all_tables = self._combine_all_tables()

            # Parse sections
            self._parse_effective_date(full_text)
            self._parse_finishes(full_text)
            self._parse_net_add_options(full_text)
            self._parse_model_tables(full_text, all_tables)

            # Build final results
            results = self._build_results()

            self.logger.info(f"SELECT parsing completed: {self._get_summary()}")
            return results

        except Exception as e:
            self.logger.error(f"Error during SELECT parsing: {e}")
            return self._build_error_results(str(e))

    def _combine_text_content(self) -> str:
        """Combine text content from all pages."""
        if not self.document:
            return ""

        text_parts = []
        for page in self.document.pages:
            if page.text:
                text_parts.append(f"--- PAGE {page.page_number} ---\n{page.text}")

        return "\n\n".join(text_parts)

    def _combine_all_tables(self) -> List[Any]:
        """Combine all tables from all pages."""
        if not self.document:
            return []

        all_tables = []
        for page in self.document.pages:
            for table in page.tables:
                all_tables.append(table)

        return all_tables

    def _parse_effective_date(self, text: str) -> None:
        """Parse effective date from document."""
        self.logger.info("Parsing effective date...")
        self.effective_date = self.section_extractor.extract_effective_date(text)

        if self.effective_date:
            self.logger.info(f"Found effective date: {self.effective_date.value}")
        else:
            self.logger.warning("No effective date found")

    def _parse_finishes(self, text: str) -> None:
        """Parse finish symbols from document."""
        self.logger.info("Parsing finish symbols...")
        self.finishes = self.section_extractor.extract_finish_symbols(text)
        self.logger.info(f"Found {len(self.finishes)} finish symbols")

    def _parse_net_add_options(self, text: str) -> None:
        """Parse net add options from document."""
        self.logger.info("Parsing net add options...")
        self.net_add_options = self.section_extractor.extract_net_add_options(text)

        self.logger.info(f"Found {len(self.net_add_options)} net add options")
        for option in self.net_add_options:
            if isinstance(option.value, dict):
                code = option.value.get('option_code', 'Unknown')
                price = option.value.get('adder_value', 0)
                self.logger.debug(f"  {code}: ${price}")

    def _parse_model_tables(self, text: str, tables: List[Any]) -> None:
        """Parse product model tables page by page using Camelot."""
        self.logger.info("Parsing model tables...")
        self.products = []

        # Process each page individually with Camelot
        for page in self.document.pages:
            page_text = page.text or ''

            # Extract tables for this page using Camelot
            page_tables = self.section_extractor.extract_tables_with_camelot(
                self.pdf_path, page.page_number
            )

            # If Camelot didn't find tables, fallback to pdfplumber tables
            if not page_tables and page.tables:
                page_tables = page.tables

            # Extract products from this page
            if page_tables:
                page_products = self.section_extractor.extract_model_tables(
                    page_text, page_tables, page_number=page.page_number
                )
                self.products.extend(page_products)

        self.logger.info(f"Found {len(self.products)} products")

        # Log sample products for verification
        for i, product in enumerate(self.products[:5]):  # First 5 products
            if isinstance(product.value, dict):
                sku = product.value.get('sku', 'Unknown')
                price = product.value.get('base_price', 0)
                self.logger.debug(f"  {sku}: ${price}")

    def _build_results(self) -> Dict[str, Any]:
        """Build final parsing results."""
        # Calculate overall confidence
        all_items = []
        if self.effective_date:
            all_items.append(self.effective_date)
        all_items.extend(self.net_add_options)
        all_items.extend(self.products)

        # Analyze extraction quality
        analyzer = ProvenanceAnalyzer()
        quality_analysis = analyzer.analyze_extraction_quality(all_items)

        # Build structured results
        results = {
            'manufacturer': 'SELECT Hinges',
            'source_file': self.pdf_path,
            'parsing_metadata': {
                'parser_version': '2.0',
                'extraction_method': 'enhanced_pipeline',
                'total_pages': len(self.document.pages) if self.document else 0,
                'overall_confidence': quality_analysis['quality_score'],
                'extraction_quality': quality_analysis
            },
            'effective_date': self._serialize_item(self.effective_date),
            'net_add_options': [self._serialize_item(item) for item in self.net_add_options],
            'products': [self._serialize_item(item) for item in self.products],
            'summary': {
                'total_products': len(self.products),
                'total_options': len(self.net_add_options),
                'has_effective_date': self.effective_date is not None,
                'confidence_distribution': quality_analysis.get('confidence_distribution', {}),
                'recommendations': quality_analysis.get('recommendations', [])
            }
        }

        # Add validation results
        results['validation'] = self._validate_results(results)

        return results

    def _build_error_results(self, error_message: str) -> Dict[str, Any]:
        """Build results when parsing fails."""
        return {
            'manufacturer': 'SELECT Hinges',
            'source_file': self.pdf_path,
            'parsing_metadata': {
                'parser_version': '2.0',
                'extraction_method': 'enhanced_pipeline',
                'status': 'failed',
                'error': error_message
            },
            'effective_date': None,
            'net_add_options': [],
            'products': [],
            'summary': {
                'total_products': 0,
                'total_options': 0,
                'has_effective_date': False,
                'parsing_failed': True,
                'error_message': error_message
            },
            'validation': {
                'is_valid': False,
                'errors': [f"Parsing failed: {error_message}"],
                'warnings': [],
                'accuracy_metrics': {}
            }
        }

    def _serialize_item(self, item: Optional[ParsedItem]) -> Optional[Dict[str, Any]]:
        """Serialize a parsed item for output."""
        if not item:
            return None

        return {
            'value': item.value,
            'data_type': item.data_type,
            'normalized_value': item.normalized_value,
            'confidence': item.confidence,
            'provenance': item.provenance.to_dict() if item.provenance else None,
            'validation_errors': item.validation_errors
        }

    def _validate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parsing results."""
        validation = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'accuracy_metrics': {}
        }

        # Check for effective date
        if not results['effective_date']:
            validation['warnings'].append("No effective date found")

        # Check product count
        product_count = len(results['products'])
        if product_count == 0:
            validation['errors'].append("No products extracted")
            validation['is_valid'] = False
        elif product_count < 10:
            validation['warnings'].append(f"Low product count: {product_count}")

        # Check option count
        option_count = len(results['net_add_options'])
        if option_count == 0:
            validation['warnings'].append("No net add options found")

        # Calculate accuracy metrics
        total_items = product_count + option_count
        if total_items > 0:
            # Count items with high confidence
            high_confidence_count = 0
            for item_list in [results['products'], results['net_add_options']]:
                for item in item_list:
                    if item and item.get('confidence', 0) >= 0.8:
                        high_confidence_count += 1

            confidence_rate = high_confidence_count / total_items
            validation['accuracy_metrics']['confidence_rate'] = confidence_rate

            if confidence_rate < 0.7:
                validation['warnings'].append(f"Low confidence rate: {confidence_rate:.1%}")

        # Overall validation
        if len(validation['errors']) == 0 and len(validation['warnings']) <= 2:
            validation['accuracy_metrics']['overall_quality'] = 'good'
        elif len(validation['errors']) == 0:
            validation['accuracy_metrics']['overall_quality'] = 'acceptable'
        else:
            validation['accuracy_metrics']['overall_quality'] = 'poor'

        return validation

    def _get_summary(self) -> str:
        """Get parsing summary for logging."""
        return (f"{len(self.products)} products, "
                f"{len(self.net_add_options)} options, "
                f"effective_date={'found' if self.effective_date else 'not_found'}")

    def get_provenance_report(self) -> str:
        """Generate detailed provenance report."""
        all_items = []
        if self.effective_date:
            all_items.append(self.effective_date)
        all_items.extend(self.net_add_options)
        all_items.extend(self.products)

        analyzer = ProvenanceAnalyzer()
        return analyzer.export_provenance_report(all_items)

    def export_golden_data(self, output_dir: str) -> Dict[str, str]:
        """Export golden test data for validation."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        files_created = {}

        # Export effective date
        if self.effective_date:
            date_file = output_path / "effective_date.json"
            import json
            with open(date_file, 'w') as f:
                json.dump(self._serialize_item(self.effective_date), f, indent=2, default=str)
            files_created['effective_date'] = str(date_file)

        # Export options
        if self.net_add_options:
            options_file = output_path / "net_add_options.json"
            with open(options_file, 'w') as f:
                options_data = [self._serialize_item(item) for item in self.net_add_options]
                json.dump(options_data, f, indent=2, default=str)
            files_created['options'] = str(options_file)

        # Export products (sample)
        if self.products:
            products_file = output_path / "products_sample.json"
            sample_products = self.products[:10]  # First 10 products
            with open(products_file, 'w') as f:
                products_data = [self._serialize_item(item) for item in sample_products]
                json.dump(products_data, f, indent=2, default=str)
            files_created['products'] = str(products_file)

        # Export provenance report
        provenance_file = output_path / "provenance_report.txt"
        with open(provenance_file, 'w') as f:
            f.write(self.get_provenance_report())
        files_created['provenance'] = str(provenance_file)

        return files_created

    def identify_manufacturer(self) -> str:
        """Identify manufacturer from PDF content for compatibility with app.py."""
        # Extract text if not already done
        if not hasattr(self, 'document') or not self.document:
            try:
                self.document = self.pdf_extractor.extract_document()
            except Exception:
                pass

        # Get text content
        text = self._extract_text_content()
        if not text:
            return 'select_hinges'  # Default for SELECT parser

        # Look for SELECT indicators
        text_lower = text.lower()
        select_indicators = [
            'select hinges', 'select hardware', 'selecthinges',
            'manufactured by select', 'select hinge'
        ]

        for indicator in select_indicators:
            if indicator in text_lower:
                return 'select_hinges'

        # Check for Hager indicators (in case wrong parser was used)
        hager_indicators = ['hager', 'hager companies', 'architectural hardware group']
        for indicator in hager_indicators:
            if indicator in text_lower:
                return 'hager'

        # Default to select_hinges for this parser
        return 'select_hinges'