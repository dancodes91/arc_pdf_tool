"""
Advanced table processing for PDF parsing.

Handles header welding, merged cell recovery, cross-page stitching,
and other table heuristics for robust data extraction.
"""

import re
import logging
import pandas as pd
from typing import List, Dict, Tuple, Union
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TableStructure:
    """Metadata about table structure."""

    has_multi_row_header: bool
    merged_cells: List[Tuple[int, int, int, int]]  # (start_row, end_row, start_col, end_col)
    header_rows: int
    data_rows: int
    confidence: float
    fingerprint: str  # For cross-page matching


@dataclass
class ProcessedTable:
    """Result of table processing."""

    dataframe: pd.DataFrame
    structure: TableStructure
    original_shape: Tuple[int, int]
    processing_notes: List[str]
    confidence: float


class TableProcessor:
    """
    Advanced table processing with layout heuristics.

    Handles common PDF table issues like multi-row headers,
    merged cells, and cross-page table continuation.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def process_table(
        self,
        table_data: Union[pd.DataFrame, List[List]],
        page_number: int = 0,
        table_index: int = 0,
    ) -> ProcessedTable:
        """
        Process a raw table with all heuristics.

        Args:
            table_data: Raw table data (DataFrame or list of lists)
            page_number: Page number for context
            table_index: Table index on page

        Returns:
            ProcessedTable with enhanced structure
        """
        # Convert to DataFrame if needed
        if isinstance(table_data, list):
            df = pd.DataFrame(table_data)
        else:
            df = table_data.copy()

        if df.empty:
            return ProcessedTable(
                dataframe=df,
                structure=TableStructure(False, [], 0, 0, 0.0, ""),
                original_shape=(0, 0),
                processing_notes=["Empty table"],
                confidence=0.0,
            )

        original_shape = df.shape
        processing_notes = []

        # Step 1: Detect and weld multi-row headers
        df, header_info = self._weld_headers(df)
        if header_info["welded"]:
            processing_notes.append(f"Welded {header_info['rows']} header rows")

        # Step 2: Recover merged cells
        df, merged_cells = self._recover_merged_cells(df)
        if merged_cells:
            processing_notes.append(f"Recovered {len(merged_cells)} merged cell regions")

        # Step 3: Normalize data types and clean
        df = self._normalize_table_data(df)
        processing_notes.append("Normalized data types")

        # Step 4: Calculate structure metadata
        structure = self._analyze_structure(df, merged_cells, header_info)

        # Step 5: Calculate processing confidence
        confidence = self._calculate_confidence(df, structure, original_shape)

        return ProcessedTable(
            dataframe=df,
            structure=structure,
            original_shape=original_shape,
            processing_notes=processing_notes,
            confidence=confidence,
        )

    def _weld_headers(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """
        Detect and weld multi-row headers into single logical row.

        Args:
            df: Input DataFrame

        Returns:
            Tuple of (processed_df, header_info)
        """
        if len(df) < 2:
            return df, {"welded": False, "rows": 0}

        # Look for header patterns in first few rows
        header_candidates = []

        for i in range(min(3, len(df))):
            row = df.iloc[i]

            # Check if this looks like a header row
            is_header = self._is_header_row(row, df)
            header_candidates.append((i, is_header))

        # Find consecutive header rows
        header_rows = []
        for i, (row_idx, is_header) in enumerate(header_candidates):
            if is_header:
                header_rows.append(row_idx)
            elif header_rows:  # Stop at first non-header after headers found
                break

        if len(header_rows) <= 1:
            return df, {"welded": False, "rows": 0}

        # Weld headers together
        welded_header = []
        for col_idx in range(len(df.columns)):
            # Combine header text from all header rows
            header_parts = []
            for row_idx in header_rows:
                cell_value = str(df.iloc[row_idx, col_idx]).strip()
                if cell_value and cell_value.lower() not in ["nan", "none", ""]:
                    header_parts.append(cell_value)

            # Join with space, remove duplicates
            welded_text = " ".join(dict.fromkeys(header_parts))  # Preserves order, removes dupes
            welded_header.append(welded_text or f"col_{col_idx}")

        # Create new DataFrame with welded header
        data_start_row = max(header_rows) + 1
        new_df = df.iloc[data_start_row:].copy()
        new_df.columns = welded_header
        new_df.reset_index(drop=True, inplace=True)

        return new_df, {"welded": True, "rows": len(header_rows)}

    def _is_header_row(self, row: pd.Series, df: pd.DataFrame) -> bool:
        """
        Determine if a row looks like a header.

        Args:
            row: Row to check
            df: Full dataframe for context

        Returns:
            True if row appears to be a header
        """
        row_text = " ".join(str(cell) for cell in row).lower()

        # Header indicators
        header_keywords = [
            "model",
            "description",
            "price",
            "series",
            "size",
            "finish",
            "code",
            "name",
            "qty",
            "quantity",
            "part",
            "sku",
            "item",
        ]

        # Check for header keywords
        has_keywords = any(keyword in row_text for keyword in header_keywords)

        # Check if mostly text (not numbers/prices)
        numeric_cells = sum(1 for cell in row if self._is_numeric_or_price(str(cell)))
        mostly_text = numeric_cells / len(row) < 0.3

        # Check if different from data rows (if any exist below)
        different_pattern = True
        if len(df) > row.name + 1:
            next_row = df.iloc[row.name + 1]
            next_numeric = sum(1 for cell in next_row if self._is_numeric_or_price(str(cell)))
            current_numeric = sum(1 for cell in row if self._is_numeric_or_price(str(cell)))
            different_pattern = abs(next_numeric - current_numeric) >= 2

        return has_keywords and mostly_text and different_pattern

    def _is_numeric_or_price(self, text: str) -> bool:
        """Check if text represents a number or price."""
        text = text.strip()
        if not text or text.lower() in ["nan", "none", ""]:
            return False

        # Remove currency symbols and check if numeric
        clean_text = re.sub(r"[$,]", "", text)
        try:
            float(clean_text)
            return True
        except ValueError:
            return False

    def _recover_merged_cells(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Tuple]]:
        """
        Recover merged cells by propagating values downward and rightward.

        Args:
            df: Input DataFrame

        Returns:
            Tuple of (processed_df, merged_cell_regions)
        """
        if df.empty:
            return df, []

        new_df = df.copy()
        merged_regions = []

        # Forward fill for vertically merged cells
        for col_idx in range(len(df.columns)):
            col_data = new_df.iloc[:, col_idx]

            # Find spans of empty cells after non-empty cells
            current_value = None
            span_start = None

            for row_idx in range(len(col_data)):
                cell_value = str(col_data.iloc[row_idx]).strip()

                if cell_value and cell_value.lower() not in ["nan", "none", ""]:
                    # Non-empty cell
                    if span_start is not None and current_value:
                        # End of merged span - fill it
                        merged_regions.append((span_start, row_idx - 1, col_idx, col_idx))
                        new_df.iloc[span_start:row_idx, col_idx] = current_value

                    current_value = cell_value
                    span_start = None

                elif current_value and span_start is None:
                    # Start of potential merged span
                    span_start = row_idx

            # Handle span at end of column
            if span_start is not None and current_value:
                merged_regions.append((span_start, len(col_data) - 1, col_idx, col_idx))
                new_df.iloc[span_start:, col_idx] = current_value

        # Forward fill for horizontally merged cells (headers mainly)
        for row_idx in range(min(3, len(new_df))):  # Only check first few rows
            row_data = new_df.iloc[row_idx]

            current_value = None
            span_start = None

            for col_idx in range(len(row_data)):
                cell_value = str(row_data.iloc[col_idx]).strip()

                if cell_value and cell_value.lower() not in ["nan", "none", ""]:
                    # Non-empty cell
                    if span_start is not None and current_value:
                        # End of merged span
                        merged_regions.append((row_idx, row_idx, span_start, col_idx - 1))
                        new_df.iloc[row_idx, span_start:col_idx] = current_value

                    current_value = cell_value
                    span_start = None

                elif current_value and span_start is None:
                    # Start of potential merged span
                    span_start = col_idx

            # Handle span at end of row
            if span_start is not None and current_value:
                merged_regions.append((row_idx, row_idx, span_start, len(row_data) - 1))
                new_df.iloc[row_idx, span_start:] = current_value

        return new_df, merged_regions

    def _normalize_table_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize table data types and clean content.

        Args:
            df: Input DataFrame

        Returns:
            Normalized DataFrame
        """
        new_df = df.copy()

        for col_idx in range(len(new_df.columns)):
            column = new_df.iloc[:, col_idx]

            # Clean whitespace
            new_df.iloc[:, col_idx] = column.astype(str).str.strip()

            # Convert obvious numeric columns
            if self._column_looks_numeric(column):
                new_df.iloc[:, col_idx] = self._convert_to_numeric(column)

        return new_df

    def _column_looks_numeric(self, column: pd.Series) -> bool:
        """Check if a column appears to contain numeric data."""
        # Sample non-null values
        non_null = column.dropna()
        if len(non_null) == 0:
            return False

        sample_size = min(10, len(non_null))
        sample = non_null.head(sample_size)

        numeric_count = sum(1 for val in sample if self._is_numeric_or_price(str(val)))
        return numeric_count / sample_size > 0.7

    def _convert_to_numeric(self, column: pd.Series) -> pd.Series:
        """Convert a column to numeric, handling currency and formatting."""

        def clean_numeric(text):
            if pd.isna(text):
                return np.nan

            text = str(text).strip()
            if not text or text.lower() in ["nan", "none", ""]:
                return np.nan

            # Remove currency symbols and formatting
            cleaned = re.sub(r"[$,]", "", text)
            try:
                return float(cleaned)
            except ValueError:
                return text  # Keep as text if can't convert

        return column.apply(clean_numeric)

    def _analyze_structure(
        self, df: pd.DataFrame, merged_cells: List, header_info: Dict
    ) -> TableStructure:
        """
        Analyze table structure and create metadata.

        Args:
            df: Processed DataFrame
            merged_cells: List of merged cell regions
            header_info: Header processing information

        Returns:
            TableStructure with metadata
        """
        # Calculate fingerprint for cross-page matching
        fingerprint = self._calculate_fingerprint(df)

        # Estimate data rows (exclude obvious header/footer rows)
        data_rows = len(df)
        if data_rows > 2:
            # Remove potential footer rows (totals, etc.)
            last_row_text = " ".join(str(cell) for cell in df.iloc[-1]).lower()
            if any(word in last_row_text for word in ["total", "subtotal", "sum"]):
                data_rows -= 1

        structure = TableStructure(
            has_multi_row_header=header_info.get("welded", False),
            merged_cells=merged_cells,
            header_rows=header_info.get("rows", 1),
            data_rows=data_rows,
            confidence=0.0,  # Will be calculated separately
            fingerprint=fingerprint,
        )

        return structure

    def _calculate_fingerprint(self, df: pd.DataFrame) -> str:
        """
        Calculate a fingerprint for table structure matching.

        Args:
            df: DataFrame to fingerprint

        Returns:
            String fingerprint for matching
        """
        if df.empty:
            return "empty"

        # Use column names and basic structure
        col_signature = "|".join(str(col).lower()[:10] for col in df.columns)
        shape_signature = f"{len(df.columns)}x{len(df)}"

        # Sample some data patterns
        data_patterns = []
        for col_idx in range(min(3, len(df.columns))):
            col_data = df.iloc[:, col_idx].head(3)
            pattern = "".join(
                "N" if self._is_numeric_or_price(str(val)) else "T" for val in col_data
            )
            data_patterns.append(pattern)

        pattern_signature = ",".join(data_patterns)

        return f"{col_signature}#{shape_signature}#{pattern_signature}"

    def _calculate_confidence(
        self, df: pd.DataFrame, structure: TableStructure, original_shape: Tuple[int, int]
    ) -> float:
        """
        Calculate confidence in table processing results.

        Args:
            df: Processed DataFrame
            structure: Table structure metadata
            original_shape: Original table dimensions

        Returns:
            Confidence score 0.0-1.0
        """
        if df.empty:
            return 0.0

        confidence_factors = []

        # Factor 1: Data completeness
        total_cells = df.shape[0] * df.shape[1]
        if total_cells > 0:
            non_empty_cells = sum(
                1
                for _, row in df.iterrows()
                for cell in row
                if str(cell).strip() and str(cell).lower() not in ["nan", "none"]
            )
            completeness = non_empty_cells / total_cells
            confidence_factors.append(min(completeness * 2, 1.0))  # Weight completeness

        # Factor 2: Structure consistency
        if len(df.columns) >= 2 and len(df) >= 2:
            # Check if columns have consistent data types
            type_consistency = 0
            for col_idx in range(len(df.columns)):
                col_data = df.iloc[:, col_idx].dropna()
                if len(col_data) > 1:
                    # Check if most values in column are same type
                    numeric_ratio = sum(
                        1 for val in col_data if self._is_numeric_or_price(str(val))
                    ) / len(col_data)
                    consistency = max(
                        numeric_ratio, 1 - numeric_ratio
                    )  # Either mostly numeric or mostly text
                    type_consistency += consistency

            if len(df.columns) > 0:
                type_consistency /= len(df.columns)
                confidence_factors.append(type_consistency)

        # Factor 3: Size reasonableness
        if original_shape[0] > 0 and original_shape[1] > 0:
            # Penalize excessive changes in dimensions
            row_change = abs(df.shape[0] - original_shape[0]) / original_shape[0]
            col_change = abs(df.shape[1] - original_shape[1]) / original_shape[1]
            size_factor = max(0, 1.0 - (row_change + col_change))
            confidence_factors.append(size_factor)

        # Factor 4: Header quality
        if structure.has_multi_row_header or len(df.columns) > 0:
            header_quality = 0
            for col_name in df.columns:
                col_name_str = str(col_name).strip()
                if col_name_str and col_name_str not in ["0", "1", "2", "col_0", "col_1"]:
                    header_quality += 1
            header_quality = header_quality / len(df.columns) if len(df.columns) > 0 else 0
            confidence_factors.append(header_quality)

        # Combine factors
        if confidence_factors:
            base_confidence = sum(confidence_factors) / len(confidence_factors)

            # Bonus for successful processing
            if structure.has_multi_row_header:
                base_confidence += 0.1
            if structure.merged_cells:
                base_confidence += 0.05

            return min(base_confidence, 1.0)
        else:
            return 0.1  # Minimal confidence if no factors available

    def stitch_cross_page_tables(self, tables: List[ProcessedTable]) -> List[ProcessedTable]:
        """
        Stitch tables that continue across pages.

        Args:
            tables: List of processed tables from different pages

        Returns:
            List of tables with cross-page tables stitched together
        """
        if len(tables) <= 1:
            return tables

        stitched_tables = []
        i = 0

        while i < len(tables):
            current_table = tables[i]

            # Look for continuation on next pages
            continuation_tables = [current_table]
            j = i + 1

            while j < len(tables):
                next_table = tables[j]

                # Check if tables can be stitched
                if self._can_stitch_tables(current_table, next_table):
                    continuation_tables.append(next_table)
                    j += 1
                else:
                    break

            # Stitch if we found continuations
            if len(continuation_tables) > 1:
                stitched_table = self._stitch_tables(continuation_tables)
                stitched_tables.append(stitched_table)
                i = j  # Skip the tables we just stitched
            else:
                stitched_tables.append(current_table)
                i += 1

        return stitched_tables

    def _can_stitch_tables(self, table1: ProcessedTable, table2: ProcessedTable) -> bool:
        """
        Check if two tables can be stitched together.

        Args:
            table1: First table
            table2: Second table

        Returns:
            True if tables can be stitched
        """
        # Check fingerprint similarity
        if table1.structure.fingerprint == table2.structure.fingerprint:
            return True

        # Check column compatibility
        if (
            len(table1.dataframe.columns) == len(table2.dataframe.columns)
            and table1.dataframe.columns.tolist() == table2.dataframe.columns.tolist()
        ):
            return True

        # Check structure similarity (flexible matching)
        if (
            abs(len(table1.dataframe.columns) - len(table2.dataframe.columns)) <= 1
            and table1.structure.has_multi_row_header == table2.structure.has_multi_row_header
        ):

            # Check if column patterns are similar
            pattern1 = self._get_column_patterns(table1.dataframe)
            pattern2 = self._get_column_patterns(table2.dataframe)

            # Allow some flexibility in pattern matching
            if len(pattern1) == len(pattern2):
                matches = sum(1 for p1, p2 in zip(pattern1, pattern2) if p1 == p2)
                similarity = matches / len(pattern1)
                return similarity >= 0.7

        return False

    def _get_column_patterns(self, df: pd.DataFrame) -> List[str]:
        """Get data type patterns for columns."""
        patterns = []
        for col_idx in range(len(df.columns)):
            col_data = df.iloc[:, col_idx].head(3)  # Sample first few rows
            if self._column_looks_numeric(col_data):
                patterns.append("N")
            else:
                patterns.append("T")
        return patterns

    def _stitch_tables(self, tables: List[ProcessedTable]) -> ProcessedTable:
        """
        Stitch multiple tables into one.

        Args:
            tables: List of tables to stitch

        Returns:
            Single stitched table
        """
        if len(tables) == 1:
            return tables[0]

        # Combine DataFrames
        dataframes = [table.dataframe for table in tables]

        # Align columns (take from first table, pad others if needed)
        target_columns = dataframes[0].columns
        aligned_dfs = []

        for df in dataframes:
            if len(df.columns) == len(target_columns):
                df.columns = target_columns  # Ensure same column names
                aligned_dfs.append(df)
            elif len(df.columns) < len(target_columns):
                # Pad with empty columns
                for i in range(len(target_columns) - len(df.columns)):
                    df[f"pad_col_{i}"] = ""
                df.columns = target_columns
                aligned_dfs.append(df)
            else:
                # Truncate extra columns
                df_truncated = df.iloc[:, : len(target_columns)]
                df_truncated.columns = target_columns
                aligned_dfs.append(df_truncated)

        # Concatenate
        combined_df = pd.concat(aligned_dfs, ignore_index=True)

        # Merge processing notes
        all_notes = []
        for table in tables:
            all_notes.extend(table.processing_notes)
        all_notes.append(f"Stitched {len(tables)} cross-page tables")

        # Combine structure info
        merged_cells = []
        row_offset = 0
        for table in tables:
            # Adjust merged cell coordinates for combined table
            for start_row, end_row, start_col, end_col in table.structure.merged_cells:
                merged_cells.append(
                    (start_row + row_offset, end_row + row_offset, start_col, end_col)
                )
            row_offset += len(table.dataframe)

        combined_structure = TableStructure(
            has_multi_row_header=tables[0].structure.has_multi_row_header,
            merged_cells=merged_cells,
            header_rows=tables[0].structure.header_rows,
            data_rows=sum(table.structure.data_rows for table in tables),
            confidence=sum(table.structure.confidence for table in tables) / len(tables),
            fingerprint=tables[0].structure.fingerprint,
        )

        # Calculate combined confidence
        combined_confidence = sum(table.confidence for table in tables) / len(tables)

        return ProcessedTable(
            dataframe=combined_df,
            structure=combined_structure,
            original_shape=(
                sum(table.original_shape[0] for table in tables),
                tables[0].original_shape[1],
            ),
            processing_notes=all_notes,
            confidence=combined_confidence,
        )
