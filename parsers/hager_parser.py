import re
from typing import List, Dict, Any, Optional
import pandas as pd
from .base_parser import BasePDFParser


class HagerParser(BasePDFParser):
    """Specialized parser for Hager price books"""

    def __init__(self, pdf_path: str, config: Dict[str, Any] = None):
        super().__init__(pdf_path, config)
        self.manufacturer = "hager"
        self.finish_adder_patterns = {
            "US3": r"US3.*?(\d+\.?\d*)",
            "US4": r"US4.*?(\d+\.?\d*)",
            "US10B": r"US10B.*?(\d+\.?\d*)",
            "US15": r"US15.*?(\d+\.?\d*)",
            "US26D": r"US26D.*?(\d+\.?\d*)",
            "US32D": r"US32D.*?(\d+\.?\d*)",
            "US33D": r"US33D.*?(\d+\.?\d*)",
        }

    def identify_manufacturer(self) -> str:
        """Identify Hager manufacturer from content"""
        if not self.text_content:
            self.text_content = self.extract_text_content()

        hager_indicators = ["hager", "hager companies", "hager manufacturing", "hager hinges"]

        for indicator in hager_indicators:
            if indicator.lower() in self.text_content.lower():
                return "hager"

        return "unknown"

    def parse(self) -> Dict[str, Any]:
        """Parse Hager price book"""
        self.logger.info(f"Starting Hager parsing for {self.pdf_path}")

        # Extract text content
        self.text_content = self.extract_text_content()

        # Extract effective date
        self.effective_date = self.extract_effective_date()

        # Extract tables
        tables = self.extract_tables()

        # Parse products from tables
        self.products = self._parse_products_from_tables(tables)

        # Parse finish adders
        self.finishes = self._parse_finish_adders()

        # Parse option adders
        self.options = self._parse_option_adders()

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

        self.logger.info(f"Hager parsing completed: {len(self.products)} products found")
        return data

    def _parse_products_from_tables(self, tables: List[pd.DataFrame]) -> List[Dict[str, Any]]:
        """Parse product information from tables"""
        products = []

        for table in tables:
            try:
                # Look for product tables (containing SKUs and prices)
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

        # Look for common product table indicators
        text_content = " ".join(table.astype(str).values.flatten()).lower()

        product_indicators = [
            "sku",
            "model",
            "price",
            "finish",
            "description",
            "hinge",
            "door",
            "hardware",
            "bb",
            "bbh",
        ]

        return any(indicator in text_content for indicator in product_indicators)

    def _extract_products_from_table(self, table: pd.DataFrame) -> List[Dict[str, Any]]:
        """Extract products from a single table"""
        products = []

        # Find columns that might contain SKUs, descriptions, and prices
        sku_col = self._find_sku_column(table)
        price_col = self._find_price_column(table)
        desc_col = self._find_description_column(table)

        if sku_col is None or price_col is None:
            return products

        for idx, row in table.iterrows():
            try:
                sku = self.clean_sku(row.iloc[sku_col]) if sku_col < len(row) else ""
                price = self.clean_price(row.iloc[price_col]) if price_col < len(row) else None
                description = (
                    str(row.iloc[desc_col]) if desc_col is not None and desc_col < len(row) else ""
                )

                if sku and price is not None:
                    product = {
                        "sku": sku,
                        "model": self._extract_model_from_sku(sku),
                        "description": description,
                        "base_price": price,
                        "effective_date": self.effective_date,
                        "finish_code": self._extract_finish_from_sku(sku),
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
            if any(indicator in col_text for indicator in ["sku", "part", "number", "item"]):
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
            if any(indicator in col_text for indicator in ["price", "cost", "$", "each"]):
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
            if any(indicator in col_text for indicator in ["description", "desc", "name", "type"]):
                return col_idx

        return None

    def _looks_like_sku(self, text: str) -> bool:
        """Check if text looks like a SKU"""
        if not text or len(text) < 3:
            return False

        # Hager SKU patterns - allow mixed letters and digits
        sku_patterns = [
            r"^BB\d+",  # BB followed by numbers
            r"^BBH\d+",  # BBH followed by numbers
            r"^[A-Z]{2,3}\d+",  # 2-3 letters followed by numbers
            r"^[A-Z]+\d+[A-Z]*",  # Letters, numbers, optional letters (H3A)
        ]

        return any(re.match(pattern, text.upper()) for pattern in sku_patterns)

    def _looks_like_price(self, text: str) -> bool:
        """Check if text looks like a price"""
        if not text:
            return False

        # Price patterns - support dollars and commas
        price_patterns = [
            r"^\$?\d+\.?\d*$",  # $123.45 or 123.45
            r"^\$?\d{1,3}(,\d{3})*(\.\d{1,2})?$",  # $1,234.56 or 1,234.56
            r"^\d+\.\d{2}$",  # 123.45
        ]

        return any(re.match(pattern, text) for pattern in price_patterns)

    def _extract_model_from_sku(self, sku: str) -> str:
        """Extract model number from SKU"""
        if not sku:
            return ""

        # Remove finish codes (like -US3, -US10B) to get base model
        model = re.sub(r"-US\d+[A-Z]*$", "", sku)

        # Remove any trailing dash
        model = model.rstrip("-")

        return model

    def _extract_finish_from_sku(self, sku: str) -> Optional[str]:
        """Extract finish code from SKU"""
        for finish_code in self.finish_adder_patterns.keys():
            if finish_code in sku.upper():
                return finish_code
        return None

    def _parse_finish_adders(self) -> List[Dict[str, Any]]:
        """Parse finish adder information"""
        finishes = []

        if not self.text_content:
            return finishes

        # Look for finish adder tables in text
        finish_section = self._extract_finish_section()

        for finish_code, pattern in self.finish_adder_patterns.items():
            matches = re.findall(pattern, finish_section, re.IGNORECASE)
            if matches:
                try:
                    adder_value = float(matches[0])
                    finish = {
                        "code": finish_code,
                        "name": self._get_finish_name(finish_code),
                        "adder_type": "net_add",
                        "adder_value": adder_value,
                        "is_required": False,
                    }
                    finishes.append(finish)
                except ValueError:
                    continue

        return finishes

    def _extract_finish_section(self) -> str:
        """Extract the section containing finish adders"""
        # Look for common finish section headers
        section_patterns = [
            r"finish.*?adder.*?(?=finish|option|preparation|$)",
            r"finish.*?code.*?(?=finish|option|preparation|$)",
            r"finish.*?pricing.*?(?=finish|option|preparation|$)",
        ]

        for pattern in section_patterns:
            match = re.search(pattern, self.text_content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(0)

        return self.text_content

    def _get_finish_name(self, finish_code: str) -> str:
        """Get finish name from code"""
        finish_names = {
            "US3": "Satin Chrome",
            "US4": "Bright Chrome",
            "US10B": "Satin Bronze",
            "US15": "Satin Brass",
            "US26D": "Oil Rubbed Bronze",
            "US32D": "Antique Brass",
            "US33D": "Antique Copper",
        }
        return finish_names.get(finish_code, finish_code)

    def _parse_option_adders(self) -> List[Dict[str, Any]]:
        """Parse option adder information"""
        options = []

        if not self.text_content:
            return options

        # Look for option adder patterns
        option_patterns = [
            r"preparation.*?adder.*?(\d+\.?\d*)",
            r"size.*?adder.*?(\d+\.?\d*)",
            r"option.*?adder.*?(\d+\.?\d*)",
        ]

        for pattern in option_patterns:
            matches = re.findall(pattern, self.text_content, re.IGNORECASE)
            for match in matches:
                try:
                    adder_value = float(match)
                    option = {
                        "option_type": "preparation",
                        "option_name": "Preparation Adder",
                        "adder_type": "net_add",
                        "adder_value": adder_value,
                        "is_required": False,
                    }
                    options.append(option)
                    break  # Only add one preparation adder
                except ValueError:
                    continue

        return options
