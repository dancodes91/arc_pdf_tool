"""
Provenance tracking for parsed data - track where each piece of data came from.
"""
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from datetime import datetime
import json


logger = logging.getLogger(__name__)


@dataclass
class ProvenanceInfo:
    """Track the origin of parsed data."""
    source_file: str
    page_number: int
    extraction_method: str
    bbox: Optional[Dict[str, float]] = None  # Bounding box coordinates
    section: Optional[str] = None  # Section/header context
    table_index: Optional[int] = None  # Which table on the page
    row_index: Optional[int] = None  # Which row in the table
    column_index: Optional[int] = None  # Which column in the table
    raw_text: Optional[str] = None  # Original raw text
    context_text: Optional[str] = None  # Surrounding text context
    confidence: Optional[float] = None  # Extraction confidence
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'source_file': self.source_file,
            'page_number': self.page_number,
            'extraction_method': self.extraction_method,
            'bbox': self.bbox,
            'section': self.section,
            'table_index': self.table_index,
            'row_index': self.row_index,
            'column_index': self.column_index,
            'raw_text': self.raw_text,
            'context_text': self.context_text,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProvenanceInfo':
        """Create from dictionary."""
        data = data.copy()
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class ParsedItem:
    """Container for a parsed data item with full provenance."""
    value: Any
    data_type: str  # 'price', 'sku', 'description', 'date', etc.
    normalized_value: Optional[Any] = None
    provenance: Optional[ProvenanceInfo] = None
    validation_errors: List[str] = field(default_factory=list)
    confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'value': self.value,
            'data_type': self.data_type,
            'normalized_value': self.normalized_value,
            'provenance': self.provenance.to_dict() if self.provenance else None,
            'validation_errors': self.validation_errors,
            'confidence': self.confidence
        }


class ProvenanceTracker:
    """Track provenance for parsed data throughout the extraction pipeline."""

    def __init__(self, source_file: str):
        self.source_file = source_file
        self.current_page = 1
        self.current_method = "unknown"
        self.current_section = None
        self.current_table_index = None
        self.context_stack: List[str] = []

    def set_context(self, page_number: int = None, method: str = None,
                   section: str = None, table_index: int = None):
        """Set current extraction context."""
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

    def pop_context(self):
        """Pop context from stack."""
        if self.context_stack:
            return self.context_stack.pop()
        return None

    def create_provenance(self,
                         raw_text: str = None,
                         bbox: Dict[str, float] = None,
                         row_index: int = None,
                         column_index: int = None,
                         confidence: float = None,
                         **metadata) -> ProvenanceInfo:
        """Create provenance info with current context."""

        # Get context text from stack
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
            metadata=metadata
        )

    def create_parsed_item(self,
                          value: Any,
                          data_type: str,
                          raw_text: str = None,
                          bbox: Dict[str, float] = None,
                          row_index: int = None,
                          column_index: int = None,
                          confidence: float = None,
                          **metadata) -> ParsedItem:
        """Create a parsed item with provenance."""

        provenance = self.create_provenance(
            raw_text=raw_text,
            bbox=bbox,
            row_index=row_index,
            column_index=column_index,
            confidence=confidence,
            **metadata
        )

        return ParsedItem(
            value=value,
            data_type=data_type,
            provenance=provenance,
            confidence=confidence
        )


class ProvenanceAnalyzer:
    """Analyze provenance data for quality assessment."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__class__.__name__}")

    def analyze_extraction_quality(self, parsed_items: List[ParsedItem]) -> Dict[str, Any]:
        """Analyze overall extraction quality based on provenance."""
        if not parsed_items:
            return {
                'total_items': 0,
                'quality_score': 0.0,
                'method_breakdown': {},
                'page_breakdown': {},
                'confidence_distribution': {},
                'issues': ['No items to analyze']
            }

        # Method breakdown
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

                # Check for potential issues
                if item.validation_errors:
                    issues.extend(item.validation_errors)

                if item.confidence and item.confidence < 0.5:
                    issues.append(f"Low confidence item: {item.value} (page {page})")

        # Calculate quality metrics
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        # Quality score based on method distribution (prefer digital methods)
        method_quality_weights = {
            'pymupdf_digital': 1.0,
            'pdfplumber_digital': 0.95,
            'camelot_lattice': 0.85,
            'camelot_stream': 0.75,
            'ocr_tesseract': 0.5,
            'failed': 0.1
        }

        weighted_quality = 0.0
        total_items = len(parsed_items)

        for method, count in method_counts.items():
            weight = method_quality_weights.get(method, 0.3)
            weighted_quality += (count / total_items) * weight

        # Combine weighted quality and confidence
        quality_score = (weighted_quality * 0.6) + (avg_confidence * 0.4)

        # Confidence distribution
        confidence_dist = {}
        for score in confidence_scores:
            if score >= 0.8:
                confidence_dist['high'] = confidence_dist.get('high', 0) + 1
            elif score >= 0.6:
                confidence_dist['medium'] = confidence_dist.get('medium', 0) + 1
            else:
                confidence_dist['low'] = confidence_dist.get('low', 0) + 1

        return {
            'total_items': total_items,
            'quality_score': quality_score,
            'average_confidence': avg_confidence,
            'method_breakdown': method_counts,
            'page_breakdown': page_counts,
            'confidence_distribution': confidence_dist,
            'issues': issues[:10],  # Limit to first 10 issues
            'recommendations': self._generate_recommendations(
                method_counts, avg_confidence, issues
            )
        }

    def _generate_recommendations(self, method_counts: Dict[str, int],
                                avg_confidence: float,
                                issues: List[str]) -> List[str]:
        """Generate recommendations for improving extraction quality."""
        recommendations = []

        # Method-based recommendations
        total_items = sum(method_counts.values())
        ocr_ratio = method_counts.get('ocr_tesseract', 0) / total_items

        if ocr_ratio > 0.5:
            recommendations.append(
                "High OCR usage detected. Consider using higher resolution scans "
                "or digital PDFs for better accuracy."
            )

        if method_counts.get('failed', 0) > 0:
            recommendations.append(
                "Some extractions failed completely. Check PDF file integrity "
                "and ensure all required dependencies are installed."
            )

        # Confidence-based recommendations
        if avg_confidence < 0.6:
            recommendations.append(
                "Low average confidence score. Review extraction results manually "
                "and consider alternative parsing strategies."
            )

        # Issue-based recommendations
        if len(issues) > total_items * 0.2:  # More than 20% of items have issues
            recommendations.append(
                "High number of validation issues detected. Review input data "
                "format and parser configuration."
            )

        return recommendations

    def export_provenance_report(self, parsed_items: List[ParsedItem],
                               output_file: str = None) -> str:
        """Export detailed provenance report."""
        analysis = self.analyze_extraction_quality(parsed_items)

        report_lines = [
            "PROVENANCE ANALYSIS REPORT",
            "=" * 50,
            f"Total Items: {analysis['total_items']}",
            f"Quality Score: {analysis['quality_score']:.2f}",
            f"Average Confidence: {analysis['average_confidence']:.2f}",
            "",
            "EXTRACTION METHOD BREAKDOWN:",
            "-" * 30
        ]

        for method, count in analysis['method_breakdown'].items():
            percentage = (count / analysis['total_items']) * 100
            report_lines.append(f"{method}: {count} ({percentage:.1f}%)")

        report_lines.extend([
            "",
            "PAGE BREAKDOWN:",
            "-" * 15
        ])

        for page, count in sorted(analysis['page_breakdown'].items()):
            report_lines.append(f"Page {page}: {count} items")

        if analysis['issues']:
            report_lines.extend([
                "",
                "ISSUES IDENTIFIED:",
                "-" * 18
            ])
            for issue in analysis['issues'][:10]:
                report_lines.append(f"• {issue}")

        if analysis['recommendations']:
            report_lines.extend([
                "",
                "RECOMMENDATIONS:",
                "-" * 16
            ])
            for rec in analysis['recommendations']:
                report_lines.append(f"• {rec}")

        report_text = "\n".join(report_lines)

        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report_text)
                self.logger.info(f"Provenance report saved to {output_file}")
            except Exception as e:
                self.logger.error(f"Could not save report to {output_file}: {e}")

        return report_text


# Utility functions for common provenance tasks
def create_table_provenance(tracker: ProvenanceTracker,
                          table_index: int,
                          row_index: int,
                          column_index: int,
                          raw_value: str,
                          confidence: float = None) -> ProvenanceInfo:
    """Helper to create provenance for table cell data."""
    return tracker.create_provenance(
        raw_text=raw_value,
        row_index=row_index,
        column_index=column_index,
        confidence=confidence,
        table_index=table_index
    )


def create_text_provenance(tracker: ProvenanceTracker,
                         raw_text: str,
                         bbox: Dict[str, float] = None,
                         confidence: float = None) -> ProvenanceInfo:
    """Helper to create provenance for free text data."""
    return tracker.create_provenance(
        raw_text=raw_text,
        bbox=bbox,
        confidence=confidence
    )