"""
Confidence scoring utilities for parser results.

Provides comprehensive confidence scoring for:
- Individual field values (prices, SKUs, dates)
- Table extraction quality
- Overall extraction results
"""

import re
import logging
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

import pandas as pd

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Confidence levels for parsed data."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


@dataclass
class ConfidenceScore:
    """Container for confidence scoring data."""
    score: float
    level: ConfidenceLevel = field(default=ConfidenceLevel.LOW)
    reasons: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Set confidence level based on score."""
        if self.score >= 0.90:
            self.level = ConfidenceLevel.HIGH
        elif self.score >= 0.70:
            self.level = ConfidenceLevel.MEDIUM
        elif self.score >= 0.50:
            self.level = ConfidenceLevel.LOW
        else:
            self.level = ConfidenceLevel.VERY_LOW


class ConfidenceScorer:
    """
    Calculate confidence scores for parsed PDF data.
    
    Provides scoring for:
    - Extraction method quality
    - Individual field values
    - Table structure quality
    - Overall extraction results
    """

    def __init__(self):
        """Initialize the confidence scorer."""
        self.price_pattern = re.compile(r"^\$?\d{1,3}(?:,?\d{3})*(?:\.\d{2})?$")
        self.sku_pattern = re.compile(r"^[A-Z0-9][A-Z0-9\-]{1,19}$")
        self.date_pattern = re.compile(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}")
        self.logger = logging.getLogger(f"{__class__.__name__}")

    def score_extraction_method(
        self,
        method: str,
        table_quality: Optional[float] = None
    ) -> float:
        """
        Score based on extraction method used.
        
        Args:
            method: Name of extraction method
            table_quality: Optional quality score from extractor
            
        Returns:
            Confidence score 0.0-1.0
        """
        method_scores = {
            "pymupdf": 0.95,
            "pymupdf_native": 0.95,
            "pdfplumber": 0.90,
            "pdfplumber_digital": 0.90,
            "camelot_lattice": 0.85,
            "camelot_stream": 0.75,
            "paddleocr": 0.80,
            "ocr_tesseract": 0.60,
            "tesseract": 0.60,
            "fallback_text": 0.40,
        }

        method_lower = method.lower().replace("-", "_")
        base_score = method_scores.get(method_lower, 0.50)

        if table_quality is not None:
            base_score = (base_score * 0.7) + (table_quality * 0.3)

        return min(1.0, base_score)

    def score_price_value(
        self,
        price_str: str,
        context: Dict[str, Any] = None
    ) -> ConfidenceScore:
        """
        Score confidence of a parsed price value.
        
        Args:
            price_str: Price string to score
            context: Optional context with similar prices for comparison
            
        Returns:
            ConfidenceScore with detailed breakdown
        """
        reasons = []
        score = 0.0
        metadata = {"original_value": price_str}

        if not price_str or pd.isna(price_str):
            return ConfidenceScore(
                0.0, ConfidenceLevel.VERY_LOW, ["No price value found"]
            )

        price_clean = str(price_str).strip()

        normalized = price_clean.replace("$", "").replace(",", "")
        if self.price_pattern.match(price_clean) or re.match(r"^\d+\.?\d*$", normalized):
            score += 0.4
            reasons.append("Valid price format")
        else:
            score += 0.1
            reasons.append("Non-standard price format")

        try:
            price_val = float(normalized)
            metadata["parsed_value"] = price_val
            
            if 0.01 <= price_val <= 100000:
                score += 0.3
                reasons.append("Price in reasonable range")
            elif price_val > 100000:
                score += 0.1
                reasons.append("High price value - verify")
                metadata["flag"] = "high_price"
            elif price_val <= 0:
                score -= 0.2
                reasons.append("Invalid price value (zero or negative)")
            else:
                score += 0.2
                reasons.append("Price value very low")
        except ValueError:
            score -= 0.3
            reasons.append("Cannot parse price as number")

        if context and "similar_prices" in context:
            similar = context["similar_prices"]
            if similar and len(similar) > 0:
                try:
                    current_price = float(normalized)
                    avg_similar = sum(similar) / len(similar)
                    
                    if avg_similar > 0:
                        ratio = current_price / avg_similar
                        if 0.1 <= ratio <= 10:
                            score += 0.2
                            reasons.append("Consistent with similar prices")
                        else:
                            score -= 0.1
                            reasons.append("Inconsistent with similar prices")
                            metadata["similar_avg"] = avg_similar
                except (ValueError, ZeroDivisionError):
                    pass

        return ConfidenceScore(
            max(0.0, min(1.0, score)),
            ConfidenceLevel.LOW,
            reasons,
            metadata
        )

    def score_sku_value(
        self,
        sku_str: str,
        manufacturer: str = None
    ) -> ConfidenceScore:
        """
        Score confidence of a parsed SKU value.
        
        Args:
            sku_str: SKU string to score
            manufacturer: Optional manufacturer for pattern matching
            
        Returns:
            ConfidenceScore with detailed breakdown
        """
        reasons = []
        score = 0.0
        metadata = {"original_value": sku_str}

        if not sku_str or pd.isna(sku_str):
            return ConfidenceScore(
                0.0, ConfidenceLevel.VERY_LOW, ["No SKU value found"]
            )

        sku_clean = str(sku_str).strip().upper()
        metadata["cleaned_value"] = sku_clean

        if self.sku_pattern.match(sku_clean):
            score += 0.5
            reasons.append("Valid SKU format")
        elif re.match(r"^[A-Z0-9\-\s]{2,25}$", sku_clean):
            score += 0.3
            reasons.append("Acceptable SKU format")
        else:
            score += 0.1
            reasons.append("Non-standard SKU format")

        if 3 <= len(sku_clean) <= 20:
            score += 0.2
            reasons.append("Appropriate SKU length")
        elif len(sku_clean) > 20:
            score += 0.1
            reasons.append("SKU unusually long")
        else:
            score -= 0.1
            reasons.append("SKU too short")

        if manufacturer:
            manufacturer_lower = manufacturer.lower()
            
            if "hager" in manufacturer_lower:
                if re.match(r"^[A-Z]{2,4}[0-9]{2,6}", sku_clean):
                    score += 0.2
                    reasons.append("Matches Hager SKU pattern")
            elif "select" in manufacturer_lower:
                if re.match(r"^SL[0-9]{2}", sku_clean) or re.match(r"^[A-Z]{2,3}[0-9\-]+", sku_clean):
                    score += 0.2
                    reasons.append("Matches SELECT SKU pattern")
            elif "abh" in manufacturer_lower:
                if re.match(r"^[A-Z]?[0-9]{3,6}", sku_clean):
                    score += 0.2
                    reasons.append("Matches ABH SKU pattern")

        return ConfidenceScore(
            max(0.0, min(1.0, score)),
            ConfidenceLevel.LOW,
            reasons,
            metadata
        )

    def score_effective_date(
        self,
        date_str: str,
        context: Dict[str, Any] = None
    ) -> ConfidenceScore:
        """
        Score confidence of parsed effective date.
        
        Args:
            date_str: Date string to score
            context: Optional context information
            
        Returns:
            ConfidenceScore with detailed breakdown
        """
        reasons = []
        score = 0.0
        metadata = {"original_value": date_str}

        if not date_str or pd.isna(date_str):
            return ConfidenceScore(
                0.0, ConfidenceLevel.VERY_LOW, ["No date value found"]
            )

        date_clean = str(date_str).strip()

        date_patterns = [
            (self.date_pattern, "Standard date format"),
            (re.compile(
                r"(?:january|february|march|april|may|june|july|august|"
                r"september|october|november|december)\s+\d{1,2},?\s+\d{4}",
                re.IGNORECASE
            ), "Month name format"),
            (re.compile(r"\d{4}[/-]\d{1,2}[/-]\d{1,2}"), "ISO date format"),
        ]

        format_found = False
        for pattern, description in date_patterns:
            if pattern.search(date_clean):
                score += 0.5
                reasons.append(f"Valid format: {description}")
                format_found = True
                break

        if not format_found:
            score += 0.1
            reasons.append("Non-standard date format")

        if "effective" in date_clean.lower():
            score += 0.3
            reasons.append("Explicit 'effective' context")

        year_match = re.search(r"\b(20\d{2})\b", date_clean)
        if year_match:
            year = int(year_match.group(1))
            current_year = 2025
            
            if current_year - 2 <= year <= current_year + 2:
                score += 0.2
                reasons.append("Recent year")
            elif 2020 <= year <= 2030:
                score += 0.1
                reasons.append("Reasonable year range")
            else:
                score -= 0.1
                reasons.append("Year outside expected range")

        return ConfidenceScore(
            max(0.0, min(1.0, score)),
            ConfidenceLevel.LOW,
            reasons,
            metadata
        )

    def score_table_extraction(
        self,
        df: pd.DataFrame,
        expected_columns: List[str] = None
    ) -> ConfidenceScore:
        """
        Score confidence of extracted table.
        
        Args:
            df: Extracted DataFrame
            expected_columns: Optional list of expected column names
            
        Returns:
            ConfidenceScore with detailed breakdown
        """
        reasons = []
        score = 0.0
        metadata = {
            "rows": len(df) if not df.empty else 0,
            "columns": len(df.columns) if not df.empty else 0,
        }

        if df.empty:
            return ConfidenceScore(
                0.0, ConfidenceLevel.VERY_LOW, ["Empty table"]
            )

        total_cells = len(df) * len(df.columns)
        empty_cells = df.isnull().sum().sum() + (df == "").sum().sum()
        completeness = (total_cells - empty_cells) / total_cells if total_cells > 0 else 0
        
        metadata["completeness"] = completeness
        metadata["empty_cells"] = int(empty_cells)

        score += completeness * 0.4
        reasons.append(f"Table {completeness:.1%} complete")

        if expected_columns:
            found_columns = 0
            columns_lower = [str(col).lower() for col in df.columns]
            
            for expected in expected_columns:
                expected_lower = expected.lower()
                if any(expected_lower in col for col in columns_lower):
                    found_columns += 1

            column_score = found_columns / len(expected_columns)
            score += column_score * 0.3
            reasons.append(f"Found {found_columns}/{len(expected_columns)} expected columns")
            metadata["column_match_rate"] = column_score

        numeric_columns = df.select_dtypes(include=["number"]).columns
        if len(numeric_columns) > 0:
            score += 0.15
            reasons.append("Contains numeric data")

        if 1 <= len(df) <= 10000:
            score += 0.15
            reasons.append("Reasonable row count")
        elif len(df) > 10000:
            score += 0.05
            reasons.append("Large table - verify completeness")

        return ConfidenceScore(
            max(0.0, min(1.0, score)),
            ConfidenceLevel.LOW,
            reasons,
            metadata
        )

    def score_overall_extraction(
        self,
        extraction_results: Dict[str, Any],
        method_used: str,
        table_quality: Optional[float] = None
    ) -> ConfidenceScore:
        """
        Calculate overall confidence for an extraction result.
        
        Args:
            extraction_results: Dictionary with extracted data
            method_used: Extraction method name
            table_quality: Optional quality score from extractor
            
        Returns:
            ConfidenceScore with overall assessment
        """
        method_score = self.score_extraction_method(method_used, table_quality)
        
        component_scores = []
        reasons = [f"Extraction method: {method_used} (score: {method_score:.2f})"]

        if "effective_date" in extraction_results and extraction_results["effective_date"]:
            date_score = self.score_effective_date(extraction_results["effective_date"])
            component_scores.append(("date", date_score.score, 0.15))
            reasons.append(f"Date confidence: {date_score.level.value}")

        if "products" in extraction_results:
            products = extraction_results["products"]
            if products and len(products) > 0:
                sample_size = min(10, len(products))
                sample_products = products[:sample_size]
                
                price_scores = []
                sku_scores = []

                for product in sample_products:
                    if isinstance(product, dict):
                        if "base_price" in product and product["base_price"]:
                            ps = self.score_price_value(str(product["base_price"]))
                            price_scores.append(ps.score)

                        if "sku" in product and product["sku"]:
                            ss = self.score_sku_value(str(product["sku"]))
                            sku_scores.append(ss.score)

                if price_scores:
                    avg_price = sum(price_scores) / len(price_scores)
                    component_scores.append(("prices", avg_price, 0.35))
                    reasons.append(f"Price quality: {avg_price:.2f}")

                if sku_scores:
                    avg_sku = sum(sku_scores) / len(sku_scores)
                    component_scores.append(("skus", avg_sku, 0.25))
                    reasons.append(f"SKU quality: {avg_sku:.2f}")

        if component_scores:
            total_weight = sum(weight for _, _, weight in component_scores)
            data_score = sum(score * weight for _, score, weight in component_scores)
            
            if total_weight > 0:
                data_score = data_score / total_weight * 0.6
            
            final_score = (method_score * 0.4) + data_score
        else:
            final_score = method_score

        metadata = {
            "method_score": method_score,
            "component_scores": {name: score for name, score, _ in component_scores},
            "extraction_method": method_used,
        }

        return ConfidenceScore(
            max(0.0, min(1.0, final_score)),
            ConfidenceLevel.LOW,
            reasons,
            metadata
        )


confidence_scorer = ConfidenceScorer()


def score_extraction(
    results: Dict[str, Any],
    method: str,
    quality: float = None
) -> ConfidenceScore:
    """
    Convenience function to score extraction results.
    
    Args:
        results: Extraction results dictionary
        method: Extraction method used
        quality: Optional quality score
        
    Returns:
        ConfidenceScore for the extraction
    """
    return confidence_scorer.score_overall_extraction(results, method, quality)
