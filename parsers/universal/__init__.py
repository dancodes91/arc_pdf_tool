"""
Universal adaptive parser for ANY manufacturer price book.

Uses img2table + PaddleOCR for complete table extraction (90-95% accuracy).
"""

from .parser import UniversalParser
from .img2table_detector import Img2TableDetector
from .pattern_extractor import SmartPatternExtractor

__all__ = ["UniversalParser", "Img2TableDetector", "SmartPatternExtractor"]
