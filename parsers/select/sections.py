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

        # Finish code mappings for SELECT
        self.finish_codes = {
            'CL': {'code': 'CL', 'label': 'Clear Anodized', 'bhma': None},
            'BR': {'code': 'BR', 'label': 'Bronze Anodized', 'bhma': None},
            'BK': {'code': 'BK', 'label': 'Black Anodized', 'bhma': None},
        }

        # SELECT-specific patterns
        self.effective_date_patterns = [
            r'EFFECTIVE\s+([A-Z]+\s+\d{1,2},?\s+\d{4})',
            r'PRICES\s+EFFECTIVE\s+([A-Z]+\s+\d{1,2},?\s+\d{4})',
            r'EFFECTIVE\s+DATE:?\s*([A-Z]+\s+\d{1,2},?\s+\d{4})',
        ]

        # Net add option patterns with pricing - updated to match actual PDF format
        self.net_add_patterns = {
            'CTW-4': [r'\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+CTW-4'],
            'CTW-5': [r'\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+CTW-5'],
            'CTW-8': [r'\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+CTW-8'],
            'CTW-10': [r'\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+CTW-10'],
            'CTW-12': [r'\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+CTW-12'],
            'EPT': [r'\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+prep'],
            'EMS': [r'\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+EMS'],
            'ATW-4': [r'\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+ATW-4'],
            'ATW-8': [r'\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+ATW-8'],
            'ATW-12': [r'\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+ATW-12'],
            'CMG': [r'\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+CMG'],
            'AP': [r'\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+prep'],
            'RP': [r'\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+prep'],
        }

        # Model table patterns for SL series
        self.model_patterns = {
            'SL11': r'SL\s*11.*?(?=SL\s*\d{2}|$)',
            'SL14': r'SL\s*14.*?(?=SL\s*\d{2}|$)',
            'SL24': r'SL\s*24.*?(?=SL\s*\d{2}|$)',
            'SL41': r'SL\s*41.*?(?=SL\s*\d{2}|$)',
        }

    @staticmethod
    def extract_tables_with_camelot(pdf_path: str, page_number: int, flavor: str = "lattice"):
        """Extract tables from specific page using Camelot."""
        import camelot
        page_str = str(page_number)
        try:
            tables = camelot.read_pdf(pdf_path, pages=page_str, flavor=flavor)
            return [t.df for t in tables] if tables.n else []
        except Exception as e:
            logger.warning(f"Camelot extraction failed for page {page_number}: {e}")
            return []

    def extract_finish_symbols(self, text: str) -> List[ParsedItem]:
        """Extract finish symbols/abbreviations from SELECT PDF."""
        self.tracker.set_context(section="Finishes", method="text_extraction")
        finishes = []

        # Look for finish abbreviations in text
        # Pattern: "Clear [CL], Dark Bronze [BR] or Black [BK]"
        finish_pattern = r'(Clear|Dark\s+Bronze|Black)\s*\[([A-Z]{2})\]'
        matches = re.finditer(finish_pattern, text, re.IGNORECASE)

        for match in matches:
            finish_name = match.group(1).strip()
            finish_code = match.group(2).upper()

            if finish_code in self.finish_codes:
                finish_data = {
                    'code': finish_code,
                    'label': self.finish_codes[finish_code]['label'],
                    'bhma': self.finish_codes[finish_code]['bhma'],
                    'manufacturer': 'SELECT'
                }

                item = self.tracker.create_parsed_item(
                    value=finish_data,
                    data_type="finish_symbol",
                    raw_text=match.group(0),
                    confidence=0.9
                )
                finishes.append(item)

        self.logger.info(f"Extracted {len(finishes)} finish symbols")
        return finishes

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

    def extract_model_tables(self, text: str, tables: List[pd.DataFrame], page_number: int = None) -> List[ParsedItem]:
        """Extract product model tables using table normalization and melting for finish columns."""
        self.tracker.set_context(section="Model Tables", method="table_extraction", page_number=page_number)
        products = []

        for table_idx, table in enumerate(tables):
            if isinstance(table, pd.DataFrame):
                df = table
            else:
                df = pd.DataFrame(table)

            # Clean up the table
            df = df.replace("", pd.NA).dropna(how="all")
            if df.empty or len(df) < 2:
                continue

            self.tracker.set_context(table_index=table_idx, page_number=page_number)

            # Try structured extraction first (for proper tables with headers)
            structured_products = self._extract_products_structured(df, table_idx, page_number)
            if structured_products:
                products.extend(structured_products)
                continue

            # Fallback to pattern-based extraction for complex layouts
            pattern_products = self._extract_products_from_table_simple(df, table_idx, page_number)
            products.extend(pattern_products)

        self.logger.info(f"Extracted {len(products)} products from model tables")
        return products

    def _extract_products_structured(self, df: pd.DataFrame, table_idx: int, page_number: int = None) -> List[ParsedItem]:
        """Extract products using comprehensive table melting - extracts ALL row×finish combinations."""
        products = []

        try:
            # Clean header row
            header = [str(cell).strip() for cell in df.iloc[0]]
            df.columns = header
            df = df.iloc[1:]  # Remove header row

            # Drop completely empty rows
            df = df.dropna(how='all')

            if df.empty:
                return []

            # Identify all columns
            header_upper = [h.upper() for h in header]

            # Find model column (first column with model codes)
            model_col = None
            for idx, col in enumerate(df.columns):
                # Check if column contains SL## patterns
                sample = df[col].dropna().head(10)
                if any(re.match(r'SL\s*\d{2}', str(val), re.IGNORECASE) for val in sample):
                    model_col = col
                    break

            if not model_col:
                return []

            # Look for finish columns (CL, BR, BK) - these contain prices
            finish_cols = []
            for col in header:
                col_upper = col.upper().strip()
                if col_upper in ['CL', 'BR', 'BK']:
                    finish_cols.append(col)

            if not finish_cols:
                return []

            # Identify descriptor columns (keep these as id_vars)
            id_vars = [model_col]
            desc_col = None
            length_col = None
            duty_col = None

            for col in header:
                col_upper = col.upper()
                if col in finish_cols or col == model_col:
                    continue
                if 'DESC' in col_upper or 'NAME' in col_upper:
                    desc_col = col
                    id_vars.append(col)
                elif 'LENGTH' in col_upper or 'SIZE' in col_upper or '"' in col_upper:
                    length_col = col
                    id_vars.append(col)
                elif 'DUTY' in col_upper or 'WEIGHT' in col_upper or 'TYPE' in col_upper:
                    duty_col = col
                    id_vars.append(col)

            # Melt finish columns to create one row per (model × finish) combination
            long_df = df.melt(
                id_vars=id_vars,
                value_vars=finish_cols,
                var_name="Finish",
                value_name="Price"
            )

            # Keep only rows with prices
            long_df = long_df.dropna(subset=["Price"])
            long_df = long_df[long_df["Price"].astype(str).str.strip() != '']
            long_df = long_df[long_df["Price"].astype(str).str.upper() != 'NAN']

            # Extract products from melted table
            for _, row in long_df.iterrows():
                model = str(row[model_col]).strip()
                finish = str(row["Finish"]).strip().upper()
                price_str = str(row["Price"]).strip()

                # Skip invalid models
                if not model or model.lower() in ['nan', 'none', 'model', '']:
                    continue

                # Extract clean model code (remove any suffixes)
                model_match = re.match(r'(SL\s*\d{2})', model, re.IGNORECASE)
                if not model_match:
                    continue

                base_model = model_match.group(1).replace(' ', '')

                # Build comprehensive SKU with all attributes
                sku_parts = [base_model, finish]
                specs = {}

                if length_col and pd.notna(row.get(length_col)):
                    length_val = str(row[length_col]).strip()
                    if length_val and length_val.upper() not in ['NAN', 'NONE', '']:
                        # Clean length value
                        length_clean = re.sub(r'[^\d\-/]', '', length_val)
                        if length_clean:
                            sku_parts.append(length_clean)
                            specs['length'] = length_val

                if duty_col and pd.notna(row.get(duty_col)):
                    duty_val = str(row[duty_col]).strip()
                    if duty_val and duty_val.upper() not in ['NAN', 'NONE', '']:
                        duty_clean = re.sub(r'[^\w\d]', '', duty_val)
                        if duty_clean:
                            sku_parts.append(duty_clean)
                            specs['duty'] = duty_val

                sku = '-'.join(sku_parts).replace(' ', '')

                # Normalize price
                price_normalized = data_normalizer.normalize_price(price_str)
                if not price_normalized['value']:
                    continue

                price_val = float(price_normalized['value'])

                # Sanity check price
                if price_val < 1 or price_val > 10000:
                    continue

                # Build description
                desc_parts = [base_model, finish]
                if desc_col and pd.notna(row.get(desc_col)):
                    desc_parts.append(str(row[desc_col]).strip())
                elif specs:
                    if 'length' in specs:
                        desc_parts.append(specs['length'])
                    if 'duty' in specs:
                        desc_parts.append(specs['duty'])

                product_data = {
                    'sku': sku,
                    'model': base_model,
                    'series': base_model[:2] if len(base_model) >= 2 else base_model,
                    'description': ' '.join(desc_parts),
                    'base_price': price_val,
                    'finish_code': finish if finish in ['CL', 'BR', 'BK'] else None,
                    'specifications': specs,
                    'is_active': True,
                    'manufacturer': 'SELECT'
                }

                item = self.tracker.create_parsed_item(
                    value=product_data,
                    data_type="product",
                    raw_text=f"{model} {finish} ${price_str}",
                    row_index=None,
                    confidence=safe_confidence_score(price_normalized['confidence'], 0.9),
                    page_number=page_number,
                    table_index=table_idx
                )
                products.append(item)

        except Exception as e:
            self.logger.debug(f"Structured extraction failed on table {table_idx}: {e}")
            return []

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

    def _extract_products_from_table_simple(self, df: pd.DataFrame, table_idx: int, page_number: int = None) -> List[ParsedItem]:
        """Simple robust extraction from SELECT tables - handles complex table formats with embedded SKUs."""
        products = []
        seen_entries = set()  # Track (sku, price) tuples to allow same SKU with different prices

        # Iterate through all rows and columns
        for row_idx, row in df.iterrows():
            # Skip first row (usually header)
            if row_idx == 0:
                continue

            # Scan all cells in this row for SKU patterns
            for col_idx in range(len(row)):
                cell_value = str(row.iloc[col_idx]).strip()

                if cell_value.lower() in ['nan', 'none', '', '-']:
                    continue

                # Look for SELECT SKU pattern: SL## optionally followed by finish code and variant
                # Examples: "SL21 CL HD300", "SL11 BR HD600", "SL14CL", or just "SL21"
                sku_match = re.search(r'(SL\s*\d{2})(?:\s+([A-Z]{2}))?(?:\s+(HD\d+|LD\d+|LL|\d+"?))?', cell_value, re.IGNORECASE)

                if not sku_match:
                    continue

                base_model = sku_match.group(1).replace(' ', '')  # SL21
                finish_code = sku_match.group(2).upper() if sku_match.group(2) else None  # CL, BR, BK or None
                variant = sku_match.group(3).upper() if sku_match.group(3) else ""  # HD300, etc

                # If finish code missing, check adjacent cells
                if not finish_code:
                    for offset in [-1, 1]:
                        adj_col = col_idx + offset
                        if 0 <= adj_col < len(row):
                            adj_text = str(row.iloc[adj_col]).strip().upper()
                            if adj_text in ['CL', 'BR', 'BK']:
                                finish_code = adj_text
                                break
                    # If still no finish, try to infer from column header
                    if not finish_code and col_idx < len(df.columns):
                        header_text = str(df.iloc[0, col_idx]).strip().upper()
                        if any(f in header_text for f in ['CL', 'BR', 'BK']):
                            finish_code = next((f for f in ['CL', 'BR', 'BK'] if f in header_text), None)
                    # Last resort: use position-based code
                    if not finish_code:
                        finish_code = f"V{col_idx}"  # Variant by column position

                # Build full SKU with position to make unique
                sku = f"{base_model}-{finish_code}-{variant}".replace(' ', '') if variant else f"{base_model}-{finish_code}"

                # Now find price in the same cell or adjacent cells
                price_val = None

                # First try same cell
                price_matches = re.findall(r'(\d+\.?\d{0,2})', cell_value)
                for price_str in price_matches:
                    try:
                        pval = float(price_str)
                        # Relaxed range: allow lower prices (20-40 range common in SELECT)
                        if 10 <= pval <= 5000:
                            price_val = pval
                            break
                    except:
                        continue

                # If no price in same cell, check adjacent cells
                if price_val is None:
                    for offset in [1, -1, 2, -2]:  # Check more adjacent cells
                        adj_col = col_idx + offset
                        if 0 <= adj_col < len(row):
                            adj_cell = str(row.iloc[adj_col]).strip()
                            price_matches = re.findall(r'(\d+\.?\d{0,2})', adj_cell.replace(',', ''))
                            for price_str in price_matches:
                                try:
                                    pval = float(price_str)
                                    # Relaxed range here too
                                    if 10 <= pval <= 5000:
                                        price_val = pval
                                        break
                                except:
                                    continue
                            if price_val:
                                break

                # If still no price, skip this entry (was creating too many 0-price entries)
                if price_val is None or price_val == 0:
                    continue

                # Check for duplicates using (sku, price) tuple - allows same SKU with different prices
                entry_key = (sku, price_val)
                if entry_key in seen_entries:
                    continue
                seen_entries.add(entry_key)

                # Clean up finish code for display
                display_finish = finish_code if finish_code in ['CL', 'BR', 'BK'] else None

                # Create product
                product_data = {
                    'sku': sku,
                    'model': base_model,
                    'series': base_model[:2] if len(base_model) >= 2 else base_model,
                    'description': f"{base_model} {finish_code} {variant}".strip(),
                    'base_price': price_val,
                    'finish_code': display_finish,
                    'specifications': {'duty': variant, 'column': col_idx} if variant else {'column': col_idx},
                    'is_active': True,
                    'manufacturer': 'SELECT'
                }

                item = self.tracker.create_parsed_item(
                    value=product_data,
                    data_type="product",
                    raw_text=cell_value[:100],
                    row_index=row_idx,
                    confidence=0.9,  # Higher confidence since we have both SKU and price
                    page_number=page_number,
                    table_index=table_idx
                )
                products.append(item)

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