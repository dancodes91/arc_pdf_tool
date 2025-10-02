#!/usr/bin/env python
"""
Chunked PDF analysis script for large price books.

Analyzes PDF in batches to stay within token/memory limits.
Extracts structure, tables, and identifies parser improvements.
"""
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

import pdfplumber
import re

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ChunkedPDFAnalyzer:
    """Analyze PDF in manageable chunks."""

    def __init__(self, pdf_path: str, chunk_size: int = 100):
        self.pdf_path = pdf_path
        self.chunk_size = chunk_size
        self.analysis_results = {
            'chunks': [],
            'structure': {},
            'table_patterns': [],
            'errors': []
        }

    def analyze_chunk(self, start_page: int, end_page: int) -> Dict[str, Any]:
        """Analyze a chunk of pages."""
        logger.info(f"Analyzing pages {start_page}-{end_page}...")

        chunk_data = {
            'range': f"{start_page}-{end_page}",
            'pages_analyzed': 0,
            'sections_found': [],
            'tables_found': [],
            'sample_tables': [],
            'errors': []
        }

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                total_pages = len(pdf.pages)
                actual_end = min(end_page, total_pages)

                for page_num in range(start_page - 1, actual_end):
                    try:
                        page = pdf.pages[page_num]
                        page_analysis = self._analyze_page(page, page_num + 1)

                        chunk_data['pages_analyzed'] += 1
                        if page_analysis['section']:
                            chunk_data['sections_found'].append(page_analysis['section'])
                        if page_analysis['tables']:
                            chunk_data['tables_found'].extend(page_analysis['tables'])

                        # Keep sample tables (every 10th page or significant tables)
                        if page_num % 10 == 0 or len(page_analysis['tables']) > 2:
                            chunk_data['sample_tables'].append({
                                'page': page_num + 1,
                                'tables': page_analysis['tables'][:2]  # First 2 tables
                            })

                    except Exception as e:
                        error = {
                            'page': page_num + 1,
                            'error': str(e),
                            'type': type(e).__name__
                        }
                        chunk_data['errors'].append(error)
                        logger.warning(f"Error on page {page_num + 1}: {e}")

        except Exception as e:
            logger.error(f"Error analyzing chunk {start_page}-{end_page}: {e}")
            chunk_data['errors'].append({
                'chunk': f"{start_page}-{end_page}",
                'error': str(e),
                'type': type(e).__name__
            })

        return chunk_data

    def _analyze_page(self, page, page_num: int) -> Dict[str, Any]:
        """Analyze a single page."""
        analysis = {
            'page_num': page_num,
            'section': None,
            'tables': [],
            'text_blocks': []
        }

        # Extract text for section detection
        text = page.extract_text() or ''

        # Detect section headers (large font, all caps, specific patterns)
        section = self._detect_section(text, page_num)
        if section:
            analysis['section'] = section

        # Extract tables
        tables = page.extract_tables()
        if tables:
            for table_idx, table in enumerate(tables):
                if table and len(table) > 1:  # At least header + 1 row
                    table_info = {
                        'page': page_num,
                        'table_index': table_idx,
                        'rows': len(table),
                        'cols': len(table[0]) if table else 0,
                        'sample_rows': table[:3],  # First 3 rows
                        'has_prices': self._has_prices(table)
                    }
                    analysis['tables'].append(table_info)

        return analysis

    def _detect_section(self, text: str, page_num: int) -> Dict[str, Any]:
        """Detect section headers from text."""
        lines = text.split('\n')[:10]  # Check first 10 lines

        for line in lines:
            line_clean = line.strip()

            # Patterns for Hager sections
            patterns = [
                (r'^(PART|SECTION|CHAPTER)\s+(\d+|[A-Z])', 'major_section'),
                (r'^([A-Z\s&]{10,})\s*$', 'section_title'),  # All caps title
                (r'^(BB|CTW|EC|EL|SG|TH|MA|PS)\d+\s+Series', 'product_family'),
                (r'^\d+\s+HAGER\s+COMPANIES', 'page_header'),
            ]

            for pattern, section_type in patterns:
                match = re.search(pattern, line_clean, re.IGNORECASE)
                if match:
                    return {
                        'page': page_num,
                        'type': section_type,
                        'text': line_clean,
                        'match': match.group(0)
                    }

        return None

    def _has_prices(self, table: List[List]) -> bool:
        """Check if table contains price data."""
        for row in table[:5]:  # Check first 5 rows
            for cell in row:
                if cell and isinstance(cell, str):
                    # Look for currency or decimal patterns
                    if re.search(r'\$?\d+\.\d{2}', cell):
                        return True
        return False

    def save_chunk_results(self, chunk_data: Dict, output_dir: Path):
        """Save chunk analysis results."""
        chunk_range = chunk_data['range']
        output_file = output_dir / f"batch_{chunk_range}.json"

        with open(output_file, 'w') as f:
            json.dump(chunk_data, f, indent=2, default=str)

        logger.info(f"Saved chunk results to {output_file}")

    def run_full_analysis(self) -> Dict[str, Any]:
        """Run analysis on entire PDF in chunks."""
        logger.info(f"Starting chunked analysis of {self.pdf_path}")

        # Get total pages
        with pdfplumber.open(self.pdf_path) as pdf:
            total_pages = len(pdf.pages)

        logger.info(f"Total pages: {total_pages}")

        # Process in chunks
        output_dir = Path('samples/extracted')
        output_dir.mkdir(parents=True, exist_ok=True)

        chunks = []
        for start in range(1, total_pages + 1, self.chunk_size):
            end = min(start + self.chunk_size - 1, total_pages)
            chunk_data = self.analyze_chunk(start, end)
            chunks.append(chunk_data)

            # Save intermediate results
            self.save_chunk_results(chunk_data, output_dir)

        # Compile summary
        summary = {
            'pdf_path': str(self.pdf_path),
            'total_pages': total_pages,
            'chunk_size': self.chunk_size,
            'chunks_processed': len(chunks),
            'timestamp': datetime.now().isoformat(),
            'chunks': chunks
        }

        return summary


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Analyze PDF in chunks')
    parser.add_argument('pdf_path', help='Path to PDF file')
    parser.add_argument('--chunk-size', type=int, default=100, help='Pages per chunk')
    parser.add_argument('--start-page', type=int, default=1, help='Start page')
    parser.add_argument('--end-page', type=int, help='End page (default: all)')

    args = parser.parse_args()

    analyzer = ChunkedPDFAnalyzer(args.pdf_path, chunk_size=args.chunk_size)

    if args.end_page:
        # Single chunk
        chunk_data = analyzer.analyze_chunk(args.start_page, args.end_page)
        output_dir = Path('samples/extracted')
        output_dir.mkdir(parents=True, exist_ok=True)
        analyzer.save_chunk_results(chunk_data, output_dir)
        print(json.dumps(chunk_data, indent=2, default=str))
    else:
        # Full analysis
        summary = analyzer.run_full_analysis()

        # Save summary
        summary_file = Path('samples/extracted/analysis_summary.json')
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        logger.info(f"Analysis complete. Summary saved to {summary_file}")
        print(f"\nAnalysis Summary:")
        print(f"Total pages: {summary['total_pages']}")
        print(f"Chunks processed: {summary['chunks_processed']}")
        print(f"Total tables found: {sum(len(c['tables_found']) for c in summary['chunks'])}")


if __name__ == '__main__':
    main()
