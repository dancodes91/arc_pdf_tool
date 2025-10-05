"""
OCR fallback processor for PDF parsing.

Handles OCR extraction when native text extraction fails or produces
insufficient results, with preprocessing and confidence routing.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import pandas as pd

try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    from pdf2image import convert_from_path

    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Result of OCR processing."""

    text: str
    confidence: float
    word_confidences: List[Tuple[str, float]]  # (word, confidence)
    preprocessing_applied: List[str]
    method: str  # tesseract, cloud_api, etc.
    bbox_data: Optional[List[Dict]] = None  # Word-level bounding boxes


@dataclass
class OCRConfig:
    """OCR processing configuration."""

    engine: str = "tesseract"
    psm: int = 6  # Page segmentation mode
    oem: int = 3  # OCR Engine Mode
    config_string: str = "--psm 6"
    preprocess: bool = True
    enhance_contrast: bool = True
    denoise: bool = True
    deskew: bool = False
    language: str = "eng"
    dpi: int = 300


class OCRProcessor:
    """
    OCR processor with fallback capabilities.

    Handles image preprocessing, OCR extraction, and confidence-based
    routing for pages where native text extraction fails.
    """

    def __init__(self, config: Optional[OCRConfig] = None):
        self.config = config or OCRConfig()
        self.logger = logging.getLogger(__name__)

        if not TESSERACT_AVAILABLE:
            self.logger.warning(
                "OCR dependencies not available. Install with: pip install pytesseract pillow pdf2image"
            )

        # Verify Tesseract installation
        self._verify_tesseract()

    def _verify_tesseract(self):
        """Verify Tesseract is available."""
        if not TESSERACT_AVAILABLE:
            return

        try:
            pytesseract.get_tesseract_version()
            self.logger.info(f"Tesseract version: {pytesseract.get_tesseract_version()}")
        except Exception as e:
            self.logger.error(f"Tesseract not available: {e}")
            self.logger.info("Install Tesseract: https://github.com/tesseract-ocr/tesseract")

    def should_use_ocr(
        self, text: str, tables: List, text_threshold: int = 50, table_threshold: float = 0.3
    ) -> bool:
        """
        Determine if OCR should be used based on extraction quality.

        Args:
            text: Extracted text from native methods
            tables: Extracted tables
            text_threshold: Minimum text length
            table_threshold: Minimum table confidence

        Returns:
            True if OCR should be used
        """
        # Trigger OCR if very little text
        if len(text.strip()) < text_threshold:
            self.logger.info("OCR triggered: insufficient text")
            return True

        # Trigger OCR if expected tables but none found
        text_lower = text.lower()
        table_indicators = ["model", "price", "description", "series", "$"]
        has_table_indicators = any(indicator in text_lower for indicator in table_indicators)

        if has_table_indicators and len(tables) == 0:
            self.logger.info("OCR triggered: table indicators found but no tables extracted")
            return True

        # Trigger OCR if tables have very low confidence
        if tables:
            avg_confidence = sum(getattr(table, "confidence", 1.0) for table in tables) / len(
                tables
            )
            if avg_confidence < table_threshold:
                self.logger.info(f"OCR triggered: low table confidence {avg_confidence}")
                return True

        return False

    def extract_text_from_pdf_page(self, pdf_path: str, page_number: int) -> OCRResult:
        """
        Extract text from a PDF page using OCR.

        Args:
            pdf_path: Path to PDF file
            page_number: Page number (1-based)

        Returns:
            OCRResult with extracted text and metadata
        """
        if not TESSERACT_AVAILABLE:
            return OCRResult(
                text="",
                confidence=0.0,
                word_confidences=[],
                preprocessing_applied=["ERROR: OCR not available"],
                method="none",
            )

        try:
            # Convert PDF page to image
            images = convert_from_path(
                pdf_path, first_page=page_number, last_page=page_number, dpi=self.config.dpi
            )

            if not images:
                raise ValueError(f"Could not convert page {page_number} to image")

            image = images[0]

            # Preprocess image if enabled
            preprocessing_applied = []
            if self.config.preprocess:
                image, preprocessing_steps = self._preprocess_image(image)
                preprocessing_applied.extend(preprocessing_steps)

            # Extract text with confidence
            result = self._extract_text_with_confidence(image)
            result.preprocessing_applied = preprocessing_applied

            return result

        except Exception as e:
            self.logger.error(f"OCR extraction failed for page {page_number}: {e}")
            return OCRResult(
                text="",
                confidence=0.0,
                word_confidences=[],
                preprocessing_applied=[f"ERROR: {str(e)}"],
                method="tesseract",
            )

    def _preprocess_image(self, image: Image.Image) -> Tuple[Image.Image, List[str]]:
        """
        Preprocess image for better OCR results.

        Args:
            image: Input PIL Image

        Returns:
            Tuple of (processed_image, preprocessing_steps)
        """
        processed = image.copy()
        steps = []

        # Convert to grayscale
        if processed.mode != "L":
            processed = processed.convert("L")
            steps.append("converted_to_grayscale")

        # Enhance contrast
        if self.config.enhance_contrast:
            enhancer = ImageEnhance.Contrast(processed)
            processed = enhancer.enhance(1.5)
            steps.append("enhanced_contrast")

        # Denoise
        if self.config.denoise:
            processed = processed.filter(ImageFilter.MedianFilter(size=3))
            steps.append("denoised")

        # Resize if too small (OCR works better on larger images)
        width, height = processed.size
        if width < 1200 or height < 1600:
            scale_factor = max(1200 / width, 1600 / height)
            new_size = (int(width * scale_factor), int(height * scale_factor))
            processed = processed.resize(new_size, Image.Resampling.LANCZOS)
            steps.append(f"resized_{scale_factor:.1f}x")

        # Threshold to binary (black and white)
        # Find optimal threshold using Otsu's method approximation
        histogram = processed.histogram()
        sum(histogram)

        # Simple threshold - can be improved with actual Otsu's method
        threshold = 128
        processed = processed.point(lambda x: 255 if x > threshold else 0, mode="1")
        steps.append("binary_threshold")

        return processed, steps

    def _extract_text_with_confidence(self, image: Image.Image) -> OCRResult:
        """
        Extract text with word-level confidence scores.

        Args:
            image: Preprocessed PIL Image

        Returns:
            OCRResult with text and confidence data
        """
        try:
            # Get detailed OCR data with confidence
            custom_config = (
                f"--oem {self.config.oem} --psm {self.config.psm} -l {self.config.language}"
            )

            # Extract text
            text = pytesseract.image_to_string(image, config=custom_config)

            # Extract word-level confidence data
            data = pytesseract.image_to_data(
                image, config=custom_config, output_type=pytesseract.Output.DICT
            )

            # Process confidence data
            word_confidences = []
            bbox_data = []

            for i in range(len(data["text"])):
                word = data["text"][i].strip()
                conf = float(data["conf"][i])

                if word and conf > 0:  # Only include words with positive confidence
                    word_confidences.append((word, conf / 100.0))  # Normalize to 0-1

                    # Store bounding box data
                    bbox_data.append(
                        {
                            "word": word,
                            "confidence": conf / 100.0,
                            "left": data["left"][i],
                            "top": data["top"][i],
                            "width": data["width"][i],
                            "height": data["height"][i],
                        }
                    )

            # Calculate overall confidence
            if word_confidences:
                overall_confidence = sum(conf for _, conf in word_confidences) / len(
                    word_confidences
                )
            else:
                overall_confidence = 0.0

            return OCRResult(
                text=text,
                confidence=overall_confidence,
                word_confidences=word_confidences,
                preprocessing_applied=[],  # Will be set by caller
                method="tesseract",
                bbox_data=bbox_data,
            )

        except Exception as e:
            self.logger.error(f"Tesseract extraction failed: {e}")
            return OCRResult(
                text="",
                confidence=0.0,
                word_confidences=[],
                preprocessing_applied=[f"ERROR: {str(e)}"],
                method="tesseract",
            )

    def extract_tables_from_ocr(
        self, ocr_result: OCRResult, page_number: int = 0
    ) -> List[pd.DataFrame]:
        """
        Extract tables from OCR text using layout analysis.

        Args:
            ocr_result: OCR extraction result
            page_number: Page number for context

        Returns:
            List of DataFrames representing detected tables
        """
        if not ocr_result.text or not ocr_result.bbox_data:
            return []

        tables = []

        try:
            # Analyze word positions to detect table structure
            words_with_pos = sorted(ocr_result.bbox_data, key=lambda x: (x["top"], x["left"]))

            # Group words into lines based on vertical position
            lines = self._group_words_into_lines(words_with_pos)

            # Detect table regions
            table_regions = self._detect_table_regions(lines)

            # Extract tables from regions
            for region in table_regions:
                table_df = self._extract_table_from_region(region)
                if not table_df.empty:
                    tables.append(table_df)

        except Exception as e:
            self.logger.error(f"Table extraction from OCR failed: {e}")

        return tables

    def _group_words_into_lines(
        self, words: List[Dict], line_tolerance: int = 10
    ) -> List[List[Dict]]:
        """
        Group words into lines based on vertical position.

        Args:
            words: List of word dictionaries with position data
            line_tolerance: Tolerance for grouping words into same line

        Returns:
            List of lines, each containing word dictionaries
        """
        if not words:
            return []

        lines = []
        current_line = [words[0]]
        current_top = words[0]["top"]

        for word in words[1:]:
            # Check if word is on same line
            if abs(word["top"] - current_top) <= line_tolerance:
                current_line.append(word)
            else:
                # Start new line
                if current_line:
                    # Sort words in line by horizontal position
                    current_line.sort(key=lambda x: x["left"])
                    lines.append(current_line)

                current_line = [word]
                current_top = word["top"]

        # Add last line
        if current_line:
            current_line.sort(key=lambda x: x["left"])
            lines.append(current_line)

        return lines

    def _detect_table_regions(self, lines: List[List[Dict]]) -> List[List[List[Dict]]]:
        """
        Detect table regions from grouped lines.

        Args:
            lines: Lines of words with position data

        Returns:
            List of table regions (each region is a list of lines)
        """
        if len(lines) < 2:
            return []

        table_regions = []
        current_region = []

        for i, line in enumerate(lines):
            # Check if this line looks like part of a table
            if self._line_looks_tabular(line, lines):
                current_region.append(line)
            else:
                # End current region if it has enough lines
                if len(current_region) >= 2:
                    table_regions.append(current_region)
                current_region = []

        # Add final region
        if len(current_region) >= 2:
            table_regions.append(current_region)

        return table_regions

    def _line_looks_tabular(self, line: List[Dict], all_lines: List[List[Dict]]) -> bool:
        """
        Check if a line appears to be part of a table.

        Args:
            line: Line to check
            all_lines: All lines for context

        Returns:
            True if line appears tabular
        """
        if len(line) < 2:
            return False

        # Check for tabular indicators
        line_text = " ".join(word["word"] for word in line).lower()

        # Table headers
        table_keywords = ["model", "price", "description", "series", "size", "qty"]
        has_table_keywords = any(keyword in line_text for keyword in table_keywords)

        # Numeric data (prices, quantities)
        has_numbers = bool(re.search(r"\$\d+|\d+\.\d{2}|\d+", line_text))

        # Regular spacing (words are somewhat evenly distributed)
        if len(line) >= 3:
            positions = [word["left"] for word in line]
            gaps = [positions[i + 1] - positions[i] for i in range(len(positions) - 1)]
            avg_gap = sum(gaps) / len(gaps) if gaps else 0
            regular_spacing = (
                all(abs(gap - avg_gap) < avg_gap * 0.5 for gap in gaps) if avg_gap > 0 else False
            )
        else:
            regular_spacing = False

        # Combine indicators
        tabular_score = sum(
            [has_table_keywords, has_numbers, regular_spacing, len(line) >= 3]  # Multiple columns
        )

        return tabular_score >= 2

    def _extract_table_from_region(self, region: List[List[Dict]]) -> pd.DataFrame:
        """
        Extract a DataFrame from a table region.

        Args:
            region: Table region (list of lines)

        Returns:
            DataFrame representing the table
        """
        if not region:
            return pd.DataFrame()

        # Determine column boundaries by analyzing word positions
        all_lefts = []
        for line in region:
            all_lefts.extend(word["left"] for word in line)

        if not all_lefts:
            return pd.DataFrame()

        # Find column boundaries using clustering
        sorted_lefts = sorted(set(all_lefts))
        column_boundaries = self._find_column_boundaries(sorted_lefts)

        # Extract data into table structure
        table_data = []
        for line in region:
            row_data = [""] * len(column_boundaries)

            for word in line:
                # Find which column this word belongs to
                col_idx = self._find_column_index(word["left"], column_boundaries)
                if 0 <= col_idx < len(row_data):
                    if row_data[col_idx]:
                        row_data[col_idx] += " " + word["word"]
                    else:
                        row_data[col_idx] = word["word"]

            table_data.append(row_data)

        if not table_data:
            return pd.DataFrame()

        # Create DataFrame
        df = pd.DataFrame(table_data)

        # Clean up empty columns and rows
        df = df.dropna(how="all").dropna(axis=1, how="all")

        return df

    def _find_column_boundaries(self, positions: List[int], min_gap: int = 30) -> List[int]:
        """
        Find column boundaries from word positions.

        Args:
            positions: Sorted list of word left positions
            min_gap: Minimum gap to consider a column boundary

        Returns:
            List of column boundary positions
        """
        if len(positions) <= 1:
            return positions

        boundaries = [positions[0]]

        for i in range(1, len(positions)):
            if positions[i] - positions[i - 1] >= min_gap:
                boundaries.append(positions[i])

        return boundaries

    def _find_column_index(self, position: int, boundaries: List[int]) -> int:
        """
        Find which column a position belongs to.

        Args:
            position: Word position
            boundaries: Column boundary positions

        Returns:
            Column index
        """
        for i, boundary in enumerate(boundaries):
            if position < boundary + 20:  # Allow some tolerance
                return max(0, i - 1)
        return len(boundaries) - 1

    def post_process_ocr_result(self, ocr_result: OCRResult) -> OCRResult:
        """
        Post-process OCR result to improve accuracy.

        Args:
            ocr_result: Raw OCR result

        Returns:
            Processed OCR result
        """
        processed_text = ocr_result.text

        # Common OCR error corrections
        corrections = {
            # Common character substitutions
            r"\b0(?=\w)": "O",  # 0 at beginning of word -> O
            r"(?<=\w)0\b": "O",  # 0 at end of word -> O
            r"\b1(?=\w)": "I",  # 1 at beginning of word -> I
            r"rn": "m",  # rn -> m
            r"vv": "w",  # vv -> w
            r"\|": "I",  # | -> I
            # Fix common price errors
            r"\$(\s+)(\d)": r"$\2",  # Remove space after $
            r"(\d)\s+\.(\d{2})": r"\1.\2",  # Fix decimal point spacing
            # Fix model number patterns
            r"([A-Z]+)(\s+)(\d+)": r"\1\3",  # Remove space in model codes like "BB 1100"
        }

        for pattern, replacement in corrections.items():
            processed_text = re.sub(pattern, replacement, processed_text)

        # Update word confidences if they were affected
        processed_word_confidences = []
        for word, conf in ocr_result.word_confidences:
            # Apply same corrections to individual words
            processed_word = word
            for pattern, replacement in corrections.items():
                if re.search(pattern, processed_word):
                    processed_word = re.sub(pattern, replacement, processed_word)
                    conf *= 0.9  # Slightly reduce confidence for corrected words

            processed_word_confidences.append((processed_word, conf))

        return OCRResult(
            text=processed_text,
            confidence=ocr_result.confidence,
            word_confidences=processed_word_confidences,
            preprocessing_applied=ocr_result.preprocessing_applied + ["post_processed"],
            method=ocr_result.method,
            bbox_data=ocr_result.bbox_data,
        )


# Convenience functions for integration
def extract_with_ocr_fallback(
    pdf_path: str, page_number: int, text: str, tables: List, config: Optional[OCRConfig] = None
) -> Tuple[str, List, OCRResult]:
    """
    Extract text and tables with OCR fallback if needed.

    Args:
        pdf_path: Path to PDF file
        page_number: Page number
        text: Already extracted text
        tables: Already extracted tables
        config: OCR configuration

    Returns:
        Tuple of (final_text, final_tables, ocr_result_or_none)
    """
    processor = OCRProcessor(config)

    # Check if OCR is needed
    if not processor.should_use_ocr(text, tables):
        return text, tables, None

    # Run OCR
    ocr_result = processor.extract_text_from_pdf_page(pdf_path, page_number)
    ocr_result = processor.post_process_ocr_result(ocr_result)

    # Extract tables from OCR if needed
    ocr_tables = processor.extract_tables_from_ocr(ocr_result, page_number)

    # Decide whether to use OCR results
    if ocr_result.confidence > 0.6:  # Use OCR if confidence is decent
        final_text = ocr_result.text if len(ocr_result.text) > len(text) else text
        final_tables = ocr_tables if len(ocr_tables) > len(tables) else tables
    else:
        # Keep original results but log OCR attempt
        final_text = text
        final_tables = tables

    return final_text, final_tables, ocr_result
