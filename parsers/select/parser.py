"""
Enhanced SELECT Hinges parser using shared utilities.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from ..shared.pdf_io import EnhancedPDFExtractor, PDFDocument
from ..shared.provenance import ProvenanceTracker, ParsedItem, ProvenanceAnalyzer
from .sections import SelectSectionExtractor


logger = logging.getLogger(__name__)


class SelectHingesParser:
    """Enhanced SELECT Hinges parser with comprehensive extraction capabilities."""

    def __init__(self, pdf_path: str, config: Dict[str, Any] = None):
        self.pdf_path = pdf_path
        self.config = config or {}
        self.logger = logging.getLogger(f"{__class__.__name__}")

        # Initialize utilities
        self.provenance_tracker = ProvenanceTracker(pdf_path)
        self.section_extractor = SelectSectionExtractor(self.provenance_tracker)
        self.pdf_extractor = EnhancedPDFExtractor(pdf_path, config)

        # Parser results
        self.document: Optional[PDFDocument] = None
        self.effective_date: Optional[ParsedItem] = None
        self.net_add_options: List[ParsedItem] = []
        self.products: List[ParsedItem] = []
        self.finishes: List[ParsedItem] = []

        # Progress callback for async updates
        self.progress_callback: Optional[callable] = None

        # OPTIMIZATION: Reusable pdfplumber handle to avoid re-opening PDF 100+ times
        self._pdfplumber_handle = None

    def set_progress_callback(self, callback: callable):
        """Set callback function for progress updates (progress: int, message: str)"""
        self.progress_callback = callback

    def _update_progress(self, progress: int, message: str):
        """Internal method to call progress callback if set"""
        if self.progress_callback:
            try:
                self.progress_callback(progress, message)
            except Exception as e:
                self.logger.warning(f"Error calling progress callback: {e}")

    def _open_pdfplumber_once(self):
        """
        OPTIMIZATION: Open pdfplumber handle once and reuse it.
        Prevents re-opening the entire PDF for each page (saves 50-100MB per page).
        """
        if self._pdfplumber_handle is None:
            import pdfplumber
            self._pdfplumber_handle = pdfplumber.open(self.pdf_path)
            self.logger.debug(f"Opened pdfplumber handle (will be reused for all pages)")
        return self._pdfplumber_handle

    def _close_pdfplumber(self):
        """OPTIMIZATION: Close pdfplumber handle to free memory."""
        if self._pdfplumber_handle is not None:
            try:
                self._pdfplumber_handle.close()
                self._pdfplumber_handle = None
                self.logger.debug("Closed pdfplumber handle")
            except Exception as e:
                self.logger.warning(f"Error closing pdfplumber: {e}")

    def __del__(self):
        """Cleanup: Ensure pdfplumber handle is closed."""
        self._close_pdfplumber()

    def parse(self) -> Dict[str, Any]:
        """Parse SELECT Hinges PDF with comprehensive extraction."""
        self.logger.info(f"Starting enhanced SELECT Hinges parsing: {self.pdf_path}")

        try:
            # Extract PDF document
            self._update_progress(15, 'Extracting PDF pages...')
            self.document = self.pdf_extractor.extract_document()
            total_pages = len(self.document.pages)
            self.logger.info(f"Extracted PDF with {total_pages} pages")
            self._update_progress(20, f'Extracted {total_pages} pages')

            # Combine all text content
            self._update_progress(25, 'Processing text content...')
            full_text = self._combine_text_content()

            # Extract all tables
            self._update_progress(30, 'Extracting tables...')
            all_tables = self._combine_all_tables()

            # Parse sections
            self._update_progress(35, 'Parsing document sections...')
            self._parse_effective_date(full_text)
            self._parse_finishes(full_text)
            self._parse_net_add_options(full_text)
            self._parse_model_tables(full_text, all_tables, total_pages=total_pages)

            # Build final results
            results = self._build_results()

            self.logger.info(f"SELECT parsing completed: {self._get_summary()}")
            return results

        except Exception as e:
            self.logger.error(f"Error during SELECT parsing: {e}")
            return self._build_error_results(str(e))
        finally:
            # OPTIMIZATION: Always close pdfplumber handle to free memory
            self._close_pdfplumber()
            import gc
            gc.collect()

    def _combine_text_content(self) -> str:
        """Combine text content from all pages."""
        if not self.document:
            return ""

        text_parts = []
        for page in self.document.pages:
            if page.text:
                text_parts.append(f"--- PAGE {page.page_number} ---\n{page.text}")

        return "\n\n".join(text_parts)

    def _combine_all_tables(self) -> List[Any]:
        """Combine all tables from all pages."""
        if not self.document:
            return []

        all_tables = []
        for page in self.document.pages:
            for table in page.tables:
                all_tables.append(table)

        return all_tables

    def _parse_effective_date(self, text: str) -> None:
        """Parse effective date from document."""
        self.logger.info("Parsing effective date...")
        self.effective_date = self.section_extractor.extract_effective_date(text)

        if self.effective_date:
            self.logger.info(f"Found effective date: {self.effective_date.value}")
        else:
            self.logger.warning("No effective date found")

    def _parse_finishes(self, text: str) -> None:
        """Parse finish symbols from document."""
        self.logger.info("Parsing finish symbols...")
        self.finishes = self.section_extractor.extract_finish_symbols(text)
        self.logger.info(f"Found {len(self.finishes)} finish symbols")

    def _parse_net_add_options(self, text: str) -> None:
        """Parse net add options from document."""
        self.logger.info("Parsing net add options...")
        self.net_add_options = self.section_extractor.extract_net_add_options(text)

        self.logger.info(f"Found {len(self.net_add_options)} net add options")
        for option in self.net_add_options:
            if isinstance(option.value, dict):
                code = option.value.get("option_code", "Unknown")
                price = option.value.get("adder_value", 0)
                self.logger.debug(f"  {code}: ${price}")

    def _parse_model_tables(self, text: str, tables: List[Any], total_pages: int = None) -> None:
        """Parse product model tables page by page - ALWAYS try Camelot for complete extraction."""
        import time
        import gc
        
        self.logger.info("Parsing model tables...")
        self.products = []
        pages_processed = []

        # Time limit for Render Pro tier (9 minutes to leave buffer for 10min gunicorn timeout)
        start_time = time.time()
        max_processing_time = 540.0  # 9 minutes (leaves 60s buffer)
        max_pages = self.config.get("max_pages")  # Limit pages if configured

        camelot_settings = {
            "quality_threshold": self.config.get("table_quality_threshold", 45),
            "enable": self.config.get("enable_camelot", True),
            "flavors": self.config.get("camelot_flavors", ["stream"]),  # Only stream for speed
            "max_pages": self.config.get("max_camelot_pages"),
        }
        camelot_pages_used = 0

        # Process pages with timeout and page limit protection
        pages_to_process = self.document.pages
        if max_pages:
            pages_to_process = pages_to_process[:max_pages]
            self.logger.info(f"Limiting to first {max_pages} pages due to max_pages config")
        else:
            self.logger.info(f"Processing all {len(pages_to_process)} pages (Pro tier - no page limit)")
        
        # Process pages in batches of 5 for memory management
        batch_size = 5
        total_pages_to_process = len(pages_to_process)
        for batch_idx, page in enumerate(pages_to_process):
            # Check if we're running out of time
            elapsed = time.time() - start_time
            if elapsed > max_processing_time:
                self.logger.warning(
                    f"Stopping parsing early after {elapsed:.1f}s to prevent timeout. "
                    f"Processed {len(pages_processed)} pages, found {len(self.products)} products."
                )
                break
            
            # Update progress every page (progress from 40% to 65% for page processing)
            page_num = page.page_number
            if total_pages_to_process > 0:
                # Progress: 40% (start) to 65% (end of page processing)
                page_progress = 40 + int((batch_idx + 1) / total_pages_to_process * 25)
                self._update_progress(
                    page_progress,
                    f'Processing page {page_num}/{total_pages_to_process} ({len(self.products)} products found)'
                )
            
            # Use pdfplumber for text extraction to preserve table formatting
            # Open PDF fresh for each page to prevent memory accumulation
            # The Enhanced PDF Extractor (pypdf) fragments tables into separate lines
            page_text = self._extract_page_text_with_pdfplumber(page.page_number)
            
            # Fallback to existing page text if pdfplumber timed out or failed
            if not page_text and page.text:
                page_text = page.text
                self.logger.debug(f"Using fallback text extraction for page {page.page_number}")

            # Check time remaining before starting expensive operations
            elapsed = time.time() - start_time
            time_remaining = max_processing_time - elapsed
            
            # Skip Camelot if we're running low on time (need at least 20s for Camelot)
            if time_remaining < 20.0:
                self.logger.warning(
                    f"Skipping Camelot extraction for page {page_num} - only {time_remaining:.1f}s remaining"
                )
                # Disable Camelot for this page
                page_camelot_settings = camelot_settings.copy()
                page_camelot_settings['enable'] = False
            else:
                page_camelot_settings = camelot_settings

            page_tables, extraction_method, camelot_used = self._resolve_page_tables(
                page, page_text, camelot_pages_used, page_camelot_settings
            )

            if camelot_used:
                camelot_pages_used += 1

            # ALWAYS try extraction, even if no tables found
            # Text-based extraction can find products that table extraction misses
            page_products = self.section_extractor.extract_model_tables(
                page_text, page_tables or [], page_number=page_num
            )

            # OPTIMIZATION: Clear references immediately after use
            del page_tables

            if page_products:
                self.products.extend(page_products)
                pages_processed.append(page_num)
                self.logger.debug(
                    f"Page {page_num}: extracted {len(page_products)} products using {extraction_method or 'text'}"
                )
                # Clear page_products reference after extending
                del page_products

            # Clear page_text after processing
            del page_text

            # OPTIMIZATION: Aggressive garbage collection after EVERY page
            # This prevents memory accumulation on large PDFs
            gc.collect()

            # Full garbage collection every 10 pages (increased from 5 for efficiency)
            if (batch_idx + 1) % 10 == 0:
                gc.collect(2)  # Full generation 2 collection
                gc.collect(1)  # Generation 1 collection
                gc.collect(0)  # Young generation collection
                self.logger.debug(f"Completed {batch_idx + 1} pages, performed full GC (3 generations)")

        elapsed_total = time.time() - start_time
        self.logger.info(
            f"Found {len(self.products)} products across {len(pages_processed)} pages "
            f"in {elapsed_total:.1f}s: {pages_processed}"
        )

        # Log sample products for verification
        for i, product in enumerate(self.products[:5]):  # First 5 products
            if isinstance(product.value, dict):
                sku = product.value.get("sku", "Unknown")
                price = product.value.get("base_price", 0)
                self.logger.debug(f"  {sku}: ${price}")

    def _extract_page_text_with_pdfplumber(self, page_number: int) -> str:
        """Extract text from a specific page using pdfplumber with timeout protection.

        OPTIMIZED: Reuses single pdfplumber handle instead of opening PDF for each page.
        This saves 50-100MB per page on large PDFs.

        pdfplumber preserves table formatting better than pypdf,
        which is critical for extracting horizontal product tables.

        Args:
            page_number: 1-based page number
        """
        import threading

        # Timeout per page to prevent hanging (15 seconds)
        page_timeout = 15.0

        class TextExtractor:
            def __init__(self):
                self.result = ""
                self.completed = False
                self.error = None

            def extract(self, pdf, page_idx):
                try:
                    page = pdf.pages[page_idx]
                    self.result = page.extract_text() or ""
                    self.completed = True
                except Exception as e:
                    self.error = str(e)
                    self.completed = True

        try:
            # OPTIMIZATION: Reuse single pdfplumber handle
            pdf = self._open_pdfplumber_once()

            # Run extraction in a thread with timeout
            extractor = TextExtractor()
            page_idx = page_number - 1  # pdfplumber uses 0-based indexing

            thread = threading.Thread(target=extractor.extract, args=(pdf, page_idx))
            thread.daemon = True
            thread.start()
            thread.join(timeout=page_timeout)

            if thread.is_alive():
                # Thread is still running - it timed out
                self.logger.warning(
                    f"pdfplumber text extraction timed out after {page_timeout}s for page {page_number}. "
                    f"Falling back to existing page text."
                )
                # OPTIMIZATION: Force cleanup of timed-out thread resources
                del extractor
                import gc
                gc.collect()
                # Return empty string - will use existing page text from document
                return ""

            if extractor.completed:
                if extractor.error:
                    self.logger.warning(f"pdfplumber text extraction failed for page {page_number}: {extractor.error}")
                    return ""
                return extractor.result
            else:
                self.logger.warning(f"pdfplumber text extraction did not complete for page {page_number}")
                return ""
        except Exception as e:
            self.logger.warning(f"pdfplumber text extraction failed for page {page_number}: {e}")
            return ""

    def _detect_has_grid_lines(self, page_text: str) -> bool:
        """
        OPTIMIZATION: Detect if page likely has grid lines for smart Camelot flavor selection.
        Reduces Camelot attempts from 2-3 to 1, saving 50% processing time.

        Returns:
            True if page likely has grid/border lines (use lattice)
            False if borderless tables (use stream)
        """
        # Heuristic: Look for patterns that indicate structured tables with borders
        grid_indicators = [
            r'\+[-+]+\+',           # ASCII box drawing characters
            r'\|.*\|.*\|',          # Multiple pipes suggesting columns
            r'─',                   # Unicode box drawing
            r'│',                   # Unicode vertical lines
        ]

        for pattern in grid_indicators:
            if re.search(pattern, page_text):
                return True

        # Check for dense numeric content (often in bordered tables)
        lines = page_text.split('\n')
        numeric_lines = sum(1 for line in lines if re.search(r'\d+\.\d{2}', line))
        if numeric_lines > len(lines) * 0.3:  # 30%+ lines have prices
            return True

        return False

    def _resolve_page_tables(
        self,
        page: Any,
        page_text: str,
        camelot_pages_used: int,
        camelot_settings: Dict[str, Any],
    ) -> Tuple[List[Any], str, bool]:
        """
        Determine the best table extraction for a page.

        OPTIMIZED: Smart flavor selection - only tries 1 Camelot flavor instead of 2-3.

        Prioritizes tables already extracted during PDF parsing and only falls back to
        Camelot when required. Returns the tables, the method name chosen, and whether
        Camelot was invoked for this page.
        """

        fallback_tables = list(page.tables) if page.tables else []
        fallback_method = getattr(page, "extraction_method", "pdfplumber") or "pdfplumber"
        fallback_score = self._table_quality_score(fallback_tables)

        quality_threshold = camelot_settings.get("quality_threshold", 45)
        camelot_enabled = camelot_settings.get("enable", True)
        camelot_max_pages = camelot_settings.get("max_pages")

        if camelot_enabled and camelot_max_pages is not None:
            camelot_enabled = camelot_pages_used < camelot_max_pages

        # Use existing tables if they look good enough
        if fallback_tables and fallback_score >= quality_threshold:
            self.logger.debug(
                f"Page {page.page_number}: using existing tables (score={fallback_score})"
            )
            return fallback_tables, fallback_method, False

        best_tables = fallback_tables
        best_method = fallback_method if fallback_tables else "none"
        best_score = fallback_score
        camelot_used = False

        if camelot_enabled:
            # Get timeout from config, default to 15 seconds (reduced for speed)
            camelot_timeout = self.config.get("camelot_timeout", 15)

            # OPTIMIZATION: Smart flavor selection based on page analysis
            has_grid_lines = self._detect_has_grid_lines(page_text)

            if has_grid_lines:
                camelot_flavors = ['lattice']  # Only try lattice for gridded tables
                self.logger.debug(f"Page {page.page_number}: Detected grid lines, using lattice only")
            else:
                camelot_flavors = ['stream']   # Only try stream for borderless tables
                self.logger.debug(f"Page {page.page_number}: No grid detected, using stream only")

            for flavor in camelot_flavors:
                self.logger.info(
                    f"Page {page.page_number}: Attempting Camelot {flavor} extraction "
                    f"(timeout={camelot_timeout}s)"
                )

                tables = self.section_extractor.extract_tables_with_camelot(
                    self.pdf_path, page.page_number, flavor=flavor, timeout=camelot_timeout
                )

                if not tables:
                    self.logger.debug(
                        f"Page {page.page_number}: Camelot {flavor} returned no tables "
                        f"(possibly timed out or failed)"
                    )
                    continue

                camelot_used = True
                tables_score = self._table_quality_score(tables)
                self.logger.info(
                    f"Page {page.page_number}: Camelot {flavor} score={tables_score} "
                    f"(fallback_score={best_score})"
                )

                if tables_score > best_score:
                    # Clear previous best_tables if replacing
                    if best_tables and best_tables != fallback_tables:
                        del best_tables
                    best_tables = tables
                    best_method = f"camelot_{flavor}"
                    best_score = tables_score
                    self.logger.info(
                        f"Page {page.page_number}: Using Camelot {flavor} as best method"
                    )
                else:
                    # Clear tables that didn't win to free memory
                    del tables

                # OPTIMIZATION: Since we only try 1 flavor now, no need for quality check break
                break

        if best_tables:
            return best_tables, best_method, camelot_used

        return [], "none", camelot_used

    def _build_results(self) -> Dict[str, Any]:
        """Build final parsing results."""
        # Calculate overall confidence
        all_items = []
        if self.effective_date:
            all_items.append(self.effective_date)
        all_items.extend(self.net_add_options)
        all_items.extend(self.products)

        # Analyze extraction quality
        analyzer = ProvenanceAnalyzer()
        quality_analysis = analyzer.analyze_extraction_quality(all_items)

        # Build structured results
        results = {
            "manufacturer": "SELECT Hinges",
            "source_file": self.pdf_path,
            "parsing_metadata": {
                "parser_version": "2.0",
                "extraction_method": "enhanced_pipeline",
                "total_pages": len(self.document.pages) if self.document else 0,
                "overall_confidence": quality_analysis["quality_score"],
                "extraction_quality": quality_analysis,
            },
            "effective_date": self._serialize_item(self.effective_date),
            "net_add_options": [self._serialize_item(item) for item in self.net_add_options],
            "products": [self._serialize_item(item) for item in self.products],
            "finish_symbols": [self._serialize_item(item) for item in self.finishes],
            "summary": {
                "total_products": len(self.products),
                "total_finishes": len(self.finishes),
                "total_options": len(self.net_add_options),
                "has_effective_date": self.effective_date is not None,
                "confidence_distribution": quality_analysis.get("confidence_distribution", {}),
                "recommendations": quality_analysis.get("recommendations", []),
            },
        }

        # Add validation results
        results["validation"] = self._validate_results(results)

        return results

    def _table_quality_score(self, tables: List[Any]) -> int:
        """Heuristic score to determine how usable a set of tables is."""
        if not tables:
            return 0

        score = 0
        for table in tables:
            try:
                df = table if hasattr(table, "values") else None
                if df is None:
                    continue

                num_cols = df.shape[1]
                numeric_cells = 0
                for cell in df.values.flatten():
                    if isinstance(cell, str) and re.search(r"\d", cell):
                        numeric_cells += 1

                # Weighted score: favor tables with more columns and numeric entries
                score += num_cols * 10 + numeric_cells

            except Exception:
                continue

        return score

    def _build_error_results(self, error_message: str) -> Dict[str, Any]:
        """Build results when parsing fails."""
        return {
            "manufacturer": "SELECT Hinges",
            "source_file": self.pdf_path,
            "parsing_metadata": {
                "parser_version": "2.0",
                "extraction_method": "enhanced_pipeline",
                "status": "failed",
                "error": error_message,
            },
            "effective_date": None,
            "net_add_options": [],
            "products": [],
            "summary": {
                "total_products": 0,
                "total_options": 0,
                "has_effective_date": False,
                "parsing_failed": True,
                "error_message": error_message,
            },
            "validation": {
                "is_valid": False,
                "errors": [f"Parsing failed: {error_message}"],
                "warnings": [],
                "accuracy_metrics": {},
            },
        }

    def _serialize_item(self, item: Optional[ParsedItem]) -> Optional[Dict[str, Any]]:
        """Serialize a parsed item for output."""
        if not item:
            return None

        return {
            "value": item.value,
            "data_type": item.data_type,
            "normalized_value": item.normalized_value,
            "confidence": item.confidence,
            "provenance": item.provenance.to_dict() if item.provenance else None,
            "validation_errors": item.validation_errors,
        }

    def _validate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parsing results."""
        validation = {"is_valid": True, "errors": [], "warnings": [], "accuracy_metrics": {}}

        # Check for effective date
        if not results["effective_date"]:
            validation["warnings"].append("No effective date found")

        # Check product count
        product_count = len(results["products"])
        if product_count == 0:
            validation["errors"].append("No products extracted")
            validation["is_valid"] = False
        elif product_count < 10:
            validation["warnings"].append(f"Low product count: {product_count}")

        # Check option count
        option_count = len(results["net_add_options"])
        if option_count == 0:
            validation["warnings"].append("No net add options found")

        # Calculate accuracy metrics
        total_items = product_count + option_count
        if total_items > 0:
            # Count items with high confidence
            high_confidence_count = 0
            for item_list in [results["products"], results["net_add_options"]]:
                for item in item_list:
                    if item and item.get("confidence", 0) >= 0.8:
                        high_confidence_count += 1

            confidence_rate = high_confidence_count / total_items
            validation["accuracy_metrics"]["confidence_rate"] = confidence_rate

            if confidence_rate < 0.7:
                validation["warnings"].append(f"Low confidence rate: {confidence_rate:.1%}")

        # Overall validation
        if len(validation["errors"]) == 0 and len(validation["warnings"]) <= 2:
            validation["accuracy_metrics"]["overall_quality"] = "good"
        elif len(validation["errors"]) == 0:
            validation["accuracy_metrics"]["overall_quality"] = "acceptable"
        else:
            validation["accuracy_metrics"]["overall_quality"] = "poor"

        return validation

    def _get_summary(self) -> str:
        """Get parsing summary for logging."""
        return (
            f"{len(self.products)} products, "
            f"{len(self.net_add_options)} options, "
            f"effective_date={'found' if self.effective_date else 'not_found'}"
        )

    def get_provenance_report(self) -> str:
        """Generate detailed provenance report."""
        all_items = []
        if self.effective_date:
            all_items.append(self.effective_date)
        all_items.extend(self.net_add_options)
        all_items.extend(self.products)

        analyzer = ProvenanceAnalyzer()
        return analyzer.export_provenance_report(all_items)

    def export_golden_data(self, output_dir: str) -> Dict[str, str]:
        """Export golden test data for validation."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        files_created = {}

        # Export effective date
        if self.effective_date:
            date_file = output_path / "effective_date.json"
            import json

            with open(date_file, "w") as f:
                json.dump(self._serialize_item(self.effective_date), f, indent=2, default=str)
            files_created["effective_date"] = str(date_file)

        # Export options
        if self.net_add_options:
            options_file = output_path / "net_add_options.json"
            with open(options_file, "w") as f:
                options_data = [self._serialize_item(item) for item in self.net_add_options]
                json.dump(options_data, f, indent=2, default=str)
            files_created["options"] = str(options_file)

        # Export products (sample)
        if self.products:
            products_file = output_path / "products_sample.json"
            sample_products = self.products[:10]  # First 10 products
            with open(products_file, "w") as f:
                products_data = [self._serialize_item(item) for item in sample_products]
                json.dump(products_data, f, indent=2, default=str)
            files_created["products"] = str(products_file)

        # Export provenance report
        provenance_file = output_path / "provenance_report.txt"
        with open(provenance_file, "w") as f:
            f.write(self.get_provenance_report())
        files_created["provenance"] = str(provenance_file)

        return files_created

    def identify_manufacturer(self) -> str:
        """Identify manufacturer from PDF content for compatibility with app.py."""
        # Extract text if not already done
        if not hasattr(self, "document") or not self.document:
            try:
                self.document = self.pdf_extractor.extract_document()
            except Exception:
                pass

        # Get text content
        text = self._combine_text_content()
        if not text:
            return "select_hinges"  # Default for SELECT parser

        # Look for SELECT indicators
        text_lower = text.lower()
        select_indicators = [
            "select hinges",
            "select hardware",
            "selecthinges",
            "manufactured by select",
            "select hinge",
        ]

        for indicator in select_indicators:
            if indicator in text_lower:
                return "select_hinges"

        # Check for Hager indicators (in case wrong parser was used)
        hager_indicators = ["hager", "hager companies", "architectural hardware group"]
        for indicator in hager_indicators:
            if indicator in text_lower:
                return "hager"

        # Default to select_hinges for this parser
        return "select_hinges"
