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


def safe_confidence_score(confidence_obj, default=0.7):
    """Safely extract confidence score from various types."""
    if hasattr(confidence_obj, 'score'):
        return confidence_obj.score
    elif isinstance(confidence_obj, (int, float)):
        return float(confidence_obj)
    else:
        return default


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

        # Price mapping rules (e.g., "US10B use US10A price", "20% above US10A or US10B price")
        self.price_rule_patterns = [
            r'(US\d+[A-Z]?)\s+(?:use|uses?)\s+(US\d+[A-Z]?)\s+price',
            r'(US\d+[A-Z]?)\s*=\s*(US\d+[A-Z]?)\s+pricing',
            r'For\s+(US\d+[A-Z]?)\s+use\s+(US\d+[A-Z]?)',
            # Percentage-based rules
            r'(\d+)%\s+above\s+(US\d+[A-Z]?)\s+(?:or\s+(US\d+[A-Z]?)\s+)?price',
            r'(\d+)%\s+(?:additional|extra|add)\s+(?:to\s+)?(US\d+[A-Z]?)',
            r'(US\d+[A-Z]?)\s+(?:plus|add)\s+(\d+)%',
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

    @staticmethod
    def extract_tables_with_camelot(pdf_path: str, page_number: int, flavor: str = "lattice"):
        """Extract tables from specific page using Camelot."""
        import camelot
        import gc
        page_str = str(page_number)
        try:
            tables = camelot.read_pdf(pdf_path, pages=page_str, flavor=flavor)
            result = [t.df for t in tables] if tables.n else []
            # Force cleanup to prevent Windows file locking on temp files
            del tables
            gc.collect()
            return result
        except Exception as e:
            logger.warning(f"Camelot extraction failed for page {page_number}: {e}")
            return []

    def extract_finish_symbols(self, page_text: str, tables: list, page_number: int) -> List[ParsedItem]:
        """Extract finish symbols table with BHMA codes and pricing using Camelot DataFrame."""
        self.tracker.set_context(section="Finish Symbols", page_number=page_number)

        results: List[ParsedItem] = []
        for table_idx, table in enumerate(tables):
            # Clean up the Camelot df
            df = table.replace("", pd.NA).dropna(how="all")
            if df.empty:
                continue

            # Check if this table contains finish symbols data
            header_text = " ".join(str(cell) for cell in df.iloc[0]).upper()
            table_text = str(df).upper()

            # Check for finish-related keywords in table or header
            has_finish_keywords = any(keyword in header_text or keyword in table_text
                                    for keyword in ["FINISH", "BHMA", "US3", "US4", "US10", "US26", "US", "2C", "3A"])

            if not has_finish_keywords:
                self.logger.debug(f"Table {table_idx} skipped - no finish keywords found")
                continue

            self.logger.debug(f"Processing table {table_idx} - found finish keywords")

            # Process all rows looking for finish codes
            for row_idx, row in df.iterrows():
                for col_idx, cell in enumerate(row):
                    cell_str = str(cell).strip()

                    # Look for finish codes - patterns like US3, US4, US10A, US26D, 2C, 3A, etc.
                    if cell_str and len(cell_str) <= 10:  # Reasonable length for finish codes
                        # Check if it looks like a finish code
                        is_finish_code = (
                            cell_str.startswith('US') or
                            (cell_str.isalnum() and any(c.isdigit() for c in cell_str)) or
                            cell_str in ['2C', '3', '3A', '4', '5', '10', '10A', '10B', '15', '26', '26D', '32D']
                        )

                        if is_finish_code:
                            self.logger.debug(f"Found finish code: {cell_str} at [{row_idx},{col_idx}]")

                            # Try to find description and pricing in adjacent cells
                            desc = ""
                            pricing_text = ""

                            # Look in adjacent columns for description and pricing
                            for offset in [1, 2, 3]:
                                if col_idx + offset < len(row):
                                    next_cell = str(row.iloc[col_idx + offset]).strip()
                                    if next_cell and next_cell.lower() not in ['nan', 'none']:
                                        if any(c in next_cell for c in ['$', '%', 'price', 'above']):
                                            pricing_text = next_cell
                                        elif not desc and len(next_cell) > 3:  # Likely description
                                            desc = next_cell

                            # Extract price if possible
                            base_price = self._extract_price_from_text(pricing_text) if pricing_text else 0.0

                            # Create finish symbol entry
                            finish_data = {
                                'finish_code': cell_str,
                                'description': desc or f"{cell_str} finish",
                                'base_price': base_price,
                                'pricing_text': pricing_text,
                                'manufacturer': 'hager',
                            }

                            finish_item = self.tracker.create_parsed_item(
                                value=finish_data,
                                data_type="finish_symbol",
                                confidence=0.7,  # Lower confidence for extracted codes
                                extraction_method='camelot_table_scan',
                                page_number=page_number,
                                table_index=table_idx,
                                source_section='finish_symbols'
                            )

                            results.append(finish_item)
                            self.logger.debug(f"Added finish symbol: {cell_str}")

        return results

    def extract_price_rules(self, page_text: str, tables: list, page_number: int) -> List[ParsedItem]:
        """Extract pricing rules (e.g., US10B uses US10A price) using both tables and text patterns."""
        self.tracker.set_context(section="Price Rules", page_number=page_number)
        rules = []

        # Process Camelot tables first for structured rules
        for table_idx, table in enumerate(tables):
            df = table.replace("", pd.NA).dropna(how="all")
            if df.empty:
                continue

            # Check if this table contains price rules or mappings
            header_text = " ".join(str(cell) for cell in df.iloc[0]).upper()
            if not any(keyword in header_text for keyword in ["RULE", "MAPPING", "USE", "PRICE"]):
                continue

            # Process table rows for rules
            for _, row in df.iterrows():
                row_text = " ".join(str(cell) for cell in row if str(cell).strip()).upper()

                # Look for "USE" patterns in table data
                for pattern in self.price_rule_patterns:
                    match = re.search(pattern, row_text, re.IGNORECASE)
                    if match:
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

                            rule_item = self.tracker.create_parsed_item(
                                value=rule_data,
                                data_type="price_rule",
                                confidence=0.9,
                                extraction_method='camelot_table',
                                page_number=page_number,
                                table_index=table_idx,
                                source_section='price_rules'
                            )
                            rules.append(rule_item)
                        except (IndexError, AttributeError) as e:
                            self.logger.warning(f"Could not parse table price rule: {e}")

        # Fallback to text pattern matching
        for pattern in self.price_rule_patterns:
            matches = re.finditer(pattern, page_text, re.IGNORECASE)

            for match in matches:
                try:
                    groups = match.groups()
                    rule_data = {'rule_type': 'price_mapping', 'manufacturer': 'hager'}

                    # Handle different pattern types
                    if '% above' in match.group(0):
                        # Percentage rule like "20% above US10A or US10B price"
                        percentage = groups[0]
                        base_finish = groups[1]
                        alt_finish = groups[2] if len(groups) > 2 and groups[2] else None

                        rule_data.update({
                            'rule_type': 'percentage_markup',
                            'percentage': int(percentage),
                            'base_finish': base_finish,
                            'alternative_finish': alt_finish,
                            'description': f"{percentage}% above {base_finish}" + (f" or {alt_finish}" if alt_finish else "") + " price"
                        })
                    elif len(groups) >= 2:
                        # Standard mapping rule like "US10B use US10A price"
                        source_finish = groups[0].strip().upper()
                        target_finish = groups[1].strip().upper()

                        rule_data.update({
                            'source_finish': source_finish,
                            'target_finish': target_finish,
                            'description': f"{source_finish} uses {target_finish} pricing"
                        })

                    rule_item = self.tracker.create_parsed_item(
                        value=rule_data,
                        data_type="price_rule",
                        confidence=0.95,
                        extraction_method='regex_pattern',
                        page_number=page_number,
                        source_section='price_rules'
                    )
                    rules.append(rule_item)

                except (IndexError, AttributeError, ValueError) as e:
                    self.logger.warning(f"Could not parse price rule: {e}")

        self.logger.info(f"Extracted {len(rules)} price rules")
        return rules

    def extract_hinge_additions(self, page_text: str, tables: list, page_number: int) -> List[ParsedItem]:
        """Extract hinge addition options (EPT, ETW, EMS, etc.) using Camelot DataFrame."""
        self.tracker.set_context(section="Hinge Additions", page_number=page_number)
        additions = []

        # Process Camelot tables first for structured data
        for table_idx, table in enumerate(tables):
            df = table.replace("", pd.NA).dropna(how="all")
            if df.empty:
                continue

            # Check if this table contains addition options
            header_text = " ".join(str(cell) for cell in df.iloc[0]).upper()
            if not any(keyword in header_text for keyword in ["ADDITION", "OPTION", "EPT", "ETW", "EMS"]):
                continue

            # Set up column mapping based on table structure
            if len(df.columns) >= 3:
                df.columns = ["code", "description", "price"] + [f"col_{i}" for i in range(3, len(df.columns))]
            else:
                continue

            # Skip header row and process data rows
            df = df.iloc[1:].dropna(subset=["code"])

            for _, row in df.iterrows():
                code = str(row["code"]).strip().upper()
                desc = str(row.get("description", "")).strip()
                price_text = str(row.get("price", "")).strip()

                if not code or code.lower() in ['nan', 'none']:
                    continue

                # Extract price value
                base_price = self._extract_price_from_text(price_text)

                # Create addition entry
                addition_data = {
                    'option_code': code,
                    'option_name': desc or self._get_addition_name(code),
                    'adder_type': 'net_add',
                    'adder_value': base_price,
                    'description': desc,
                    'manufacturer': 'hager',
                    'constraints': self._get_addition_constraints(code),
                    'pricing_text': price_text
                }

                addition_item = self.tracker.create_parsed_item(
                    value=addition_data,
                    data_type="hinge_addition",
                    confidence=0.85,
                    extraction_method='camelot_table',
                    page_number=page_number,
                    table_index=table_idx,
                    source_section='hinge_additions'
                )

                additions.append(addition_item)

        # Fallback to pattern matching for text-based additions
        for addition_code, patterns in self.addition_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, page_text, re.IGNORECASE)

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
                                'constraints': self._get_addition_constraints(addition_code),
                                'pricing_text': price_str
                            }

                            item = self.tracker.create_parsed_item(
                                value=addition_data,
                                data_type="hinge_addition",
                                confidence=price_normalized['confidence'],
                                extraction_method='regex_pattern',
                                page_number=page_number,
                                source_section='hinge_additions'
                            )
                            additions.append(item)

                    except (ValueError, IndexError) as e:
                        self.logger.warning(f"Could not parse addition {addition_code}: {e}")

        self.logger.info(f"Extracted {len(additions)} hinge additions")
        return additions

    def extract_item_tables(self, page_text: str, tables: list, page_number: int) -> List[ParsedItem]:
        """Extract product items from tables using Camelot DataFrame parsing."""
        self.tracker.set_context(section="Item Tables", page_number=page_number)
        products = []

        # Process Camelot tables for structured data
        for table_idx, table in enumerate(tables):
            df = table.replace("", pd.NA).dropna(how="all")
            if df.empty:
                continue

            # Check if this is a product table
            if self._is_hager_product_table(df):
                table_products = self._extract_products_from_table(df, table_idx, page_number)
                products.extend(table_products)

        # Fallback to text patterns for specific series
        for series_code, pattern in self.product_patterns.items():
            series_match = re.search(pattern, page_text, re.IGNORECASE | re.DOTALL)
            if series_match:
                series_products = self._extract_products_from_series_text(
                    series_match.group(0), series_code, page_number
                )
                products.extend(series_products)

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

    def _extract_products_from_table(self, table: pd.DataFrame, table_idx: int, page_number: int) -> List[ParsedItem]:
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
                self.logger.warning(f"Error processing Hager row {row_idx}: {e}")

        return products

    def _extract_products_from_series_text(self, text_section: str, series_code: str, page_number: int) -> List[ParsedItem]:
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
                        safe_confidence_score(sku_normalized['confidence']),
                        safe_confidence_score(price_normalized['confidence'])
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

    def _extract_price_from_text(self, price_text: str) -> float:
        """Extract numeric price value from text."""
        if not price_text or price_text.lower() in ['nan', 'none', '']:
            return 0.0

        try:
            # Use the shared normalization utility
            price_normalized = data_normalizer.normalize_price(price_text)
            return float(price_normalized.get('value', 0))
        except (ValueError, TypeError):
            return 0.0

    # Backward compatibility methods for tests
    def extract_finish_symbols_legacy(self, text: str) -> List[ParsedItem]:
        """Legacy method for backward compatibility with tests - falls back to regex patterns."""
        self.tracker.set_context(section="Finish Symbols", method="legacy_text_extraction")
        results = []

        # Use text-based pattern matching for tests
        for pattern in self.finish_symbol_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)

            for match in matches:
                try:
                    code = match.group(1).strip().upper()
                    description = match.group(2).strip()
                    price_str = match.group(3).strip()

                    price_normalized = data_normalizer.normalize_price(price_str)

                    finish_data = {
                        'code': code,
                        'name': description,
                        'base_price': price_normalized.get('value', 0),
                        'manufacturer': 'hager'
                    }

                    item = self.tracker.create_parsed_item(
                        value=finish_data,
                        data_type="finish_symbol",
                        raw_text=match.group(0),
                        confidence=safe_confidence_score(price_normalized.get('confidence', 0.8))
                    )
                    results.append(item)

                except (IndexError, AttributeError) as e:
                    self.logger.warning(f"Could not parse legacy finish symbol: {e}")

        return results

    def extract_price_rules_legacy(self, text: str) -> List[ParsedItem]:
        """Legacy method for backward compatibility with tests - falls back to regex patterns."""
        self.tracker.set_context(section="Price Rules", method="legacy_text_extraction")
        results = []

        # Use text-based pattern matching for tests
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
                        confidence=0.95
                    )
                    results.append(item)

                except (IndexError, AttributeError) as e:
                    self.logger.warning(f"Could not parse legacy price rule: {e}")

        return results

    def extract_hinge_additions_legacy(self, text: str) -> List[ParsedItem]:
        """Legacy method for backward compatibility with tests - falls back to regex patterns."""
        self.tracker.set_context(section="Hinge Additions", method="legacy_text_extraction")
        results = []

        # Use text-based pattern matching for tests
        for addition_code, patterns in self.addition_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)

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
                                confidence=safe_confidence_score(price_normalized['confidence'])
                            )
                            results.append(item)

                    except (ValueError, IndexError) as e:
                        self.logger.warning(f"Could not parse legacy addition {addition_code}: {e}")

        return results

    def extract_item_tables_legacy(self, text: str, tables: List = None) -> List[ParsedItem]:
        """
        Legacy method for backward compatibility with tests ONLY.

        WARNING: This method uses a dummy page number (1) and should NOT be used
        in production code. Use extract_item_tables() with proper page context instead.
        """
        if tables is None:
            tables = []
        # Use dummy page number for test compatibility only
        return self.extract_item_tables(text, tables, 1)