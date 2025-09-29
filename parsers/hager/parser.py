"""
Enhanced Hager parser using shared utilities.
"""
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from ..shared.pdf_io import EnhancedPDFExtractor, PDFDocument
from ..shared.confidence import confidence_scorer, ConfidenceScore
from ..shared.normalization import data_normalizer
from ..shared.provenance import ProvenanceTracker, ParsedItem, ProvenanceAnalyzer
from .sections import HagerSectionExtractor


logger = logging.getLogger(__name__)


class HagerParser:
    """Enhanced Hager parser with comprehensive extraction capabilities."""

    def __init__(self, pdf_path: str, config: Dict[str, Any] = None):
        self.pdf_path = pdf_path
        self.config = config or {}
        self.logger = logging.getLogger(f"{__class__.__name__}")

        # Initialize utilities
        self.provenance_tracker = ProvenanceTracker(pdf_path)
        self.section_extractor = HagerSectionExtractor(self.provenance_tracker)
        self.pdf_extractor = EnhancedPDFExtractor(pdf_path, config)

        # Parser results
        self.document: Optional[PDFDocument] = None
        self.effective_date: Optional[ParsedItem] = None
        self.finish_symbols: List[ParsedItem] = []
        self.price_rules: List[ParsedItem] = []
        self.hinge_additions: List[ParsedItem] = []
        self.products: List[ParsedItem] = []

    def parse(self) -> Dict[str, Any]:
        """Parse Hager PDF with comprehensive extraction."""
        self.logger.info(f"Starting enhanced Hager parsing: {self.pdf_path}")

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
            self._parse_finish_symbols(full_text)
            self._parse_price_rules(full_text)
            self._parse_hinge_additions(full_text)
            self._parse_item_tables(full_text, all_tables)

            # Build final results
            results = self._build_results()

            self.logger.info(f"Hager parsing completed: {self._get_summary()}")
            return results

        except Exception as e:
            self.logger.error(f"Error during Hager parsing: {e}")
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

        # Use generic date extraction from shared utilities
        date_result = data_normalizer.normalize_date(text)
        if date_result['value']:
            # Handle both ConfidenceScore objects and float values
            confidence_val = date_result['confidence']
            if hasattr(confidence_val, 'score'):
                confidence = confidence_val.score
            elif isinstance(confidence_val, (int, float)):
                confidence = float(confidence_val)
            else:
                confidence = 0.7

            self.effective_date = self.provenance_tracker.create_parsed_item(
                value=date_result['value'],
                data_type="effective_date",
                raw_text=date_result['raw_input'],
                confidence=confidence
            )
            self.logger.info(f"Found effective date: {self.effective_date.value}")
        else:
            self.logger.warning("No effective date found")

    def _parse_finish_symbols(self, text: str) -> None:
        """Parse finish symbols and BHMA codes page by page."""
        self.logger.info("Parsing finish symbols...")
        self.finish_symbols = []

        for page in self.document.pages:
            page_text = (page.text or '').upper()
            if 'ARCHITECTURAL FINISH SYMBOLS' not in page_text:
                continue

            # Extract tables for this page using Camelot
            tables = self.section_extractor.extract_tables_with_camelot(
                self.pdf_path, page.page_number
            )

            page_symbols = self.section_extractor.extract_finish_symbols(
                page_text, tables, page.page_number
            )
            self.finish_symbols.extend(page_symbols)

        self.logger.info(f"Found {len(self.finish_symbols)} finish symbols")
        for finish in self.finish_symbols[:3]:  # Log first 3
            if isinstance(finish.value, dict):
                code = finish.value.get('code', 'Unknown')
                name = finish.value.get('name', 'Unknown')
                price = finish.value.get('base_price', 0)
                self.logger.debug(f"  {code} ({name}): ${price}")

    def _parse_price_rules(self, text: str) -> None:
        """Parse pricing rules page by page."""
        self.logger.info("Parsing price rules...")
        self.price_rules = []

        # Optimization: Limit price rule extraction to likely pages (first 100 pages typically contain rules)
        max_pages_to_check = min(100, len(self.document.pages))
        self.logger.info(f"Checking first {max_pages_to_check} pages for price rules")

        for page in self.document.pages[:max_pages_to_check]:
            page_text = page.text or ''
            page_upper = page_text.upper()

            # More specific keyword filtering to reduce false positives
            if not any(keyword in page_upper for keyword in ['FINISH PRICE', 'USE PRICE OF', 'PRICE MAPPING']):
                continue

            # Extract tables for this page using Camelot
            tables = self.section_extractor.extract_tables_with_camelot(
                self.pdf_path, page.page_number
            )

            page_rules = self.section_extractor.extract_price_rules(
                page_text, tables, page.page_number
            )
            self.price_rules.extend(page_rules)

        self.logger.info(f"Found {len(self.price_rules)} price rules")
        for rule in self.price_rules[:3]:  # Log first 3
            if isinstance(rule.value, dict):
                source = rule.value.get('source_finish', 'Unknown')
                target = rule.value.get('target_finish', 'Unknown')
                self.logger.debug(f"  {source} → {target}")

    def _parse_hinge_additions(self, text: str) -> None:
        """Parse hinge additions and modifications page by page."""
        self.logger.info("Parsing hinge additions...")
        self.hinge_additions = []

        # Optimization: Limit to first 100 pages (additions typically in front matter)
        max_pages_to_check = min(100, len(self.document.pages))
        self.logger.info(f"Checking first {max_pages_to_check} pages for hinge additions")

        for page in self.document.pages[:max_pages_to_check]:
            page_text = page.text or ''
            page_upper = page_text.upper()

            # Look for addition-related keywords
            if not any(keyword in page_upper for keyword in ['ADDITION', 'OPTION', 'EPT', 'ETW', 'EMS']):
                continue

            # Extract tables for this page using Camelot
            tables = self.section_extractor.extract_tables_with_camelot(
                self.pdf_path, page.page_number
            )

            page_additions = self.section_extractor.extract_hinge_additions(
                page_text, tables, page.page_number
            )
            self.hinge_additions.extend(page_additions)

        self.logger.info(f"Found {len(self.hinge_additions)} hinge additions")
        for addition in self.hinge_additions:
            if isinstance(addition.value, dict):
                code = addition.value.get('option_code', 'Unknown')
                price = addition.value.get('adder_value', 0)
                self.logger.debug(f"  {code}: ${price}")

    def _parse_item_tables(self, text: str, tables: List[Any]) -> None:
        """Parse product item tables page by page with performance optimization."""
        self.logger.info("Parsing item tables...")
        self.products = []

        # PERFORMANCE OPTIMIZATION: Only process pages likely to contain product tables
        # Skip pages without product indicators (BB, WT, ECBB patterns or $ prices)
        product_indicators = ['BB', 'WT', 'ECBB', '$', 'Price', 'Model', 'Series']

        pages_to_process = []
        for page in self.document.pages:
            page_text = page.text or ''
            # Quick check: does this page have product-like content?
            if any(indicator in page_text for indicator in product_indicators):
                pages_to_process.append(page)

        self.logger.info(f"Processing {len(pages_to_process)}/{len(self.document.pages)} pages with product indicators")

        for page in pages_to_process:
            page_text = page.text or ''

            # Extract tables for this page using Camelot
            tables = self.section_extractor.extract_tables_with_camelot(
                self.pdf_path, page.page_number
            )

            page_products = self.section_extractor.extract_item_tables(
                page_text, tables, page.page_number
            )
            self.products.extend(page_products)

        self.logger.info(f"Found {len(self.products)} products")

        # Log sample products for verification
        for i, product in enumerate(self.products[:5]):  # First 5 products
            if isinstance(product.value, dict):
                sku = product.value.get('sku', 'Unknown')
                price = product.value.get('base_price', 0)
                series = product.value.get('series', 'Unknown')
                self.logger.debug(f"  {sku} ({series}): ${price}")

    def _build_results(self) -> Dict[str, Any]:
        """Build final parsing results."""
        # Calculate overall confidence
        all_items = []
        if self.effective_date:
            all_items.append(self.effective_date)
        all_items.extend(self.finish_symbols)
        all_items.extend(self.price_rules)
        all_items.extend(self.hinge_additions)
        all_items.extend(self.products)

        # Analyze extraction quality
        analyzer = ProvenanceAnalyzer()
        quality_analysis = analyzer.analyze_extraction_quality(all_items)

        # Build structured results
        results = {
            'manufacturer': 'Hager',
            'source_file': self.pdf_path,
            'parsing_metadata': {
                'parser_version': '2.0',
                'extraction_method': 'enhanced_pipeline',
                'total_pages': len(self.document.pages) if self.document else 0,
                'overall_confidence': quality_analysis['quality_score'],
                'extraction_quality': quality_analysis
            },
            'effective_date': self._serialize_item(self.effective_date),
            'finish_symbols': [self._serialize_item(item) for item in self.finish_symbols],
            'price_rules': [self._serialize_item(item) for item in self.price_rules],
            'hinge_additions': [self._serialize_item(item) for item in self.hinge_additions],
            'products': [self._serialize_item(item) for item in self.products],
            'summary': {
                'total_products': len(self.products),
                'total_finishes': len(self.finish_symbols),
                'total_rules': len(self.price_rules),
                'total_additions': len(self.hinge_additions),
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
            'manufacturer': 'Hager',
            'source_file': self.pdf_path,
            'parsing_metadata': {
                'parser_version': '2.0',
                'extraction_method': 'enhanced_pipeline',
                'status': 'failed',
                'error': error_message
            },
            'effective_date': None,
            'finish_symbols': [],
            'price_rules': [],
            'hinge_additions': [],
            'products': [],
            'summary': {
                'total_products': 0,
                'total_finishes': 0,
                'total_rules': 0,
                'total_additions': 0,
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
        """Validate Hager parsing results."""
        validation = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'accuracy_metrics': {}
        }

        # Check for finish symbols
        finish_count = len(results['finish_symbols'])
        if finish_count == 0:
            validation['warnings'].append("No finish symbols found")
        elif finish_count < 5:
            validation['warnings'].append(f"Low finish count: {finish_count}")

        # Check for products
        product_count = len(results['products'])
        if product_count == 0:
            validation['errors'].append("No products extracted")
            validation['is_valid'] = False
        elif product_count < 10:
            validation['warnings'].append(f"Low product count: {product_count}")

        # Check for price rules
        rule_count = len(results['price_rules'])
        if rule_count == 0:
            validation['warnings'].append("No price rules found")

        # Calculate accuracy metrics
        total_items = product_count + finish_count + rule_count + len(results['hinge_additions'])
        if total_items > 0:
            # Count items with high confidence
            high_confidence_count = 0
            for item_list in [results['products'], results['finish_symbols'],
                            results['price_rules'], results['hinge_additions']]:
                for item in item_list:
                    if item and item.get('confidence', 0) >= 0.8:
                        high_confidence_count += 1

            confidence_rate = high_confidence_count / total_items
            validation['accuracy_metrics']['confidence_rate'] = confidence_rate

            if confidence_rate < 0.7:
                validation['warnings'].append(f"Low confidence rate: {confidence_rate:.1%}")

        # Overall validation
        if len(validation['errors']) == 0 and len(validation['warnings']) <= 3:
            validation['accuracy_metrics']['overall_quality'] = 'good'
        elif len(validation['errors']) == 0:
            validation['accuracy_metrics']['overall_quality'] = 'acceptable'
        else:
            validation['accuracy_metrics']['overall_quality'] = 'poor'

        return validation

    def _get_summary(self) -> str:
        """Get parsing summary for logging."""
        return (f"{len(self.products)} products, "
                f"{len(self.finish_symbols)} finishes, "
                f"{len(self.price_rules)} rules, "
                f"{len(self.hinge_additions)} additions, "
                f"effective_date={'found' if self.effective_date else 'not_found'}")

    def get_provenance_report(self) -> str:
        """Generate detailed provenance report."""
        all_items = []
        if self.effective_date:
            all_items.append(self.effective_date)
        all_items.extend(self.finish_symbols)
        all_items.extend(self.price_rules)
        all_items.extend(self.hinge_additions)
        all_items.extend(self.products)

        analyzer = ProvenanceAnalyzer()
        return analyzer.export_provenance_report(all_items)

    def export_golden_data(self, output_dir: str) -> Dict[str, str]:
        """Export golden test data for validation."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        files_created = {}
        import json

        # Export finish symbols
        if self.finish_symbols:
            finishes_file = output_path / "finish_symbols.json"
            with open(finishes_file, 'w') as f:
                finishes_data = [self._serialize_item(item) for item in self.finish_symbols]
                json.dump(finishes_data, f, indent=2, default=str)
            files_created['finishes'] = str(finishes_file)

        # Export price rules
        if self.price_rules:
            rules_file = output_path / "price_rules.json"
            with open(rules_file, 'w') as f:
                rules_data = [self._serialize_item(item) for item in self.price_rules]
                json.dump(rules_data, f, indent=2, default=str)
            files_created['rules'] = str(rules_file)

        # Export additions
        if self.hinge_additions:
            additions_file = output_path / "hinge_additions.json"
            with open(additions_file, 'w') as f:
                additions_data = [self._serialize_item(item) for item in self.hinge_additions]
                json.dump(additions_data, f, indent=2, default=str)
            files_created['additions'] = str(additions_file)

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
            return 'hager'  # Default for Hager parser

        # Look for Hager indicators
        text_lower = text.lower()
        hager_indicators = [
            'hager', 'hager companies', 'architectural hardware group',
            'hager door hardware', 'architectural hardware'
        ]

        for indicator in hager_indicators:
            if indicator in text_lower:
                return 'hager'

        # Check for SELECT indicators (in case wrong parser was used)
        select_indicators = ['select hinges', 'select hardware']
        for indicator in select_indicators:
            if indicator in text_lower:
                return 'select_hinges'

        # Default to hager for this parser
        return 'hager'