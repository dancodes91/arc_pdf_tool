"""Parallel PDF table extraction utilities."""

import os
from typing import List, Dict
from concurrent.futures import ProcessPoolExecutor
from functools import partial
import logging

logger = logging.getLogger(__name__)


def extract_page_batch(
    pdf_path: str, page_numbers: List[int], flavor: str = "lattice"
) -> Dict[int, List]:
    """Extract tables from a batch of pages in a worker process."""
    import camelot

    results = {}
    for page_num in page_numbers:
        try:
            tables = camelot.read_pdf(
                pdf_path,
                pages=str(page_num),
                flavor=flavor,
                suppress_stdout=True,
                backend="pdfium",  # Faster than ghostscript
            )
            # Convert to DataFrames immediately
            results[page_num] = [t.df for t in tables] if tables.n else []
        except Exception as e:
            logger.warning(f"Failed to extract page {page_num}: {e}")
            results[page_num] = []
    return results


def parallel_table_extraction(
    pdf_path: str,
    page_numbers: List[int],
    max_workers: int = None,
    batch_size: int = 25,
    flavor: str = "lattice",
) -> Dict[int, List]:
    """
    Extract tables from PDF pages in parallel.

    Args:
        pdf_path: Path to PDF file
        page_numbers: List of page numbers to process
        max_workers: Number of parallel workers (default: CPU count, max 8)
        batch_size: Pages per batch (default: 25)
        flavor: Camelot flavor ('lattice' or 'stream')

    Returns:
        Dict mapping page_number -> list of DataFrames
    """
    if max_workers is None:
        max_workers = min(os.cpu_count() or 4, 8)

    # Split pages into batches for workers
    page_batches = [
        page_numbers[i : i + batch_size] for i in range(0, len(page_numbers), batch_size)
    ]

    logger.info(
        f"Processing {len(page_numbers)} pages in {len(page_batches)} batches "
        f"with {max_workers} workers (flavor={flavor})"
    )

    all_results = {}
    extract_func = partial(extract_page_batch, pdf_path, flavor=flavor)

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for batch_idx, batch_results in enumerate(executor.map(extract_func, page_batches)):
            all_results.update(batch_results)
            logger.info(f"Completed batch {batch_idx + 1}/{len(page_batches)}")

    logger.info(f"Extracted {sum(len(tables) for tables in all_results.values())} total tables")
    return all_results
