"""
Enhanced PDF I/O utilities with multiple extraction methods.
"""

import os
import re
import io
import logging
from typing import List, Dict, Any
from dataclasses import dataclass

import fitz  # PyMuPDF
import pdfplumber
import camelot
import pandas as pd
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import cv2
import numpy as np

from .confidence import confidence_scorer, ConfidenceScore


logger = logging.getLogger(__name__)


def _confidence_value(conf) -> float:
    if hasattr(conf, "score"):
        return float(conf.score)
    if isinstance(conf, (int, float)):
        return float(conf)
    return 0.0


@dataclass
class PDFPage:
    """Container for PDF page data."""

    page_number: int
    text: str
    tables: List[pd.DataFrame]
    images: List[Image.Image]
    bbox_info: Dict[str, Any]
    extraction_method: str
    confidence: ConfidenceScore


@dataclass
class PDFDocument:
    """Container for entire PDF document."""

    file_path: str
    pages: List[PDFPage]
    metadata: Dict[str, Any]
    total_confidence: ConfidenceScore


class EnhancedPDFExtractor:
    """Enhanced PDF extraction with multiple methods and confidence scoring."""

    def __init__(self, pdf_path: str, config: Dict[str, Any] = None):
        self.pdf_path = pdf_path
        self.config = config or {}
        self.logger = logging.getLogger(f"{__class__.__name__}")

        # Extraction method preferences
        self.method_priority = [
            "pymupdf_digital",
            "pdfplumber_digital",
            "camelot_lattice",
            "camelot_stream",
            "ocr_tesseract",
        ]

        # Validate file exists
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    def extract_document(self) -> PDFDocument:
        """Extract complete document with all pages."""
        self.logger.info(f"Starting extraction of {self.pdf_path}")

        pages = []
        document_metadata = self._get_document_metadata()

        # Determine total pages
        total_pages = self._get_page_count()
        max_pages = self.config.get("max_pages_to_process", 1000)
        pages_to_process = min(total_pages, max_pages)

        self.logger.info(f"Processing {pages_to_process} of {total_pages} pages")

        for page_num in range(pages_to_process):
            try:
                page = self._extract_page(page_num)
                pages.append(page)

                if page_num % 10 == 0:  # Progress logging
                    self.logger.info(f"Processed page {page_num + 1}/{pages_to_process}")

            except Exception as e:
                self.logger.error(f"Error processing page {page_num + 1}: {e}")
                # Create empty page to maintain indexing
                empty_page = PDFPage(
                    page_number=page_num + 1,
                    text="",
                    tables=[],
                    images=[],
                    bbox_info={},
                    extraction_method="failed",
                    confidence=confidence_scorer.score_extraction_method("failed"),
                )
                pages.append(empty_page)

        # Calculate overall document confidence
        if pages:
            avg_confidence = sum(_confidence_value(p.confidence) for p in pages) / len(pages)
            total_confidence = confidence_scorer.score_extraction_method(
                "document_average", avg_confidence
            )
        else:
            total_confidence = confidence_scorer.score_extraction_method("failed")

        return PDFDocument(
            file_path=self.pdf_path,
            pages=pages,
            metadata=document_metadata,
            total_confidence=total_confidence,
        )

    def _get_document_metadata(self) -> Dict[str, Any]:
        """Extract document metadata."""
        metadata = {
            "file_size": os.path.getsize(self.pdf_path),
            "file_name": os.path.basename(self.pdf_path),
        }

        try:
            # Try PyMuPDF for metadata
            doc = fitz.open(self.pdf_path)
            fitz_metadata = doc.metadata
            metadata.update(
                {
                    "title": fitz_metadata.get("title", ""),
                    "author": fitz_metadata.get("author", ""),
                    "creator": fitz_metadata.get("creator", ""),
                    "producer": fitz_metadata.get("producer", ""),
                    "creation_date": fitz_metadata.get("creationDate", ""),
                    "modification_date": fitz_metadata.get("modDate", ""),
                    "is_encrypted": doc.is_encrypted,
                    "page_count": doc.page_count,
                }
            )
            doc.close()
        except Exception as e:
            self.logger.warning(f"Could not extract metadata with PyMuPDF: {e}")

        return metadata

    def _get_page_count(self) -> int:
        """Get total page count."""
        try:
            doc = fitz.open(self.pdf_path)
            count = doc.page_count
            doc.close()
            return count
        except Exception:
            try:
                with pdfplumber.open(self.pdf_path) as pdf:
                    return len(pdf.pages)
            except Exception:
                return 1  # Fallback

    def _extract_page(self, page_num: int) -> PDFPage:
        """Extract single page with best available method."""

        for method in self.method_priority:
            try:
                if method == "pymupdf_digital":
                    return self._extract_page_pymupdf(page_num)
                elif method == "pdfplumber_digital":
                    return self._extract_page_pdfplumber(page_num)
                elif method == "camelot_lattice":
                    return self._extract_page_camelot(page_num, flavor="lattice")
                elif method == "camelot_stream":
                    return self._extract_page_camelot(page_num, flavor="stream")
                elif method == "ocr_tesseract":
                    return self._extract_page_ocr(page_num)

            except Exception as e:
                self.logger.warning(f"Method {method} failed for page {page_num + 1}: {e}")
                continue

        # If all methods fail, create empty page
        return PDFPage(
            page_number=page_num + 1,
            text="",
            tables=[],
            images=[],
            bbox_info={},
            extraction_method="failed",
            confidence=confidence_scorer.score_extraction_method("failed"),
        )

    def _extract_page_pymupdf(self, page_num: int) -> PDFPage:
        """Extract page using PyMuPDF (fast, good for digital PDFs)."""
        doc = fitz.open(self.pdf_path)
        page = doc.load_page(page_num)

        # Extract text
        text = page.get_text()

        # Extract text with bounding boxes
        bbox_info = {}
        page.get_text("dict")

        # Extract images
        images = []
        image_list = page.get_images()
        for img_index, img in enumerate(image_list):
            try:
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)

                # Convert CMYK to RGB if needed
                if pix.n - pix.alpha > 3:  # CMYK or other color space
                    pix = fitz.Pixmap(fitz.csRGB, pix)  # Convert to RGB

                # Now save as PNG
                if pix.n - pix.alpha < 4:  # GRAY or RGB
                    img_data = pix.tobytes("png")
                    images.append(Image.open(io.BytesIO(img_data)))
                pix = None
            except Exception as e:
                # Only log if it's not the common CMYK issue
                if "pixmap must be grayscale or rgb" not in str(e):
                    self.logger.warning(f"Could not extract image {img_index}: {e}")

        # Try to extract tables (basic table detection)
        tables = self._detect_tables_from_text(text)

        doc.close()

        # Calculate confidence
        confidence = confidence_scorer.score_extraction_method(
            "pymupdf_digital", self._calculate_text_quality(text)
        )

        return PDFPage(
            page_number=page_num + 1,
            text=text,
            tables=tables,
            images=images,
            bbox_info=bbox_info,
            extraction_method="pymupdf_digital",
            confidence=confidence,
        )

    def _extract_page_pdfplumber(self, page_num: int) -> PDFPage:
        """Extract page using pdfplumber (good for tables)."""
        with pdfplumber.open(self.pdf_path) as pdf:
            page = pdf.pages[page_num]

            # Extract text
            text = page.extract_text() or ""

            # Extract tables
            tables = []
            page_tables = page.extract_tables()

            if page_tables:
                for table_data in page_tables:
                    if table_data and len(table_data) > 1:
                        try:
                            # Create DataFrame with first row as headers
                            headers = (
                                table_data[0]
                                if table_data[0]
                                else [f"col_{i}" for i in range(len(table_data[0]))]
                            )
                            df = pd.DataFrame(table_data[1:], columns=headers)

                            # Clean empty rows/columns
                            df = df.dropna(how="all").reset_index(drop=True)
                            df = df.loc[:, df.notna().any()]

                            if not df.empty:
                                tables.append(df)

                        except Exception as e:
                            self.logger.warning(f"Could not create DataFrame from table: {e}")

            # Extract bounding box info
            bbox_info = {"chars": page.chars, "words": page.extract_words(), "page_bbox": page.bbox}

        # Calculate confidence based on table extraction success
        table_quality = len(tables) / max(1, len(page_tables or []))
        confidence = confidence_scorer.score_extraction_method("pdfplumber_digital", table_quality)

        return PDFPage(
            page_number=page_num + 1,
            text=text,
            tables=tables,
            images=[],
            bbox_info=bbox_info,
            extraction_method="pdfplumber_digital",
            confidence=confidence,
        )

    def _extract_page_camelot(self, page_num: int, flavor: str = "lattice") -> PDFPage:
        """Extract page using Camelot (specialized for tables)."""
        page_str = str(page_num + 1)

        # Extract tables using Camelot
        tables = []
        table_quality = 0.0

        try:
            camelot_tables = camelot.read_pdf(self.pdf_path, pages=page_str, flavor=flavor)

            quality_scores = []
            for table in camelot_tables:
                if table.accuracy > self.config.get("min_table_confidence", 0.7):
                    df = table.df
                    # Clean the table
                    df = df.replace("", pd.NA).dropna(how="all")
                    df = df.loc[:, df.notna().any()]

                    if not df.empty:
                        tables.append(df)
                        quality_scores.append(table.accuracy)

            table_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        except Exception as e:
            self.logger.warning(f"Camelot {flavor} extraction failed: {e}")

        # Extract basic text (Camelot doesn't extract full text)
        text = ""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                if page_num < len(pdf.pages):
                    text = pdf.pages[page_num].extract_text() or ""
        except Exception:
            pass

        method_name = f"camelot_{flavor}"
        confidence = confidence_scorer.score_extraction_method(method_name, table_quality)

        return PDFPage(
            page_number=page_num + 1,
            text=text,
            tables=tables,
            images=[],
            bbox_info={},
            extraction_method=method_name,
            confidence=confidence,
        )

    def _extract_page_ocr(self, page_num: int) -> PDFPage:
        """Extract page using OCR (fallback for scanned PDFs)."""
        try:
            # Convert PDF page to image
            images = convert_from_path(
                self.pdf_path, first_page=page_num + 1, last_page=page_num + 1, dpi=300
            )

            if not images:
                raise ValueError("No image generated from PDF page")

            image = images[0]

            # Preprocess image for better OCR
            processed_image = self._preprocess_for_ocr(image)

            # Extract text using OCR
            text = pytesseract.image_to_string(processed_image)

            # Try to extract tables from OCR text
            tables = self._detect_tables_from_text(text)

            # OCR confidence based on text quality
            ocr_quality = self._calculate_text_quality(text)
            confidence = confidence_scorer.score_extraction_method("ocr_tesseract", ocr_quality)

            return PDFPage(
                page_number=page_num + 1,
                text=text,
                tables=tables,
                images=[image],
                bbox_info={},
                extraction_method="ocr_tesseract",
                confidence=confidence,
            )

        except Exception as e:
            self.logger.error(f"OCR extraction failed: {e}")
            raise

    def _preprocess_for_ocr(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results."""
        # Convert PIL to OpenCV format
        img_array = np.array(image)

        # Convert to grayscale if needed
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # Apply denoising
        denoised = cv2.fastNlMeansDenoising(gray)

        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Morphological operations to clean up
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        return Image.fromarray(cleaned)

    def _detect_tables_from_text(self, text: str) -> List[pd.DataFrame]:
        """Attempt to detect table structures from plain text."""
        tables = []

        if not text:
            return tables

        lines = text.split("\n")

        # Look for lines that might be table rows (contain multiple fields)
        potential_rows = []
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for lines with multiple "fields" (separated by whitespace or tabs)
            fields = [f.strip() for f in re.split(r"\s{2,}|\t", line) if f.strip()]

            # Heuristic: likely table row if has 3+ fields with at least one number
            if len(fields) >= 3 and any(re.search(r"\d", field) for field in fields):
                potential_rows.append(fields)

        # If we found potential rows, try to create a table
        if len(potential_rows) >= 2:  # At least header + 1 data row
            try:
                # Use first row as headers, rest as data
                max_cols = max(len(row) for row in potential_rows)

                # Pad rows to same length
                normalized_rows = []
                for row in potential_rows:
                    padded_row = row + [""] * (max_cols - len(row))
                    normalized_rows.append(padded_row[:max_cols])

                if len(normalized_rows) > 1:
                    headers = normalized_rows[0]
                    data = normalized_rows[1:]

                    df = pd.DataFrame(data, columns=headers)
                    df = df.dropna(how="all").reset_index(drop=True)

                    if not df.empty:
                        tables.append(df)

            except Exception as e:
                self.logger.warning(f"Could not create table from text: {e}")

        return tables

    def _calculate_text_quality(self, text: str) -> float:
        """Calculate text quality score (0.0 to 1.0)."""
        if not text:
            return 0.0

        # Basic quality indicators
        total_chars = len(text)
        if total_chars == 0:
            return 0.0

        # Count recognizable words vs garbage characters
        words = text.split()
        recognizable_words = sum(1 for word in words if re.match(r"^[A-Za-z0-9$.,%-]+$", word))
        word_quality = recognizable_words / max(1, len(words))

        # Check for common OCR errors
        error_chars = sum(1 for char in text if char in "|§¦¨©«»°±²³")
        error_penalty = min(0.3, error_chars / total_chars)

        # Check for reasonable line structure
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        avg_line_length = sum(len(line) for line in lines) / max(1, len(lines))
        structure_score = min(1.0, avg_line_length / 50) if avg_line_length > 0 else 0

        quality = (word_quality * 0.6) + (structure_score * 0.4) - error_penalty
        return max(0.0, min(1.0, quality))


# Import fix for missing io
import io
