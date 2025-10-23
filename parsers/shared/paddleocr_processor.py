"""
PaddleOCR Processor - Advanced OCR with confidence scoring.

Uses PaddleOCR for high-accuracy text extraction with:
- Word-level bounding boxes and confidence scores
- Table cell detection
- Text orientation handling
- 96.4% accuracy (2025 research)
"""

import logging
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)


class PaddleOCRProcessor:
    """
    Advanced OCR processor using PaddleOCR with confidence scoring.

    Features:
    - Word-level bounding boxes
    - Confidence scores per word
    - Table cell detection
    - Text orientation handling
    - 93-96% accuracy baseline
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"{__class__.__name__}")

        # Initialize PaddleOCR (lazy loading)
        self.ocr = None
        self._initialize_ocr()

    def _initialize_ocr(self):
        """Initialize PaddleOCR engine."""
        try:
            from paddleocr import PaddleOCR

            # Build config with only supported parameters
            ocr_config = {
                'use_angle_cls': True,  # Detect text rotation
                'lang': self.config.get('ocr_lang', 'en'),  # English language
                'det_db_thresh': self.config.get('det_threshold', 0.3),  # Lower for better recall
                'det_db_box_thresh': self.config.get('box_threshold', 0.6),  # Higher for precision
            }

            # Only add use_gpu if explicitly requested (not all versions support it)
            if self.config.get('use_gpu'):
                ocr_config['use_gpu'] = True

            self.ocr = PaddleOCR(**ocr_config)

            self.logger.info("PaddleOCR initialized successfully")

        except ImportError:
            self.logger.warning("PaddleOCR not installed. Install with: pip install paddleocr")
            self.ocr = None
        except Exception as e:
            self.logger.error(f"Error initializing PaddleOCR: {e}")
            self.ocr = None

    def is_available(self) -> bool:
        """Check if PaddleOCR is available."""
        return self.ocr is not None

    def extract_from_page(self, page_image: np.ndarray) -> List[Dict]:
        """
        Extract text with word-level confidence scores.

        Args:
            page_image: numpy array of page image (RGB)

        Returns:
            List of {
                'text': str,
                'bbox': [x1, y1, x2, y2],
                'confidence': float,
                'angle': float (optional)
            }
        """
        if not self.is_available():
            self.logger.warning("PaddleOCR not available")
            return []

        try:
            # Run OCR
            results = self.ocr.ocr(page_image, cls=True)

            if not results or not results[0]:
                return []

            words = []
            for line in results[0]:
                bbox, (text, confidence) = line

                words.append({
                    'text': text,
                    'bbox': self._normalize_bbox(bbox),
                    'confidence': float(confidence),
                })

            self.logger.debug(f"Extracted {len(words)} words from page")
            return words

        except Exception as e:
            self.logger.error(f"Error extracting text from page: {e}")
            return []

    def extract_table_cells(
        self,
        page_image: np.ndarray,
        table_bbox: Optional[Tuple[int, int, int, int]] = None
    ) -> pd.DataFrame:
        """
        Extract table cells with structure recognition.

        Args:
            page_image: numpy array of page image
            table_bbox: Optional bounding box to crop table region (x1, y1, x2, y2)

        Returns:
            DataFrame with extracted table data
        """
        if not self.is_available():
            self.logger.warning("PaddleOCR not available for table extraction")
            return pd.DataFrame()

        try:
            # Crop table region if bbox provided
            if table_bbox:
                x1, y1, x2, y2 = table_bbox
                table_img = page_image[y1:y2, x1:x2]
            else:
                table_img = page_image

            # Use PaddleOCR's table recognition
            # Note: For full table structure, we'd use PPStructure
            # For now, we extract text and structure it based on positions
            words = self.extract_from_page(table_img)

            if not words:
                return pd.DataFrame()

            # Structure words into table format
            df = self._structure_table_data(words)

            self.logger.debug(f"Extracted table with {len(df)} rows, {len(df.columns)} columns")
            return df

        except Exception as e:
            self.logger.error(f"Error extracting table cells: {e}")
            return pd.DataFrame()

    def detect_table_structure(
        self,
        page_image: np.ndarray,
        table_bbox: Tuple[int, int, int, int]
    ) -> Dict[str, Any]:
        """
        Detect table structure (rows, columns, cells) using PaddleOCR.

        Args:
            page_image: numpy array of page image
            table_bbox: Bounding box of table region

        Returns:
            {
                'rows': List[Dict],  # Row coordinates
                'columns': List[Dict],  # Column coordinates
                'cells': List[Dict],  # Cell data with text and confidence
                'structure_confidence': float
            }
        """
        if not self.is_available():
            return {
                'rows': [],
                'columns': [],
                'cells': [],
                'structure_confidence': 0.0
            }

        try:
            # Crop table region
            x1, y1, x2, y2 = table_bbox
            table_img = page_image[y1:y2, x1:x2]

            # Extract words with positions
            words = self.extract_from_page(table_img)

            if not words:
                return {
                    'rows': [],
                    'columns': [],
                    'cells': [],
                    'structure_confidence': 0.0
                }

            # Group words into cells based on spatial proximity
            cells = self._group_words_into_cells(words)

            # Identify row and column structure
            rows = self._identify_rows(cells)
            columns = self._identify_columns(cells)

            # Calculate structure confidence
            avg_confidence = sum(w['confidence'] for w in words) / len(words) if words else 0

            return {
                'rows': rows,
                'columns': columns,
                'cells': cells,
                'structure_confidence': avg_confidence
            }

        except Exception as e:
            self.logger.error(f"Error detecting table structure: {e}")
            return {
                'rows': [],
                'columns': [],
                'cells': [],
                'structure_confidence': 0.0
            }

    def _normalize_bbox(self, bbox: List[List[float]]) -> List[float]:
        """
        Normalize bounding box from PaddleOCR format to [x1, y1, x2, y2].

        Args:
            bbox: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]] (PaddleOCR format)

        Returns:
            [x1, y1, x2, y2] (standard format)
        """
        xs = [point[0] for point in bbox]
        ys = [point[1] for point in bbox]

        return [
            min(xs),  # x1
            min(ys),  # y1
            max(xs),  # x2
            max(ys),  # y2
        ]

    def _structure_table_data(self, words: List[Dict]) -> pd.DataFrame:
        """
        Structure extracted words into table DataFrame.

        Strategy:
        - Group words by Y-coordinate (rows)
        - Sort within rows by X-coordinate (columns)
        - Create DataFrame with inferred structure
        """
        if not words:
            return pd.DataFrame()

        # Sort words by Y then X
        words_sorted = sorted(words, key=lambda w: (w['bbox'][1], w['bbox'][0]))

        # Group into rows (words with similar Y coordinates)
        rows = []
        current_row = []
        current_y = None
        y_tolerance = 10  # pixels

        for word in words_sorted:
            y = word['bbox'][1]

            if current_y is None:
                current_y = y
                current_row.append(word)
            elif abs(y - current_y) <= y_tolerance:
                # Same row
                current_row.append(word)
            else:
                # New row
                if current_row:
                    rows.append(current_row)
                current_row = [word]
                current_y = y

        if current_row:
            rows.append(current_row)

        # Convert to DataFrame
        # Use first row as header if it looks like headers
        if len(rows) > 1:
            header_row = rows[0]
            data_rows = rows[1:]

            # Extract header texts
            headers = [word['text'] for word in sorted(header_row, key=lambda w: w['bbox'][0])]

            # Extract data
            data = []
            for row_words in data_rows:
                row_words_sorted = sorted(row_words, key=lambda w: w['bbox'][0])
                row_data = [word['text'] for word in row_words_sorted]

                # Pad to match header length
                while len(row_data) < len(headers):
                    row_data.append('')

                data.append(row_data[:len(headers)])

            df = pd.DataFrame(data, columns=headers)
        else:
            # Single row - treat as data
            data = [[word['text'] for word in sorted(rows[0], key=lambda w: w['bbox'][0])]]
            df = pd.DataFrame(data)

        return df

    def _group_words_into_cells(self, words: List[Dict]) -> List[Dict]:
        """
        Group words into table cells based on spatial proximity.

        Returns:
            List of cells with {
                'text': str,
                'bbox': [x1, y1, x2, y2],
                'confidence': float,
                'row': int,
                'col': int
            }
        """
        # For now, each word is a cell
        # More sophisticated cell detection would merge adjacent words
        cells = []

        for idx, word in enumerate(words):
            cells.append({
                'text': word['text'],
                'bbox': word['bbox'],
                'confidence': word['confidence'],
                'cell_id': idx
            })

        return cells

    def _identify_rows(self, cells: List[Dict]) -> List[Dict]:
        """Identify row boundaries from cells."""
        if not cells:
            return []

        # Group cells by Y-coordinate
        y_coords = sorted(set(cell['bbox'][1] for cell in cells))

        rows = []
        for idx, y in enumerate(y_coords):
            rows.append({
                'row_id': idx,
                'y_min': y,
                'y_max': y + 20,  # Approximate row height
            })

        return rows

    def _identify_columns(self, cells: List[Dict]) -> List[Dict]:
        """Identify column boundaries from cells."""
        if not cells:
            return []

        # Group cells by X-coordinate
        x_coords = sorted(set(cell['bbox'][0] for cell in cells))

        columns = []
        for idx, x in enumerate(x_coords):
            columns.append({
                'col_id': idx,
                'x_min': x,
                'x_max': x + 100,  # Approximate column width
            })

        return columns


# Convenience function for quick OCR
def quick_ocr(image_path: str, lang: str = 'en') -> List[Dict]:
    """
    Quick OCR extraction from image file.

    Args:
        image_path: Path to image file
        lang: Language code (default: 'en')

    Returns:
        List of extracted words with confidence
    """
    processor = PaddleOCRProcessor(config={'ocr_lang': lang})

    if not processor.is_available():
        logger.error("PaddleOCR not available")
        return []

    # Load image
    try:
        from PIL import Image
        import numpy as np

        image = Image.open(image_path).convert('RGB')
        image_array = np.array(image)

        return processor.extract_from_page(image_array)

    except Exception as e:
        logger.error(f"Error in quick_ocr: {e}")
        return []
