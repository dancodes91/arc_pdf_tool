"""
Multi-Source Validator - Cross-validates data from multiple extraction layers.

Phase 2 of 98% accuracy improvement plan.

Validates extracted data by comparing results from multiple sources (layers)
to identify agreements and conflicts, boosting confidence for multi-source data.
"""

import logging
from typing import List, Dict, Any, Optional
from collections import defaultdict

from .provenance import ParsedItem

logger = logging.getLogger(__name__)


class MultiSourceValidator:
    """
    Validates extracted data by comparing results from multiple sources.

    Implements uncertainty quantification and multi-source agreement detection.

    Strategy:
    1. Build index of items by unique identifier (SKU)
    2. Identify multi-source items (found by 2+ layers)
    3. Boost confidence for agreements
    4. Flag conflicts for review
    5. Merge with smart deduplication
    """

    def __init__(self, confidence_threshold: float = 0.7):
        """
        Initialize validator.

        Args:
            confidence_threshold: Minimum confidence for accepting single-source items
        """
        self.confidence_threshold = confidence_threshold
        self.logger = logging.getLogger(__name__)

    def validate_products(
        self,
        layer1_products: List[ParsedItem],
        layer2_products: List[ParsedItem],
        layer3_products: List[ParsedItem]
    ) -> List[ParsedItem]:
        """
        Cross-validate products from multiple layers.

        Args:
            layer1_products: Products from Layer 1 (pdfplumber text extraction)
            layer2_products: Products from Layer 2 (Camelot table extraction)
            layer3_products: Products from Layer 3 (PaddleOCR ML extraction)

        Returns:
            List of validated products with boosted confidence
        """
        self.logger.info("Starting multi-source validation")

        # Build SKU index
        sku_index = self._build_sku_index(
            layer1_products, layer2_products, layer3_products
        )

        self.logger.info(f"Found {len(sku_index)} unique SKUs across all layers")

        validated = []
        conflicts = []
        multi_source_count = 0

        for sku, sources in sku_index.items():
            if len(sources) >= 2:
                # Multi-source agreement - boost confidence
                merged = self._merge_multi_source(sources)

                # Boost confidence based on number of sources
                confidence_boost = self._calculate_confidence_boost(len(sources))
                merged.confidence = min(merged.confidence + confidence_boost, 1.0)

                # Mark as validated
                if not hasattr(merged.provenance, 'validation_status'):
                    merged.provenance.validation_status = "multi_source_validated"
                else:
                    merged.provenance.validation_status = "multi_source_validated"

                validated.append(merged)
                multi_source_count += 1

            elif len(sources) == 1:
                # Single source
                product = sources[0]
                if product.confidence >= self.confidence_threshold:
                    validated.append(product)
                else:
                    # Low confidence single-source item
                    conflicts.append(product)

        self.logger.info(
            f"Validated {len(validated)} products "
            f"({multi_source_count} multi-source, "
            f"{len(validated) - multi_source_count} single-source)"
        )

        if conflicts:
            self.logger.warning(
                f"Flagged {len(conflicts)} low-confidence products for review"
            )

        return validated

    def _build_sku_index(self, *layers) -> Dict[str, List[ParsedItem]]:
        """
        Build index of SKU → List[ParsedItem] from all layers.

        Args:
            *layers: Variable number of layer product lists

        Returns:
            Dictionary mapping SKU to list of ParsedItems from different layers
        """
        index = defaultdict(list)

        for layer_idx, layer in enumerate(layers, 1):
            for product in layer:
                sku = product.value.get('sku')
                if sku:
                    # Normalize SKU for matching
                    sku_normalized = self._normalize_sku(sku)
                    index[sku_normalized].append(product)

        return dict(index)

    def _normalize_sku(self, sku: str) -> str:
        """
        Normalize SKU for matching across layers.

        Handles minor variations:
        - Case insensitive
        - Trim whitespace
        - Remove common separators for matching

        Args:
            sku: Raw SKU string

        Returns:
            Normalized SKU for matching
        """
        if not sku:
            return ""

        # Convert to uppercase and trim
        normalized = str(sku).upper().strip()

        # Remove common variations for matching
        # But preserve original in the product data
        normalized = normalized.replace(" ", "").replace("-", "").replace("_", "")

        return normalized

    def _merge_multi_source(self, sources: List[ParsedItem]) -> ParsedItem:
        """
        Merge products from multiple sources.

        Strategy:
        1. Use highest confidence version as base
        2. Fill in missing fields from other sources
        3. Average numeric values (prices) if they differ
        4. Track variance for quality assessment

        Args:
            sources: List of ParsedItems for the same product from different layers

        Returns:
            Merged ParsedItem with best data from all sources
        """
        if not sources:
            raise ValueError("Cannot merge empty sources list")

        # Sort by confidence (highest first)
        sources = sorted(sources, key=lambda p: p.confidence, reverse=True)

        # Use highest confidence as base
        base = sources[0]

        # Merge data from other sources
        for source in sources[1:]:
            for key, value in source.value.items():
                # Fill in missing fields
                if key not in base.value or base.value[key] is None:
                    base.value[key] = value

        # Handle price averaging if multiple prices exist
        prices = [
            s.value.get('base_price')
            for s in sources
            if s.value.get('base_price') is not None
        ]

        if len(prices) > 1:
            # Check if prices are similar (within 1%)
            price_variance = (max(prices) - min(prices)) / min(prices) if min(prices) > 0 else 0

            if price_variance <= 0.01:
                # Very similar prices - use average
                base.value['base_price'] = sum(prices) / len(prices)
                base.value['price_variance'] = price_variance
                base.value['price_sources'] = len(prices)
            else:
                # Significant variance - flag for review
                base.value['price_variance'] = price_variance
                base.value['price_sources'] = len(prices)
                base.value['price_conflict'] = True
                self.logger.warning(
                    f"Price variance {price_variance:.1%} for SKU {base.value.get('sku')}: "
                    f"${min(prices):.2f} - ${max(prices):.2f}"
                )

        # Track extraction methods used
        extraction_methods = [
            s.provenance.extraction_method
            for s in sources
            if hasattr(s.provenance, 'extraction_method')
        ]
        base.value['extraction_methods'] = list(set(extraction_methods))
        base.value['source_count'] = len(sources)

        return base

    def _calculate_confidence_boost(self, num_sources: int) -> float:
        """
        Calculate confidence boost based on number of agreeing sources.

        Args:
            num_sources: Number of layers that extracted this item

        Returns:
            Confidence boost value (0.0 to 0.15)
        """
        # Confidence boost based on research:
        # 2 sources agree: +8% confidence
        # 3 sources agree: +10% confidence

        boost_map = {
            1: 0.0,   # No boost for single source
            2: 0.08,  # 8% boost for 2 sources
            3: 0.10,  # 10% boost for 3 sources
        }

        return boost_map.get(num_sources, 0.10)

    def validate_options(
        self,
        layer1_options: List[ParsedItem],
        layer2_options: List[ParsedItem],
        layer3_options: List[ParsedItem]
    ) -> List[ParsedItem]:
        """
        Validate options/add-ons from multiple layers.

        Similar to product validation but uses option_code instead of SKU.

        Args:
            layer1_options: Options from Layer 1
            layer2_options: Options from Layer 2
            layer3_options: Options from Layer 3

        Returns:
            List of validated options
        """
        # Build index by option_code
        option_index = defaultdict(list)

        for layer in [layer1_options, layer2_options, layer3_options]:
            for option in layer:
                code = option.value.get('option_code')
                if code:
                    code_normalized = code.upper().strip()
                    option_index[code_normalized].append(option)

        validated = []
        multi_source_count = 0

        for code, sources in option_index.items():
            if len(sources) >= 2:
                # Multi-source agreement
                merged = self._merge_options(sources)
                boost = self._calculate_confidence_boost(len(sources))
                merged.confidence = min(merged.confidence + boost, 1.0)

                if not hasattr(merged.provenance, 'validation_status'):
                    merged.provenance.validation_status = "multi_source_validated"
                else:
                    merged.provenance.validation_status = "multi_source_validated"

                validated.append(merged)
                multi_source_count += 1
            else:
                validated.append(sources[0])

        self.logger.info(
            f"Validated {len(validated)} options "
            f"({multi_source_count} multi-source)"
        )

        return validated

    def _merge_options(self, sources: List[ParsedItem]) -> ParsedItem:
        """
        Merge options from multiple sources.

        Args:
            sources: List of ParsedItems for the same option from different layers

        Returns:
            Merged option with best data
        """
        if not sources:
            raise ValueError("Cannot merge empty sources list")

        # Sort by confidence
        sources = sorted(sources, key=lambda p: p.confidence, reverse=True)
        base = sources[0]

        # Merge fields
        for source in sources[1:]:
            for key, value in source.value.items():
                if key not in base.value or base.value[key] is None:
                    base.value[key] = value

        # Average adder values if multiple exist
        adder_values = [
            s.value.get('adder_value')
            for s in sources
            if s.value.get('adder_value') is not None
        ]

        if len(adder_values) > 1:
            base.value['adder_value'] = sum(adder_values) / len(adder_values)
            base.value['adder_sources'] = len(adder_values)

        base.value['source_count'] = len(sources)

        return base

    def get_validation_stats(
        self,
        validated_items: List[ParsedItem]
    ) -> Dict[str, Any]:
        """
        Get validation statistics for reporting.

        Args:
            validated_items: List of validated items

        Returns:
            Dictionary with validation statistics
        """
        multi_source = sum(
            1 for item in validated_items
            if hasattr(item.provenance, 'validation_status')
            and item.provenance.validation_status == "multi_source_validated"
        )

        high_confidence = sum(
            1 for item in validated_items
            if item.confidence >= 0.9
        )

        avg_confidence = (
            sum(item.confidence for item in validated_items) / len(validated_items)
            if validated_items else 0
        )

        return {
            'total_items': len(validated_items),
            'multi_source_validated': multi_source,
            'multi_source_rate': multi_source / len(validated_items) if validated_items else 0,
            'high_confidence_items': high_confidence,
            'high_confidence_rate': high_confidence / len(validated_items) if validated_items else 0,
            'average_confidence': avg_confidence,
        }
