"""
ML-based table detector using Microsoft Table Transformer (TATR).

Detects tables in PDF pages using pre-trained deep learning models.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import torch
from transformers import AutoModelForObjectDetection, AutoImageProcessor
from PIL import Image
import pdf2image
import pandas as pd

logger = logging.getLogger(__name__)


class MLTableDetector:
    """
    ML-based table detector using Microsoft Table Transformer.

    Uses pre-trained models from Hugging Face:
    - Table detection: microsoft/table-transformer-detection
    - Structure recognition: microsoft/table-transformer-structure-recognition
    """

    def __init__(self, device: str = None):
        """
        Initialize ML table detector.

        Args:
            device: 'cuda', 'cpu', or None (auto-detect)
        """
        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"Initializing MLTableDetector on device: {self.device}")

        # Load models lazily (on first use to save memory)
        self.detection_model = None
        self.structure_model = None
        self.detection_processor = None
        self.structure_processor = None

    def _load_detection_model(self):
        """Load table detection model (lazy loading)."""
        if self.detection_model is None:
            logger.info("Loading table detection model...")
            self.detection_model = AutoModelForObjectDetection.from_pretrained(
                "microsoft/table-transformer-detection", revision="no_timm"
            ).to(self.device)
            self.detection_processor = AutoImageProcessor.from_pretrained(
                "microsoft/table-transformer-detection", revision="no_timm"
            )
            logger.info("Table detection model loaded")

    def _load_structure_model(self):
        """Load table structure recognition model (lazy loading)."""
        if self.structure_model is None:
            logger.info("Loading table structure model...")
            self.structure_model = AutoModelForObjectDetection.from_pretrained(
                "microsoft/table-transformer-structure-recognition-v1.1-all"
            ).to(self.device)
            self.structure_processor = AutoImageProcessor.from_pretrained(
                "microsoft/table-transformer-structure-recognition-v1.1-all"
            )
            logger.info("Table structure model loaded")

    def detect_tables_in_pdf(
        self, pdf_path: str, max_pages: int = None, confidence_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Detect all tables in a PDF.

        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum pages to process (None = all)
            confidence_threshold: Minimum confidence for table detection (0-1)

        Returns:
            List of detected tables with metadata
        """
        logger.info(f"Detecting tables in {pdf_path}")

        # Load detection model
        self._load_detection_model()

        # Convert PDF to images
        try:
            images = pdf2image.convert_from_path(
                pdf_path, dpi=150, fmt="jpeg", thread_count=2
            )
        except Exception as e:
            logger.error(f"Failed to convert PDF to images: {e}")
            return []

        # Limit pages if specified
        if max_pages:
            images = images[:max_pages]

        logger.info(f"Processing {len(images)} pages...")

        all_tables = []
        for page_num, img in enumerate(images, 1):
            # Detect tables on this page
            page_tables = self._detect_tables_in_image(
                img, page_num, confidence_threshold
            )
            all_tables.extend(page_tables)

            if page_num % 10 == 0:
                logger.info(f"Processed {page_num}/{len(images)} pages, {len(all_tables)} tables found")

        logger.info(f"Total tables detected: {len(all_tables)}")
        return all_tables

    def _detect_tables_in_image(
        self, image: Image.Image, page_num: int, confidence_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Detect tables in a single page image.

        Args:
            image: PIL Image of page
            page_num: Page number
            confidence_threshold: Minimum confidence (0-1)

        Returns:
            List of table detections with bounding boxes
        """
        # Prepare image for model
        inputs = self.detection_processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Run detection
        with torch.no_grad():
            outputs = self.detection_model(**inputs)

        # Post-process results
        target_sizes = torch.tensor([image.size[::-1]]).to(self.device)
        results = self.detection_processor.post_process_object_detection(
            outputs, threshold=confidence_threshold, target_sizes=target_sizes
        )[0]

        tables = []
        for score, label, box in zip(
            results["scores"], results["labels"], results["boxes"]
        ):
            # Convert box to list [x1, y1, x2, y2]
            box = box.cpu().tolist()

            # Crop table region from image
            table_img = image.crop(box)

            tables.append(
                {
                    "page": page_num,
                    "bbox": box,
                    "confidence": score.item(),
                    "image": table_img,
                    "image_size": image.size,
                }
            )

        logger.debug(f"Page {page_num}: Found {len(tables)} tables")
        return tables

    def recognize_table_structure(
        self, table_image: Image.Image, confidence_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Recognize structure of a table (rows, columns, cells).

        Args:
            table_image: Cropped table image
            confidence_threshold: Minimum confidence

        Returns:
            Table structure with rows, columns, cells
        """
        # Load structure model
        self._load_structure_model()

        # Prepare image
        inputs = self.structure_processor(images=table_image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Run structure recognition
        with torch.no_grad():
            outputs = self.structure_model(**inputs)

        # Post-process
        target_sizes = torch.tensor([table_image.size[::-1]]).to(self.device)
        results = self.structure_processor.post_process_object_detection(
            outputs, threshold=confidence_threshold, target_sizes=target_sizes
        )[0]

        # Extract structure elements
        structure = {"rows": [], "columns": [], "cells": []}

        for score, label, box in zip(
            results["scores"], results["labels"], results["boxes"]
        ):
            box = box.cpu().tolist()
            element = {
                "bbox": box,
                "confidence": score.item(),
                "label": self.structure_model.config.id2label[label.item()],
            }

            # Classify element type
            label_name = element["label"].lower()
            if "row" in label_name:
                structure["rows"].append(element)
            elif "column" in label_name or "header" in label_name:
                structure["columns"].append(element)
            else:
                structure["cells"].append(element)

        return structure

    def extract_table_to_dataframe(
        self, table_data: Dict[str, Any], ocr_text: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Convert detected table structure to pandas DataFrame.

        Args:
            table_data: Table with structure info
            ocr_text: Optional OCR text to fill cells

        Returns:
            DataFrame representation of table
        """
        # For now, return placeholder
        # In production, would use OCR + structure to build proper DataFrame
        # This is a simplified version

        structure = table_data.get("structure", {})
        rows = structure.get("rows", [])
        columns = structure.get("columns", [])

        if not rows or not columns:
            return pd.DataFrame()

        # Create empty DataFrame with estimated dimensions
        num_rows = len(rows)
        num_cols = len(columns)

        # Placeholder data
        return pd.DataFrame(
            {"col_" + str(i): [""] * num_rows for i in range(num_cols)}
        )

    def detect_and_extract_tables(
        self, pdf_path: str, max_pages: int = None, extract_structure: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Full pipeline: detect tables and optionally extract structure.

        Args:
            pdf_path: PDF file path
            max_pages: Max pages to process
            extract_structure: Whether to run structure recognition

        Returns:
            List of tables with detection and structure info
        """
        # Detect tables
        tables = self.detect_tables_in_pdf(pdf_path, max_pages=max_pages)

        if not extract_structure:
            return tables

        # Extract structure for each table
        logger.info("Extracting table structures...")
        for i, table in enumerate(tables):
            try:
                structure = self.recognize_table_structure(table["image"])
                table["structure"] = structure
                logger.debug(
                    f"Table {i+1}/{len(tables)}: "
                    f"{len(structure['rows'])} rows, "
                    f"{len(structure['columns'])} cols"
                )
            except Exception as e:
                logger.warning(f"Failed to extract structure for table {i+1}: {e}")
                table["structure"] = None

        return tables
