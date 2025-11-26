"""
Universal PDF Parser - High-accuracy extraction for any PDF type.

Implements a multi-strategy extraction pipeline with:
- Automatic PDF type detection (scanned vs digital)
- Confidence-based method selection and fallback
- Integrated table processing and cross-page stitching
- Full provenance tracking

Target: ~98% accuracy on structured documents like price lists.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class PDFType(Enum):
    """Classification of PDF document type."""
    DIGITAL = "digital"
    SCANNED = "scanned"
    HYBRID = "hybrid"


class ExtractionMethod(Enum):
    """Available extraction methods."""
    PYMUPDF = "pymupdf"
    PDFPLUMBER = "pdfplumber"
    CAMELOT_LATTICE = "camelot_lattice"
    CAMELOT_STREAM = "camelot_stream"
    PADDLEOCR = "paddleocr"
    TESSERACT = "tesseract"


@dataclass
class PageAnalysis:
    """Analysis results for a single PDF page."""
    page_number: int
    has_text: bool
    text_density: float
    has_images: bool
    image_coverage: float
    has_tables: bool
    table_count: int
    table_regions: List[Tuple[float, float, float, float]]
    recommended_method: ExtractionMethod
    is_scanned: bool


@dataclass
class ExtractionResult:
    """Result from a single extraction attempt."""
    method: ExtractionMethod
    tables: List[pd.DataFrame]
    text_content: str
    confidence: float
    page_number: int
    processing_time_ms: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    """Complete parsed document with all extracted data."""
    source_file: str
    pdf_type: PDFType
    page_count: int
    tables: List[pd.DataFrame]
    text_content: str
    effective_date: Optional[str]
    products: List[Dict[str, Any]]
    extraction_results: List[ExtractionResult]
    overall_confidence: float
    processing_notes: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class UniversalPDFParser:
    """
    Universal PDF parser with multi-strategy extraction.
    
    Automatically detects PDF type and selects optimal extraction
    strategy for maximum accuracy. Implements confidence-based
    fallback to ensure high-quality results.
    
    Usage:
        parser = UniversalPDFParser()
        result = parser.parse("path/to/document.pdf")
        
        for table in result.tables:
            print(table)
        
        print(f"Confidence: {result.overall_confidence:.2%}")
    """
    
    HIGH_CONFIDENCE_THRESHOLD = 0.85
    ACCEPTABLE_CONFIDENCE_THRESHOLD = 0.70
    MIN_CONFIDENCE_THRESHOLD = 0.50
    
    DIGITAL_METHOD_PRIORITY = [
        ExtractionMethod.PYMUPDF,
        ExtractionMethod.PDFPLUMBER,
        ExtractionMethod.CAMELOT_LATTICE,
        ExtractionMethod.CAMELOT_STREAM,
    ]
    
    SCANNED_METHOD_PRIORITY = [
        ExtractionMethod.PADDLEOCR,
        ExtractionMethod.TESSERACT,
    ]
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the universal parser.
        
        Args:
            config: Optional configuration dictionary with:
                - min_confidence: Minimum acceptable confidence (default: 0.70)
                - enable_ocr: Whether to use OCR for scanned pages (default: True)
                - table_processing: Enable advanced table processing (default: True)
                - cross_page_stitching: Stitch tables across pages (default: True)
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"{__class__.__name__}")
        
        self._table_processor = None
        self._ocr_processor = None
        self._provenance_tracker = None
        
    def parse(self, pdf_path: str) -> ParsedDocument:
        """
        Parse a PDF document with automatic method selection.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            ParsedDocument with all extracted data and metadata
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        self.logger.info(f"Starting parse of: {pdf_path.name}")
        
        from parsers.shared.provenance import ProvenanceTracker
        self._provenance_tracker = ProvenanceTracker(str(pdf_path))
        
        self.logger.info("Phase 1: Analyzing PDF structure...")
        page_analyses = self._analyze_pdf(str(pdf_path))
        pdf_type = self._determine_pdf_type(page_analyses)
        self.logger.info(f"PDF type detected: {pdf_type.value}")
        
        self.logger.info("Phase 2: Extracting content...")
        extraction_results = self._extract_all_pages(str(pdf_path), page_analyses, pdf_type)
        
        self.logger.info("Phase 3: Post-processing...")
        tables, text_content = self._consolidate_results(extraction_results)
        
        if self.config.get("table_processing", True):
            self.logger.info("Phase 4: Enhancing tables...")
            tables = self._enhance_tables(tables)
        
        self.logger.info("Phase 5: Extracting structured data...")
        effective_date = self._extract_effective_date(text_content)
        products = self._extract_products(tables)
        
        overall_confidence = self._calculate_overall_confidence(extraction_results)
        
        processing_notes = self._compile_processing_notes(extraction_results, page_analyses)
        
        result = ParsedDocument(
            source_file=str(pdf_path),
            pdf_type=pdf_type,
            page_count=len(page_analyses),
            tables=tables,
            text_content=text_content,
            effective_date=effective_date,
            products=products,
            extraction_results=extraction_results,
            overall_confidence=overall_confidence,
            processing_notes=processing_notes,
            metadata={
                "page_analyses": [self._page_analysis_to_dict(pa) for pa in page_analyses],
            }
        )
        
        self.logger.info(
            f"Parse complete: {len(tables)} tables, {len(products)} products, "
            f"confidence: {overall_confidence:.2%}"
        )
        
        return result
    
    def _analyze_pdf(self, pdf_path: str) -> List[PageAnalysis]:
        """
        Analyze PDF structure to determine optimal extraction strategy.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of PageAnalysis for each page
        """
        analyses = []
        
        try:
            import fitz
            
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                text = page.get_text()
                text_length = len(text.strip())
                
                page_area = page.rect.width * page.rect.height
                text_density = text_length / page_area if page_area > 0 else 0
                
                image_list = page.get_images()
                has_images = len(image_list) > 0
                
                image_coverage = 0.0
                if has_images:
                    total_image_area = 0
                    for img in image_list:
                        try:
                            xref = img[0]
                            img_rect = page.get_image_bbox(xref)
                            if img_rect:
                                total_image_area += img_rect.width * img_rect.height
                        except Exception:
                            pass
                    image_coverage = min(1.0, total_image_area / page_area) if page_area > 0 else 0
                
                tables = []
                table_regions = []
                try:
                    tabs = page.find_tables()
                    if tabs and tabs.tables:
                        tables = tabs.tables
                        for tab in tables:
                            table_regions.append(tab.bbox)
                except Exception as e:
                    self.logger.debug(f"Table detection error on page {page_num + 1}: {e}")
                
                is_scanned = (text_density < 0.001 and image_coverage > 0.5) or \
                             (text_length < 100 and has_images)
                
                if is_scanned:
                    recommended = ExtractionMethod.PADDLEOCR
                elif tables:
                    recommended = ExtractionMethod.PYMUPDF
                else:
                    recommended = ExtractionMethod.PDFPLUMBER
                
                analysis = PageAnalysis(
                    page_number=page_num + 1,
                    has_text=text_length > 50,
                    text_density=text_density,
                    has_images=has_images,
                    image_coverage=image_coverage,
                    has_tables=len(tables) > 0,
                    table_count=len(tables),
                    table_regions=table_regions,
                    recommended_method=recommended,
                    is_scanned=is_scanned,
                )
                analyses.append(analysis)
            
            doc.close()
            
        except ImportError:
            self.logger.warning("PyMuPDF not available, using basic analysis")
            analyses = self._basic_pdf_analysis(pdf_path)
        except Exception as e:
            self.logger.error(f"Error analyzing PDF: {e}")
            analyses = self._basic_pdf_analysis(pdf_path)
        
        return analyses
    
    def _basic_pdf_analysis(self, pdf_path: str) -> List[PageAnalysis]:
        """Fallback PDF analysis without PyMuPDF."""
        analyses = []
        
        try:
            import pdfplumber
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    tables = page.find_tables()
                    
                    analysis = PageAnalysis(
                        page_number=page_num + 1,
                        has_text=len(text.strip()) > 50,
                        text_density=len(text) / (page.width * page.height) if page.width and page.height else 0,
                        has_images=bool(page.images),
                        image_coverage=0.0,
                        has_tables=len(tables) > 0,
                        table_count=len(tables),
                        table_regions=[],
                        recommended_method=ExtractionMethod.PDFPLUMBER,
                        is_scanned=len(text.strip()) < 100 and bool(page.images),
                    )
                    analyses.append(analysis)
                    
        except Exception as e:
            self.logger.error(f"Basic PDF analysis failed: {e}")
            analyses = [PageAnalysis(
                page_number=1,
                has_text=False,
                text_density=0,
                has_images=False,
                image_coverage=0,
                has_tables=False,
                table_count=0,
                table_regions=[],
                recommended_method=ExtractionMethod.PDFPLUMBER,
                is_scanned=False,
            )]
        
        return analyses
    
    def _determine_pdf_type(self, analyses: List[PageAnalysis]) -> PDFType:
        """Determine overall PDF type from page analyses."""
        if not analyses:
            return PDFType.DIGITAL
        
        scanned_pages = sum(1 for a in analyses if a.is_scanned)
        digital_pages = len(analyses) - scanned_pages
        
        if scanned_pages == 0:
            return PDFType.DIGITAL
        elif digital_pages == 0:
            return PDFType.SCANNED
        else:
            return PDFType.HYBRID
    
    def _extract_all_pages(
        self,
        pdf_path: str,
        page_analyses: List[PageAnalysis],
        pdf_type: PDFType
    ) -> List[ExtractionResult]:
        """
        Extract content from all pages using optimal methods.
        
        Args:
            pdf_path: Path to PDF
            page_analyses: Analysis results for each page
            pdf_type: Overall PDF type
            
        Returns:
            List of ExtractionResult for each page
        """
        results = []
        
        for analysis in page_analyses:
            if analysis.is_scanned:
                method_priority = self.SCANNED_METHOD_PRIORITY
            else:
                method_priority = self.DIGITAL_METHOD_PRIORITY
            
            page_result = None
            
            for method in method_priority:
                try:
                    result = self._extract_page(pdf_path, analysis.page_number, method)
                    
                    if result.confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
                        page_result = result
                        break
                    elif result.confidence >= self.ACCEPTABLE_CONFIDENCE_THRESHOLD:
                        if page_result is None or result.confidence > page_result.confidence:
                            page_result = result
                    elif page_result is None or result.confidence > page_result.confidence:
                        page_result = result
                        
                except Exception as e:
                    self.logger.warning(
                        f"Method {method.value} failed on page {analysis.page_number}: {e}"
                    )
                    continue
            
            if page_result:
                results.append(page_result)
            else:
                results.append(ExtractionResult(
                    method=method_priority[0],
                    tables=[],
                    text_content="",
                    confidence=0.0,
                    page_number=analysis.page_number,
                    processing_time_ms=0,
                    errors=["All extraction methods failed"],
                ))
        
        return results
    
    def _extract_page(
        self,
        pdf_path: str,
        page_number: int,
        method: ExtractionMethod
    ) -> ExtractionResult:
        """
        Extract content from a single page using specified method.
        
        Args:
            pdf_path: Path to PDF
            page_number: 1-indexed page number
            method: Extraction method to use
            
        Returns:
            ExtractionResult with extracted data
        """
        start_time = time.time()
        
        tables = []
        text_content = ""
        errors = []
        warnings = []
        metadata = {}
        
        try:
            if method == ExtractionMethod.PYMUPDF:
                tables, text_content, metadata = self._extract_with_pymupdf(pdf_path, page_number)
            elif method == ExtractionMethod.PDFPLUMBER:
                tables, text_content, metadata = self._extract_with_pdfplumber(pdf_path, page_number)
            elif method == ExtractionMethod.CAMELOT_LATTICE:
                tables, text_content, metadata = self._extract_with_camelot(pdf_path, page_number, "lattice")
            elif method == ExtractionMethod.CAMELOT_STREAM:
                tables, text_content, metadata = self._extract_with_camelot(pdf_path, page_number, "stream")
            elif method == ExtractionMethod.PADDLEOCR:
                tables, text_content, metadata = self._extract_with_paddleocr(pdf_path, page_number)
            elif method == ExtractionMethod.TESSERACT:
                tables, text_content, metadata = self._extract_with_tesseract(pdf_path, page_number)
            else:
                raise ValueError(f"Unknown extraction method: {method}")
                
        except Exception as e:
            errors.append(str(e))
            self.logger.error(f"Extraction error with {method.value}: {e}")
        
        confidence = self._calculate_extraction_confidence(tables, text_content, method, metadata)
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        return ExtractionResult(
            method=method,
            tables=tables,
            text_content=text_content,
            confidence=confidence,
            page_number=page_number,
            processing_time_ms=processing_time_ms,
            errors=errors,
            warnings=warnings,
            metadata=metadata,
        )
    
    def _extract_with_pymupdf(
        self,
        pdf_path: str,
        page_number: int
    ) -> Tuple[List[pd.DataFrame], str, Dict]:
        """Extract using PyMuPDF (fitz) - best for digital PDFs."""
        import fitz
        
        tables = []
        metadata = {"method_details": "pymupdf_native"}
        
        doc = fitz.open(pdf_path)
        page = doc[page_number - 1]
        
        text_content = page.get_text("text")
        
        try:
            tab_finder = page.find_tables()
            if tab_finder and tab_finder.tables:
                for tab in tab_finder.tables:
                    table_data = tab.extract()
                    if table_data and len(table_data) > 0:
                        if len(table_data) > 1:
                            df = pd.DataFrame(table_data[1:], columns=table_data[0])
                        else:
                            df = pd.DataFrame(table_data)
                        
                        df["_page_number"] = page_number
                        df["_extraction_method"] = "pymupdf"
                        tables.append(df)
                
                metadata["tables_found"] = len(tab_finder.tables)
                metadata["table_accuracy"] = getattr(tab_finder, 'accuracy', None)
        except Exception as e:
            self.logger.debug(f"PyMuPDF table extraction error: {e}")
        
        doc.close()
        
        return tables, text_content, metadata
    
    def _extract_with_pdfplumber(
        self,
        pdf_path: str,
        page_number: int
    ) -> Tuple[List[pd.DataFrame], str, Dict]:
        """Extract using pdfplumber - good general-purpose extractor."""
        import pdfplumber
        
        tables = []
        metadata = {"method_details": "pdfplumber"}
        
        with pdfplumber.open(pdf_path) as pdf:
            if page_number > len(pdf.pages):
                return [], "", {"error": "Page number out of range"}
            
            page = pdf.pages[page_number - 1]
            
            text_content = page.extract_text() or ""
            
            table_settings = {
                "vertical_strategy": "lines_strict",
                "horizontal_strategy": "lines_strict",
                "snap_tolerance": 3,
                "join_tolerance": 3,
                "edge_min_length": 10,
                "min_words_vertical": 1,
                "min_words_horizontal": 1,
            }
            
            try:
                page_tables = page.extract_tables(table_settings)
                
                if not page_tables:
                    table_settings["vertical_strategy"] = "text"
                    table_settings["horizontal_strategy"] = "text"
                    page_tables = page.extract_tables(table_settings)
                
                for table_data in page_tables:
                    if table_data and len(table_data) > 1:
                        table_data = [row for row in table_data if any(cell for cell in row)]
                        
                        if len(table_data) > 1:
                            df = pd.DataFrame(table_data[1:], columns=table_data[0])
                            df["_page_number"] = page_number
                            df["_extraction_method"] = "pdfplumber"
                            tables.append(df)
                
                metadata["tables_found"] = len(page_tables) if page_tables else 0
                
            except Exception as e:
                self.logger.debug(f"pdfplumber table extraction error: {e}")
        
        return tables, text_content, metadata
    
    def _extract_with_camelot(
        self,
        pdf_path: str,
        page_number: int,
        flavor: str
    ) -> Tuple[List[pd.DataFrame], str, Dict]:
        """Extract using Camelot - specialized for tables."""
        import camelot
        from pdfminer.high_level import extract_text
        
        tables = []
        metadata = {"method_details": f"camelot_{flavor}"}
        
        try:
            text_content = extract_text(pdf_path, page_numbers=[page_number - 1])
        except Exception:
            text_content = ""
        
        try:
            camelot_tables = camelot.read_pdf(
                pdf_path,
                pages=str(page_number),
                flavor=flavor,
            )
            
            for table in camelot_tables:
                if table.accuracy > 0.5:
                    df = table.df.copy()
                    
                    if len(df) > 1:
                        df.columns = df.iloc[0]
                        df = df.iloc[1:].reset_index(drop=True)
                    
                    df["_page_number"] = page_number
                    df["_extraction_method"] = f"camelot_{flavor}"
                    df["_camelot_accuracy"] = table.accuracy
                    tables.append(df)
            
            metadata["tables_found"] = len(camelot_tables)
            if camelot_tables:
                metadata["avg_accuracy"] = sum(t.accuracy for t in camelot_tables) / len(camelot_tables)
                
        except Exception as e:
            self.logger.debug(f"Camelot extraction error: {e}")
        
        return tables, text_content, metadata
    
    def _extract_with_paddleocr(
        self,
        pdf_path: str,
        page_number: int
    ) -> Tuple[List[pd.DataFrame], str, Dict]:
        """Extract using PaddleOCR - best for scanned documents."""
        from parsers.shared.paddleocr_processor import PaddleOCRProcessor
        
        tables = []
        text_parts = []
        metadata = {"method_details": "paddleocr"}
        
        try:
            from pdf2image import convert_from_path
            
            images = convert_from_path(
                pdf_path,
                first_page=page_number,
                last_page=page_number,
                dpi=300,
            )
            
            if not images:
                return [], "", {"error": "Could not convert page to image"}
            
            page_image = np.array(images[0])
            
            if self._ocr_processor is None:
                self._ocr_processor = PaddleOCRProcessor(self.config)
            
            if not self._ocr_processor.is_available():
                return [], "", {"error": "PaddleOCR not available"}
            
            words = self._ocr_processor.extract_from_page(page_image)
            
            for word in words:
                text_parts.append(word["text"])
            
            text_content = " ".join(text_parts)
            
            table_df = self._ocr_processor.extract_table_cells(page_image)
            if not table_df.empty:
                table_df["_page_number"] = page_number
                table_df["_extraction_method"] = "paddleocr"
                tables.append(table_df)
            
            if words:
                avg_confidence = sum(w["confidence"] for w in words) / len(words)
                metadata["avg_ocr_confidence"] = avg_confidence
                metadata["word_count"] = len(words)
            
        except ImportError as e:
            self.logger.warning(f"PaddleOCR dependencies not available: {e}")
            return [], "", {"error": str(e)}
        except Exception as e:
            self.logger.error(f"PaddleOCR extraction error: {e}")
            return [], "", {"error": str(e)}
        
        return tables, text_content, metadata
    
    def _extract_with_tesseract(
        self,
        pdf_path: str,
        page_number: int
    ) -> Tuple[List[pd.DataFrame], str, Dict]:
        """Extract using Tesseract OCR - fallback for scanned documents."""
        import pytesseract
        from PIL import Image
        
        tables = []
        metadata = {"method_details": "tesseract"}
        
        try:
            from pdf2image import convert_from_path
            
            images = convert_from_path(
                pdf_path,
                first_page=page_number,
                last_page=page_number,
                dpi=300,
            )
            
            if not images:
                return [], "", {"error": "Could not convert page to image"}
            
            page_image = images[0]
            
            processed_image = self._preprocess_for_ocr(page_image)
            
            text_content = pytesseract.image_to_string(processed_image)
            
            try:
                tsv_data = pytesseract.image_to_data(
                    processed_image,
                    output_type=pytesseract.Output.DATAFRAME
                )
                
                tsv_data = tsv_data[tsv_data["conf"] > 0]
                
                if not tsv_data.empty:
                    metadata["avg_confidence"] = tsv_data["conf"].mean() / 100
                    metadata["word_count"] = len(tsv_data)
                    
            except Exception as e:
                self.logger.debug(f"Tesseract TSV extraction error: {e}")
            
            table_data = self._parse_table_from_text(text_content)
            if table_data:
                df = pd.DataFrame(table_data)
                df["_page_number"] = page_number
                df["_extraction_method"] = "tesseract"
                tables.append(df)
            
        except Exception as e:
            self.logger.error(f"Tesseract extraction error: {e}")
            return [], "", {"error": str(e)}
        
        return tables, text_content, metadata
    
    def _preprocess_for_ocr(self, image) -> "Image.Image":
        """Preprocess image for better OCR accuracy."""
        import cv2
        from PIL import Image
        
        img_array = np.array(image)
        
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )
        
        denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)
        
        coords = np.column_stack(np.where(denoised < 255))
        if len(coords) > 100:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = 90 + angle
            if abs(angle) > 0.5:
                (h, w) = denoised.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                denoised = cv2.warpAffine(
                    denoised, M, (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE
                )
        
        return Image.fromarray(denoised)
    
    def _parse_table_from_text(self, text: str) -> List[List[str]]:
        """Parse table-like structure from OCR text."""
        lines = text.split("\n")
        table_data = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            parts = re.split(r"\s{2,}|\t", line)
            
            parts = [p.strip() for p in parts if len(p.strip()) > 0]
            
            if len(parts) >= 2:
                table_data.append(parts)
        
        return table_data if len(table_data) > 1 else []
    
    def _calculate_extraction_confidence(
        self,
        tables: List[pd.DataFrame],
        text_content: str,
        method: ExtractionMethod,
        metadata: Dict
    ) -> float:
        """Calculate confidence score for an extraction result."""
        confidence = 0.0
        
        method_base_confidence = {
            ExtractionMethod.PYMUPDF: 0.90,
            ExtractionMethod.PDFPLUMBER: 0.85,
            ExtractionMethod.CAMELOT_LATTICE: 0.80,
            ExtractionMethod.CAMELOT_STREAM: 0.70,
            ExtractionMethod.PADDLEOCR: 0.75,
            ExtractionMethod.TESSERACT: 0.60,
        }
        
        confidence = method_base_confidence.get(method, 0.50)
        
        if tables:
            confidence += 0.05
            
            for df in tables:
                if len(df) > 0 and len(df.columns) > 1:
                    completeness = 1 - (df.isnull().sum().sum() / (len(df) * len(df.columns)))
                    confidence += completeness * 0.05
        
        if text_content and len(text_content.strip()) > 100:
            confidence += 0.05
        
        if "avg_accuracy" in metadata:
            confidence = (confidence + metadata["avg_accuracy"]) / 2
        if "avg_ocr_confidence" in metadata:
            confidence = (confidence + metadata["avg_ocr_confidence"]) / 2
        if "avg_confidence" in metadata:
            confidence = (confidence + metadata["avg_confidence"]) / 2
        
        return min(1.0, max(0.0, confidence))
    
    def _consolidate_results(
        self,
        extraction_results: List[ExtractionResult]
    ) -> Tuple[List[pd.DataFrame], str]:
        """Consolidate extraction results from all pages."""
        all_tables = []
        all_text = []
        
        for result in extraction_results:
            all_tables.extend(result.tables)
            if result.text_content:
                all_text.append(f"--- Page {result.page_number} ---\n{result.text_content}")
        
        text_content = "\n\n".join(all_text)
        
        return all_tables, text_content
    
    def _enhance_tables(self, tables: List[pd.DataFrame]) -> List[pd.DataFrame]:
        """Apply table processing enhancements."""
        from parsers.shared.table_processor import TableProcessor
        
        if self._table_processor is None:
            self._table_processor = TableProcessor()
        
        enhanced_tables = []
        processed_tables = []
        
        for df in tables:
            processed = self._table_processor.process_table(df)
            processed_tables.append(processed)
            enhanced_tables.append(processed.dataframe)
        
        if self.config.get("cross_page_stitching", True) and len(processed_tables) > 1:
            stitched = self._table_processor.stitch_cross_page_tables(processed_tables)
            enhanced_tables = [pt.dataframe for pt in stitched]
        
        return enhanced_tables
    
    def _extract_effective_date(self, text_content: str) -> Optional[str]:
        """Extract effective date from text content."""
        if not text_content:
            return None
        
        patterns = [
            r"effective\s+(?:date)?[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"prices?\s+effective[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"valid\s+(?:from|as\s+of)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}",
            r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            if matches:
                return matches[0] if isinstance(matches[0], str) else matches[0]
        
        return None
    
    def _extract_products(self, tables: List[pd.DataFrame]) -> List[Dict[str, Any]]:
        """Extract product data from tables."""
        products = []
        
        sku_patterns = ["sku", "model", "item", "part", "code", "number", "no", "#"]
        desc_patterns = ["description", "desc", "name", "product", "item"]
        price_patterns = ["price", "cost", "msrp", "list", "retail", "net", "$"]
        meta_columns = {"_page_number", "_extraction_method"}
        def _first_scalar(val: Any):
            if isinstance(val, pd.Series):
                clean = val.dropna()
                return clean.iloc[0] if not clean.empty else None
            if isinstance(val, (list, tuple)) and val:
                return val[0]
            return val
        
        for df in tables:
            if df.empty:
                continue
            
            columns_lower = {col: str(col).lower() for col in df.columns}
            
            sku_col = None
            desc_col = None
            price_col = None
            
            for col, col_lower in columns_lower.items():
                if col in meta_columns:
                    continue
                if any(p in col_lower for p in sku_patterns):
                    sku_col = col
                elif any(p in col_lower for p in desc_patterns):
                    desc_col = col
                elif any(p in col_lower for p in price_patterns):
                    price_col = col

            # Detect price column by content (numeric-heavy and/or currency symbols)
            if price_col is None:
                candidate_price_cols = []

                for col in df.columns:
                    if col in meta_columns:
                        continue
                    series = df[col]
                    non_null = series.dropna()
                    if len(non_null) == 0:
                        continue

                    numeric_count = 0
                    currency_symbol_count = 0
                    for raw_val in non_null:
                        val = _first_scalar(raw_val)
                        if val is None:
                            continue
                        val_str = str(val)
                        price_val = self._clean_price(val_str)
                        if price_val is not None:
                            numeric_count += 1
                        if "$" in val_str:
                            currency_symbol_count += 1

                    if numeric_count / len(non_null) >= 0.5 or currency_symbol_count / len(non_null) >= 0.3:
                        candidate_price_cols.append((col, numeric_count))

                if candidate_price_cols:
                    # Choose the column with the most numeric-looking values
                    candidate_price_cols.sort(key=lambda x: x[1], reverse=True)
                    price_col = candidate_price_cols[0][0]

            # Helper to avoid treating page numbers as SKUs
            def _is_page_number_series(series: pd.Series) -> bool:
                non_null = series.dropna()
                if len(non_null) == 0:
                    return False
                if series.name and "page" in str(series.name).lower():
                    return True
                numeric_ratio = sum(str(x).replace(".", "", 1).isdigit() for x in non_null) / len(non_null)
                unique_vals = pd.unique(non_null)
                if numeric_ratio > 0.9 and len(unique_vals) <= 5:
                    return True
                return False

            # Fallback SKU extractor using regex within any non-meta column
            sku_regexes = [
                r"\b[A-Z0-9]{2,}-[A-Z0-9]{1,}\b",          # contains dash
                r"\b[A-Z]{1,3}\d{2,}[A-Z0-9]*\b",          # letters + digits
                r"\b\d{3,}[A-Z]{1,}[A-Z0-9]*\b",           # digits leading then letter
            ]

            def _extract_sku_from_row(row: pd.Series) -> str:
                # First try designated SKU column
                if sku_col and sku_col in row.index and not _is_page_number_series(df[sku_col]):
                    candidate = _first_scalar(row[sku_col])
                    if pd.notna(candidate):
                        cleaned = self._clean_sku(str(candidate))
                        if cleaned:
                            return cleaned
                # Otherwise search across other columns
                for col in row.index:
                    if col in meta_columns:
                        continue
                    val = _first_scalar(row[col])
                    if val is None or pd.isna(val):
                        continue
                    text = str(val)
                    for pattern in sku_regexes:
                        match = re.search(pattern, text, flags=re.IGNORECASE)
                        if match:
                            cleaned = self._clean_sku(match.group(0))
                            if cleaned:
                                return cleaned
                    # Heuristic: token that has letters and digits and is not all numbers
                    tokens = re.split(r"\s+", text)
                    for token in tokens:
                        if len(token) < 3 or len(token) > 24:
                            continue
                        has_digit = any(c.isdigit() for c in token)
                        has_letter = any(c.isalpha() for c in token)
                        if has_digit and has_letter:
                            cleaned = self._clean_sku(token)
                            if cleaned:
                                return cleaned
                return ""

            # Fallback description chooser: longest text-like cell
            def _choose_description(row: pd.Series) -> str:
                if desc_col and desc_col in row.index:
                    val = _first_scalar(row[desc_col])
                    if val is not None and pd.notna(val):
                        text = str(val).strip()
                        if text:
                            return text
                best_text = ""
                for col in row.index:
                    if col in meta_columns or col == sku_col:
                        continue
                    val = _first_scalar(row[col])
                    if val is None or pd.isna(val):
                        continue
                    text = str(val).strip()
                    # Prefer text that has spaces and letters
                    if len(text) > len(best_text) and any(c.isalpha() for c in text):
                        best_text = text
                return best_text
            
            for idx, row in df.iterrows():
                product = {}

                # Extract SKU with heuristics
                sku_value = _extract_sku_from_row(row)
                if sku_value:
                    product["sku"] = sku_value

                # Extract description
                desc_value = _choose_description(row)
                if desc_value:
                    product["description"] = desc_value

                # Safely extract price
                if price_col and price_col in row.index:
                    price_val = _first_scalar(row[price_col])
                    if isinstance(price_val, pd.Series):
                        price_val = price_val.iloc[0] if len(price_val) > 0 else None
                    if pd.notna(price_val):
                        product["base_price"] = self._clean_price(str(price_val))
                else:
                    # Try to find a numeric price-like cell in the row
                    for col in row.index:
                        if col in meta_columns or col == sku_col:
                            continue
                        val = _first_scalar(row[col])
                        if val is None or pd.isna(val):
                            continue
                        price_candidate = self._clean_price(str(val))
                        if price_candidate is not None:
                            product["base_price"] = price_candidate
                            break

                if product.get("sku") or product.get("description"):
                    if "_page_number" in row.index:
                        page_val = row["_page_number"]
                        product["_source_page"] = page_val.iloc[0] if isinstance(page_val, pd.Series) else page_val
                    if "_extraction_method" in row.index:
                        method_val = row["_extraction_method"]
                        product["_extraction_method"] = method_val.iloc[0] if isinstance(method_val, pd.Series) else method_val
                    products.append(product)
        
        return products
    
    def _clean_sku(self, sku_str: str) -> str:
        """Clean and normalize SKU string."""
        if not sku_str or pd.isna(sku_str):
            return ""
        
        cleaned = str(sku_str).strip().upper()
        cleaned = re.sub(r"^[^\w-]+", "", cleaned)
        cleaned = re.sub(r"[^\w-]+$", "", cleaned)

        # Reject plain numbers (these are often page numbers)
        if cleaned.isdigit():
            return ""

        # Must contain at least one letter and one digit to be a valid SKU
        has_digit = any(c.isdigit() for c in cleaned)
        has_letter = any(c.isalpha() for c in cleaned)
        if not (has_digit and has_letter):
            return ""
        
        return cleaned
    
    def _clean_price(self, price_str: str) -> Optional[float]:
        """Clean and convert price string to float."""
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
    
    def _calculate_overall_confidence(self, results: List[ExtractionResult]) -> float:
        """Calculate overall confidence from all extraction results."""
        if not results:
            return 0.0
        
        total_weight = 0
        weighted_confidence = 0
        
        for result in results:
            weight = max(1, len(result.tables))
            weighted_confidence += result.confidence * weight
            total_weight += weight
        
        return weighted_confidence / total_weight if total_weight > 0 else 0.0
    
    def _compile_processing_notes(
        self,
        results: List[ExtractionResult],
        analyses: List[PageAnalysis]
    ) -> List[str]:
        """Compile processing notes from extraction."""
        notes = []
        
        methods_used = set(r.method.value for r in results)
        notes.append(f"Extraction methods used: {', '.join(methods_used)}")
        
        total_tables = sum(len(r.tables) for r in results)
        notes.append(f"Total tables extracted: {total_tables}")
        
        scanned_pages = sum(1 for a in analyses if a.is_scanned)
        if scanned_pages > 0:
            notes.append(f"Scanned pages detected: {scanned_pages}/{len(analyses)}")
        
        for result in results:
            for error in result.errors:
                notes.append(f"Page {result.page_number} error: {error}")
            for warning in result.warnings:
                notes.append(f"Page {result.page_number} warning: {warning}")
        
        return notes
    
    def _page_analysis_to_dict(self, analysis: PageAnalysis) -> Dict[str, Any]:
        """Convert PageAnalysis to dictionary."""
        return {
            "page_number": analysis.page_number,
            "has_text": analysis.has_text,
            "text_density": analysis.text_density,
            "has_images": analysis.has_images,
            "image_coverage": analysis.image_coverage,
            "has_tables": analysis.has_tables,
            "table_count": analysis.table_count,
            "recommended_method": analysis.recommended_method.value,
            "is_scanned": analysis.is_scanned,
        }


def parse_pdf(pdf_path: str, config: Dict[str, Any] = None) -> ParsedDocument:
    """
    Quick parse a PDF file.
    
    Args:
        pdf_path: Path to PDF file
        config: Optional configuration
        
    Returns:
        ParsedDocument with extracted data
    """
    parser = UniversalPDFParser(config)
    return parser.parse(pdf_path)
