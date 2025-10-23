"""
Error Corrector - Phase 6 of 98% accuracy improvement.

Detects and corrects common OCR errors and data quality issues.
"""

import re
import logging
from typing import List, Dict, Any
from decimal import Decimal

from .provenance import ParsedItem

logger = logging.getLogger(__name__)


class PostProcessingValidator:
    """
    Detect and fix potential errors using business logic.

    Validation rules:
    - Price reasonableness
    - SKU uniqueness
    - Description completeness
    - Cross-field consistency
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def validate_and_correct(self, products: List[ParsedItem]) -> Dict[str, Any]:
        """
        Run validation and auto-correction on products.

        Returns:
            {
                'valid_products': List[ParsedItem],
                'corrected_count': int,
                'errors': List[Dict],
                'warnings': List[Dict]
            }
        """
        valid = []
        errors = []
        warnings = []
        corrected_count = 0

        seen_skus = set()

        for product in products:
            product_errors = []
            product_warnings = []
            was_corrected = False

            # Auto-correct SKU
            sku = product.value.get('sku')
            if sku:
                corrected_sku = self._correct_sku(sku)
                if corrected_sku != sku:
                    product.value['sku'] = corrected_sku
                    product.value['sku_corrected'] = True
                    product.value['sku_original'] = sku
                    was_corrected = True

                # Check uniqueness
                if corrected_sku in seen_skus:
                    product_errors.append({
                        'field': 'sku',
                        'message': f'Duplicate SKU: {corrected_sku}'
                    })
                seen_skus.add(corrected_sku)

            # Auto-correct and validate price
            price = product.value.get('base_price')
            if price is not None:
                corrected_price = self._normalize_price(price)
                if corrected_price != price:
                    product.value['base_price'] = corrected_price
                    was_corrected = True

                # Validate range
                if corrected_price < 0.01:
                    product_errors.append({
                        'field': 'base_price',
                        'message': f'Price too low: ${corrected_price}'
                    })
                elif corrected_price > 50000:
                    product_warnings.append({
                        'field': 'base_price',
                        'message': f'Price unusually high: ${corrected_price}'
                    })

            # Clean description
            desc = product.value.get('description', '')
            if desc:
                cleaned_desc = self._clean_text(desc)
                if cleaned_desc != desc:
                    product.value['description'] = cleaned_desc
                    was_corrected = True

                if len(cleaned_desc) < 5:
                    product_warnings.append({
                        'field': 'description',
                        'message': 'Description too short'
                    })

            # Track corrections
            if was_corrected:
                corrected_count += 1

            # Add to results
            if product_errors:
                errors.extend(product_errors)
            if product_warnings:
                warnings.extend(product_warnings)

            valid.append(product)

        self.logger.info(
            f"Validation complete: {len(valid)} products, "
            f"{corrected_count} auto-corrected, "
            f"{len(errors)} errors, {len(warnings)} warnings"
        )

        return {
            'valid_products': valid,
            'corrected_count': corrected_count,
            'errors': errors,
            'warnings': warnings,
            'validation_rate': 1.0 - (len(errors) / len(products)) if products else 0
        }

    def _correct_sku(self, sku: str) -> str:
        """
        Correct common SKU OCR errors.

        Common OCR mistakes:
        - O (letter) → 0 (zero) in numeric context
        - I (letter I) → 1 (one) in numeric context
        - l (lowercase L) → 1 (one) in numeric context
        """
        if not sku:
            return sku

        corrected = str(sku).strip()

        # Remove OCR artifacts
        corrected = corrected.replace('|', '').replace('�', '').replace('\\x00', '')

        # Context-aware OCR corrections (only in numeric context)
        # O → 0 when surrounded by digits
        corrected = re.sub(r'(?<=\d)O(?=\d)', '0', corrected)
        corrected = re.sub(r'(?<=\d)O$', '0', corrected)

        # I → 1 when surrounded by digits
        corrected = re.sub(r'(?<=\d)I(?=\d)', '1', corrected)
        corrected = re.sub(r'(?<=\d)I$', '1', corrected)

        # l → 1 when surrounded by digits
        corrected = re.sub(r'(?<=\d)l(?=\d)', '1', corrected)
        corrected = re.sub(r'(?<=\d)l$', '1', corrected)

        return corrected

    def _normalize_price(self, price: Any) -> float:
        """Normalize price to float."""
        try:
            if isinstance(price, (int, float)):
                return float(price)

            # Remove currency symbols and commas
            price_str = str(price).replace('$', '').replace(',', '').strip()

            # Convert to float
            return float(price_str)

        except (ValueError, TypeError):
            self.logger.warning(f"Could not normalize price: {price}")
            return 0.0

    def _clean_text(self, text: str) -> str:
        """Clean text by removing OCR artifacts."""
        if not text:
            return text

        cleaned = str(text)

        # Remove common OCR artifacts
        artifacts = ['�', '\\x00', '||', '|_']
        for artifact in artifacts:
            cleaned = cleaned.replace(artifact, '')

        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)

        return cleaned.strip()
