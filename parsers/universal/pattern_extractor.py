"""
Smart pattern-based extractor for price book data.

Extracts SKUs, prices, finishes, and other data using intelligent regex patterns
and heuristics that work across different manufacturer formats.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)


class SmartPatternExtractor:
    """
    Intelligent pattern-based extractor for price book elements.

    Uses regex patterns and heuristics to extract:
    - SKUs/Model numbers
    - Prices
    - Finish codes
    - Sizes/dimensions
    - Product descriptions
    - Options/adders
    """

    def __init__(self):
        """Initialize pattern extractor with common patterns."""

        # Price patterns (various formats)
        self.price_patterns = [
            r"\$\s*(\d+[,\d]*\.?\d{0,2})",  # $123.45, $1,234.50
            r"(\d+[,\d]*\.\d{2})\s*USD",  # 123.45 USD
            r"Price:\s*\$?\s*(\d+[,\d]*\.?\d{2})",  # Price: $123.45
            r"(\d+[,\d]*\.\d{2})",  # Simple: 123.45 (must have 2 decimals)
        ]

        # SKU/Model patterns (manufacturer-specific but common)
        self.sku_patterns = [
            # Pattern 1: Letters + Numbers (SL100, BB1279, US26D)
            r"\b([A-Z]{2,}[\s-]?\d{2,}[A-Z\d]*)\b",
            # Pattern 2: Numbers-Letters-Numbers (123-ABC-45)
            r"\b(\d{3,}-[A-Z0-9]+-\d+)\b",
            # Pattern 3: Model with finish/size (SL100-US26D-4.5x4.5)
            r"\b([A-Z]+\d+[-_][A-Z\d]+(?:[-_][A-Z\d.x]+)?)\b",
            # Pattern 4: Simple alphanumeric (MODEL123)
            r"\b([A-Z]{2,}\d{3,})\b",
        ]

        # Finish code patterns
        self.finish_patterns = [
            r"\bUS\s*\d+[A-Z]?\b",  # US26D, US10B, US 3
            r"\b([A-Z]{2,3})\b",  # BR, CL, ORB, SN (2-3 letters)
            r"\b(BHMA\s*\d+[A-Z]?)\b",  # BHMA codes
        ]

        # Size/dimension patterns
        self.size_patterns = [
            r"(\d+\.?\d*\s*x\s*\d+\.?\d*)",  # 4.5x4.5, 5 x 4.5
            r"(\d+\"\s*x\s*\d+\")",  # 4" x 5"
            r"(\d+\.?\d*)\s*(in|inch|mm|cm)",  # 5 in, 120mm
        ]

        # Option/adder patterns
        self.option_patterns = [
            r"([A-Z]{2,})\s+(?:add|adder|option):\s*\$?(\d+\.?\d*)",  # CTW add: $12
            r"Option\s+([A-Z\d]+).*?\$(\d+\.?\d*)",  # Option EPT ... $15
            r"Net\s+add:\s*([A-Z\s]+)\s*\$?(\d+\.?\d*)",  # Net add: CTW $12
        ]

        # Date patterns
        self.date_patterns = [
            r"Effective(?:\s+Date)?:?\s*([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})",  # Effective: December 1, 2024
            r"Effective:?\s*(\d{1,2}/\d{1,2}/\d{2,4})",  # Effective: 12/01/2024
            r"Valid\s+from:?\s*(\d{1,2}-[A-Z][a-z]+-\d{4})",  # Valid from: 01-Dec-2024
            r"(\d{1,2}/\d{1,2}/\d{4})\s+(?:effective|price)",  # 12/01/2024 effective
        ]

    def extract_from_text_block(self, text: str, page_num: int = 0) -> Dict[str, Any]:
        """
        Extract structured data from a text block.

        Args:
            text: Text content
            page_num: Page number for provenance

        Returns:
            Dict with extracted products, prices, dates, etc.
        """
        return {
            "products": self.extract_products_from_text(text, page_num),
            "prices": self.extract_prices(text),
            "finishes": self.extract_finishes(text),
            "options": self.extract_options(text),
            "effective_date": self.extract_effective_date(text),
        }

    def extract_products_from_text(
        self, text: str, page_num: int = 0
    ) -> List[Dict[str, Any]]:
        """Extract products from plain text using pattern matching."""
        products = []
        lines = text.split("\n")

        for line in lines:
            # Try to extract SKU
            sku = self._extract_sku(line)
            if not sku:
                continue

            # Extract price for this SKU
            price = self._extract_price(line)

            # Extract finish
            finish = self._extract_finish(line)

            # Extract size
            size = self._extract_size(line)

            # Only add if we have at least SKU and price
            if sku and price:
                product = {
                    "sku": sku,
                    "base_price": price,
                    "finish_code": finish,
                    "size": size,
                    "raw_text": line.strip(),
                    "page": page_num,
                    "confidence": self._calculate_product_confidence(
                        sku, price, finish, size
                    ),
                }
                products.append(product)

        return products

    def extract_from_table(
        self, table_df: pd.DataFrame, page_num: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Extract products from a DataFrame table.

        Args:
            table_df: Pandas DataFrame from table detection
            page_num: Page number

        Returns:
            List of extracted products
        """
        products = []

        if table_df.empty:
            return products

        # Try to identify columns
        columns = self._identify_table_columns(table_df)

        for idx, row in table_df.iterrows():
            # Convert row to text for pattern matching
            row_text = " ".join(str(cell) for cell in row if pd.notna(cell))

            # Extract using both column mapping and patterns
            sku = None
            price = None
            finish = None
            size = None
            description = None

            # Try column-based extraction first
            if columns.get("sku") is not None:
                sku = str(row.iloc[columns["sku"]]).strip()
            else:
                sku = self._extract_sku(row_text)

            if columns.get("price") is not None:
                price = self._extract_price(str(row.iloc[columns["price"]]))
            else:
                price = self._extract_price(row_text)

            if columns.get("finish") is not None:
                finish = str(row.iloc[columns["finish"]]).strip()
            else:
                finish = self._extract_finish(row_text)

            if columns.get("size") is not None:
                size = str(row.iloc[columns["size"]]).strip()
            else:
                size = self._extract_size(row_text)

            if columns.get("description") is not None:
                description = str(row.iloc[columns["description"]]).strip()

            # Only add if we have minimum viable data
            if sku and price and price > 0:
                product = {
                    "sku": sku,
                    "base_price": price,
                    "finish_code": finish,
                    "size": size,
                    "description": description,
                    "raw_text": row_text,
                    "page": page_num,
                    "confidence": self._calculate_product_confidence(
                        sku, price, finish, size
                    ),
                }
                products.append(product)

        return products

    def _identify_table_columns(self, df: pd.DataFrame) -> Dict[str, int]:
        """
        Identify which columns contain SKU, price, finish, etc.

        Args:
            df: DataFrame

        Returns:
            Dict mapping data type to column index
        """
        columns = {}

        # Check each column
        for col_idx, col_name in enumerate(df.columns):
            col_text = str(col_name).lower()
            first_values = " ".join(str(v) for v in df.iloc[:3, col_idx]).lower()

            # Identify column type
            if any(
                keyword in col_text or keyword in first_values
                for keyword in ["sku", "model", "item", "part"]
            ):
                columns["sku"] = col_idx
            elif any(
                keyword in col_text or keyword in first_values
                for keyword in ["price", "list", "cost", "$"]
            ):
                columns["price"] = col_idx
            elif any(
                keyword in col_text or keyword in first_values
                for keyword in ["finish", "color", "bhma"]
            ):
                columns["finish"] = col_idx
            elif any(
                keyword in col_text or keyword in first_values
                for keyword in ["size", "dimension", "width", "height", "x"]
            ):
                columns["size"] = col_idx
            elif any(
                keyword in col_text or keyword in first_values
                for keyword in ["description", "name", "type"]
            ):
                columns["description"] = col_idx

        return columns

    def _extract_sku(self, text: str) -> Optional[str]:
        """Extract SKU using patterns."""
        for pattern in self.sku_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                sku = match.group(1).strip()
                # Filter out common false positives
                if len(sku) >= 4 and not sku.lower() in ["page", "item", "bhma"]:
                    return sku
        return None

    def _extract_price(self, text: str) -> Optional[float]:
        """Extract price using patterns."""
        # First try regex patterns
        for pattern in self.price_patterns:
            match = re.search(pattern, text)
            if match:
                price_str = match.group(1).replace(",", "").replace("$", "").strip()
                try:
                    price = float(price_str)
                    # Sanity check: price should be reasonable
                    if 0.01 <= price <= 100000:
                        return price
                except ValueError:
                    continue

        # Fallback: try to parse as plain number (for table cells like "255", "1234")
        # This handles cases where img2table extracts clean numeric values
        # Try to find any standalone number in the text
        standalone_number = re.search(r'\b(\d{1,6}(?:\.\d{1,2})?)\b', text)
        if standalone_number:
            try:
                price = float(standalone_number.group(1))
                if 10 <= price <= 100000:  # Reasonable price range
                    return price
            except ValueError:
                pass

        return None

    def _extract_finish(self, text: str) -> Optional[str]:
        """Extract finish code using patterns."""
        for pattern in self.finish_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return None

    def _extract_size(self, text: str) -> Optional[str]:
        """Extract size/dimension using patterns."""
        for pattern in self.size_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return None

    def extract_prices(self, text: str) -> List[float]:
        """Extract all prices from text."""
        prices = []
        for pattern in self.price_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                price_str = match.replace(",", "").replace("$", "").strip()
                try:
                    price = float(price_str)
                    if 0.01 <= price <= 100000:
                        prices.append(price)
                except ValueError:
                    continue
        return list(set(prices))  # Remove duplicates

    def extract_finishes(self, text: str) -> List[str]:
        """Extract all finish codes from text."""
        finishes = set()
        for pattern in self.finish_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            finishes.update(m.strip() for m in matches)
        return list(finishes)

    def extract_options(self, text: str) -> List[Dict[str, Any]]:
        """Extract options/adders from text."""
        options = []
        for pattern in self.option_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                option_code = match[0].strip()
                adder_value = float(match[1])
                options.append(
                    {
                        "option_code": option_code,
                        "adder_value": adder_value,
                        "adder_type": "net_add",
                    }
                )
        return options

    def extract_effective_date(self, text: str) -> Optional[str]:
        """Extract effective date from text."""
        for pattern in self.date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _calculate_product_confidence(
        self, sku: str, price: float, finish: str, size: str
    ) -> float:
        """Calculate confidence score for extracted product."""
        confidence = 0.0

        # SKU present and reasonable
        if sku and len(sku) >= 4:
            confidence += 0.40

        # Price present and reasonable
        if price and 0.01 <= price <= 10000:
            confidence += 0.40

        # Finish code present
        if finish:
            confidence += 0.10

        # Size present
        if size:
            confidence += 0.10

        return min(confidence, 1.0)
