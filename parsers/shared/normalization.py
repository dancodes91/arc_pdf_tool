"""
Data normalization utilities for consistent data processing.
"""

import re
import logging
from typing import Optional, Dict, Any, Union
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
import pandas as pd

from .confidence import confidence_scorer, ConfidenceScore


logger = logging.getLogger(__name__)


class DataNormalizer:
    """Normalize parsed data to consistent formats."""

    def __init__(self):
        # Price patterns
        self.price_patterns = [
            r"^\$?([0-9,]+\.?[0-9]*)$",  # $123.45 or 123.45
            r"^([0-9,]+\.?[0-9]*)\s*\$?$",  # 123.45$ or 123.45
        ]

        # SKU patterns for different manufacturers
        self.sku_patterns = {
            "hager": [
                r"^([A-Z]{2,4}[0-9]{2,6}[A-Z]?)$",  # ABC123, ABCD1234A
                r"^([A-Z]+[0-9-]+[A-Z]*)$",  # ABC-123-A
            ],
            "select_hinges": [
                r"^(SL[0-9]{2}[A-Z]*)$",  # SL11, SL24A
                r"^([A-Z]{2,4}[0-9-]+)$",  # CTW-4, EPT-5
            ],
            "generic": [
                r"^([A-Z0-9-]{3,20})$",  # Generic alphanumeric SKU
            ],
        }

        # Date patterns
        self.date_patterns = [
            r"effective\s+(\w+\s+\d{1,2},?\s+\d{4})",  # "effective January 1, 2024"
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",  # MM/DD/YYYY or MM-DD-YYYY
            r"(\w+\s+\d{1,2},?\s+\d{4})",  # "January 1, 2024"
        ]

        # Unit of measure mappings
        self.uom_mappings = {
            "each": "EA",
            "ea": "EA",
            "piece": "EA",
            "pcs": "EA",
            "set": "SET",
            "pair": "PR",
            "dozen": "DZ",
            "doz": "DZ",
            "linear foot": "LF",
            "lf": "LF",
            "square foot": "SF",
            "sf": "SF",
        }

        # Finish code mappings (BHMA standard)
        self.finish_mappings = {
            "US3": {"bhma": "US3", "name": "Satin Chrome", "alt_codes": ["SC", "CR3"]},
            "US4": {"bhma": "US4", "name": "Bright Chrome", "alt_codes": ["BC", "CR4"]},
            "US10B": {"bhma": "US10B", "name": "Satin Bronze", "alt_codes": ["SB", "BR10B"]},
            "US15": {"bhma": "US15", "name": "Satin Brass", "alt_codes": ["SBR", "BR15"]},
            "US26D": {"bhma": "US26D", "name": "Oil Rubbed Bronze", "alt_codes": ["ORB", "RB"]},
            "US32D": {"bhma": "US32D", "name": "Antique Brass", "alt_codes": ["AB", "ANT"]},
            "US33D": {"bhma": "US33D", "name": "Antique Copper", "alt_codes": ["AC", "COP"]},
        }

    def normalize_price(
        self, price_input: Union[str, float, int], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Normalize price value to decimal format."""
        result = {
            "value": None,
            "currency": "USD",
            "confidence": None,
            "raw_input": str(price_input),
            "errors": [],
        }

        if price_input is None or pd.isna(price_input):
            result["errors"].append("No price value provided")
            result["confidence"] = confidence_scorer.score_price_value("", context)
            return result

        # Convert to string for processing
        price_str = str(price_input).strip()

        # Try to extract numeric value
        cleaned_price = None
        for pattern in self.price_patterns:
            match = re.match(pattern, price_str, re.IGNORECASE)
            if match:
                cleaned_price = match.group(1).replace(",", "")
                break

        if not cleaned_price:
            # Fallback: extract any numeric value
            numeric_match = re.search(r"([0-9,]+\.?[0-9]*)", price_str)
            if numeric_match:
                cleaned_price = numeric_match.group(1).replace(",", "")

        if cleaned_price:
            try:
                price_decimal = Decimal(cleaned_price)
                result["value"] = price_decimal
                result["confidence"] = confidence_scorer.score_price_value(price_str, context)
            except InvalidOperation:
                result["errors"].append(f"Could not convert '{cleaned_price}' to decimal")
                result["confidence"] = confidence_scorer.score_price_value("", context)
        else:
            result["errors"].append(f"Could not extract numeric value from '{price_str}'")
            result["confidence"] = confidence_scorer.score_price_value("", context)

        return result

    def normalize_sku(self, sku_input: str, manufacturer: str = None) -> Dict[str, Any]:
        """Normalize SKU/model code."""
        result = {
            "value": None,
            "manufacturer": manufacturer,
            "confidence": None,
            "raw_input": str(sku_input),
            "errors": [],
        }

        if not sku_input or pd.isna(sku_input):
            result["errors"].append("No SKU value provided")
            result["confidence"] = confidence_scorer.score_sku_value("", manufacturer)
            return result

        sku_str = str(sku_input).strip().upper()

        # Select patterns based on manufacturer
        patterns_to_try = []
        if manufacturer and manufacturer.lower() in self.sku_patterns:
            patterns_to_try.extend(self.sku_patterns[manufacturer.lower()])
        patterns_to_try.extend(self.sku_patterns["generic"])

        # Try to match patterns
        matched = False
        for pattern in patterns_to_try:
            match = re.match(pattern, sku_str)
            if match:
                result["value"] = match.group(1)
                matched = True
                break

        if not matched:
            # If no pattern matches, clean and use as-is if reasonable
            cleaned_sku = re.sub(r"[^A-Z0-9-]", "", sku_str)
            if 2 <= len(cleaned_sku) <= 20:
                result["value"] = cleaned_sku
            else:
                result["errors"].append(f"SKU '{sku_str}' doesn't match expected patterns")

        result["confidence"] = confidence_scorer.score_sku_value(
            result["value"] or sku_str, manufacturer
        )

        return result

    def normalize_date(self, date_input: str) -> Dict[str, Any]:
        """Normalize date string to standard format."""
        result = {
            "value": None,
            "format": None,
            "confidence": None,
            "raw_input": str(date_input),
            "errors": [],
        }

        if not date_input or pd.isna(date_input):
            result["errors"].append("No date value provided")
            result["confidence"] = confidence_scorer.score_effective_date("")
            return result

        date_str = str(date_input).strip()

        # Try different date patterns
        extracted_date = None
        for pattern in self.date_patterns:
            match = re.search(pattern, date_str, re.IGNORECASE)
            if match:
                extracted_date = match.group(1).strip()
                break

        if extracted_date:
            # Try to parse the date
            parsed_date = self._parse_date_string(extracted_date)
            if parsed_date:
                result["value"] = parsed_date
                result["format"] = "date"
            else:
                result["errors"].append(f"Could not parse date: '{extracted_date}'")
        else:
            result["errors"].append(f"No date pattern matched in: '{date_str}'")

        result["confidence"] = confidence_scorer.score_effective_date(date_str)
        return result

    def normalize_finish_code(self, finish_input: str) -> Dict[str, Any]:
        """Normalize finish code to BHMA standard."""
        result = {
            "code": None,
            "bhma_code": None,
            "name": None,
            "confidence": None,
            "raw_input": str(finish_input),
            "errors": [],
        }

        if not finish_input or pd.isna(finish_input):
            result["errors"].append("No finish code provided")
            return result

        finish_str = str(finish_input).strip().upper()

        # Direct BHMA code match
        if finish_str in self.finish_mappings:
            mapping = self.finish_mappings[finish_str]
            result.update(
                {"code": finish_str, "bhma_code": mapping["bhma"], "name": mapping["name"]}
            )
            return result

        # Check alternative codes
        for bhma_code, mapping in self.finish_mappings.items():
            if finish_str in mapping["alt_codes"]:
                result.update(
                    {"code": finish_str, "bhma_code": mapping["bhma"], "name": mapping["name"]}
                )
                return result

        # If no match found, keep original
        result.update({"code": finish_str, "bhma_code": None, "name": None})
        result["errors"].append(f"Finish code '{finish_str}' not recognized")

        return result

    def normalize_unit_of_measure(self, uom_input: str) -> Dict[str, Any]:
        """Normalize unit of measure."""
        result = {"code": None, "name": None, "raw_input": str(uom_input), "errors": []}

        if not uom_input or pd.isna(uom_input):
            result["code"] = "EA"  # Default to each
            result["name"] = "Each"
            return result

        uom_str = str(uom_input).strip().lower()

        # Check mappings
        if uom_str in self.uom_mappings:
            result["code"] = self.uom_mappings[uom_str]
            result["name"] = uom_str.title()
        else:
            # Use as-is if not recognized
            result["code"] = uom_str.upper()[:10]  # Limit length
            result["name"] = uom_str.title()
            result["errors"].append(f"UOM '{uom_str}' not recognized, using as-is")

        return result

    def normalize_description(self, desc_input: str) -> Dict[str, Any]:
        """Normalize product description."""
        result = {"value": None, "cleaned": None, "raw_input": str(desc_input), "errors": []}

        if not desc_input or pd.isna(desc_input):
            result["errors"].append("No description provided")
            return result

        desc_str = str(desc_input).strip()

        # Basic cleaning
        cleaned = re.sub(r"\s+", " ", desc_str)  # Normalize whitespace
        cleaned = re.sub(r"[^\w\s\-.,()&/]", "", cleaned)  # Remove special chars

        result.update({"value": desc_str, "cleaned": cleaned})

        return result

    def _parse_date_string(self, date_str: str) -> Optional[date]:
        """Parse date string using various formats."""
        # Common date formats to try
        formats = [
            "%B %d, %Y",  # January 1, 2024
            "%b %d, %Y",  # Jan 1, 2024
            "%B %d %Y",  # January 1 2024
            "%m/%d/%Y",  # 01/01/2024
            "%m-%d-%Y",  # 01-01-2024
            "%m/%d/%y",  # 01/01/24
            "%m-%d-%y",  # 01-01-24
            "%Y-%m-%d",  # 2024-01-01
        ]

        for format_str in formats:
            try:
                parsed = datetime.strptime(date_str.strip(), format_str).date()
                return parsed
            except ValueError:
                continue

        return None

    def validate_normalized_data(self, data: Dict[str, Any], data_type: str) -> ConfidenceScore:
        """Validate normalized data and return confidence score."""
        if data_type == "price":
            if data.get("value") and not data.get("errors"):
                return ConfidenceScore(0.9, None, ["Successfully normalized price"])
            else:
                return ConfidenceScore(0.3, None, data.get("errors", []))

        elif data_type == "sku":
            if data.get("value") and not data.get("errors"):
                return ConfidenceScore(0.9, None, ["Successfully normalized SKU"])
            else:
                return ConfidenceScore(0.4, None, data.get("errors", []))

        elif data_type == "date":
            if data.get("value") and not data.get("errors"):
                return ConfidenceScore(0.95, None, ["Successfully parsed date"])
            else:
                return ConfidenceScore(0.2, None, data.get("errors", []))

        else:
            return ConfidenceScore(0.5, None, ["Unknown data type"])


# Global normalizer instance
data_normalizer = DataNormalizer()
