"""
Adaptive Pattern Learner - Phase 5 of 98% accuracy improvement.

Learns manufacturer-specific patterns from successful extractions.
"""

import json
import os
import re
import logging
from typing import Dict, List, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class AdaptivePatternLearner:
    """
    Learn and adapt extraction patterns based on successful extractions.

    Stores manufacturer-specific patterns and improves over time.
    """

    def __init__(self, pattern_cache_path: str = "data/pattern_cache.json"):
        self.pattern_cache_path = pattern_cache_path
        self.patterns = self._load_patterns()
        self.logger = logging.getLogger(__name__)

    def learn_from_extraction(
        self,
        manufacturer: str,
        successful_products: List[Dict]
    ):
        """
        Learn patterns from successful extractions.

        Args:
            manufacturer: Manufacturer name
            successful_products: List of high-confidence products
        """
        if not successful_products:
            return

        if manufacturer not in self.patterns:
            self.patterns[manufacturer] = {
                'sku_patterns': set(),
                'price_patterns': set(),
                'description_keywords': set(),
                'extraction_count': 0
            }

        # Learn SKU patterns
        for product in successful_products:
            sku = product.get('sku', '')
            if sku:
                pattern = self._generalize_sku(sku)
                self.patterns[manufacturer]['sku_patterns'].add(pattern)

            # Learn description keywords
            desc = product.get('description', '')
            if desc:
                keywords = self._extract_keywords(desc)
                self.patterns[manufacturer]['description_keywords'].update(keywords)

        self.patterns[manufacturer]['extraction_count'] += len(successful_products)

        # Save patterns
        self._save_patterns()

        self.logger.info(
            f"Learned {len(self.patterns[manufacturer]['sku_patterns'])} SKU patterns "
            f"for {manufacturer} from {len(successful_products)} products"
        )

    def _generalize_sku(self, sku: str) -> str:
        """
        Generalize SKU to a regex pattern.

        Examples:
        - SL100 → ^SL\\d{3}$
        - BB-1279 → ^BB-\\d{4}$
        """
        pattern = sku
        # Replace sequences of digits with \d+
        pattern = re.sub(r'\d+', r'\\d+', pattern)
        # Wrap in boundaries
        pattern = f'^{pattern}$'
        return pattern

    def _extract_keywords(self, description: str) -> Set[str]:
        """Extract significant keywords from description."""
        # Split and filter
        words = description.lower().split()
        # Keep words longer than 3 characters
        keywords = {w for w in words if len(w) > 3}
        return keywords

    def get_manufacturer_patterns(self, manufacturer: str) -> Dict:
        """Get learned patterns for a manufacturer."""
        return self.patterns.get(manufacturer, {
            'sku_patterns': set(),
            'price_patterns': set(),
            'description_keywords': set(),
            'extraction_count': 0
        })

    def validate_sku(self, manufacturer: str, sku: str) -> float:
        """
        Validate SKU against learned patterns.

        Returns:
            Confidence boost (0.0 to 0.05) if SKU matches learned patterns
        """
        if manufacturer not in self.patterns:
            return 0.0

        sku_patterns = self.patterns[manufacturer].get('sku_patterns', set())

        for pattern in sku_patterns:
            try:
                if re.match(pattern, sku):
                    return 0.05  # 5% confidence boost for pattern match
            except re.error:
                continue

        return 0.0

    def _save_patterns(self):
        """Persist patterns to disk."""
        try:
            cache_path = Path(self.pattern_cache_path)
            cache_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert sets to lists for JSON serialization
            serializable = {}
            for mfr, data in self.patterns.items():
                serializable[mfr] = {
                    'sku_patterns': list(data.get('sku_patterns', set())),
                    'price_patterns': list(data.get('price_patterns', set())),
                    'description_keywords': list(data.get('description_keywords', set())),
                    'extraction_count': data.get('extraction_count', 0)
                }

            with open(cache_path, 'w') as f:
                json.dump(serializable, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error saving patterns: {e}")

    def _load_patterns(self) -> Dict:
        """Load patterns from disk."""
        try:
            if os.path.exists(self.pattern_cache_path):
                with open(self.pattern_cache_path, 'r') as f:
                    loaded = json.load(f)

                # Convert lists back to sets
                patterns = {}
                for mfr, data in loaded.items():
                    patterns[mfr] = {
                        'sku_patterns': set(data.get('sku_patterns', [])),
                        'price_patterns': set(data.get('price_patterns', [])),
                        'description_keywords': set(data.get('description_keywords', [])),
                        'extraction_count': data.get('extraction_count', 0)
                    }
                return patterns
        except Exception as e:
            self.logger.warning(f"Error loading patterns: {e}")

        return {}
