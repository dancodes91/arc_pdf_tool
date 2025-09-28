"""
Page classifier for PDF parsing.

Classifies page types (title/TOC/data, option lists, finish symbols, footnotes)
and routes to the best extraction method based on content analysis.
"""
import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class PageType(Enum):
    """Page classification types."""
    TITLE_PAGE = "title_page"
    TABLE_OF_CONTENTS = "table_of_contents"
    DATA_TABLE = "data_table"
    OPTION_LIST = "option_list"
    FINISH_SYMBOLS = "finish_symbols"
    PRICE_RULES = "price_rules"
    FOOTNOTES = "footnotes"
    MIXED_CONTENT = "mixed_content"
    UNKNOWN = "unknown"


class ExtractionMethod(Enum):
    """Available extraction methods."""
    PDFPLUMBER = "pdfplumber"
    CAMELOT_LATTICE = "camelot_lattice"
    CAMELOT_STREAM = "camelot_stream"
    OCR_FALLBACK = "ocr_fallback"
    TEXT_ONLY = "text_only"


@dataclass
class PageAnalysis:
    """Analysis results for a page."""
    page_number: int
    page_type: PageType
    confidence: float
    recommended_method: ExtractionMethod
    features: Dict[str, Any]
    text_length: int
    table_count: int
    has_tables: bool
    needs_ocr: bool


class PageClassifier:
    """
    Classifies PDF pages and recommends extraction methods.

    Uses regex patterns, content density, and layout features to determine
    the best approach for extracting data from each page.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_patterns()

        # OCR trigger thresholds
        self.min_text_length = 50  # Below this, consider OCR
        self.min_table_confidence = 0.3  # Below this, consider OCR

    def _setup_patterns(self):
        """Setup regex patterns for page classification."""

        # Title page patterns
        self.title_patterns = [
            r'(?i)price\s+book',
            r'(?i)catalog',
            r'(?i)effective\s+\d{1,2}[/\-]\d{1,2}[/\-]\d{4}',
            r'(?i)door\s+hardware',
            r'(?i)hager|select',
        ]

        # Table of contents patterns
        self.toc_patterns = [
            r'(?i)table\s+of\s+contents',
            r'(?i)contents',
            r'(?i)index',
            r'\.{3,}',  # Dot leaders
            r'\d+\s*$',  # Page numbers at end of line
        ]

        # Finish symbols patterns
        self.finish_patterns = [
            r'(?i)finish\s+symbols?',
            r'(?i)architectural\s+finish',
            r'(?i)bhma\s+(?:symbol|code)',
            r'US\d+[A-Z]?',  # BHMA codes
            r'(?i)satin\s+(?:chrome|brass|bronze)',
            r'(?i)oil\s+rubbed\s+bronze',
        ]

        # Option list patterns
        self.option_patterns = [
            r'(?i)(?:CTW|EPT|EMS|TIPIT|HT|FR3)',  # Common option codes
            r'(?i)preparation\s+add',
            r'(?i)electromagnetic\s+shielding',
            r'(?i)electric\s+thru[\-\s]wire',
            r'(?i)heavy\s+weight',
            r'add\s+\$\d+',  # "add $25.00"
        ]

        # Price rule patterns
        self.price_rule_patterns = [
            r'(?i)pricing\s+rules?',
            r'(?i)use\s+price\s+of',
            r'\d+%\s+above',
            r'(?i)same\s+as',
            r'(?i)see\s+price\s+for',
        ]

        # Data table indicators
        self.data_table_patterns = [
            r'\$\d+\.\d{2}',  # Price patterns
            r'(?i)model\s*(?:number|#)?',
            r'(?i)description',
            r'(?i)series',
            r'(?i)size',
        ]

    def classify_page(self, page_text: str, page_number: int,
                     tables: Optional[List] = None,
                     page_features: Optional[Dict] = None) -> PageAnalysis:
        """
        Classify a page and recommend extraction method.

        Args:
            page_text: Extracted text from the page
            page_number: Page number
            tables: List of detected tables (if any)
            page_features: Additional page features (bbox, etc.)

        Returns:
            PageAnalysis with classification and recommendations
        """
        if not page_text:
            page_text = ""

        text_length = len(page_text.strip())
        table_count = len(tables) if tables else 0
        has_tables = table_count > 0

        # Extract features for classification
        features = self._extract_features(page_text, page_features or {})

        # Classify page type
        page_type, type_confidence = self._classify_page_type(page_text, features)

        # Determine if OCR is needed
        needs_ocr = self._needs_ocr(text_length, table_count, features)

        # Recommend extraction method
        recommended_method = self._recommend_extraction_method(
            page_type, has_tables, needs_ocr, features
        )

        return PageAnalysis(
            page_number=page_number,
            page_type=page_type,
            confidence=type_confidence,
            recommended_method=recommended_method,
            features=features,
            text_length=text_length,
            table_count=table_count,
            has_tables=has_tables,
            needs_ocr=needs_ocr
        )

    def _extract_features(self, text: str, page_features: Dict) -> Dict[str, Any]:
        """Extract features for classification."""
        if not text:
            return {
                'line_count': 0,
                'word_count': 0,
                'density': 0.0,
                'has_prices': False,
                'has_codes': False,
                'has_tables_markers': False,
                'pattern_scores': {}
            }

        lines = text.split('\n')
        words = text.split()

        features = {
            'line_count': len(lines),
            'word_count': len(words),
            'density': len(words) / max(len(lines), 1),
            'has_prices': bool(re.search(r'\$\d+\.\d{2}', text)),
            'has_codes': bool(re.search(r'(?:US\d+[A-Z]?|CTW|EPT|EMS)', text)),
            'has_table_markers': bool(re.search(r'(?i)model|description|price|series', text)),
            'pattern_scores': self._calculate_pattern_scores(text)
        }

        # Add page-level features if available
        features.update(page_features)

        return features

    def _calculate_pattern_scores(self, text: str) -> Dict[str, float]:
        """Calculate pattern match scores for different page types."""
        scores = {}

        pattern_sets = {
            'title': self.title_patterns,
            'toc': self.toc_patterns,
            'finish': self.finish_patterns,
            'options': self.option_patterns,
            'price_rules': self.price_rule_patterns,
            'data_table': self.data_table_patterns,
        }

        for category, patterns in pattern_sets.items():
            matches = 0
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    matches += 1
            scores[category] = matches / len(patterns) if patterns else 0.0

        return scores

    def _classify_page_type(self, text: str, features: Dict) -> Tuple[PageType, float]:
        """Classify the page type based on patterns and features."""
        pattern_scores = features.get('pattern_scores', {})

        # Priority-based classification
        if pattern_scores.get('title', 0) > 0.3:
            return PageType.TITLE_PAGE, pattern_scores['title']

        if pattern_scores.get('toc', 0) > 0.3:
            return PageType.TABLE_OF_CONTENTS, pattern_scores['toc']

        if pattern_scores.get('finish', 0) > 0.4:
            return PageType.FINISH_SYMBOLS, pattern_scores['finish']

        if pattern_scores.get('price_rules', 0) > 0.3:
            return PageType.PRICE_RULES, pattern_scores['price_rules']

        if pattern_scores.get('options', 0) > 0.4:
            return PageType.OPTION_LIST, pattern_scores['options']

        # Data table classification based on multiple indicators
        data_indicators = [
            pattern_scores.get('data_table', 0) > 0.3,
            features.get('has_prices', False),
            features.get('has_table_markers', False),
            features.get('density', 0) > 3.0,  # Dense content
        ]

        if sum(data_indicators) >= 2:
            confidence = sum([
                pattern_scores.get('data_table', 0),
                0.2 if features.get('has_prices') else 0,
                0.2 if features.get('has_table_markers') else 0,
                min(features.get('density', 0) / 10.0, 0.3)
            ])
            return PageType.DATA_TABLE, min(confidence, 1.0)

        # Mixed content if multiple patterns found
        total_score = sum(pattern_scores.values())
        if total_score > 0.5:
            return PageType.MIXED_CONTENT, total_score / len(pattern_scores)

        return PageType.UNKNOWN, 0.1

    def _needs_ocr(self, text_length: int, table_count: int, features: Dict) -> bool:
        """Determine if OCR fallback is needed."""
        # OCR if very little text extracted
        if text_length < self.min_text_length:
            return True

        # OCR if no tables found but should have them
        if (features.get('has_table_markers', False) and
            table_count == 0 and
            features.get('density', 0) < 2.0):
            return True

        return False

    def _recommend_extraction_method(self, page_type: PageType, has_tables: bool,
                                   needs_ocr: bool, features: Dict) -> ExtractionMethod:
        """Recommend the best extraction method for this page."""

        if needs_ocr:
            return ExtractionMethod.OCR_FALLBACK

        # Method selection based on page type and content
        if page_type in [PageType.TITLE_PAGE, PageType.TABLE_OF_CONTENTS]:
            return ExtractionMethod.TEXT_ONLY

        if page_type == PageType.FINISH_SYMBOLS and has_tables:
            # Finish symbols often have structured tables
            return ExtractionMethod.CAMELOT_LATTICE

        if page_type == PageType.DATA_TABLE and has_tables:
            # Choose lattice vs stream based on table structure hints
            if features.get('density', 0) > 5.0:
                return ExtractionMethod.CAMELOT_LATTICE  # Dense, likely gridded
            else:
                return ExtractionMethod.CAMELOT_STREAM   # Sparse, likely unstructured

        if page_type in [PageType.OPTION_LIST, PageType.PRICE_RULES]:
            # Option lists and rules are often text-based
            if has_tables:
                return ExtractionMethod.PDFPLUMBER  # Hybrid approach
            else:
                return ExtractionMethod.TEXT_ONLY

        # Default fallback
        if has_tables:
            return ExtractionMethod.PDFPLUMBER
        else:
            return ExtractionMethod.TEXT_ONLY

    def analyze_document(self, pages_data: List[Dict]) -> List[PageAnalysis]:
        """
        Analyze an entire document and classify all pages.

        Args:
            pages_data: List of dicts with 'text', 'page_number', 'tables', etc.

        Returns:
            List of PageAnalysis for each page
        """
        analyses = []

        for page_data in pages_data:
            analysis = self.classify_page(
                page_text=page_data.get('text', ''),
                page_number=page_data.get('page_number', 0),
                tables=page_data.get('tables', []),
                page_features=page_data.get('features', {})
            )
            analyses.append(analysis)

        self.logger.info(f"Analyzed {len(analyses)} pages")

        # Log summary statistics
        type_counts = {}
        method_counts = {}
        ocr_count = 0

        for analysis in analyses:
            type_counts[analysis.page_type.value] = type_counts.get(analysis.page_type.value, 0) + 1
            method_counts[analysis.recommended_method.value] = method_counts.get(analysis.recommended_method.value, 0) + 1
            if analysis.needs_ocr:
                ocr_count += 1

        self.logger.info(f"Page types: {type_counts}")
        self.logger.info(f"Recommended methods: {method_counts}")
        self.logger.info(f"Pages needing OCR: {ocr_count}")

        return analyses


def route_extraction(page_analysis: PageAnalysis, page_data: Dict) -> Dict[str, Any]:
    """
    Route page extraction based on classification.

    Args:
        page_analysis: Classification results
        page_data: Page content and metadata

    Returns:
        Extraction configuration dict
    """
    config = {
        'method': page_analysis.recommended_method.value,
        'page_type': page_analysis.page_type.value,
        'confidence_threshold': 0.7,  # Default
        'ocr_fallback': page_analysis.needs_ocr,
    }

    # Method-specific configuration
    if page_analysis.recommended_method == ExtractionMethod.CAMELOT_LATTICE:
        config.update({
            'camelot_flavor': 'lattice',
            'table_areas': None,  # Auto-detect
            'edge_tol': 50,
        })
    elif page_analysis.recommended_method == ExtractionMethod.CAMELOT_STREAM:
        config.update({
            'camelot_flavor': 'stream',
            'row_tol': 2,
            'col_tol': 0,
        })
    elif page_analysis.recommended_method == ExtractionMethod.PDFPLUMBER:
        config.update({
            'extract_tables': page_analysis.has_tables,
            'table_settings': {'vertical_strategy': 'lines', 'horizontal_strategy': 'lines'},
        })
    elif page_analysis.recommended_method == ExtractionMethod.OCR_FALLBACK:
        config.update({
            'ocr_engine': 'tesseract',
            'ocr_config': '--psm 6',  # Assume uniform block of text
            'preprocess': True,
        })

    # Page type specific adjustments
    if page_analysis.page_type == PageType.FINISH_SYMBOLS:
        config['confidence_threshold'] = 0.6  # Lower threshold for finish symbols
    elif page_analysis.page_type == PageType.DATA_TABLE:
        config['confidence_threshold'] = 0.8  # Higher threshold for product data

    return config