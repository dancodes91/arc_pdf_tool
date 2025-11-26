"""
Provenance tracking for parsed data - track where each piece of data came from.

Provides comprehensive lineage tracking for:
- Source file and page location
- Extraction method used
- Bounding box coordinates
- Confidence scores
- Processing context
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ProvenanceInfo:
    """Track the origin of parsed data."""

    source_file: str
    page_number: int
    extraction_method: str
    bbox: Optional[Dict[str, float]] = None
    section: Optional[str] = None
    table_index: Optional[int] = None
    row_index: Optional[int] = None
    column_index: Optional[int] = None
    raw_text: Optional[str] = None
    context_text: Optional[str] = None
    confidence: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "source_file": self.source_file,
            "page_number": self.page_number,
            "extraction_method": self.extraction_method,
            "bbox": self.bbox,
            "section": self.section,
            "table_index": self.table_index,
            "row_index": self.row_index,
            "column_index": self.column_index,
            "raw_text": self.raw_text,
            "context_text": self.context_text,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProvenanceInfo":
        """Create from dictionary."""
        data = data.copy()
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)
    
    def __str__(self) -> str:
        """Human-readable representation."""
        parts = [f"Page {self.page_number}"]
        if self.table_index is not None:
            parts.append(f"Table {self.table_index}")
        if self.row_index is not None:
            parts.append(f"Row {self.row_index}")
        parts.append(f"via {self.extraction_method}")
        if self.confidence is not None:
            parts.append(f"({self.confidence:.0%} confidence)")
        return " | ".join(parts)


@dataclass
class ParsedItem:
    """Container for a parsed data item with full provenance."""

    value: Any
    data_type: str
    normalized_value: Optional[Any] = None
    provenance: Optional[ProvenanceInfo] = None
    validation_errors: List[str] = field(default_factory=list)
    confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "value": self.value,
            "data_type": self.data_type,
            "normalized_value": self.normalized_value,
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "validation_errors": self.validation_errors,
            "confidence": self.confidence,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParsedItem":
        """Create from dictionary."""
        data = data.copy()
        if data.get("provenance"):
            data["provenance"] = ProvenanceInfo.from_dict(data["provenance"])
        return cls(**data)

    def is_valid(self) -> bool:
        """Check if item passed validation."""
        return len(self.validation_errors) == 0

    def __str__(self) -> str:
        """Human-readable representation."""
        val = self.normalized_value if self.normalized_value is not None else self.value
        conf = f" ({self.confidence:.0%})" if self.confidence else ""
        return f"{self.data_type}: {val}{conf}"


class ProvenanceTracker:
    """Track provenance for parsed data throughout the extraction pipeline."""

    def __init__(self, source_file: str):
        """
        Initialize tracker for a source file.
        
        Args:
            source_file: Path to the source PDF file
        """
        self.source_file = source_file
        self.current_page = 1
        self.current_method = "unknown"
        self.current_section = None
        self.current_table_index = None
        self.context_stack: List[str] = []
        self.items: List[ParsedItem] = []
        self.logger = logging.getLogger(f"{__class__.__name__}")

    def set_context(
        self,
        page_number: int = None,
        method: str = None,
        section: str = None,
        table_index: int = None,
    ):
        """
        Set current extraction context.
        
        Args:
            page_number: Current page number (1-indexed)
            method: Extraction method being used
            section: Current document section
            table_index: Current table index on page
        """
        if page_number is not None:
            self.current_page = page_number
        if method is not None:
            self.current_method = method
        if section is not None:
            self.current_section = section
        if table_index is not None:
            self.current_table_index = table_index

    def push_context(self, context: str):
        """Push context onto stack (for nested sections)."""
        self.context_stack.append(context)

    def pop_context(self) -> Optional[str]:
        """Pop context from stack."""
        if self.context_stack:
            return self.context_stack.pop()
        return None

    def clear_context(self):
        """Clear all context."""
        self.context_stack.clear()
        self.current_section = None
        self.current_table_index = None

    def create_provenance(
        self,
        raw_text: str = None,
        bbox: Dict[str, float] = None,
        row_index: int = None,
        column_index: int = None,
        confidence: float = None,
        **metadata,
    ) -> ProvenanceInfo:
        """
        Create provenance info with current context.
        
        Args:
            raw_text: Original raw text value
            bbox: Bounding box coordinates
            row_index: Row index in table
            column_index: Column index in table
            confidence: Extraction confidence score
            **metadata: Additional metadata
            
        Returns:
            ProvenanceInfo with full context
        """
        context_text = " > ".join(self.context_stack) if self.context_stack else None

        return ProvenanceInfo(
            source_file=self.source_file,
            page_number=self.current_page,
            extraction_method=self.current_method,
            bbox=bbox,
            section=self.current_section,
            table_index=self.current_table_index,
            row_index=row_index,
            column_index=column_index,
            raw_text=raw_text,
            context_text=context_text,
            confidence=confidence,
            metadata=metadata,
        )

    def create_parsed_item(
        self,
        value: Any,
        data_type: str,
        raw_text: str = None,
        bbox: Dict[str, float] = None,
        row_index: int = None,
        column_index: int = None,
        confidence: float = None,
        normalized_value: Any = None,
        **metadata,
    ) -> ParsedItem:
        """
        Create a parsed item with provenance.
        
        Args:
            value: The parsed value
            data_type: Type of data ('price', 'sku', 'description', etc.)
            raw_text: Original raw text
            bbox: Bounding box coordinates
            row_index: Row index in table
            column_index: Column index in table
            confidence: Extraction confidence
            normalized_value: Normalized/cleaned value
            **metadata: Additional metadata
            
        Returns:
            ParsedItem with full provenance
        """
        provenance = self.create_provenance(
            raw_text=raw_text,
            bbox=bbox,
            row_index=row_index,
            column_index=column_index,
            confidence=confidence,
            **metadata,
        )

        item = ParsedItem(
            value=value,
            data_type=data_type,
            normalized_value=normalized_value,
            provenance=provenance,
            confidence=confidence,
        )
        
        self.items.append(item)
        return item

    def get_items_by_type(self, data_type: str) -> List[ParsedItem]:
        """Get all tracked items of a specific type."""
        return [item for item in self.items if item.data_type == data_type]

    def get_items_by_page(self, page_number: int) -> List[ParsedItem]:
        """Get all tracked items from a specific page."""
        return [
            item for item in self.items 
            if item.provenance and item.provenance.page_number == page_number
        ]

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of tracked items."""
        by_type = {}
        by_page = {}
        by_method = {}
        
        for item in self.items:
            by_type[item.data_type] = by_type.get(item.data_type, 0) + 1
            
            if item.provenance:
                page = item.provenance.page_number
                by_page[page] = by_page.get(page, 0) + 1
                
                method = item.provenance.extraction_method
                by_method[method] = by_method.get(method, 0) + 1
        
        return {
            "total_items": len(self.items),
            "by_type": by_type,
            "by_page": by_page,
            "by_method": by_method,
            "source_file": self.source_file,
        }


class ProvenanceAnalyzer:
    """Analyze provenance data for quality assessment."""

    def __init__(self):
        """Initialize the analyzer."""
        self.logger = logging.getLogger(f"{__class__.__name__}")

    def analyze_extraction_quality(
        self,
        parsed_items: List[ParsedItem]
    ) -> Dict[str, Any]:
        """
        Analyze overall extraction quality based on provenance.
        
        Args:
            parsed_items: List of parsed items with provenance
            
        Returns:
            Quality analysis dictionary
        """
        if not parsed_items:
            return {
                "total_items": 0,
                "quality_score": 0.0,
                "method_breakdown": {},
                "page_breakdown": {},
                "confidence_distribution": {},
                "issues": ["No items to analyze"],
            }

        method_counts = {}
        page_counts = {}
        confidence_scores = []
        issues = []

        for item in parsed_items:
            if item.provenance:
                method = item.provenance.extraction_method
                page = item.provenance.page_number

                method_counts[method] = method_counts.get(method, 0) + 1
                page_counts[page] = page_counts.get(page, 0) + 1

                if item.confidence is not None:
                    confidence_scores.append(item.confidence)

                if item.validation_errors:
                    issues.extend(item.validation_errors)

                if item.confidence and item.confidence < 0.5:
                    issues.append(f"Low confidence item: {item.value} (page {page})")

        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores) 
            if confidence_scores else 0.0
        )

        method_quality_weights = {
            "pymupdf": 1.0,
            "pymupdf_native": 1.0,
            "pdfplumber": 0.95,
            "pdfplumber_digital": 0.95,
            "camelot_lattice": 0.85,
            "camelot_stream": 0.75,
            "paddleocr": 0.80,
            "ocr_tesseract": 0.60,
            "tesseract": 0.60,
            "failed": 0.1,
        }

        weighted_quality = 0.0
        total_items = len(parsed_items)

        for method, count in method_counts.items():
            method_lower = method.lower().replace("-", "_")
            weight = method_quality_weights.get(method_lower, 0.5)
            weighted_quality += (count / total_items) * weight

        quality_score = (weighted_quality * 0.6) + (avg_confidence * 0.4)

        confidence_dist = {"high": 0, "medium": 0, "low": 0}
        for score in confidence_scores:
            if score >= 0.8:
                confidence_dist["high"] += 1
            elif score >= 0.6:
                confidence_dist["medium"] += 1
            else:
                confidence_dist["low"] += 1

        return {
            "total_items": total_items,
            "quality_score": quality_score,
            "average_confidence": avg_confidence,
            "method_breakdown": method_counts,
            "page_breakdown": dict(sorted(page_counts.items())),
            "confidence_distribution": confidence_dist,
            "issues": issues[:10],
            "recommendations": self._generate_recommendations(
                method_counts, avg_confidence, issues
            ),
        }

    def _generate_recommendations(
        self,
        method_counts: Dict[str, int],
        avg_confidence: float,
        issues: List[str]
    ) -> List[str]:
        """Generate recommendations for improving extraction quality."""
        recommendations = []
        total_items = sum(method_counts.values()) if method_counts else 0

        if total_items == 0:
            return ["No data extracted - check PDF file and parser configuration"]

        ocr_methods = ["paddleocr", "ocr_tesseract", "tesseract"]
        ocr_count = sum(method_counts.get(m, 0) for m in ocr_methods)
        ocr_ratio = ocr_count / total_items if total_items > 0 else 0

        if ocr_ratio > 0.5:
            recommendations.append(
                "High OCR usage detected. Consider using higher resolution scans "
                "or digital PDFs for better accuracy."
            )

        if method_counts.get("failed", 0) > 0:
            recommendations.append(
                "Some extractions failed. Check PDF file integrity "
                "and ensure all required dependencies are installed."
            )

        if avg_confidence < 0.6:
            recommendations.append(
                "Low average confidence score. Review extraction results manually "
                "and consider alternative parsing strategies."
            )
        elif avg_confidence < 0.8:
            recommendations.append(
                "Moderate confidence scores. Spot-check extracted data for accuracy."
            )

        if len(issues) > total_items * 0.2:
            recommendations.append(
                "High number of validation issues. Review input data "
                "format and parser configuration."
            )

        if not recommendations:
            recommendations.append("Extraction quality looks good!")

        return recommendations

    def export_provenance_report(
        self,
        parsed_items: List[ParsedItem],
        output_file: str = None
    ) -> str:
        """
        Export detailed provenance report.
        
        Args:
            parsed_items: List of parsed items
            output_file: Optional file path to save report
            
        Returns:
            Report text
        """
        analysis = self.analyze_extraction_quality(parsed_items)

        report_lines = [
            "=" * 60,
            "PROVENANCE ANALYSIS REPORT",
            "=" * 60,
            f"Total Items: {analysis['total_items']}",
            f"Quality Score: {analysis['quality_score']:.2%}",
            f"Average Confidence: {analysis['average_confidence']:.2%}",
            "",
            "EXTRACTION METHOD BREAKDOWN",
            "-" * 40,
        ]

        for method, count in analysis["method_breakdown"].items():
            percentage = (count / analysis["total_items"]) * 100 if analysis["total_items"] > 0 else 0
            report_lines.append(f"  {method}: {count} ({percentage:.1f}%)")

        report_lines.extend(["", "PAGE BREAKDOWN", "-" * 40])

        for page, count in analysis["page_breakdown"].items():
            report_lines.append(f"  Page {page}: {count} items")

        report_lines.extend(["", "CONFIDENCE DISTRIBUTION", "-" * 40])
        for level, count in analysis["confidence_distribution"].items():
            report_lines.append(f"  {level.capitalize()}: {count}")

        if analysis["issues"]:
            report_lines.extend(["", "ISSUES IDENTIFIED", "-" * 40])
            for issue in analysis["issues"]:
                report_lines.append(f"  * {issue}")

        if analysis["recommendations"]:
            report_lines.extend(["", "RECOMMENDATIONS", "-" * 40])
            for rec in analysis["recommendations"]:
                report_lines.append(f"  * {rec}")

        report_lines.append("")
        report_lines.append("=" * 60)

        report_text = "\n".join(report_lines)

        if output_file:
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(report_text)
                self.logger.info(f"Provenance report saved to {output_file}")
            except Exception as e:
                self.logger.error(f"Could not save report to {output_file}: {e}")

        return report_text


def create_table_provenance(
    tracker: ProvenanceTracker,
    table_index: int,
    row_index: int,
    column_index: int,
    raw_value: str,
    confidence: float = None,
) -> ProvenanceInfo:
    """Helper to create provenance for table cell data."""
    tracker.current_table_index = table_index
    return tracker.create_provenance(
        raw_text=raw_value,
        row_index=row_index,
        column_index=column_index,
        confidence=confidence,
    )


def create_text_provenance(
    tracker: ProvenanceTracker,
    raw_text: str,
    bbox: Dict[str, float] = None,
    confidence: float = None,
) -> ProvenanceInfo:
    """Helper to create provenance for free text data."""
    return tracker.create_provenance(
        raw_text=raw_text,
        bbox=bbox,
        confidence=confidence,
    )
