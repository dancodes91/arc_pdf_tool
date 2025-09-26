"""
Hager section extraction utilities for finish symbols, rules, and items.
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
import pandas as pd

from ..shared.confidence import confidence_scorer, ConfidenceScore
from ..shared.normalization import data_normalizer
from ..shared.provenance import ProvenanceTracker, ParsedItem


logger = logging.getLogger(__name__)


class HagerSectionExtractor:
    """Extract specific sections from Hager PDFs."""

    def __init__(self, provenance_tracker: ProvenanceTracker):
        self.tracker = provenance_tracker
        self.logger = logging.getLogger(f"{__class__.__name__}")

        # Hager finish symbols patterns
        self.finish_symbol_patterns = [
            r'(US\d+[A-Z]?)\s+([^\n\r]+?)\s+(\$?[\d.]+)',  # US10B Description $price
            r'Symbol:\s*(US\d+[A-Z]?)\s*-?\s*([^\n\r$]+?)\s*(\$?[\d.]+)',
            r'(US\d+[A-Z]?)\s*-\s*([^$\n\r]+?)\s*(\$?[\d.]+)',
        ]

        # Price mapping rules (e.g., "US10B use US10A price")
        self.price_rule_patterns = [
            r'(US\d+[A-Z]?)\s+(?:use|uses?)\s+(US\d+[A-Z]?)\s+price',
            r'(US\d+[A-Z]?)\s*=\s*(US\d+[A-Z]?)\s+pricing',
            r'For\s+(US\d+[A-Z]?)\s+use\s+(US\d+[A-Z]?)',
        ]

        # Hinge addition patterns (EPT, ETW, EMS, etc.)
        self.addition_patterns = {
            'EPT': [
                r'EPT\s+(?:preparation|prep)\s+add\s+(\$?[\d.]+)',
                r'Electroplated\s+(?:preparation|prep).*?(\$?[\d.]+)',
            ],
            'ETW': [
                r'ETW\s+(?:electric|thru-wire)\s+add\s+(\$?[\d.]+)',
                r'Electric\s+thru.*?wire.*?(\$?[\d.]+)',
            ],
            'EMS': [
                r'EMS\s+(?:electromagnetic|shield)\s+add\s+(\$?[\d.]+)',
                r'Electromagnetic\s+shielding.*?(\$?[\d.]+)',
            ],
            'HWS': [
                r'HWS\s+(?:heavy|weight)\s+add\s+(\$?[\d.]+)',
                r'Heavy\s+weight\s+stainless.*?(\$?[\d.]+)',
            ],
            'CWP': [
                r'CWP\s+(?:continuous|weld)\s+add\s+(\$?[\d.]+)',
                r'Continuous\s+weld\s+prep.*?(\$?[\d.]+)',
            ]
        }

        # Hager product patterns (series and models)
        self.product_patterns = {
            'BB1100': r'BB\s*1100.*?(?=BB\s*\d{4}|$)',
            'BB1279': r'BB\s*1279.*?(?=BB\s*\d{4}|$)',
            'BB1290': r'BB\s*1290.*?(?=BB\s*\d{4}|$)',
            'ECBB1100': r'ECBB\s*1100.*?(?=(?:EC)?BB\s*\d{4}|$)',
            'WT1279': r'WT\s*1279.*?(?=WT\s*\d{4}|$)',
        }

        # Standard Hager finish mappings
        self.hager_finishes = {
            'US3': {'bhma': 'US3', 'name': 'Satin Chrome', 'standard': True},
            'US4': {'bhma': 'US4', 'name': 'Bright Chrome', 'standard': True},
            'US10B': {'bhma': 'US10B', 'name': 'Satin Bronze', 'standard': True},
            'US15': {'bhma': 'US15', 'name': 'Satin Brass', 'standard': True},
            'US26D': {'bhma': 'US26D', 'name': 'Oil Rubbed Bronze', 'standard': True},
            'US32D': {'bhma': 'US32D', 'name': 'Antique Brass', 'standard': True},
        }

    def extract_finish_symbols(self, text: str) -> List[ParsedItem]:
        """Extract finish symbols table with BHMA codes and pricing."""
        self.tracker.set_context(section="Finish Symbols", method="pattern_matching")
        finishes = []

        # Look for finish symbols section
        finish_section = self._extract_finish_section(text)

        for pattern in self.finish_symbol_patterns:
            matches = re.finditer(pattern, finish_section, re.IGNORECASE)

            for match in matches:
                try:
                    finish_code = match.group(1).strip().upper()
                    description = match.group(2).strip()
                    price_str = match.group(3).strip()

                    # Normalize price
                    price_normalized = data_normalizer.normalize_price(price_str)
                    finish_normalized = data_normalizer.normalize_finish_code(finish_code)

                    if price_normalized['value'] and finish_normalized['code']:
                        finish_data = {
                            'code': finish_normalized['code'],
                            'bhma_code': finish_normalized['bhma_code'],
                            'name': finish_normalized['name'] or description,
                            'description': description,
                            'base_price': float(price_normalized['value']),
                            'is_standard': finish_code in self.hager_finishes,
                            'manufacturer': 'hager'
                        }

                        item = self.tracker.create_parsed_item(
                            value=finish_data,
                            data_type="finish",
                            raw_text=match.group(0),
                            confidence=min(price_normalized['confidence'].score, 0.9)
                        )
                        finishes.append(item)

                except (ValueError, IndexError) as e:
                    self.logger.warning(f"Could not parse finish symbol: {e}")

        self.logger.info(f"Extracted {len(finishes)} finish symbols")
        return finishes

    def extract_price_rules(self, text: str) -> List[ParsedItem]:
        """Extract pricing rules (e.g., US10B uses US10A price)."""
        self.tracker.set_context(section="Price Rules", method="pattern_matching")
        rules = []

        for pattern in self.price_rule_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)

            for match in matches:
                try:
                    source_finish = match.group(1).strip().upper()
                    target_finish = match.group(2).strip().upper()

                    rule_data = {
                        'rule_type': 'price_mapping',
                        'source_finish': source_finish,
                        'target_finish': target_finish,
                        'description': f"{source_finish} uses {target_finish} pricing",
                        'manufacturer': 'hager'
                    }

                    item = self.tracker.create_parsed_item(
                        value=rule_data,
                        data_type="price_rule",
                        raw_text=match.group(0),
                        confidence=0.95  # High confidence for explicit rules
                    )
                    rules.append(item)

                except (IndexError, AttributeError) as e:
                    self.logger.warning(f"Could not parse price rule: {e}")

        self.logger.info(f"Extracted {len(rules)} price rules")
        return rules

    def extract_hinge_additions(self, text: str) -> List[ParsedItem]:
        """Extract hinge addition options (EPT, ETW, EMS, etc.)."""
        self.tracker.set_context(section="Hinge Additions", method="pattern_matching")
        additions = []

        # Look for additions section
        additions_section = self._extract_additions_section(text)

        for addition_code, patterns in self.addition_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, additions_section, re.IGNORECASE)

                for match in matches:
                    try:
                        price_str = match.group(1).strip()
                        price_normalized = data_normalizer.normalize_price(price_str)

                        if price_normalized['value']:
                            addition_data = {
                                'option_code': addition_code,
                                'option_name': self._get_addition_name(addition_code),
                                'adder_type': 'net_add',
                                'adder_value': float(price_normalized['value']),
                                'description': self._get_addition_description(addition_code),
                                'manufacturer': 'hager',
                                'constraints': self._get_addition_constraints(addition_code)
                            }

                            item = self.tracker.create_parsed_item(
                                value=addition_data,
                                data_type="hinge_addition",
                                raw_text=match.group(0),
                                confidence=price_normalized['confidence'].score
                            )
                            additions.append(item)

                    except (ValueError, IndexError) as e:
                        self.logger.warning(f"Could not parse addition {addition_code}: {e}")

        self.logger.info(f"Extracted {len(additions)} hinge additions")
        return additions

    def extract_item_tables(self, text: str, tables: List[pd.DataFrame]) -> List[ParsedItem]:
        """Extract product items from tables and text."""
        self.tracker.set_context(section="Item Tables", method="table_extraction")
        products = []

        # Extract from structured tables
        for table_idx, table in enumerate(tables):
            self.tracker.set_context(table_index=table_idx)

            if self._is_hager_product_table(table):
                table_products = self._extract_products_from_table(table, table_idx)
                products.extend(table_products)

        # Extract from text patterns for specific series
        for series_code, pattern in self.product_patterns.items():
            series_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if series_match:
                series_products = self._extract_products_from_series_text(
                    series_match.group(0), series_code
                )
                products.extend(series_products)

        self.logger.info(f"Extracted {len(products)} Hager products")
        return products

    def _extract_finish_section(self, text: str) -> str:
        """Extract finish symbols section from text."""
        section_patterns = [
            r'finish\s+symbols?.*?(?=(?:hinge|addition|preparation|price|$))',
            r'standard\s+finishes?.*?(?=(?:hinge|addition|preparation|$))',
            r'bhma\s+finish.*?(?=(?:hinge|addition|preparation|$))',
        ]

        for pattern in section_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(0)

        return text  # Fallback to full text

    def _extract_additions_section(self, text: str) -> str:
        """Extract hinge additions section from text."""
        section_patterns = [
            r'(?:hinge\s+)?(?:additions?|modifications?).*?(?=(?:finish|price|standard|$))',
            r'(?:net\s+)?add\s+options?.*?(?=(?:finish|price|standard|$))',
            r'ept.*?ems.*?(?=(?:finish|price|standard|$))',
        ]

        for pattern in section_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(0)

        return text

    def _is_hager_product_table(self, table: pd.DataFrame) -> bool:
        """Check if table contains Hager product data."""
        if table.empty or len(table) < 2:
            return False

        table_text = ' '.join(table.astype(str).values.flatten()).lower()

        # Look for Hager-specific indicators
        indicators = [
            'bb1100', 'bb1279', 'bb1290',  # Ball bearing hinges
            'ecbb1100',                     # Electric hinge
            'wt1279',                       # Wide throw
            'us3', 'us4', 'us10b',         # Finish codes
            'hager', 'heavy', 'standard',  # General terms
        ]

        return sum(1 for indicator in indicators if indicator in table_text) >= 2

    def _extract_products_from_table(self, table: pd.DataFrame, table_idx: int) -> List[ParsedItem]:
        """Extract products from Hager table."""
        products = []

        # Identify columns
        columns = self._identify_hager_table_columns(table)

        if columns.get('model') is None or columns.get('price') is None:
            self.logger.warning(f"Hager table {table_idx} missing essential columns: {columns}")
            return products

        for row_idx, row in table.iterrows():
            try:
                model_code = str(row.iloc[columns['model']]).strip()
                price_str = str(row.iloc[columns['price']]).strip()

                # Skip header/empty rows
                if not model_code or model_code.lower() in ['nan', 'model', 'part']:
                    continue

                # Normalize data
                sku_normalized = data_normalizer.normalize_sku(model_code, "hager")
                price_normalized = data_normalizer.normalize_price(price_str)

                if sku_normalized['value'] and price_normalized['value']:
                    product_data = {
                        'sku': sku_normalized['value'],
                        'model': self._extract_hager_base_model(sku_normalized['value']),
                        'description': self._build_hager_description(row, columns),
                        'base_price': float(price_normalized['value']),
                        'series': self._extract_series_from_sku(sku_normalized['value']),
                        'specifications': self._extract_hager_specifications(row, columns),
                        'manufacturer': 'hager',
                        'is_active': True
                    }

                    confidence = min(
                        sku_normalized['confidence'].score,
                        price_normalized['confidence'].score
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
                self.logger.warning(f"Error processing Hager row {row_idx}: {e}")

        return products

    def _extract_products_from_series_text(self, text_section: str, series_code: str) -> List[ParsedItem]:
        """Extract products from text section for specific series."""
        products = []

        # Pattern for product entries in text
        product_pattern = r'(\w+(?:-\w+)*)\s+([^\$\n]+?)\s+(\$?[\d.]+)'
        matches = re.finditer(product_pattern, text_section)

        for match in matches:
            try:
                variant = match.group(1).strip()
                description = match.group(2).strip()
                price_str = match.group(3).strip()

                # Build full SKU
                full_sku = f"{series_code}{variant}" if variant else series_code

                # Normalize
                sku_normalized = data_normalizer.normalize_sku(full_sku, "hager")
                price_normalized = data_normalizer.normalize_price(price_str)

                if sku_normalized['value'] and price_normalized['value']:
                    product_data = {
                        'sku': sku_normalized['value'],
                        'model': series_code,
                        'description': f"{series_code} {description}".strip(),
                        'base_price': float(price_normalized['value']),
                        'series': series_code,
                        'specifications': {'variant': variant},
                        'manufacturer': 'hager',
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

            except Exception as e:
                self.logger.warning(f"Error parsing series text product: {e}")

        return products

    def _identify_hager_table_columns(self, table: pd.DataFrame) -> Dict[str, Optional[int]]:
        """Identify column purposes in Hager table."""
        columns = {
            'model': None,
            'price': None,
            'description': None,
            'series': None,
            'duty': None,
            'size': None
        }

        # Check headers
        for col_idx, col_name in enumerate(table.columns):
            col_text = str(col_name).lower()

            if any(keyword in col_text for keyword in ['model', 'part', 'item', 'sku']):
                columns['model'] = col_idx
            elif any(keyword in col_text for keyword in ['price', 'list', 'each', 'cost']):
                columns['price'] = col_idx
            elif any(keyword in col_text for keyword in ['desc', 'description', 'name']):
                columns['description'] = col_idx
            elif any(keyword in col_text for keyword in ['series', 'type']):
                columns['series'] = col_idx
            elif any(keyword in col_text for keyword in ['duty', 'weight', 'grade']):
                columns['duty'] = col_idx
            elif any(keyword in col_text for keyword in ['size', 'dimension']):
                columns['size'] = col_idx

        # Try exact matches
        if 'Model' in table.columns:
            columns['model'] = list(table.columns).index('Model')
        if 'Price' in table.columns:
            columns['price'] = list(table.columns).index('Price')

        return columns

    def _extract_hager_base_model(self, sku: str) -> str:
        """Extract base model from Hager SKU."""
        # Common Hager patterns
        patterns = [
            r'^(BB\d{4})',    # BB1100, BB1279
            r'^(ECBB\d{4})',  # ECBB1100
            r'^(WT\d{4})',    # WT1279
            r'^([A-Z]{2,4}\d+)', # General pattern
        ]

        for pattern in patterns:
            match = re.match(pattern, sku.upper())
            if match:
                return match.group(1)

        return sku[:6]  # Fallback

    def _extract_series_from_sku(self, sku: str) -> str:
        """Extract series from Hager SKU."""
        sku_upper = sku.upper()

        if sku_upper.startswith('BB'):
            return 'Ball Bearing Hinge'
        elif sku_upper.startswith('ECBB'):
            return 'Electric Hinge'
        elif sku_upper.startswith('WT'):
            return 'Wide Throw Hinge'
        else:
            return 'Standard Hinge'

    def _build_hager_description(self, row: pd.Series, columns: Dict[str, Optional[int]]) -> str:
        """Build Hager product description."""
        parts = []

        if columns.get('description') is not None:
            desc = str(row.iloc[columns['description']]).strip()
            if desc and desc.lower() != 'nan':
                parts.append(desc)

        if columns.get('duty') is not None:
            duty = str(row.iloc[columns['duty']]).strip()
            if duty and duty.lower() != 'nan':
                parts.append(f"Duty: {duty}")

        if columns.get('size') is not None:
            size = str(row.iloc[columns['size']]).strip()
            if size and size.lower() != 'nan':
                parts.append(f"Size: {size}")

        return " - ".join(parts) if parts else "Hager Hardware"

    def _extract_hager_specifications(self, row: pd.Series, columns: Dict[str, Optional[int]]) -> Dict[str, Any]:
        """Extract Hager specifications."""
        specs = {}

        if columns.get('duty') is not None:
            duty = str(row.iloc[columns['duty']]).strip()
            if duty and duty.lower() != 'nan':
                specs['duty'] = duty

        if columns.get('size') is not None:
            size = str(row.iloc[columns['size']]).strip()
            if size and size.lower() != 'nan':
                specs['size'] = size

        return specs

    def _get_addition_name(self, code: str) -> str:
        """Get full name for addition code."""
        names = {
            'EPT': 'Electroplated Preparation',
            'ETW': 'Electric Thru-Wire',
            'EMS': 'Electromagnetic Shielding',
            'HWS': 'Heavy Weight Stainless',
            'CWP': 'Continuous Weld Preparation'
        }
        return names.get(code, code)

    def _get_addition_description(self, code: str) -> str:
        """Get description for addition code."""
        descriptions = {
            'EPT': 'Electroplated finish preparation',
            'ETW': 'Electric through-wire capability',
            'EMS': 'Electromagnetic shielding option',
            'HWS': 'Heavy weight stainless steel option',
            'CWP': 'Continuous weld preparation'
        }
        return descriptions.get(code, f"{code} option")

    def _get_addition_constraints(self, code: str) -> Dict[str, Any]:
        """Get constraints for addition code."""
        constraints = {
            'EPT': {'compatible_finishes': ['US3', 'US4', 'US15']},
            'ETW': {'requires_power': True},
            'EMS': {'excludes': ['ETW']},
            'HWS': {'weight_rating': 'heavy_duty'},
            'CWP': {'preparation_required': True}
        }
        return constraints.get(code, {})