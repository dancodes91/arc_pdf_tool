"""
Field-Specific Confidence Models - Phase 3 of 98% accuracy improvement.

Different fields require different validation criteria:
- SKUs: Pattern matching + uniqueness
- Prices: Numeric validation + range checks
- Descriptions: Completeness + coherence
"""

import re
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class FieldSpecificConfidenceModel:
    """
    Adaptive confidence scoring based on field type and data characteristics.

    Implements field-specific thresholds and validation rules.
    """

    # Confidence thresholds by field type
    THRESHOLDS = {
        'sku': 0.85,         # SKUs must be high confidence
        'base_price': 0.80,  # Prices are critical
        'description': 0.70, # Descriptions can be lower
        'model': 0.75,
        'finish': 0.70,
        'option_code': 0.75,
    }

    # Extraction method reliability weights
    METHOD_WEIGHTS = {
        'layer1_text': 0.85,
        'layer2_camelot': 0.90,
        'layer3_paddleocr': 0.95,
        'layer3_ml': 0.70,
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def calculate_confidence(
        self,
        field_name: str,
        value: Any,
        extraction_method: str = 'unknown',
        ocr_confidence: float = None
    ) -> float:
        """
        Calculate field-specific confidence score.

        Args:
            field_name: Field name (sku, base_price, description, etc.)
            value: Field value
            extraction_method: How the data was extracted
            ocr_confidence: OCR confidence if available

        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from OCR or method
        base_confidence = ocr_confidence if ocr_confidence else 0.7

        # Pattern validation score
        pattern_score = self._validate_pattern(field_name, value)

        # Data quality score
        quality_score = self._assess_quality(field_name, value)

        # Method reliability
        method_weight = self.METHOD_WEIGHTS.get(extraction_method, 0.70)

        # Weighted average
        confidence = (
            base_confidence * 0.4 +
            pattern_score * 0.3 +
            quality_score * 0.2 +
            method_weight * 0.1
        )

        return min(confidence, 1.0)

    def _validate_pattern(self, field_name: str, value: Any) -> float:
        """Validate value matches expected pattern for field type."""
        if field_name == 'sku':
            return self._validate_sku_pattern(value)
        elif field_name == 'base_price':
            return self._validate_price_pattern(value)
        elif field_name == 'description':
            return self._validate_description_pattern(value)
        elif field_name == 'option_code':
            return self._validate_option_code_pattern(value)
        else:
            return 0.75  # Default

    def _validate_sku_pattern(self, sku: Any) -> float:
        """Validate SKU pattern strength."""
        if not sku:
            return 0.0

        sku_str = str(sku).strip()

        # Strong patterns (95% confidence)
        strong_patterns = [
            r'^[A-Z]{2,}\d{2,}$',           # SL100, BB1279
            r'^[A-Z]{2,}\d{2,}-[A-Z\d]+$',  # SL100-US26D
            r'^\d{4,}-[A-Z\d]+$',           # 1279-US26D
        ]

        for pattern in strong_patterns:
            if re.match(pattern, sku_str):
                return 0.95

        # Medium patterns (85% confidence)
        medium_patterns = [
            r'^[A-Z\d-]{4,}$',  # General alphanumeric with dashes
            r'^[A-Z]{1}\d{3,}$', # A123
        ]

        for pattern in medium_patterns:
            if re.match(pattern, sku_str):
                return 0.85

        # Weak pattern (60% confidence)
        if len(sku_str) >= 3:
            return 0.60

        return 0.30

    def _validate_price_pattern(self, price: Any) -> float:
        """Validate price format and reasonableness."""
        try:
            # Convert to float
            if isinstance(price, str):
                price_clean = price.replace('$', '').replace(',', '').strip()
                price_float = float(price_clean)
            else:
                price_float = float(price)

            # Check reasonable range
            if 0.01 <= price_float <= 100000:
                return 0.95  # Normal price range
            elif 0 < price_float < 0.01:
                return 0.70  # Very small price
            elif 100000 < price_float <= 500000:
                return 0.80  # High price (possible but unusual)
            else:
                return 0.50  # Suspicious price

        except (ValueError, TypeError):
            return 0.30  # Invalid price

    def _validate_description_pattern(self, description: Any) -> float:
        """Validate description completeness."""
        if not description:
            return 0.0

        desc_str = str(description).strip()

        # Check length
        if len(desc_str) < 5:
            return 0.40  # Too short

        if len(desc_str) > 20:
            score = 0.85
        else:
            score = 0.65

        # Bonus for domain keywords
        keywords = ['hinge', 'lock', 'door', 'closer', 'hardware', 'continuous', 'geared']
        if any(keyword in desc_str.lower() for keyword in keywords):
            score += 0.10

        return min(score, 1.0)

    def _validate_option_code_pattern(self, code: Any) -> float:
        """Validate option/add-on code pattern."""
        if not code:
            return 0.0

        code_str = str(code).strip()

        # Common option code patterns
        if re.match(r'^[A-Z]{2,4}$', code_str):  # LM, CTW, BHMA
            return 0.90
        elif re.match(r'^[A-Z\d]{2,}$', code_str):  # General
            return 0.75
        else:
            return 0.50

    def _assess_quality(self, field_name: str, value: Any) -> float:
        """Assess data quality (completeness, coherence)."""
        if value is None or str(value).strip() == '':
            return 0.0

        value_str = str(value)

        # Check for OCR artifacts
        ocr_artifacts = ['�', '||', '|_', '\\x', '\x00']
        if any(artifact in value_str for artifact in ocr_artifacts):
            return 0.40  # Has OCR garbage

        # Check for reasonable length (not just 1-2 characters unless SKU/code)
        if field_name in ['sku', 'option_code', 'finish']:
            if len(value_str) >= 2:
                return 0.90
            else:
                return 0.50
        else:
            if len(value_str) >= 3:
                return 0.90
            else:
                return 0.60

    def get_field_threshold(self, field_name: str) -> float:
        """Get minimum confidence threshold for field."""
        return self.THRESHOLDS.get(field_name, 0.70)

    def is_acceptable(self, field_name: str, confidence: float) -> bool:
        """Check if confidence meets field threshold."""
        threshold = self.get_field_threshold(field_name)
        return confidence >= threshold
