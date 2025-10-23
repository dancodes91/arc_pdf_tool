"""
Feedback Loop System - Phase 7 of 98% accuracy improvement.

Collects user corrections and learns from them to improve future extractions.
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """
    Collect and learn from user corrections.

    Implements feedback loop for continuous improvement:
    1. Track user corrections vs original extractions
    2. Identify systematic errors
    3. Update extraction patterns and thresholds
    4. Generate improvement metrics
    """

    def __init__(self, feedback_path: str = "data/feedback.json"):
        self.feedback_path = feedback_path
        self.feedback_data = self._load_feedback()
        self.logger = logging.getLogger(__name__)

    def record_correction(
        self,
        original_value: Any,
        corrected_value: Any,
        field_name: str,
        manufacturer: str,
        confidence: float,
        extraction_method: str
    ):
        """
        Record a user correction.

        Args:
            original_value: Original extracted value
            corrected_value: User-corrected value
            field_name: Field that was corrected (sku, base_price, etc.)
            manufacturer: Manufacturer name
            confidence: Original confidence score
            extraction_method: How the data was extracted
        """
        correction = {
            'timestamp': datetime.now().isoformat(),
            'field_name': field_name,
            'manufacturer': manufacturer,
            'original_value': str(original_value),
            'corrected_value': str(corrected_value),
            'confidence': confidence,
            'extraction_method': extraction_method,
        }

        # Initialize manufacturer feedback if needed
        if manufacturer not in self.feedback_data:
            self.feedback_data[manufacturer] = {
                'corrections': [],
                'error_patterns': {},
                'total_corrections': 0,
                'field_accuracy': {}
            }

        # Add correction
        self.feedback_data[manufacturer]['corrections'].append(correction)
        self.feedback_data[manufacturer]['total_corrections'] += 1

        # Update field accuracy tracking
        if field_name not in self.feedback_data[manufacturer]['field_accuracy']:
            self.feedback_data[manufacturer]['field_accuracy'][field_name] = {
                'total': 0,
                'errors': 0,
                'accuracy': 1.0
            }

        field_stats = self.feedback_data[manufacturer]['field_accuracy'][field_name]
        field_stats['total'] += 1
        field_stats['errors'] += 1
        field_stats['accuracy'] = 1.0 - (field_stats['errors'] / field_stats['total'])

        # Detect error pattern
        self._detect_error_pattern(manufacturer, field_name, original_value, corrected_value)

        # Persist feedback
        self._save_feedback()

        self.logger.info(
            f"Recorded correction for {manufacturer} {field_name}: "
            f"'{original_value}' -> '{corrected_value}'"
        )

    def record_acceptance(
        self,
        value: Any,
        field_name: str,
        manufacturer: str,
        confidence: float
    ):
        """
        Record that a user accepted an extracted value without correction.

        This helps track accuracy and validates our confidence scoring.

        Args:
            value: Accepted value
            field_name: Field name
            manufacturer: Manufacturer name
            confidence: Confidence score
        """
        # Initialize manufacturer feedback if needed
        if manufacturer not in self.feedback_data:
            self.feedback_data[manufacturer] = {
                'corrections': [],
                'error_patterns': {},
                'total_corrections': 0,
                'field_accuracy': {}
            }

        # Update field accuracy tracking
        if field_name not in self.feedback_data[manufacturer]['field_accuracy']:
            self.feedback_data[manufacturer]['field_accuracy'][field_name] = {
                'total': 0,
                'errors': 0,
                'accuracy': 1.0
            }

        field_stats = self.feedback_data[manufacturer]['field_accuracy'][field_name]
        field_stats['total'] += 1
        # Don't increment errors - this was correct
        field_stats['accuracy'] = 1.0 - (field_stats['errors'] / field_stats['total'])

        # Persist feedback
        self._save_feedback()

    def _detect_error_pattern(
        self,
        manufacturer: str,
        field_name: str,
        original: str,
        corrected: str
    ):
        """
        Detect systematic error patterns from corrections.

        Examples:
        - OCR errors: O->0, I->1
        - Missing characters
        - Wrong decimal places
        """
        original_str = str(original)
        corrected_str = str(corrected)

        # Detect character substitutions
        if len(original_str) == len(corrected_str):
            for i, (orig_char, corr_char) in enumerate(zip(original_str, corrected_str)):
                if orig_char != corr_char:
                    pattern = f"{orig_char}->{corr_char}"

                    # Track pattern frequency
                    pattern_key = f"{field_name}:{pattern}"
                    if pattern_key not in self.feedback_data[manufacturer]['error_patterns']:
                        self.feedback_data[manufacturer]['error_patterns'][pattern_key] = 0

                    self.feedback_data[manufacturer]['error_patterns'][pattern_key] += 1

    def get_accuracy_report(self, manufacturer: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate accuracy report from feedback data.

        Args:
            manufacturer: Specific manufacturer or None for all

        Returns:
            Report with accuracy metrics by field
        """
        if manufacturer and manufacturer in self.feedback_data:
            mfr_data = self.feedback_data[manufacturer]

            return {
                'manufacturer': manufacturer,
                'total_corrections': mfr_data['total_corrections'],
                'field_accuracy': mfr_data['field_accuracy'],
                'top_error_patterns': self._get_top_error_patterns(manufacturer, limit=10),
                'recommendations': self._generate_recommendations(manufacturer)
            }

        # Overall report across all manufacturers
        total_corrections = sum(
            mfr['total_corrections']
            for mfr in self.feedback_data.values()
        )

        # Aggregate field accuracy
        field_accuracy = {}
        for mfr_data in self.feedback_data.values():
            for field_name, stats in mfr_data.get('field_accuracy', {}).items():
                if field_name not in field_accuracy:
                    field_accuracy[field_name] = {'total': 0, 'errors': 0}

                field_accuracy[field_name]['total'] += stats['total']
                field_accuracy[field_name]['errors'] += stats['errors']

        # Calculate overall accuracy by field
        for field_name in field_accuracy:
            stats = field_accuracy[field_name]
            if stats['total'] > 0:
                stats['accuracy'] = 1.0 - (stats['errors'] / stats['total'])
            else:
                stats['accuracy'] = 1.0

        return {
            'manufacturer': 'all',
            'total_corrections': total_corrections,
            'field_accuracy': field_accuracy,
            'manufacturers': list(self.feedback_data.keys())
        }

    def _get_top_error_patterns(self, manufacturer: str, limit: int = 10) -> List[Dict]:
        """Get most common error patterns for a manufacturer."""
        if manufacturer not in self.feedback_data:
            return []

        patterns = self.feedback_data[manufacturer].get('error_patterns', {})

        # Sort by frequency
        sorted_patterns = sorted(
            patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        return [
            {'pattern': pattern, 'frequency': count}
            for pattern, count in sorted_patterns
        ]

    def _generate_recommendations(self, manufacturer: str) -> List[str]:
        """
        Generate recommendations for improving accuracy.

        Args:
            manufacturer: Manufacturer name

        Returns:
            List of actionable recommendations
        """
        recommendations = []

        if manufacturer not in self.feedback_data:
            return recommendations

        mfr_data = self.feedback_data[manufacturer]

        # Check field accuracy
        for field_name, stats in mfr_data.get('field_accuracy', {}).items():
            if stats['total'] >= 10 and stats['accuracy'] < 0.90:
                recommendations.append(
                    f"Low accuracy for {field_name} ({stats['accuracy']:.1%}). "
                    f"Consider improving extraction patterns."
                )

        # Check common error patterns
        error_patterns = self._get_top_error_patterns(manufacturer, limit=3)
        for pattern_info in error_patterns:
            if pattern_info['frequency'] >= 5:
                recommendations.append(
                    f"Common error pattern: {pattern_info['pattern']} "
                    f"(occurred {pattern_info['frequency']} times). "
                    f"Add auto-correction rule."
                )

        return recommendations

    def get_correction_suggestions(
        self,
        value: Any,
        field_name: str,
        manufacturer: str
    ) -> Optional[Any]:
        """
        Suggest correction based on learned patterns.

        Args:
            value: Current value
            field_name: Field name
            manufacturer: Manufacturer name

        Returns:
            Suggested corrected value or None
        """
        if manufacturer not in self.feedback_data:
            return None

        value_str = str(value)

        # Check historical corrections for exact matches
        for correction in self.feedback_data[manufacturer].get('corrections', []):
            if (correction['field_name'] == field_name and
                correction['original_value'] == value_str):
                # Found exact match - suggest same correction
                return correction['corrected_value']

        # Check error patterns
        error_patterns = self.feedback_data[manufacturer].get('error_patterns', {})

        # Apply most common error patterns
        suggested = value_str
        for pattern_key, frequency in error_patterns.items():
            if frequency >= 3:  # Only apply patterns seen 3+ times
                parts = pattern_key.split(':')
                if len(parts) == 2:
                    pattern_field, pattern = parts
                    if pattern_field == field_name and '->' in pattern:
                        orig_char, corr_char = pattern.split('->')
                        suggested = suggested.replace(orig_char, corr_char)

        return suggested if suggested != value_str else None

    def _save_feedback(self):
        """Persist feedback data to disk."""
        try:
            feedback_path = Path(self.feedback_path)
            feedback_path.parent.mkdir(parents=True, exist_ok=True)

            with open(feedback_path, 'w') as f:
                json.dump(self.feedback_data, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error saving feedback: {e}")

    def _load_feedback(self) -> Dict:
        """Load feedback data from disk."""
        try:
            if os.path.exists(self.feedback_path):
                with open(self.feedback_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Error loading feedback: {e}")

        return {}
