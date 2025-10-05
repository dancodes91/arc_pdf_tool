"""
Confidence scoring utilities for parser results.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import re
import pandas as pd


class ConfidenceLevel(Enum):
    """Confidence levels for parsed data."""

    HIGH = "high"  # 90-100% confidence
    MEDIUM = "medium"  # 70-89% confidence
    LOW = "low"  # 50-69% confidence
    VERY_LOW = "very_low"  # <50% confidence


@dataclass
class ConfidenceScore:
    """Container for confidence scoring data."""

    score: float  # 0.0 to 1.0
    level: ConfidenceLevel
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
    """Calculate confidence scores for parsed PDF data."""

    def __init__(self):
        self.price_pattern = re.compile(r"^\$?\d+\.?\d*$")
        self.sku_pattern = re.compile(r"^[A-Z0-9-]{2,20}$")
        self.date_pattern = re.compile(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}")

    def score_extraction_method(self, method: str, table_quality: Optional[float] = None) -> float:
        """Score based on extraction method used."""
        method_scores = {
            "pdfplumber_digital": 0.95,
            "camelot_lattice": 0.90,
            "camelot_stream": 0.75,
            "ocr_tesseract": 0.50,
            "fallback_text": 0.30,
        }

        base_score = method_scores.get(method, 0.30)

        # Adjust based on table quality if available
        if table_quality is not None:
            base_score = (base_score * 0.7) + (table_quality * 0.3)

        return min(1.0, base_score)

    def score_price_value(self, price_str: str, context: Dict[str, Any] = None) -> ConfidenceScore:
        """Score confidence of a parsed price value."""
        reasons = []
        score = 0.0
        metadata = {"original_value": price_str}

        if not price_str or pd.isna(price_str):
            return ConfidenceScore(0.0, ConfidenceLevel.VERY_LOW, ["No price value found"])

        price_clean = str(price_str).strip()

        # Check format
        if self.price_pattern.match(price_clean.replace("$", "").replace(",", "")):
            score += 0.4
            reasons.append("Valid price format")
        else:
            score -= 0.2
            reasons.append("Invalid price format")

        # Check reasonable price range
        try:
            price_val = float(price_clean.replace("$", "").replace(",", ""))
            if 0.01 <= price_val <= 50000:  # Reasonable hardware price range
                score += 0.3
                reasons.append("Price in reasonable range")
            elif price_val > 50000:
                score += 0.1
                reasons.append("High price value - verify")
                metadata["flag"] = "high_price"
            else:
                score -= 0.3
                reasons.append("Price value too low")
        except ValueError:
            score -= 0.4
            reasons.append("Cannot parse price as number")

        # Context-based scoring
        if context:
            # Check if price is consistent with similar items
            if "similar_prices" in context:
                similar = context["similar_prices"]
                if similar and len(similar) > 0:
                    avg_similar = sum(similar) / len(similar)
                    try:
                        current_price = float(price_clean.replace("$", "").replace(",", ""))
                        ratio = min(current_price, avg_similar) / max(current_price, avg_similar)
                        if ratio > 0.5:  # Within 2x of similar prices
                            score += 0.2
                            reasons.append("Consistent with similar prices")
                        else:
                            score -= 0.1
                            reasons.append("Inconsistent with similar prices")
                            metadata["similar_avg"] = avg_similar
                    except ValueError:
                        pass

        return ConfidenceScore(max(0.0, min(1.0, score)), ConfidenceLevel.LOW, reasons, metadata)

    def score_sku_value(self, sku_str: str, manufacturer: str = None) -> ConfidenceScore:
        """Score confidence of a parsed SKU value."""
        reasons = []
        score = 0.0
        metadata = {"original_value": sku_str}

        if not sku_str or pd.isna(sku_str):
            return ConfidenceScore(0.0, ConfidenceLevel.VERY_LOW, ["No SKU value found"])

        sku_clean = str(sku_str).strip().upper()

        # Check basic format
        if self.sku_pattern.match(sku_clean):
            score += 0.5
            reasons.append("Valid SKU format")
        else:
            score -= 0.3
            reasons.append("Invalid SKU format")

        # Check length
        if 3 <= len(sku_clean) <= 15:
            score += 0.2
            reasons.append("Appropriate SKU length")
        elif len(sku_clean) > 15:
            score -= 0.1
            reasons.append("SKU unusually long")
        else:
            score -= 0.2
            reasons.append("SKU too short")

        # Manufacturer-specific patterns
        if manufacturer:
            manufacturer = manufacturer.lower()
            if manufacturer == "hager":
                # Hager SKUs often start with letters followed by numbers
                if re.match(r"^[A-Z]{2,4}[0-9]{2,6}", sku_clean):
                    score += 0.2
                    reasons.append("Matches Hager SKU pattern")
            elif manufacturer == "select_hinges":
                # SELECT often has model codes like SL11, SL24, etc.
                if re.match(r"^SL[0-9]{2}", sku_clean) or re.match(
                    r"^[A-Z]{2,3}[0-9-]+", sku_clean
                ):
                    score += 0.2
                    reasons.append("Matches SELECT SKU pattern")

        return ConfidenceScore(max(0.0, min(1.0, score)), ConfidenceLevel.LOW, reasons, metadata)

    def score_effective_date(
        self, date_str: str, context: Dict[str, Any] = None
    ) -> ConfidenceScore:
        """Score confidence of parsed effective date."""
        reasons = []
        score = 0.0
        metadata = {"original_value": date_str}

        if not date_str or pd.isna(date_str):
            return ConfidenceScore(0.0, ConfidenceLevel.VERY_LOW, ["No date value found"])

        date_clean = str(date_str).strip()

        # Check date format - look for month names too
        date_patterns = [
            self.date_pattern,
            re.compile(
                r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}",
                re.IGNORECASE,
            ),
        ]

        format_found = False
        for pattern in date_patterns:
            if pattern.search(date_clean):
                score += 0.6
                reasons.append("Valid date format found")
                format_found = True
                break

        if not format_found:
            score -= 0.4
            reasons.append("Invalid date format")

        # Check for explicit "effective" context
        if "effective" in date_clean.lower():
            score += 0.3
            reasons.append("Explicit 'effective' context")

        # Check year reasonableness (should be recent)
        year_match = re.search(r"\b(20\d{2})\b", date_clean)
        if year_match:
            year = int(year_match.group(1))
            if 2020 <= year <= 2030:
                score += 0.2
                reasons.append("Reasonable year range")
            else:
                score -= 0.2
                reasons.append("Year outside expected range")

        return ConfidenceScore(max(0.0, min(1.0, score)), ConfidenceLevel.LOW, reasons, metadata)

    def score_table_extraction(
        self, df: pd.DataFrame, expected_columns: List[str] = None
    ) -> ConfidenceScore:
        """Score confidence of extracted table."""
        reasons = []
        score = 0.0
        metadata = {
            "rows": len(df),
            "columns": len(df.columns),
            "empty_cells": df.isnull().sum().sum(),
        }

        if df.empty:
            return ConfidenceScore(0.0, ConfidenceLevel.VERY_LOW, ["Empty table"])

        # Score based on table completeness
        total_cells = len(df) * len(df.columns)
        empty_cells = df.isnull().sum().sum()
        completeness = (total_cells - empty_cells) / total_cells

        score += completeness * 0.4
        reasons.append(f"Table {completeness:.1%} complete")

        # Score based on expected columns
        if expected_columns:
            found_columns = 0
            for expected in expected_columns:
                if any(expected.lower() in str(col).lower() for col in df.columns):
                    found_columns += 1

            column_score = found_columns / len(expected_columns)
            score += column_score * 0.4
            reasons.append(f"Found {found_columns}/{len(expected_columns)} expected columns")
            metadata["column_match_rate"] = column_score

        # Score based on data consistency
        numeric_columns = df.select_dtypes(include=["number"]).columns
        if len(numeric_columns) > 0:
            score += 0.2
            reasons.append("Contains numeric data")

        return ConfidenceScore(max(0.0, min(1.0, score)), ConfidenceLevel.LOW, reasons, metadata)

    def score_overall_extraction(
        self,
        extraction_results: Dict[str, Any],
        method_used: str,
        table_quality: Optional[float] = None,
    ) -> ConfidenceScore:
        """Calculate overall confidence for an extraction result."""
        method_score = self.score_extraction_method(method_used, table_quality)

        # Component scores
        component_scores = []
        reasons = [f"Extraction method: {method_used} (score: {method_score:.2f})"]

        # Score key components if present
        if "effective_date" in extraction_results:
            date_score = self.score_effective_date(extraction_results["effective_date"])
            if hasattr(date_score, "score"):
                component_scores.append(date_score.score * 0.2)
            else:
                component_scores.append(float(date_score) * 0.2)
            reasons.extend([f"Date: {date_score.level.value}" for r in date_score.reasons[:2]])

        if "products" in extraction_results:
            products = extraction_results["products"]
            if products and len(products) > 0:
                # Sample a few products for scoring
                sample_products = products[:5] if len(products) > 5 else products
                product_scores = []

                for product in sample_products:
                    if isinstance(product, dict):
                        if "base_price" in product:
                            price_score = self.score_price_value(str(product["base_price"]))
                            if hasattr(price_score, "score"):
                                product_scores.append(price_score.score)
                            else:
                                product_scores.append(float(price_score))

                        if "sku" in product:
                            sku_score = self.score_sku_value(str(product["sku"]))
                            if hasattr(sku_score, "score"):
                                product_scores.append(sku_score.score)
                            else:
                                product_scores.append(float(sku_score))

                if product_scores:
                    avg_product_score = sum(product_scores) / len(product_scores)
                    component_scores.append(avg_product_score * 0.6)
                    reasons.append(f"Product data quality: {avg_product_score:.2f}")

        # Calculate final score
        if component_scores:
            data_score = sum(component_scores)
            final_score = (method_score * 0.4) + (data_score * 0.6)
        else:
            final_score = method_score

        metadata = {
            "method_score": method_score,
            "component_scores": component_scores,
            "extraction_method": method_used,
        }

        return ConfidenceScore(
            max(0.0, min(1.0, final_score)), ConfidenceLevel.LOW, reasons, metadata
        )


# Global confidence scorer instance
confidence_scorer = ConfidenceScorer()
