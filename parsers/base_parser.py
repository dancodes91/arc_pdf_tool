import re
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd
import pdfplumber
import camelot
from pdfminer.high_level import extract_text
import pytesseract
from PIL import Image
import cv2
import numpy as np


class BasePDFParser(ABC):
    """Base class for PDF parsing with common functionality"""

    def __init__(self, pdf_path: str, config: Dict[str, Any] = None):
        self.pdf_path = pdf_path
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self.pages = []
        self.tables = []
        self.text_content = ""

        # Parsing results
        self.products = []
        self.finishes = []
        self.options = []
        self.effective_date = None

    def extract_tables(self) -> List[pd.DataFrame]:
        """Extract tables from PDF using multiple methods"""
        tables = []

        try:
            # Method 1: pdfplumber (best for digital PDFs)
            tables.extend(self._extract_with_pdfplumber())

            # Method 2: camelot (good for structured tables)
            tables.extend(self._extract_with_camelot())

            # Method 3: OCR fallback if needed
            if not tables:
                self.logger.warning("No tables found with digital methods, trying OCR")
                tables.extend(self._extract_with_ocr())

        except Exception as e:
            self.logger.error(f"Error extracting tables: {e}")

        return tables

    def _extract_with_pdfplumber(self) -> List[pd.DataFrame]:
        """Extract tables using pdfplumber"""
        tables = []

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table in page_tables:
                            if table and len(table) > 1:  # Skip empty tables
                                df = pd.DataFrame(table[1:], columns=table[0])
                                df["page_number"] = page_num + 1
                                tables.append(df)

        except Exception as e:
            self.logger.error(f"Error with pdfplumber: {e}")

        return tables

    def _extract_with_camelot(self) -> List[pd.DataFrame]:
        """Extract tables using camelot"""
        tables = []

        try:
            # Try lattice method first (for tables with clear lines)
            lattice_tables = camelot.read_pdf(self.pdf_path, pages="all", flavor="lattice")

            for table in lattice_tables:
                if table.accuracy > self.config.get("min_table_confidence", 0.7):
                    df = table.df
                    df = df.replace("", np.nan).dropna(how="all")
                    if not df.empty:
                        tables.append(df)

            # Try stream method if lattice didn't work well
            if not tables:
                stream_tables = camelot.read_pdf(self.pdf_path, pages="all", flavor="stream")
                for table in stream_tables:
                    if table.accuracy > self.config.get("min_table_confidence", 0.7):
                        df = table.df
                        df = df.replace("", np.nan).dropna(how="all")
                        if not df.empty:
                            tables.append(df)

        except Exception as e:
            self.logger.error(f"Error with camelot: {e}")

        return tables

    def _extract_with_ocr(self) -> List[pd.DataFrame]:
        """Extract tables using OCR fallback"""
        tables = []

        try:
            from pdf2image import convert_from_path

            # Convert PDF to images
            images = convert_from_path(self.pdf_path)

            for page_num, image in enumerate(images):
                # Preprocess image for better OCR
                processed_image = self._preprocess_image_for_ocr(image)

                # Extract text using OCR
                ocr_text = pytesseract.image_to_string(processed_image)

                # Try to parse table-like structures from OCR text
                table_data = self._parse_ocr_table(ocr_text)
                if table_data:
                    df = pd.DataFrame(table_data)
                    df["page_number"] = page_num + 1
                    tables.append(df)

        except Exception as e:
            self.logger.error(f"Error with OCR: {e}")

        return tables

    def _preprocess_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """Preprocess image to improve OCR accuracy"""
        # Convert to numpy array
        img_array = np.array(image)

        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # Apply denoising
        denoised = cv2.fastNlMeansDenoising(gray)

        # Apply thresholding
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Convert back to PIL Image
        return Image.fromarray(thresh)

    def _parse_ocr_table(self, text: str) -> List[List[str]]:
        """Parse table-like structure from OCR text"""
        lines = text.split("\n")
        table_data = []

        for line in lines:
            # Look for lines that might be table rows
            if re.search(r"\d+\.\d+|\$\d+", line):  # Contains numbers or prices
                # Split by multiple spaces or tabs
                row = re.split(r"\s{2,}|\t", line.strip())
                if len(row) > 2:  # At least 3 columns
                    table_data.append(row)

        return table_data

    def extract_text_content(self) -> str:
        """Extract all text content from PDF"""
        try:
            self.text_content = extract_text(self.pdf_path)
            return self.text_content
        except Exception as e:
            self.logger.error(f"Error extracting text: {e}")
            return ""

    def extract_effective_date(self) -> Optional[str]:
        """Extract effective date from PDF content"""
        if not self.text_content:
            self.text_content = self.extract_text_content()

        # Common date patterns
        date_patterns = [
            r"effective\s+date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"effective[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"prices\s+effective[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, self.text_content, re.IGNORECASE)
            if matches:
                return matches[0]

        return None

    def clean_price(self, price_str: str) -> Optional[float]:
        """Clean and convert price string to float"""
        if not price_str or pd.isna(price_str):
            return None

        # Remove currency symbols and extra spaces
        cleaned = re.sub(r"[^\d.,-]", "", str(price_str))

        # Handle different decimal separators
        if "," in cleaned and "." in cleaned:
            # Assume comma is thousands separator
            cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            # Check if comma is decimal separator (last part has 1-2 digits)
            parts = cleaned.split(",")
            if len(parts) == 2 and len(parts[-1]) <= 2:
                # Assume comma is decimal separator
                cleaned = cleaned.replace(",", ".")
            else:
                # Assume comma is thousands separator
                cleaned = cleaned.replace(",", "")

        try:
            return float(cleaned)
        except ValueError:
            return None

    def clean_sku(self, sku_str: str) -> str:
        """Clean SKU string"""
        if not sku_str or pd.isna(sku_str):
            return ""

        # Remove extra whitespace and normalize
        cleaned = str(sku_str).strip().upper()

        # Remove common prefixes/suffixes that might be parsing artifacts
        cleaned = re.sub(r"^[^\w-]+", "", cleaned)
        cleaned = re.sub(r"[^\w-]+$", "", cleaned)

        return cleaned

    @abstractmethod
    def parse(self) -> Dict[str, Any]:
        """Parse the PDF and return structured data"""

    @abstractmethod
    def identify_manufacturer(self) -> str:
        """Identify the manufacturer from PDF content"""

    def validate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parsed data against requirements"""
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "accuracy_metrics": {},
        }

        # Check minimum data requirements
        if not data.get("products"):
            validation_results["is_valid"] = False
            validation_results["errors"].append("No products found")

        if not data.get("effective_date"):
            validation_results["warnings"].append("No effective date found")

        # Calculate accuracy metrics
        total_products = len(data.get("products", []))
        valid_prices = sum(1 for p in data.get("products", []) if p.get("base_price") is not None)

        if total_products > 0:
            price_accuracy = valid_prices / total_products
            validation_results["accuracy_metrics"]["price_accuracy"] = price_accuracy

            if price_accuracy < self.config.get("min_numeric_accuracy", 0.99):
                validation_results["warnings"].append(
                    f"Price accuracy below threshold: {price_accuracy:.2%}"
                )

        return validation_results
