"""
SELECT Hinges section extraction utilities.
"""

import re
import logging
from typing import List, Dict, Any, Optional
import pandas as pd

from ..shared.normalization import data_normalizer
from ..shared.provenance import ProvenanceTracker, ParsedItem


logger = logging.getLogger(__name__)


def safe_confidence_score(confidence_obj, default=0.7):
    """Safely extract confidence score from various types."""
    if hasattr(confidence_obj, "score"):
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
            "CL": {"code": "CL", "label": "Clear Anodized", "bhma": None},
            "BR": {"code": "BR", "label": "Bronze Anodized", "bhma": None},
            "BK": {"code": "BK", "label": "Black Anodized", "bhma": None},
        }

        # SELECT-specific patterns
        self.effective_date_patterns = [
            r"EFFECTIVE\s+([A-Z]+\s+\d{1,2},?\s+\d{4})",
            r"PRICES\s+EFFECTIVE\s+([A-Z]+\s+\d{1,2},?\s+\d{4})",
            r"EFFECTIVE\s+DATE:?\s*([A-Z]+\s+\d{1,2},?\s+\d{4})",
        ]

        # Net add option patterns with pricing - updated to match actual PDF format
        self.net_add_patterns = {
            "CTW-4": [r"\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+CTW-4"],
            "CTW-5": [r"\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+CTW-5"],
            "CTW-8": [r"\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+CTW-8"],
            "CTW-10": [r"\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+CTW-10"],
            "CTW-12": [r"\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+CTW-12"],
            "EPT": [r"\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+prep"],
            "EMS": [r"\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+EMS"],
            "ATW-4": [r"\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+ATW-4"],
            "ATW-8": [r"\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+ATW-8"],
            "ATW-12": [r"\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+ATW-12"],
            "CMG": [r"\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+CMG"],
            "AP": [r"\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+prep"],
            "RP": [r"\$(\d+(?:\.\d{2})?)\s+net\s+add\s+per\s+prep"],
        }

        # Model table patterns for SL series
        self.model_patterns = {
            "SL11": r"SL\s*11.*?(?=SL\s*\d{2}|$)",
            "SL14": r"SL\s*14.*?(?=SL\s*\d{2}|$)",
            "SL24": r"SL\s*24.*?(?=SL\s*\d{2}|$)",
            "SL41": r"SL\s*41.*?(?=SL\s*\d{2}|$)",
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

    def extract_finish_symbols(self, text: str) -> List[ParsedItem]:
        """Extract finish symbols/abbreviations from SELECT PDF."""
        self.tracker.set_context(section="Finishes", method="text_extraction")
        finishes = []

        # Look for finish abbreviations in text
        # Pattern: "Clear [CL], Dark Bronze [BR] or Black [BK]"
        finish_pattern = r"(Clear|Dark\s+Bronze|Black)\s*\[([A-Z]{2})\]"
        matches = re.finditer(finish_pattern, text, re.IGNORECASE)

        for match in matches:
            match.group(1).strip()
            finish_code = match.group(2).upper()

            if finish_code in self.finish_codes:
                finish_data = {
                    "code": finish_code,
                    "label": self.finish_codes[finish_code]["label"],
                    "bhma": self.finish_codes[finish_code]["bhma"],
                    "manufacturer": "SELECT",
                }

                item = self.tracker.create_parsed_item(
                    value=finish_data,
                    data_type="finish_symbol",
                    raw_text=match.group(0),
                    confidence=0.9,
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

                if normalized["value"]:
                    return self.tracker.create_parsed_item(
                        value=normalized["value"],
                        data_type="effective_date",
                        raw_text=date_str,
                        confidence=safe_confidence_score(normalized["confidence"], 0.8),
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

                        if price_normalized["value"]:
                            option_data = {
                                "option_code": option_code,
                                "option_name": self._get_option_name(option_code),
                                "size_variant": size_variant,
                                "adder_type": "net_add",
                                "adder_value": float(price_normalized["value"]),
                                "constraints": self._get_option_constraints(option_code),
                                "availability": self._get_option_availability(option_code),
                            }

                            item = self.tracker.create_parsed_item(
                                value=option_data,
                                data_type="net_add_option",
                                raw_text=match.group(0),
                                confidence=safe_confidence_score(price_normalized["confidence"]),
                            )
                            options.append(item)

                    except (ValueError, IndexError) as e:
                        self.logger.warning(f"Could not parse option {option_code}: {e}")
                        continue

        self.logger.info(f"Extracted {len(options)} net add options")
        return options

    def extract_model_tables(
        self, text: str, tables: List[pd.DataFrame], page_number: int = None
    ) -> List[ParsedItem]:
        """Extract product model tables using table normalization and melting for finish columns."""
        self.tracker.set_context(
            section="Model Tables", method="table_extraction", page_number=page_number
        )
        products = []
        seen_skus = set()  # Track SKUs across all extraction methods

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
                for p in structured_products:
                    sku = p.value.get("sku")
                    if sku and sku not in seen_skus:
                        products.append(p)
                        seen_skus.add(sku)
                # Structured extraction succeeded - skip fallback methods for this table
                continue

            # If structured didn't work, try pattern-based extraction for complex layouts
            pattern_products = self._extract_products_from_table_simple(
                df, table_idx, page_number
            )
            if pattern_products:
                for p in pattern_products:
                    sku = p.value.get("sku")
                    if sku and sku not in seen_skus:
                        products.append(p)
                        seen_skus.add(sku)
                # Pattern extraction succeeded - skip grid extraction for this table
                continue

            # If both structured and pattern failed, try aggressive grid extraction as last resort
            # This extracts every valid price cell and infers model/finish from context
            grid_products = self._extract_all_price_cells(
                df, table_idx, page_number, existing_skus=seen_skus
            )
            if grid_products:
                for p in grid_products:
                    sku = p.value.get("sku")
                    if sku and sku not in seen_skus:
                        products.append(p)
                        seen_skus.add(sku)

        # Post-processing: Filter out invalid products for SELECT pricing guides
        # Valid products MUST have length specifications (79", 83", 95", 120", etc.)
        valid_products = []
        for p in products:
            sku = p.value.get("sku", "")
            specs = p.value.get("specifications", {})
            price = p.value.get("base_price", 0)

            # Check if product has length specification
            has_length = False
            if specs and specs.get("length"):
                has_length = True
            # Also check SKU for length pattern (ends with digits like -79, -83, -95, -120)
            elif re.search(r'-\d{2,3}$', sku):
                has_length = True

            # Skip products without length specs (invalid for SELECT pricing guides)
            if not has_length:
                self.logger.debug(f"Skipping product without length: {sku}")
                continue

            # Additional price validation (SELECT prices are typically $50-$5000)
            if price < 50 or price > 10000:
                self.logger.debug(f"Skipping product with invalid price: {sku} ${price}")
                continue

            valid_products.append(p)

        self.logger.info(f"Extracted {len(valid_products)} valid products from model tables ({len(products) - len(valid_products)} filtered)")
        return valid_products

    def _extract_products_structured(
        self, df: pd.DataFrame, table_idx: int, page_number: int = None
    ) -> List[ParsedItem]:
        """Extract products from SELECT tables (handles both newline-separated and column-separated).

        Two table structures supported:
        1. Newline-separated (standalone SELECT PDF):
           - Header: "Model #\n79"\n83"/85"\n95"\n120"" (all in column 0)
           - Prices: "193\n193" (newlines in cells)

        2. Column-separated (Hager PDF):
           - Header: ['Model #', '79"', '83"/85"', '95"', '120"'] (proper columns)
           - Prices: Each in its own column
        """
        products = []

        try:
            # Get header row and data
            header_row_idx = 0
            header_detected = False
            # Detect the row that contains the actual column headers (look for "Model #" row)
            for idx in range(len(df)):
                row_values = [str(cell).strip() for cell in df.iloc[idx]]
                combined = " ".join(row_values).lower()
                if "model #" in combined and re.search(r'\d+\s*["\']', combined):
                    header_row_idx = idx
                    header_detected = True
                    break

            header = [str(cell).strip() for cell in df.iloc[header_row_idx]]
            data_rows = df.iloc[header_row_idx + 1 :]

            # Drop completely empty rows
            data_rows = data_rows.dropna(how="all")

            if data_rows.empty:
                return []

            # STEP 1: Detect table structure and extract lengths
            # Check if we have column-separated structure (Hager) or newline-separated (standalone)

            # Try column-separated first (check if header[1:] contains length patterns)
            column_lengths = []
            for col_idx, col_header in enumerate(header[1:], start=1):
                # Look for length patterns like 79", 83", 83"/85", 95", 120"
                match = re.search(r'(\d+)\s*["\']', str(col_header))
                if match:
                    column_lengths.append((col_idx, match.group(1)))

            if column_lengths:
                # COLUMN-SEPARATED structure (Hager PDF)
                structure_type = "column-separated"
                lengths = [length for _, length in column_lengths]
                length_columns = {length: col_idx for col_idx, length in column_lengths}
                self.logger.debug(f"Detected COLUMN-SEPARATED structure with lengths: {lengths}")
            else:
                # NEWLINE-SEPARATED structure (standalone SELECT PDF)
                structure_type = "newline-separated"
                first_col_header = str(header[0])

                # Extract all length values from first column header
                lengths = []
                for line in first_col_header.split('\n'):
                    line = line.strip()
                    matches = re.findall(r'(\d+)\s*["\']?\s*(?:/\s*(\d+)\s*["\']?)?', line)
                    for match in matches:
                        if match[0]:
                            lengths.append(match[0])

                # Remove duplicates while preserving order
                seen = set()
                lengths = [x for x in lengths if not (x in seen or seen.add(x))]

                if not lengths:
                    self.logger.debug(f"No lengths found in table {table_idx} header: {first_col_header}")
                    return []

                self.logger.debug(f"Detected NEWLINE-SEPARATED structure with lengths: {lengths}")

            current_descriptor = None
            current_parsed = None
            current_base_model = None

            # STEP 2: Process each data row
            for row_idx, row in data_rows.iterrows():
                # Locate the cell that contains the model descriptor (may not always be column 0)
                model_descriptor = None
                parsed = None
                found_new_model = False

                for col_idx in range(len(row)):
                    cell_value = str(row.iloc[col_idx]).strip()
                    if not cell_value or cell_value.lower() in ["nan", "none", ""] or len(cell_value) < 3:
                        continue
                    parsed_candidate = self._parse_select_model_descriptor(cell_value)
                    if parsed_candidate:
                        model_descriptor = cell_value
                        parsed = parsed_candidate
                        found_new_model = True

                        # Check if we've moved to a DIFFERENT base model family
                        new_base_model = parsed["base_model"]
                        if current_base_model and new_base_model != current_base_model:
                            # Moving to a different model family (e.g., SL11 -> SL12)
                            # Reset the current descriptor to prevent contamination
                            self.logger.debug(f"Model family changed: {current_base_model} -> {new_base_model}")

                        current_descriptor = model_descriptor
                        current_parsed = parsed
                        current_base_model = new_base_model
                        break

                if not parsed and current_parsed:
                    # Use the most recent descriptor ONLY if this row contains prices
                    # AND we haven't moved to a different model family
                    has_numeric = any(
                        self._extract_price_from_cell(str(row.iloc[col_idx]).strip())
                        for col_idx in range(len(row))
                    )
                    if has_numeric:
                        # Check if this row might belong to a DIFFERENT model
                        # by looking for model number patterns in the row
                        row_text = " ".join(str(cell) for cell in row if str(cell).strip())
                        # If we find a different SL## pattern, skip this row (don't use current_parsed)
                        different_model_match = re.search(r'SL\s*(\d{2,3})', row_text, re.IGNORECASE)
                        if different_model_match:
                            possible_model = f"SL{different_model_match.group(1)}"
                            if possible_model != current_base_model:
                                # This row mentions a DIFFERENT model - skip it
                                self.logger.debug(f"Skipping row mentioning {possible_model} (current: {current_base_model})")
                                continue

                        parsed = current_parsed
                        model_descriptor = current_descriptor
                    else:
                        continue
                elif not parsed:
                    continue

                # Skip header/empty rows
                if not model_descriptor or model_descriptor.lower() in ["model", "model #"]:
                    continue

                # Skip rows that look like headers/garbage
                if "WEB" in model_descriptor.upper() or "METRIC" in model_descriptor.upper():
                    continue

                # Parse model descriptor (e.g., "SL11 CL HD600")
                base_model = parsed["base_model"]
                finish = parsed["finish"]
                duty = parsed["duty"]

                # STEP 3: Extract prices based on structure type
                if structure_type == "column-separated":
                    # COLUMN-SEPARATED: Each length has its own column
                    # Map length -> (price, original_cell_value)
                    length_data_map = {}

                    for length, col_idx in length_columns.items():
                        if col_idx < len(row):
                            cell = str(row.iloc[col_idx]).strip()
                            # Store both the extracted price AND the original cell value
                            price_val = self._extract_price_from_cell(cell)
                            length_data_map[length] = {
                                "price": price_val,
                                "original_cell": cell
                            }

                    # Create products ONLY for cells that have valid prices
                    # DO NOT forward-fill - if a cell is "-" or empty, that size is unavailable
                    for length in lengths:
                        data = length_data_map.get(length, {})
                        price = data.get("price")
                        original_cell = data.get("original_cell", "")

                        # Skip if no price OR if original cell was a dash (explicitly unavailable)
                        if not price or original_cell in ["-", "—", "–"]:
                            continue

                        self._create_product(
                            products, base_model, finish, duty, length, price,
                            model_descriptor, row_idx, page_number, table_idx
                        )

                else:
                    # NEWLINE-SEPARATED: Prices are newline-separated across multiple cells
                    # Collect all price cells from columns 1, 2, 3, etc.
                    price_cells = []
                    for col_idx in range(1, len(row)):
                        cell = str(row.iloc[col_idx]).strip()
                        if cell and cell.lower() not in ["nan", "none", ""]:
                            price_cells.append(cell)

                    if not price_cells:
                        continue

                    # Split each cell by newlines and flatten into list
                    all_price_strings = []
                    for cell in price_cells:
                        prices_in_cell = [p.strip() for p in cell.split('\n')]
                        all_price_strings.extend(prices_in_cell)

                    # Extract prices and keep track of which ones were dashes
                    # Map: index -> (price_value, was_dash)
                    price_data = []
                    for price_str in all_price_strings:
                        # Check if this is an explicit dash (unavailable)
                        is_dash = price_str in ["-", "—", "–", ""]
                        price_val = None if is_dash else self._extract_price_from_cell(price_str)
                        price_data.append({
                            "price": price_val,
                            "is_dash": is_dash,
                            "original": price_str
                        })

                    # Match prices to lengths (zip them together)
                    # DO NOT forward-fill - dashes mean unavailable
                    min_count = min(len(lengths), len(price_data))

                    for i in range(min_count):
                        length = lengths[i]
                        data = price_data[i]
                        price = data["price"]
                        is_dash = data["is_dash"]

                        # Skip if no valid price OR if it was explicitly marked unavailable with dash
                        if price is None or is_dash:
                            continue

                        self._create_product(
                            products, base_model, finish, duty, length, price,
                            model_descriptor, row_idx, page_number, table_idx
                        )

        except Exception as e:
            self.logger.warning(f"Structured extraction failed on table {table_idx}: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return []

        return products

    def _extract_price_from_cell(self, price_str: str) -> Optional[float]:
        """Extract and validate a price from a cell string.

        Returns price as float if valid, None otherwise.
        Filters out dashes, fractions, dimensions, and invalid values.
        """
        if not price_str:
            return None

        # Explicitly reject dashes FIRST - they indicate unavailable sizes
        # This includes various dash types and empty strings
        if price_str.strip() in ["-", "—", "–", "", "n/a", "N/A"]:
            return None

        skip_keywords = [
            "mm",
            "bevel",
            "edge",
            "square",
            "clearance",
            "min",
            "web",
            "metric",
            "brochure",
            "site",
        ]

        # Examine each line within the cell separately to avoid discarding prices that share a cell
        for part in re.split(r"[\r\n]+", price_str):
            candidate = part.strip()
            # Check for dashes again at line level
            if not candidate or candidate in ["-", "—", "–", "n/a", "N/A"]:
                continue

            # Skip obvious fraction/dimension strings
            if re.search(r"\d+\s*/\s*\d+", candidate):
                continue

            if any(kw in candidate.lower() for kw in skip_keywords):
                continue

            if not re.search(r"\d", candidate):
                continue

            price_normalized = data_normalizer.normalize_price(candidate)
            if price_normalized["value"]:
                price_val = float(price_normalized["value"])
                if 50 <= price_val <= 10000:
                    return price_val

        return None

    def _create_product(
        self,
        products: List[ParsedItem],
        base_model: str,
        finish: Optional[str],
        duty: Optional[str],
        length: str,
        price: float,
        model_descriptor: str,
        row_idx: int,
        page_number: Optional[int],
        table_idx: int
    ) -> None:
        """Create a product item and add it to the products list."""
        # Build SKU: BASE_MODEL-FINISH-DUTY-LENGTH
        sku_parts = [base_model]
        if finish:
            sku_parts.append(finish)
        if duty:
            sku_parts.append(duty)
        sku_parts.append(length)
        sku = "-".join(sku_parts)

        # Build description
        desc_parts = [base_model]
        if finish:
            desc_parts.append(finish)
        if duty:
            desc_parts.append(duty)
        desc_parts.append(f'{length}"')
        description = " ".join(desc_parts)

        product_data = {
            "sku": sku,
            "model": base_model,
            "series": base_model[:2] if len(base_model) >= 2 else base_model,
            "description": description,
            "base_price": price,
            "finish_code": finish if finish and finish in ["CL", "BR", "BK"] else None,
            "specifications": {
                "length": f'{length}"',
                "duty": duty if duty else None,
            },
            "is_active": True,
            "manufacturer": "SELECT Hinges",
        }

        item = self.tracker.create_parsed_item(
            value=product_data,
            data_type="product",
            raw_text=f"{model_descriptor} {length}\" ${price}",
            row_index=row_idx,
            confidence=0.95,
            page_number=page_number,
            table_index=table_idx,
        )
        products.append(item)

    def _parse_select_model_descriptor(self, descriptor: str) -> Optional[Dict[str, str]]:
        """Parse SELECT model descriptor like 'SL11 CL HD600' into components.

        Returns dict with: base_model, finish, duty
        Returns None if descriptor doesn't match expected patterns
        """
        descriptor = descriptor.strip()

        # Skip descriptors that are just numbers (like "306", "310")
        # These are likely part numbers, not model descriptors
        if descriptor.isdigit():
            return None

        # Pattern: SL## [FINISH] [DUTY]
        # Examples: "SL11 CL HD600", "SL11 BR LL", "SL14 BK HD300"
        match = re.match(
            r'(SL\s*\d{2,3})\s*([A-Z]{2})?\s*([A-Z]{2,6}\d*)?',
            descriptor,
            re.IGNORECASE
        )

        if not match:
            return None

        base_model = match.group(1).replace(" ", "")  # "SL11"
        finish = match.group(2).upper() if match.group(2) else None  # "CL"
        duty = match.group(3).upper() if match.group(3) else None  # "HD600"

        # Validate finish code if present
        if finish and finish not in ["CL", "BR", "BK"]:
            # Maybe finish and duty are swapped or concatenated
            if finish in ["HD300", "HD600", "LL"]:
                duty = finish
                finish = None

        # For valid SELECT products, we expect at least a finish OR duty
        # Skip standalone model numbers without specifications
        if not finish and not duty:
            return None

        return {
            "base_model": base_model,
            "finish": finish,
            "duty": duty
        }

    def _is_model_table(self, table: pd.DataFrame) -> bool:
        """Check if table contains model product data."""
        if table.empty or len(table) < 2:
            return False

        # Convert table to text for analysis
        table_text = " ".join(table.astype(str).values.flatten()).lower()

        # Look for SELECT-specific indicators
        indicators = [
            "sl11",
            "sl14",
            "sl24",
            "sl41",  # Model codes
            "length",
            "duty",
            "finish",  # Column headers
            "cl",
            "br",
            "bk",  # Finish codes
            "light",
            "medium",
            "heavy",  # Duty ratings
        ]

        return sum(1 for indicator in indicators if indicator in table_text) >= 3

    def _extract_products_from_model_table(
        self, table: pd.DataFrame, table_idx: int
    ) -> List[ParsedItem]:
        """Extract products from a structured model table."""
        products = []

        # Identify columns
        columns = self._identify_table_columns(table)

        if columns.get("model") is None or columns.get("price") is None:
            self.logger.warning(f"Table {table_idx} missing essential columns: {columns}")
            self.logger.debug(f"Table columns: {list(table.columns)}")
            return products

        for row_idx, row in table.iterrows():
            try:
                # Extract basic product data
                model_code = str(row.iloc[columns["model"]]).strip()
                price_str = str(row.iloc[columns["price"]]).strip()

                # Skip header/empty rows
                if not model_code or model_code.lower() in ["nan", "model", "code"]:
                    continue

                # Normalize the data
                sku_normalized = data_normalizer.normalize_sku(model_code, "select_hinges")
                price_normalized = data_normalizer.normalize_price(price_str)

                if sku_normalized["value"] and price_normalized["value"]:
                    product_data = {
                        "sku": sku_normalized["value"],
                        "model": self._extract_base_model(sku_normalized["value"]),
                        "description": self._build_description(row, columns),
                        "base_price": float(price_normalized["value"]),
                        "specifications": self._extract_specifications(row, columns),
                        "finish_code": self._extract_finish_code(row, columns),
                        "is_active": True,
                    }

                    # Calculate combined confidence
                    confidence = min(
                        safe_confidence_score(sku_normalized["confidence"]),
                        safe_confidence_score(price_normalized["confidence"]),
                    )

                    item = self.tracker.create_parsed_item(
                        value=product_data,
                        data_type="product",
                        raw_text=f"{model_code} - {price_str}",
                        row_index=row_idx,
                        confidence=confidence,
                    )
                    products.append(item)

            except Exception as e:
                self.logger.warning(f"Error processing row {row_idx}: {e}")
                continue

        return products

    def _extract_products_from_table_simple(
        self, df: pd.DataFrame, table_idx: int, page_number: int = None
    ) -> List[ParsedItem]:
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

                if cell_value.lower() in ["nan", "none", "", "-"]:
                    continue

                # Look for SELECT SKU pattern: SL## optionally followed by finish code and variant
                # Examples: "SL21 CL HD300", "SL11 BR HD600", "SL14CL", or just "SL21"
                sku_match = re.search(
                    r'(SL\s*\d{2})(?:\s+([A-Z]{2}))?(?:\s+(HD\d+|LD\d+|LL|\d+"?))?',
                    cell_value,
                    re.IGNORECASE,
                )

                if not sku_match:
                    continue

                base_model = sku_match.group(1).replace(" ", "")  # SL21
                finish_code = (
                    sku_match.group(2).upper() if sku_match.group(2) else None
                )  # CL, BR, BK or None
                variant = sku_match.group(3).upper() if sku_match.group(3) else ""  # HD300, etc

                # If finish code missing, check adjacent cells
                if not finish_code:
                    for offset in [-1, 1]:
                        adj_col = col_idx + offset
                        if 0 <= adj_col < len(row):
                            adj_text = str(row.iloc[adj_col]).strip().upper()
                            if adj_text in ["CL", "BR", "BK"]:
                                finish_code = adj_text
                                break
                    # If still no finish, try to infer from column header
                    if not finish_code and col_idx < len(df.columns):
                        header_text = str(df.iloc[0, col_idx]).strip().upper()
                        if any(f in header_text for f in ["CL", "BR", "BK"]):
                            finish_code = next(
                                (f for f in ["CL", "BR", "BK"] if f in header_text), None
                            )
                    # SKIP products without valid finish codes - no position-based fallback
                    if not finish_code:
                        continue  # Skip this product entirely

                # Build full SKU with position to make unique
                sku = (
                    f"{base_model}-{finish_code}-{variant}".replace(" ", "")
                    if variant
                    else f"{base_model}-{finish_code}"
                )

                # Now find price in the same cell or adjacent cells
                price_val = None

                # First try same cell
                price_matches = re.findall(r"(\d+\.?\d{0,2})", cell_value)
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
                            price_matches = re.findall(
                                r"(\d+\.?\d{0,2})", adj_cell.replace(",", "")
                            )
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
                display_finish = finish_code if finish_code in ["CL", "BR", "BK"] else None

                # Create product
                product_data = {
                    "sku": sku,
                    "model": base_model,
                    "series": base_model[:2] if len(base_model) >= 2 else base_model,
                    "description": f"{base_model} {finish_code} {variant}".strip(),
                    "base_price": price_val,
                    "finish_code": display_finish,
                    "specifications": (
                        {"duty": variant, "column": col_idx} if variant else {"column": col_idx}
                    ),
                    "is_active": True,
                    "manufacturer": "SELECT",
                }

                item = self.tracker.create_parsed_item(
                    value=product_data,
                    data_type="product",
                    raw_text=cell_value[:100],
                    row_index=row_idx,
                    confidence=0.9,  # Higher confidence since we have both SKU and price
                    page_number=page_number,
                    table_index=table_idx,
                )
                products.append(item)

        return products

    def _extract_products_from_text_section(
        self, text_section: str, model_code: str
    ) -> List[ParsedItem]:
        """Extract products from a text section for specific model."""
        products = []

        # Look for price patterns in the text
        price_pattern = r"(\w+(?:-\w+)*)\s+\$?(\d+(?:\.\d{2})?)"
        matches = re.finditer(price_pattern, text_section)

        for match in matches:
            variant = match.group(1).strip()
            price_str = match.group(2).strip()

            # Build full SKU
            full_sku = f"{model_code}{variant}" if variant else model_code

            # Normalize
            sku_normalized = data_normalizer.normalize_sku(full_sku, "select_hinges")
            price_normalized = data_normalizer.normalize_price(price_str)

            if sku_normalized["value"] and price_normalized["value"]:
                product_data = {
                    "sku": sku_normalized["value"],
                    "model": model_code,
                    "description": f"{model_code} Series {variant}".strip(),
                    "base_price": float(price_normalized["value"]),
                    "specifications": {"variant": variant},
                    "is_active": True,
                }

                confidence = (
                    min(sku_normalized["confidence"].score, price_normalized["confidence"].score)
                    * 0.8
                )  # Lower confidence for text extraction

                item = self.tracker.create_parsed_item(
                    value=product_data,
                    data_type="product",
                    raw_text=match.group(0),
                    confidence=confidence,
                )
                products.append(item)

        return products

    def _identify_table_columns(self, table: pd.DataFrame) -> Dict[str, Optional[int]]:
        """Identify column purposes in a model table."""
        columns = {
            "model": None,
            "price": None,
            "description": None,
            "length": None,
            "duty": None,
            "finish": None,
        }

        # Check header row for column identification
        for col_idx, col_name in enumerate(table.columns):
            col_text = str(col_name).lower()

            if any(keyword in col_text for keyword in ["model", "sku", "part", "item"]):
                columns["model"] = col_idx
            elif any(keyword in col_text for keyword in ["price", "cost", "each", "list"]):
                columns["price"] = col_idx
            elif any(keyword in col_text for keyword in ["desc", "description", "name"]):
                columns["description"] = col_idx
            elif any(keyword in col_text for keyword in ["length", "size"]):
                columns["length"] = col_idx
            elif any(keyword in col_text for keyword in ["duty", "weight"]):
                columns["duty"] = col_idx
            elif any(keyword in col_text for keyword in ["finish", "color"]):
                columns["finish"] = col_idx

        # If using exact column names, get their positions
        if columns["model"] is None and "Model" in table.columns:
            columns["model"] = list(table.columns).index("Model")
        if columns["price"] is None and "Price" in table.columns:
            columns["price"] = list(table.columns).index("Price")
        if columns["description"] is None and "Description" in table.columns:
            columns["description"] = list(table.columns).index("Description")

        # If headers aren't clear, analyze content patterns
        if columns["model"] is None:
            columns["model"] = self._find_column_by_pattern(table, r"^[A-Z]{2}\d+")

        if columns["price"] is None:
            columns["price"] = self._find_column_by_pattern(table, r"\$?\d+\.\d{2}")

        return columns

    def _find_column_by_pattern(self, table: pd.DataFrame, pattern: str) -> Optional[int]:
        """Find column index by content pattern."""
        for col_idx, col in enumerate(table.columns):
            if table[col].dtype == "object":
                sample_values = table[col].dropna().head(5)
                matches = sum(1 for val in sample_values if re.search(pattern, str(val)))
                if matches >= 2:  # At least 2 matches
                    return col_idx
        return None

    def _extract_base_model(self, sku: str) -> str:
        """Extract base model from SKU (e.g., SL11 from SL11CL24)."""
        match = re.match(r"^(SL\d+)", sku.upper())
        return match.group(1) if match else sku[:4]

    def _build_description(self, row: pd.Series, columns: Dict[str, Optional[int]]) -> str:
        """Build product description from row data."""
        parts = []

        if columns.get("description") is not None:
            desc = str(row.iloc[columns["description"]]).strip()
            if desc and desc.lower() != "nan":
                parts.append(desc)

        if columns.get("length") is not None:
            length = str(row.iloc[columns["length"]]).strip()
            if length and length.lower() != "nan":
                parts.append(f"Length: {length}")

        if columns.get("duty") is not None:
            duty = str(row.iloc[columns["duty"]]).strip()
            if duty and duty.lower() != "nan":
                parts.append(f"Duty: {duty}")

        return " - ".join(parts) if parts else "SELECT Hinge"

    def _extract_specifications(
        self, row: pd.Series, columns: Dict[str, Optional[int]]
    ) -> Dict[str, Any]:
        """Extract specifications from row data."""
        specs = {}

        if columns.get("length") is not None:
            length = str(row.iloc[columns["length"]]).strip()
            if length and length.lower() != "nan":
                specs["length"] = length

        if columns.get("duty") is not None:
            duty = str(row.iloc[columns["duty"]]).strip()
            if duty and duty.lower() != "nan":
                specs["duty"] = duty

        return specs

    def _extract_finish_code(
        self, row: pd.Series, columns: Dict[str, Optional[int]]
    ) -> Optional[str]:
        """Extract finish code from row data."""
        if columns.get("finish") is not None:
            finish = str(row.iloc[columns["finish"]]).strip().upper()
            if finish in self.finish_codes:
                return finish

        # Try to extract from SKU
        sku = str(row.iloc[columns.get("model", 0)]).strip().upper()
        for code in self.finish_codes:
            if code in sku:
                return code

        return None

    def _get_option_name(self, option_code: str) -> str:
        """Get full name for option code."""
        names = {
            "CTW": "Continuous Weld",
            "EPT": "Electroplated Prep",
            "EMS": "Electromagnetic Shielding",
            "ATW": "Arc Weld",
            "TIPIT": "Tip It",
            "HT": "Hospital Tip",
            "FR3": "Fire Rating 3 Hour",
        }
        return names.get(option_code, option_code)

    def _extract_all_price_cells(
        self, df: pd.DataFrame, table_idx: int, page_number: int = None, existing_skus: set = None
    ) -> List[ParsedItem]:
        """
        ENHANCED: Extract ALL price cells as products with inference.
        This aggressive mode extracts every valid price and infers model/finish/specs from context.
        Only creates products with valid finish codes (CL/BR/BK).
        """
        products = []
        if existing_skus is None:
            existing_skus = set()

        if df.empty or len(df) < 2:
            return products

        # Get headers for column inference
        headers = [str(col).strip().upper() for col in df.columns]

        # Process each row
        for row_idx, row in df.iterrows():
            if row_idx == 0:  # Skip header
                continue

            # Get row header (first column - usually model)
            row_header = str(row.iloc[0]).strip() if len(row) > 0 else ""

            # Extract full model info from row header (handle 2 or 3 digit models)
            # Pattern: SL## [FINISH] [DUTY]
            model_match = re.search(
                r"(SL\s*\d{2,3})\s*([A-Z]{2})?\s*([A-Z]+\d*)?", row_header, re.IGNORECASE
            )
            if not model_match:
                continue

            base_model = model_match.group(1).replace(" ", "").upper()
            finish_from_row = model_match.group(2).upper() if model_match.group(2) else None
            duty_from_row = model_match.group(3).upper() if model_match.group(3) else None

            # Extract length/duty from row if present
            length_duty = duty_from_row if duty_from_row else ""
            if not length_duty:
                length_match = re.search(r'(HD\d+|LD\d+|LL|\d+\s*")', row_header)
                if length_match:
                    length_duty = length_match.group(1).replace(" ", "")

            # Scan all cells in this row for prices
            for col_idx, cell_value in enumerate(row):
                cell_str = str(cell_value).strip()

                if cell_str.lower() in ["nan", "none", "", "-", "n/a"]:
                    continue

                # Extract price
                price = None
                price_matches = re.findall(r"\$?\s*(\d+\.?\d{0,2})", cell_str.replace(",", ""))
                for price_str in price_matches:
                    try:
                        pval = float(price_str)
                        if 10 <= pval <= 5000:
                            price = pval
                            break
                    except:
                        continue

                if not price:
                    continue

                # Infer finish from row, column header, or cell - allow None for Pin & Barrel models
                finish_code = finish_from_row if finish_from_row else None
                col_header = headers[col_idx] if col_idx < len(headers) else ""

                # Check column header for finish code (override row finish if found)
                if col_header in ["CL", "BR", "BK"]:
                    finish_code = col_header
                elif "CL" in col_header or "CLEAR" in col_header:
                    finish_code = "CL"
                elif "BR" in col_header or "BRONZE" in col_header:
                    finish_code = "BR"
                elif "BK" in col_header or "BLACK" in col_header:
                    finish_code = "BK"
                elif not finish_code:  # Check cell text if no finish found yet
                    if re.search(r"\bCL\b", cell_str, re.IGNORECASE):
                        finish_code = "CL"
                    elif re.search(r"\bBR\b", cell_str, re.IGNORECASE):
                        finish_code = "BR"
                    elif re.search(r"\bBK\b", cell_str, re.IGNORECASE):
                        finish_code = "BK"

                # Extract length from column header
                length_from_col = ""
                length_col_match = re.search(r'(\d+)\s*"', col_header)
                if length_col_match:
                    length_from_col = length_col_match.group(1)

                # Check for length/duty in cell if not in row header
                if not length_duty:
                    length_match = re.search(r'(HD\d+|LD\d+|LL|\d+\s*")', cell_str)
                    if length_match:
                        length_duty = length_match.group(1).replace(" ", "")

                # Build SKU with proper format: {BASE}_{FINISH}_{DUTY}_{LENGTH}
                sku_parts = [base_model]
                if finish_code:
                    sku_parts.append(finish_code)
                if length_duty:
                    sku_parts.append(length_duty)
                if length_from_col:
                    sku_parts.append(length_from_col)

                sku = "_".join(sku_parts)

                # Skip duplicates (check both local and existing SKUs)
                if sku in existing_skus:
                    continue

                # Create product
                product_data = {
                    "sku": sku,
                    "model": base_model,
                    "series": "SL",
                    "finish": finish_code,
                    "length_duty": length_duty or "Standard",
                    "base_price": price,
                    "currency": "USD",
                    "manufacturer": "SELECT Hinges",
                    "is_active": True,
                    "description": f"{base_model} {finish_code} {length_duty or ''}".strip(),
                }

                # Confidence based on inference level
                # High confidence since we validated finish code is CL/BR/BK
                confidence = 0.85
                if not length_duty:
                    confidence -= 0.05  # Slightly lower if no length/duty info
                confidence = max(confidence, 0.80)

                item = self.tracker.create_parsed_item(
                    value=product_data,
                    data_type="product",
                    raw_text=f"{base_model} {finish_code} ${price}",
                    row_index=row_idx,
                    confidence=confidence,
                )
                products.append(item)

        return products

    def _get_option_constraints(self, option_code: str) -> Dict[str, Any]:
        """Get constraints for option."""
        constraints = {
            "CTW": {"requires_handing": True},
            "EPT": {"excludes": ["CTW"]},
            "EMS": {"excludes": ["CTW", "EPT"]},
            "ATW": {"requires_handing": True},
            "TIPIT": {"excludes": ["HT"]},
            "HT": {"excludes": ["TIPIT"]},
            "FR3": {},
        }
        return constraints.get(option_code, {})

    def _get_option_availability(self, option_code: str) -> str:
        """Get availability note for option."""
        availability = {
            "CTW": "Available on most models",
            "EPT": "Standard electroplated preparation",
            "EMS": "Electromagnetic shielding option",
            "ATW": "Arc weld option with handing",
            "TIPIT": "Tip adjustment mechanism",
            "HT": "Hospital tip configuration",
            "FR3": "UL Fire Rated 3-hour option",
        }
        return availability.get(option_code, "Contact for availability")
