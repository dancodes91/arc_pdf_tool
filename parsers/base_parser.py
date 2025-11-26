"""
Base PDF parser with common functionality.

This module provides the abstract base class for PDF parsing,
with shared utilities for text extraction, table processing,
and data cleaning.
"""

import re
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class BasePDFParser(ABC):
    """
    Abstract base class for PDF parsing with common functionality.
    
    Provides shared utilities for:
    - Text extraction and cleaning
    - Price and SKU normalization
    - Date extraction
    - Data validation
    
    Subclasses must implement:
    - parse(): Main parsing logic
    - identify_manufacturer(): Manufacturer detection
    """

    def __init__(self, pdf_path: str, config: Dict[str, Any] = None):
        """
        Initialize the parser.
        
        Args:
            pdf_path: Path to the PDF file
            config: Optional configuration dictionary
        """
        self.pdf_path = pdf_path
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.pages = []
        self.tables = []
        self.text_content = ""
        
        self.products = []
        self.finishes = []
        self.options = []
        self.effective_date = None

    def extract_tables(self) -> List[pd.DataFrame]:
        """
        Extract tables from PDF using the universal parser.
        
        Returns:
            List of DataFrames containing extracted tables
        """
        from parsers.universal_parser import UniversalPDFParser
        
        try:
            parser = UniversalPDFParser(self.config)
            result = parser.parse(self.pdf_path)
            
            self.tables = result.tables
            self.text_content = result.text_content
            
            return self.tables
            
        except Exception as e:
            self.logger.error(f"Error extracting tables: {e}")
            return []

    def extract_text_content(self) -> str:
        """
        Extract all text content from PDF.
        
        Returns:
            Extracted text as string
        """
        if self.text_content:
            return self.text_content
        
        try:
            from pdfminer.high_level import extract_text
            self.text_content = extract_text(self.pdf_path)
            return self.text_content
        except Exception as e:
            self.logger.error(f"Error extracting text: {e}")
            return ""

    def extract_effective_date(self) -> Optional[str]:
        """
        Extract effective date from PDF content.
        
        Returns:
            Effective date string or None
        """
        if not self.text_content:
            self.text_content = self.extract_text_content()

        date_patterns = [
            r"effective\s+date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"effective[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"prices\s+effective[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"valid\s+(?:from|as\s+of)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, self.text_content, re.IGNORECASE)
            if matches:
                self.effective_date = matches[0]
                return self.effective_date

        return None

    def clean_price(self, price_str: str) -> Optional[float]:
        """
        Clean and convert price string to float.
        
        Args:
            price_str: Raw price string (e.g., "$1,234.56")
            
        Returns:
            Float price value or None if invalid
        """
        if not price_str or pd.isna(price_str):
            return None

        cleaned = re.sub(r"[^\d.,-]", "", str(price_str))

        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            parts = cleaned.split(",")
            if len(parts) == 2 and len(parts[-1]) <= 2:
                cleaned = cleaned.replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")

        try:
            return float(cleaned)
        except ValueError:
            return None

    def clean_sku(self, sku_str: str) -> str:
        """
        Clean and normalize SKU string.
        
        Args:
            sku_str: Raw SKU string
            
        Returns:
            Cleaned SKU string
        """
        if not sku_str or pd.isna(sku_str):
            return ""

        cleaned = str(sku_str).strip().upper()

        cleaned = re.sub(r"^[^\w-]+", "", cleaned)
        cleaned = re.sub(r"[^\w-]+$", "", cleaned)

        return cleaned

    def clean_description(self, desc_str: str) -> str:
        """
        Clean and normalize description string.
        
        Args:
            desc_str: Raw description string
            
        Returns:
            Cleaned description string
        """
        if not desc_str or pd.isna(desc_str):
            return ""
        
        cleaned = " ".join(str(desc_str).split())
        
        cleaned = re.sub(r"^\s*[-•]\s*", "", cleaned)
        cleaned = cleaned.strip()
        
        return cleaned

    @abstractmethod
    def parse(self) -> Dict[str, Any]:
        """
        Parse the PDF and return structured data.
        
        Must be implemented by subclasses.
        
        Returns:
            Dictionary with parsed data including:
            - products: List of product dictionaries
            - effective_date: Effective date string
            - manufacturer: Manufacturer name
            - metadata: Additional metadata
        """
        pass

    @abstractmethod
    def identify_manufacturer(self) -> str:
        """
        Identify the manufacturer from PDF content.
        
        Must be implemented by subclasses.
        
        Returns:
            Manufacturer name string
        """
        pass

    def validate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parsed data against requirements.
        
        Args:
            data: Parsed data dictionary
            
        Returns:
            Validation results dictionary
        """
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "accuracy_metrics": {},
        }

        if not data.get("products"):
            validation_results["is_valid"] = False
            validation_results["errors"].append("No products found")

        if not data.get("effective_date"):
            validation_results["warnings"].append("No effective date found")

        total_products = len(data.get("products", []))
        valid_prices = sum(
            1 for p in data.get("products", []) 
            if p.get("base_price") is not None
        )

        if total_products > 0:
            price_accuracy = valid_prices / total_products
            validation_results["accuracy_metrics"]["price_accuracy"] = price_accuracy

            min_accuracy = self.config.get("min_numeric_accuracy", 0.99)
            if price_accuracy < min_accuracy:
                validation_results["warnings"].append(
                    f"Price accuracy below threshold: {price_accuracy:.2%}"
                )

        return validation_results

    def get_extraction_summary(self) -> Dict[str, Any]:
        """
        Get summary of extraction results.
        
        Returns:
            Summary dictionary with statistics
        """
        return {
            "pdf_path": self.pdf_path,
            "pages_processed": len(self.pages) if self.pages else 0,
            "tables_extracted": len(self.tables),
            "products_found": len(self.products),
            "effective_date": self.effective_date,
            "text_length": len(self.text_content),
        }
