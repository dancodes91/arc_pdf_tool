import re
from typing import List, Dict, Any, Optional
import pandas as pd
from .base_parser import BasePDFParser


class SelectHingesParser(BasePDFParser):
    """Specialized parser for SELECT Hinges price books with net-add options"""

    def __init__(self, pdf_path: str, config: Dict[str, Any] = None):
        super().__init__(pdf_path, config)
        self.manufacturer = "select_hinges"

        # Net-add options specific to SELECT Hinges
        self.net_add_options = {
            "CTW": "Continuous Weld",
            "EPT": "Electroplated",
            "EMS": "Electromagnetic Shielding",
            "TIPIT": "Tip It",
            "Hospital Tip": "Hospital Tip",
            "UL FR3": "UL Fire Rated 3",
        }

        # Option rules and dependencies
        self.option_rules = {
            "CTW": {"requires": [], "excludes": []},
            "EPT": {"requires": [], "excludes": ["CTW"]},
            "EMS": {"requires": [], "excludes": ["CTW", "EPT"]},
            "TIPIT": {"requires": [], "excludes": ["Hospital Tip"]},
            "Hospital Tip": {"requires": [], "excludes": ["TIPIT"]},
            "UL FR3": {"requires": [], "excludes": []},
        }

    def identify_manufacturer(self) -> str:
        """Identify SELECT Hinges manufacturer from content"""
        if not self.text_content:
            self.text_content = self.extract_text_content()

        select_indicators = [
            "select hinges",
            "select hardware",
            "select manufacturing",
            "select door hardware",
        ]

        for indicator in select_indicators:
            if indicator.lower() in self.text_content.lower():
                return "select_hinges"

        return "unknown"

    def parse(self) -> Dict[str, Any]:
        """Parse SELECT Hinges price book"""
        self.logger.info(f"Starting SELECT Hinges parsing for {self.pdf_path}")

        # Extract text content
        self.text_content = self.extract_text_content()

        # Extract effective date
        self.effective_date = self.extract_effective_date()

        # Extract tables
        tables = self.extract_tables()

        # Parse products from tables
        self.products = self._parse_products_from_tables(tables)

        # Parse net-add options
        self.options = self._parse_net_add_options()

        # Parse finish information
        self.finishes = self._parse_finish_information()

        # Validate data
        data = {
            "manufacturer": self.manufacturer,
            "effective_date": self.effective_date,
            "products": self.products,
            "finishes": self.finishes,
            "options": self.options,
        }

        validation = self.validate_data(data)
        data["validation"] = validation

        self.logger.info(f"SELECT Hinges parsing completed: {len(self.products)} products found")
        return data

    def _parse_products_from_tables(self, tables: List[pd.DataFrame]) -> List[Dict[str, Any]]:
        """Parse product information from tables"""
        products = []

        for table in tables:
            try:
                if self._is_product_table(table):
                    table_products = self._extract_products_from_table(table)
                    products.extend(table_products)
            except Exception as e:
                self.logger.error(f"Error parsing table: {e}")
                continue

        return products

    def _is_product_table(self, table: pd.DataFrame) -> bool:
        """Check if table contains product information"""
        if table.empty:
            return False

        text_content = " ".join(table.astype(str).values.flatten()).lower()

        product_indicators = [
            "sku",
            "model",
            "price",
            "hinge",
            "door",
            "hardware",
            "select",
            "series",
            "size",
            "finish",
        ]

        return any(indicator in text_content for indicator in product_indicators)

    def _extract_products_from_table(self, table: pd.DataFrame) -> List[Dict[str, Any]]:
        """Extract products from a single table"""
        products = []

        # Find relevant columns
        sku_col = self._find_sku_column(table)
        price_col = self._find_price_column(table)
        desc_col = self._find_description_column(table)
        size_col = self._find_size_column(table)

        if sku_col is None or price_col is None:
            return products

        for idx, row in table.iterrows():
            try:
                sku = self.clean_sku(row.iloc[sku_col]) if sku_col < len(row) else ""
                price = self.clean_price(row.iloc[price_col]) if price_col < len(row) else None
                description = (
                    str(row.iloc[desc_col]) if desc_col is not None and desc_col < len(row) else ""
                )
                size = (
                    str(row.iloc[size_col]) if size_col is not None and size_col < len(row) else ""
                )

                if sku and price is not None:
                    product = {
                        "sku": sku,
                        "model": self._extract_model_from_sku(sku),
                        "description": description,
                        "base_price": price,
                        "effective_date": self.effective_date,
                        "size": size,
                        "is_active": True,
                    }
                    products.append(product)

            except Exception as e:
                self.logger.error(f"Error processing row {idx}: {e}")
                continue

        return products

    def _find_sku_column(self, table: pd.DataFrame) -> Optional[int]:
        """Find the column containing SKUs"""
        for col_idx, col in enumerate(table.columns):
            col_text = str(col).lower()
            if any(
                indicator in col_text for indicator in ["sku", "part", "number", "item", "model"]
            ):
                return col_idx

        # Look for columns with SKU-like patterns
        for col_idx, col in enumerate(table.columns):
            if table[col].dtype == "object":
                sample_values = table[col].dropna().head(5)
                if any(self._looks_like_sku(str(val)) for val in sample_values):
                    return col_idx

        return None

    def _find_price_column(self, table: pd.DataFrame) -> Optional[int]:
        """Find the column containing prices"""
        for col_idx, col in enumerate(table.columns):
            col_text = str(col).lower()
            if any(indicator in col_text for indicator in ["price", "cost", "$", "each", "list"]):
                return col_idx

        # Look for columns with price-like patterns
        for col_idx, col in enumerate(table.columns):
            if table[col].dtype == "object":
                sample_values = table[col].dropna().head(5)
                if any(self._looks_like_price(str(val)) for val in sample_values):
                    return col_idx

        return None

    def _find_description_column(self, table: pd.DataFrame) -> Optional[int]:
        """Find the column containing descriptions"""
        for col_idx, col in enumerate(table.columns):
            col_text = str(col).lower()
            if any(
                indicator in col_text
                for indicator in ["description", "desc", "name", "type", "series"]
            ):
                return col_idx

        return None

    def _find_size_column(self, table: pd.DataFrame) -> Optional[int]:
        """Find the column containing sizes"""
        for col_idx, col in enumerate(table.columns):
            col_text = str(col).lower()
            if any(
                indicator in col_text
                for indicator in ["size", "dimension", "width", "height", "length"]
            ):
                return col_idx

        return None

    def _looks_like_sku(self, text: str) -> bool:
        """Check if text looks like a SKU"""
        if not text or len(text) < 3:
            return False

        # SELECT Hinges SKU patterns
        sku_patterns = [
            r"^[A-Z]{2,4}\d+",  # 2-4 letters followed by numbers
            r"^\d{3,4}[A-Z]",  # 3-4 numbers followed by letter
            r"^[A-Z]+\d+[A-Z]*",  # Letters, numbers, optional letters
        ]

        return any(re.match(pattern, text.upper()) for pattern in sku_patterns)

    def _looks_like_price(self, text: str) -> bool:
        """Check if text looks like a price"""
        if not text:
            return False

        price_patterns = [
            r"^\$?\d+\.?\d*$",
            r"^\d+\.\d{2}$",
        ]

        cleaned = re.sub(r"[^\d.,$]", "", text)
        return any(re.match(pattern, cleaned) for pattern in price_patterns)

    def _extract_model_from_sku(self, sku: str) -> str:
        """Extract model number from SKU"""
        if not sku:
            return ""

        # Extract the core model: digits + trailing letters
        # Remove leading letters, keep digits and any trailing letters
        match = re.search(r"\d+[A-Z]*", sku)
        if match:
            return match.group()

        # Fallback: remove only leading letters
        return re.sub(r"^[A-Z]+", "", sku)

    def _parse_net_add_options(self) -> List[Dict[str, Any]]:
        """Parse net-add options from text content"""
        options = []

        if not self.text_content:
            return options

        # Look for net-add option sections
        option_section = self._extract_option_section()

        for option_code, option_name in self.net_add_options.items():
            # Look for option pricing information
            option_pattern = rf"{re.escape(option_code)}.*?(\d+\.?\d*)"
            matches = re.findall(option_pattern, option_section, re.IGNORECASE)

            if matches:
                try:
                    adder_value = float(matches[0])
                    option = {
                        "option_type": "net_add",
                        "option_code": option_code,
                        "option_name": option_name,
                        "adder_type": "net_add",
                        "adder_value": adder_value,
                        "requires_option": self.option_rules[option_code]["requires"],
                        "excludes_option": self.option_rules[option_code]["excludes"],
                        "is_required": False,
                    }
                    options.append(option)
                except ValueError:
                    continue

        return options

    def _extract_option_section(self) -> str:
        """Extract the section containing option adders"""
        if not self.text_content:
            return ""

        section_patterns = [
            r"net\s+add(?:\s+options?)?:?.*?(?=\n\s*\n|$)",
            r"option\s+adders?:?.*?(?=\n\s*\n|$)",
            r"ctw.*?ept.*?ems.*?(?=option|finish|preparation|$)",
            r"tipit.*?hospital.*?ul.*?(?=option|finish|preparation|$)",
        ]

        keywords = ["CTW", "EPT", "EMS", "TIPIT", "HOSPITAL", "FR3", "UL FR3"]

        for pattern in section_patterns:
            match = re.search(pattern, self.text_content, re.IGNORECASE | re.DOTALL)
            if not match:
                continue

            section = match.group(0)

            # Skip headings without actual option rows
            if section.count("\n") < 1:
                continue

            if any(keyword in section.upper() for keyword in keywords):
                return section

        # Fallback: return entire document text so option detection can still run
        return self.text_content

    def _parse_finish_information(self) -> List[Dict[str, Any]]:
        """Parse finish information"""
        finishes = []

        if not self.text_content:
            return finishes

        # Look for finish information
        finish_section = self._extract_finish_section()

        # Common finish patterns for SELECT Hinges
        finish_patterns = [
            r"(\w+)\s+finish.*?(\d+\.?\d*)",
            r"finish.*?(\w+).*?(\d+\.?\d*)",
        ]

        for pattern in finish_patterns:
            matches = re.findall(pattern, finish_section, re.IGNORECASE)
            for match in matches:
                try:
                    finish_name = match[0].strip()
                    adder_value = float(match[1])

                    finish = {
                        "code": finish_name.upper(),
                        "name": finish_name.title(),
                        "adder_type": "net_add",
                        "adder_value": adder_value,
                        "is_required": False,
                    }
                    finishes.append(finish)
                except ValueError:
                    continue

        return finishes

    def _extract_finish_section(self) -> str:
        """Extract the section containing finish information"""
        section_patterns = [
            r"finish.*?information.*?(?=option|preparation|$)",
            r"finish.*?pricing.*?(?=option|preparation|$)",
            r"finish.*?adder.*?(?=option|preparation|$)",
        ]

        for pattern in section_patterns:
            match = re.search(pattern, self.text_content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(0)

        return self.text_content
