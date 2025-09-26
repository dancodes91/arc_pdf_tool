"""
SELECT Hinges section extraction utilities.
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import date
import pandas as pd

from ..shared.confidence import confidence_scorer, ConfidenceScore
from ..shared.normalization import data_normalizer
from ..shared.provenance import ProvenanceTracker, ParsedItem


logger = logging.getLogger(__name__)


def safe_confidence_score(confidence_obj, default=0.7):
    """Safely extract confidence score from various types."""
    if hasattr(confidence_obj, 'score'):
        return confidence_obj.score
    elif isinstance(confidence_obj, (int, float)):
        return float(confidence_obj)
    else:
        return default


class SelectSectionExtractor:
    """Extract specific sections from SELECT Hinges PDFs."""

    def __init__(self, provenance_tracker: ProvenanceTracker):
        self.tracker = provenance_tracker
        self.logger = logging.getLogger(f"{__class__.__name__}")

        # SELECT-specific patterns
        self.effective_date_patterns = [
            r'EFFECTIVE\s+([A-Z]+\s+\d{1,2},?\s+\d{4})',
            r'PRICES\s+EFFECTIVE\s+([A-Z]+\s+\d{1,2},?\s+\d{4})',
            r'EFFECTIVE\s+DATE:?\s*([A-Z]+\s+\d{1,2},?\s+\d{4})',
        ]

        # Net add option patterns with pricing
        self.net_add_patterns = {
            'CTW': [
                r'CTW-(\d+)\s+\$?(\d+(?:\.\d{2})?)',  # CTW-4 $108
                r'CTW\s*(\d+)\s+\$?(\d+(?:\.\d{2})?)',
            ],
            'EPT': [
                r'EPT\s+prep\s+\$?(\d+(?:\.\d{2})?)',  # EPT prep $41
                r'EPT\s+\$?(\d+(?:\.\d{2})?)',
            ],
            'EMS': [
                r'EMS\s+\$?(\d+(?:\.\d{2})?)',  # EMS $46
            ],
            'ATW': [
                r'ATW-(\d+)\s+\$?(\d+(?:\.\d{2})?)',  # ATW-4/8/12 $176/$188/$204
                r'ATW\s*(\d+)\s+\$?(\d+(?:\.\d{2})?)',
            ],
            'TIPIT': [
                r'TIPIT\s+(\w+)\s+\$?(\d+(?:\.\d{2})?)',  # TIPIT variants
                r'TIP\s*IT\s+(\w+)\s+\$?(\d+(?:\.\d{2})?)',
            ],
            'HT': [
                r'Hospital\s+Tip\s+\$?(\d+(?:\.\d{2})?)',  # Hospital Tip $34
                r'HT\s+\$?(\d+(?:\.\d{2})?)',
            ],
            'FR3': [
                r'FR3\s+\$?(\d+(?:\.\d{2})?)',  # FR3 $18
                r'UL\s+FR3\s+\$?(\d+(?:\.\d{2})?)',
            ]
        }

        # Model table patterns for SL series
        self.model_patterns = {
            'SL11': r'SL\s*11.*?(?=SL\s*\d{2}|$)',
            'SL14': r'SL\s*14.*?(?=SL\s*\d{2}|$)',
            'SL24': r'SL\s*24.*?(?=SL\s*\d{2}|$)',
            'SL41': r'SL\s*41.*?(?=SL\s*\d{2}|$)',
        }

        # Finish code mappings for SELECT
        self.finish_codes = {
            'CL': 'Clear Anodized',
            'BR': 'Bronze Anodized',
            'BK': 'Black Anodized'
        }

    def extract_effective_date(self, text: str) -> Optional[ParsedItem]:
        """Extract effective date from SELECT PDF text."""
        self.tracker.set_context(section="Header", method="text_extraction")

        for pattern in self.effective_date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()

                # Normalize the date
                normalized = data_normalizer.normalize_date(f"EFFECTIVE {date_str}")

                if normalized['value']:
                    return self.tracker.create_parsed_item(
                        value=normalized['value'],
                        data_type="effective_date",
                        raw_text=date_str,
                        confidence=safe_confidence_score(normalized['confidence'], 0.8)
                    )

        self.logger.warning("No effective date found in SELECT PDF")
        return None

    def extract_net_add_options(self, text: str) -> List[ParsedItem]:
        """Extract net add options with pricing from SELECT PDF."""
        self.tracker.set_context(section="Options", method="pattern_matching")
        options = []

        for option_code, patterns in self.net_add_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)

                for match in matches:
                    try:
                        # Extract size/variant and price
                        if len(match.groups()) == 2:
                            size_variant = match.group(1)
                            price_str = match.group(2)
                        else:
                            size_variant = ""
                            price_str = match.group(1)

                        # Normalize price
                        price_normalized = data_normalizer.normalize_price(price_str)

                        if price_normalized['value']:
                            option_data = {
                                'option_code': option_code,
                                'option_name': self._get_option_name(option_code),
                                'size_variant': size_variant,
                                'adder_type': 'net_add',
                                'adder_value': float(price_normalized['value']),
                                'constraints': self._get_option_constraints(option_code),
                                'availability': self._get_option_availability(option_code)
                            }

                            item = self.tracker.create_parsed_item(
                                value=option_data,
                                data_type="net_add_option",
                                raw_text=match.group(0),
                                confidence=safe_confidence_score(price_normalized['confidence'])
                            )
                            options.append(item)

                    except (ValueError, IndexError) as e:
                        self.logger.warning(f"Could not parse option {option_code}: {e}")
                        continue

        self.logger.info(f"Extracted {len(options)} net add options")
        return options

    def extract_model_tables(self, text: str, tables: List[pd.DataFrame]) -> List[ParsedItem]:
        """Extract product model tables (SL11, SL14, SL24, SL41, etc.)."""
        self.tracker.set_context(section="Model Tables", method="table_extraction")
        products = []

        # First try to extract from structured tables
        for table_idx, table in enumerate(tables):
            self.tracker.set_context(table_index=table_idx)

            if self._is_model_table(table):
                table_products = self._extract_products_from_model_table(table, table_idx)
                products.extend(table_products)

        # Also try text-based extraction for specific models
        for model_code, pattern in self.model_patterns.items():
            model_section = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if model_section:
                text_products = self._extract_products_from_text_section(
                    model_section.group(0), model_code
                )
                products.extend(text_products)

        self.logger.info(f"Extracted {len(products)} products from model tables")
        return products

    def _is_model_table(self, table: pd.DataFrame) -> bool:
        """Check if table contains model product data."""
        if table.empty or len(table) < 2:
            return False

        # Convert table to text for analysis
        table_text = ' '.join(table.astype(str).values.flatten()).lower()

        # Look for SELECT-specific indicators
        indicators = [
            'sl11', 'sl14', 'sl24', 'sl41',  # Model codes
            'length', 'duty', 'finish',      # Column headers
            'cl', 'br', 'bk',                # Finish codes
            'light', 'medium', 'heavy',      # Duty ratings
        ]

        return sum(1 for indicator in indicators if indicator in table_text) >= 3

    def _extract_products_from_model_table(self, table: pd.DataFrame, table_idx: int) -> List[ParsedItem]:
        """Extract products from a structured model table."""
        products = []

        # Identify columns
        columns = self._identify_table_columns(table)

        if columns.get('model') is None or columns.get('price') is None:
            self.logger.warning(f"Table {table_idx} missing essential columns: {columns}")
            self.logger.debug(f"Table columns: {list(table.columns)}")
            return products

        for row_idx, row in table.iterrows():
            try:
                # Extract basic product data
                model_code = str(row.iloc[columns['model']]).strip()
                price_str = str(row.iloc[columns['price']]).strip()

                # Skip header/empty rows
                if not model_code or model_code.lower() in ['nan', 'model', 'code']:
                    continue

                # Normalize the data
                sku_normalized = data_normalizer.normalize_sku(model_code, "select_hinges")
                price_normalized = data_normalizer.normalize_price(price_str)

                if sku_normalized['value'] and price_normalized['value']:
                    product_data = {
                        'sku': sku_normalized['value'],
                        'model': self._extract_base_model(sku_normalized['value']),
                        'description': self._build_description(row, columns),
                        'base_price': float(price_normalized['value']),
                        'specifications': self._extract_specifications(row, columns),
                        'finish_code': self._extract_finish_code(row, columns),
                        'is_active': True
                    }

                    # Calculate combined confidence
                    confidence = min(
                        safe_confidence_score(sku_normalized['confidence']),
                        safe_confidence_score(price_normalized['confidence'])
                    )

                    item = self.tracker.create_parsed_item(
                        value=product_data,
                        data_type="product",
                        raw_text=f"{model_code} - {price_str}",
                        row_index=row_idx,
                        confidence=confidence
                    )
                    products.append(item)

            except Exception as e:
                self.logger.warning(f"Error processing row {row_idx}: {e}")
                continue

        return products

    def _extract_products_from_text_section(self, text_section: str, model_code: str) -> List[ParsedItem]:
        """Extract products from a text section for specific model."""
        products = []

        # Look for price patterns in the text
        price_pattern = r'(\w+(?:-\w+)*)\s+\$?(\d+(?:\.\d{2})?)'
        matches = re.finditer(price_pattern, text_section)

        for match in matches:
            variant = match.group(1).strip()
            price_str = match.group(2).strip()

            # Build full SKU
            full_sku = f"{model_code}{variant}" if variant else model_code

            # Normalize
            sku_normalized = data_normalizer.normalize_sku(full_sku, "select_hinges")
            price_normalized = data_normalizer.normalize_price(price_str)

            if sku_normalized['value'] and price_normalized['value']:
                product_data = {
                    'sku': sku_normalized['value'],
                    'model': model_code,
                    'description': f"{model_code} Series {variant}".strip(),
                    'base_price': float(price_normalized['value']),
                    'specifications': {'variant': variant},
                    'is_active': True
                }

                confidence = min(
                    sku_normalized['confidence'].score,
                    price_normalized['confidence'].score
                ) * 0.8  # Lower confidence for text extraction

                item = self.tracker.create_parsed_item(
                    value=product_data,
                    data_type="product",
                    raw_text=match.group(0),
                    confidence=confidence
                )
                products.append(item)

        return products

    def _identify_table_columns(self, table: pd.DataFrame) -> Dict[str, Optional[int]]:
        """Identify column purposes in a model table."""
        columns = {
            'model': None,
            'price': None,
            'description': None,
            'length': None,
            'duty': None,
            'finish': None
        }

        # Check header row for column identification
        for col_idx, col_name in enumerate(table.columns):
            col_text = str(col_name).lower()

            if any(keyword in col_text for keyword in ['model', 'sku', 'part', 'item']):
                columns['model'] = col_idx
            elif any(keyword in col_text for keyword in ['price', 'cost', 'each', 'list']):
                columns['price'] = col_idx
            elif any(keyword in col_text for keyword in ['desc', 'description', 'name']):
                columns['description'] = col_idx
            elif any(keyword in col_text for keyword in ['length', 'size']):
                columns['length'] = col_idx
            elif any(keyword in col_text for keyword in ['duty', 'weight']):
                columns['duty'] = col_idx
            elif any(keyword in col_text for keyword in ['finish', 'color']):
                columns['finish'] = col_idx

        # If using exact column names, get their positions
        if columns['model'] is None and 'Model' in table.columns:
            columns['model'] = list(table.columns).index('Model')
        if columns['price'] is None and 'Price' in table.columns:
            columns['price'] = list(table.columns).index('Price')
        if columns['description'] is None and 'Description' in table.columns:
            columns['description'] = list(table.columns).index('Description')

        # If headers aren't clear, analyze content patterns
        if columns['model'] is None:
            columns['model'] = self._find_column_by_pattern(table, r'^[A-Z]{2}\d+')

        if columns['price'] is None:
            columns['price'] = self._find_column_by_pattern(table, r'\$?\d+\.\d{2}')

        return columns

    def _find_column_by_pattern(self, table: pd.DataFrame, pattern: str) -> Optional[int]:
        """Find column index by content pattern."""
        for col_idx, col in enumerate(table.columns):
            if table[col].dtype == 'object':
                sample_values = table[col].dropna().head(5)
                matches = sum(1 for val in sample_values
                            if re.search(pattern, str(val)))
                if matches >= 2:  # At least 2 matches
                    return col_idx
        return None

    def _extract_base_model(self, sku: str) -> str:
        """Extract base model from SKU (e.g., SL11 from SL11CL24)."""
        match = re.match(r'^(SL\d+)', sku.upper())
        return match.group(1) if match else sku[:4]

    def _build_description(self, row: pd.Series, columns: Dict[str, Optional[int]]) -> str:
        """Build product description from row data."""
        parts = []

        if columns.get('description') is not None:
            desc = str(row.iloc[columns['description']]).strip()
            if desc and desc.lower() != 'nan':
                parts.append(desc)

        if columns.get('length') is not None:
            length = str(row.iloc[columns['length']]).strip()
            if length and length.lower() != 'nan':
                parts.append(f"Length: {length}")

        if columns.get('duty') is not None:
            duty = str(row.iloc[columns['duty']]).strip()
            if duty and duty.lower() != 'nan':
                parts.append(f"Duty: {duty}")

        return " - ".join(parts) if parts else "SELECT Hinge"

    def _extract_specifications(self, row: pd.Series, columns: Dict[str, Optional[int]]) -> Dict[str, Any]:
        """Extract specifications from row data."""
        specs = {}

        if columns.get('length') is not None:
            length = str(row.iloc[columns['length']]).strip()
            if length and length.lower() != 'nan':
                specs['length'] = length

        if columns.get('duty') is not None:
            duty = str(row.iloc[columns['duty']]).strip()
            if duty and duty.lower() != 'nan':
                specs['duty'] = duty

        return specs

    def _extract_finish_code(self, row: pd.Series, columns: Dict[str, Optional[int]]) -> Optional[str]:
        """Extract finish code from row data."""
        if columns.get('finish') is not None:
            finish = str(row.iloc[columns['finish']]).strip().upper()
            if finish in self.finish_codes:
                return finish

        # Try to extract from SKU
        sku = str(row.iloc[columns.get('model', 0)]).strip().upper()
        for code in self.finish_codes:
            if code in sku:
                return code

        return None

    def _get_option_name(self, option_code: str) -> str:
        """Get full name for option code."""
        names = {
            'CTW': 'Continuous Weld',
            'EPT': 'Electroplated Prep',
            'EMS': 'Electromagnetic Shielding',
            'ATW': 'Arc Weld',
            'TIPIT': 'Tip It',
            'HT': 'Hospital Tip',
            'FR3': 'Fire Rating 3 Hour'
        }
        return names.get(option_code, option_code)

    def _get_option_constraints(self, option_code: str) -> Dict[str, Any]:
        """Get constraints for option."""
        constraints = {
            'CTW': {'requires_handing': True},
            'EPT': {'excludes': ['CTW']},
            'EMS': {'excludes': ['CTW', 'EPT']},
            'ATW': {'requires_handing': True},
            'TIPIT': {'excludes': ['HT']},
            'HT': {'excludes': ['TIPIT']},
            'FR3': {}
        }
        return constraints.get(option_code, {})

    def _get_option_availability(self, option_code: str) -> str:
        """Get availability note for option."""
        availability = {
            'CTW': 'Available on most models',
            'EPT': 'Standard electroplated preparation',
            'EMS': 'Electromagnetic shielding option',
            'ATW': 'Arc weld option with handing',
            'TIPIT': 'Tip adjustment mechanism',
            'HT': 'Hospital tip configuration',
            'FR3': 'UL Fire Rated 3-hour option'
        }
        return availability.get(option_code, 'Contact for availability')