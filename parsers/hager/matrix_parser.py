"""
Parser for Hager price matrix format.

Example matrix structure:
    BB1191
    Full Mortise Ball Bearing

    Size            Finish  List
    3-1/2" x 3-1/2" US3     117.96
                    US4     109.86
                    US10    109.86
    4" x 3-1/2"     US3     178.57
                    US4     136.95
                    ...

Generates multiple products from one matrix (model × size × finish).
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal

from ..shared.provenance import ProvenanceTracker, ParsedItem
from ..shared.normalization import data_normalizer

logger = logging.getLogger(__name__)


class HagerMatrixParser:
    """Parse Hager price matrix tables."""

    def __init__(self, provenance_tracker: ProvenanceTracker):
        self.tracker = provenance_tracker

    def extract_matrix_products(self, page_text: str, page_number: int) -> List[ParsedItem]:
        """
        Extract products from a Hager price matrix page.

        Matrix format: One model with multiple size/finish combinations.
        """
        self.tracker.set_context(section="Price Matrix", page_number=page_number)
        products = []

        # Step 1: Find model number (BB####, ECBB####, WT####)
        model_match = re.search(r'\b(BB|ECBB|WT)(\d{4})\b', page_text)
        if not model_match:
            return products

        model = model_match.group(0)  # e.g., "BB1191"

        # Step 2: Extract series/description from text near model
        description = self._extract_description(page_text, model)

        # Step 3: Find all size/finish/price combinations
        # Pattern: Size followed by multiple finish+price rows
        matrix_entries = self._parse_matrix_entries(page_text)

        # Step 4: Generate products
        for entry in matrix_entries:
            size = entry.get('size')
            finish = entry.get('finish')
            price = entry.get('price')

            if not (size and finish and price):
                continue

            # Generate SKU
            size_code = self._normalize_size(size)
            sku = f"{model}-{size_code}-{finish}"

            product_data = {
                'sku': sku,
                'model': model,
                'series': self._get_series_from_model(model),
                'description': f"{description} - {size}",
                'size': size,
                'finish': finish,
                'base_price': float(price),
                'specifications': {
                    'size': size,
                    'finish': finish
                },
                'manufacturer': 'hager',
                'is_active': True
            }

            item = self.tracker.create_parsed_item(
                value=product_data,
                data_type="product",
                raw_text=f"{model} {size} {finish} ${price}",
                confidence=0.9
            )
            products.append(item)

        logger.info(f"Extracted {len(products)} products from matrix for {model}")
        return products

    def _parse_matrix_entries(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse size/finish/price entries from matrix format.

        Format variations (PyMuPDF):
        - Line: "3-1/2\" x 3-1/2\"" (size only)
        - Next line: "US3" (finish only)
        - Next line: "117.96" (price only)

        Format variations (pdfplumber):
        - Line: "US3 117.96" (finish + price)
        - Line: "4\" x 3-1/2\" US3 178.57" (size + finish + price)
        """
        entries = []
        lines = text.split('\n')

        current_size = None
        current_finish = None

        # Enhanced size pattern to handle "3-1/2" or "4" formats
        # Handle regular quotes, curly quotes (U+201D), and no quotes
        size_pattern = r'(\d+(?:-\d+/\d+)?[\"\u201d�]?\s*[xX×]\s*\d+(?:-\d+/\d+)?[\"\u201d�]?)'
        finish_pattern = r'^\s*(US\d+[A-Z]?)\s*$'  # Match finish on its own line
        finish_with_price_pattern = r'\b(US\d+[A-Z]?)\b'  # Match finish with other content
        # Price: digits with 2 decimal places
        price_pattern = r'^(\d+\.\d{2})$'  # Price on its own line
        price_anywhere_pattern = r'(\d+\.\d{2})'  # Price anywhere in line

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 2:
                continue

            # Skip mm measurements
            if 'mm' in line.lower():
                continue

            # Check if line contains a size (update current size)
            size_match = re.search(size_pattern, line)
            if size_match:
                current_size = size_match.group(1).strip()
                logger.debug(f"Found size on line {line_num}: {current_size}")
                continue  # Size lines don't have finish/price

            # Check if line is ONLY a finish code (PyMuPDF format)
            finish_only_match = re.match(finish_pattern, line)
            if finish_only_match and current_size:
                current_finish = finish_only_match.group(1)
                logger.debug(f"Found finish on line {line_num}: {current_finish}")
                continue  # Wait for price on next line

            # Check if line is ONLY a price (PyMuPDF format)
            price_only_match = re.match(price_pattern, line)
            if price_only_match and current_size and current_finish:
                try:
                    price = Decimal(price_only_match.group(1))
                    entries.append({
                        'size': current_size,
                        'finish': current_finish,
                        'price': price
                    })
                    logger.debug(f"Extracted: {current_size} {current_finish} ${price}")
                    current_finish = None  # Reset for next entry
                except Exception as e:
                    logger.warning(f"Failed to parse price from '{price_only_match.group(1)}': {e}")
                continue

            # Check if line has finish code WITH price (pdfplumber format)
            finish_match = re.search(finish_with_price_pattern, line)
            if finish_match and current_size:
                finish = finish_match.group(1)

                # Look for price on same line (after finish code)
                text_after_finish = line[finish_match.end():]
                price_match = re.search(price_anywhere_pattern, text_after_finish)

                if price_match:
                    try:
                        price = Decimal(price_match.group(1))
                        entries.append({
                            'size': current_size,
                            'finish': finish,
                            'price': price
                        })
                        logger.debug(f"Extracted: {current_size} {finish} ${price}")
                    except Exception as e:
                        logger.warning(f"Failed to parse price from '{price_match.group(1)}': {e}")

        logger.info(f"Parsed {len(entries)} matrix entries")
        return entries

    def _extract_description(self, text: str, model: str) -> str:
        """Extract product description from text near model number."""
        # Common Hager product types
        if 'Full Mortise' in text:
            base = "Full Mortise"
        elif 'Half Mortise' in text:
            base = "Half Mortise"
        elif 'Full Surface' in text:
            base = "Full Surface"
        elif 'Half Surface' in text:
            base = "Half Surface"
        else:
            base = "Hinge"

        if 'Ball Bearing' in text:
            base += " Ball Bearing"
        elif 'Electric' in text or 'Concealed' in text:
            base += " Electric"

        if 'Heavy Weight' in text:
            base += " Heavy Weight"
        elif 'Standard Weight' in text:
            base += " Standard Weight"

        return f"{model} {base}"

    def _normalize_size(self, size: str) -> str:
        """Normalize size for SKU generation."""
        # Convert "4-1/2" x 4" to "4.5x4"
        size = size.replace('"', '').strip()
        size = size.replace(' x ', 'x')
        size = size.replace('-1/2', '.5')
        size = size.replace('-3/4', '.75')
        size = size.replace('-1/4', '.25')
        return size

    def _get_series_from_model(self, model: str) -> str:
        """Get series name from model code."""
        if model.startswith('BB'):
            return 'Ball Bearing Hinge'
        elif model.startswith('ECBB'):
            return 'Electric Hinge'
        elif model.startswith('WT'):
            return 'Wide Throw Hinge'
        return 'Standard Hinge'

    def is_matrix_page(self, page_text: str) -> bool:
        """
        Detect if page contains a price matrix.

        Indicators:
        - Has model code
        - Has multiple finish codes (3+)
        - Has prices
        - NO "PART NUMBER" column header (matrices don't use part numbers)
        """
        has_model = bool(re.search(r'\b(BB|ECBB|WT)\d{4}\b', page_text))
        finish_pattern = r'\b(US\d+[A-Z]?)\b'
        finish_count = len(re.findall(finish_pattern, page_text))
        has_prices = bool(re.search(r'\d+\.\d{2}', page_text))
        has_part_number = 'PART NUMBER' in page_text.upper()

        is_matrix = has_model and finish_count >= 3 and has_prices and not has_part_number

        if is_matrix:
            logger.debug(f"Detected matrix page: model={has_model}, finishes={finish_count}, prices={has_prices}")

        return is_matrix
