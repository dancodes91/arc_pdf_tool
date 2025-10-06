"""
Universal adaptive parser for ANY manufacturer price book.

Uses ML-based table detection with Microsoft Table Transformer (TATR).
"""

from .parser import UniversalParser
from .table_detector import MLTableDetector
from .pattern_extractor import SmartPatternExtractor

__all__ = ["UniversalParser", "MLTableDetector", "SmartPatternExtractor"]
