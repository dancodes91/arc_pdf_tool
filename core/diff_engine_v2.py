"""
Diff Engine v2 with better matching, rename detection, and confidence scoring.

Handles price book comparisons with fuzzy matching, rule differences,
and human review queue for low-confidence matches.
"""
import logging
import re
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of changes detected in diff."""
    ADDED = "added"
    REMOVED = "removed"
    PRICE_CHANGED = "price_changed"
    CURRENCY_CHANGED = "currency_changed"
    OPTION_ADDED = "option_added"
    OPTION_REMOVED = "option_removed"
    OPTION_AMOUNT_CHANGED = "option_amount_changed"
    RULE_CHANGED = "rule_changed"
    FINISH_RULE_CHANGED = "finish_rule_changed"
    CONSTRAINTS_CHANGED = "constraints_changed"
    RENAMED = "renamed"
    DESCRIPTION_CHANGED = "description_changed"


class MatchConfidence(Enum):
    """Confidence levels for item matching."""
    EXACT = "exact"        # 1.0 - Perfect match
    HIGH = "high"          # 0.8-0.99 - Very confident
    MEDIUM = "medium"      # 0.6-0.79 - Reasonably confident
    LOW = "low"           # 0.4-0.59 - Uncertain, needs review
    VERY_LOW = "very_low" # 0.0-0.39 - Poor match, likely wrong


@dataclass
class MatchResult:
    """Result of item matching between old and new books."""
    old_item: Dict[str, Any]
    new_item: Optional[Dict[str, Any]]
    confidence: float
    confidence_level: MatchConfidence
    match_key: str
    match_method: str
    match_reasons: List[str] = field(default_factory=list)
    fuzzy_score: Optional[float] = None


@dataclass
class Change:
    """Individual change detected in diff."""
    change_type: ChangeType
    confidence: float
    old_value: Optional[Any]
    new_value: Optional[Any]
    field_name: str
    description: str
    match_key: str
    old_ref: Optional[str] = None
    new_ref: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiffResult:
    """Complete diff result between two price books."""
    old_book_id: str
    new_book_id: str
    timestamp: datetime
    matches: List[MatchResult]
    changes: List[Change]
    summary: Dict[str, int]
    review_queue: List[MatchResult]  # Low confidence matches needing review
    metadata: Dict[str, Any] = field(default_factory=dict)


class DiffEngineV2:
    """
    Enhanced diff engine with intelligent matching and confidence scoring.

    Features:
    - Fuzzy matching for renamed items
    - Confidence-based review queue
    - Option and rule diffing
    - Currency change detection
    - Structured change logging
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Matching thresholds
        self.exact_match_threshold = self.config.get('exact_match_threshold', 0.98)
        self.high_confidence_threshold = self.config.get('high_confidence_threshold', 0.8)
        self.medium_confidence_threshold = self.config.get('medium_confidence_threshold', 0.6)
        self.low_confidence_threshold = self.config.get('low_confidence_threshold', 0.4)
        self.review_threshold = self.config.get('review_threshold', 0.6)

        # Fuzzy matching settings
        self.enable_fuzzy_matching = self.config.get('enable_fuzzy_matching', True)
        self.fuzzy_threshold = self.config.get('fuzzy_threshold', 70)

        if not RAPIDFUZZ_AVAILABLE and self.enable_fuzzy_matching:
            self.logger.warning("RapidFuzz not available. Install with: pip install rapidfuzz")
            self.enable_fuzzy_matching = False

    def create_diff(self, old_book: Dict[str, Any], new_book: Dict[str, Any]) -> DiffResult:
        """
        Create comprehensive diff between two price books.

        Args:
            old_book: Previous version data
            new_book: New version data

        Returns:
            DiffResult with all changes and matches
        """
        self.logger.info(f"Creating diff: {old_book.get('id', 'unknown')} -> {new_book.get('id', 'unknown')}")

        # Extract product data
        old_products = self._extract_products(old_book)
        new_products = self._extract_products(new_book)

        self.logger.info(f"Comparing {len(old_products)} old vs {len(new_products)} new products")

        # Perform matching
        matches = self._match_products(old_products, new_products)

        # Detect changes
        changes = self._detect_changes(matches, old_book, new_book)

        # Filter review queue (low confidence matches)
        review_queue = [match for match in matches
                       if match.confidence < self.review_threshold]

        # Generate summary
        summary = self._generate_summary(matches, changes)

        result = DiffResult(
            old_book_id=old_book.get('id', 'unknown'),
            new_book_id=new_book.get('id', 'unknown'),
            timestamp=datetime.now(),
            matches=matches,
            changes=changes,
            summary=summary,
            review_queue=review_queue,
            metadata={
                'config': self.config,
                'old_product_count': len(old_products),
                'new_product_count': len(new_products),
                'fuzzy_matching_enabled': self.enable_fuzzy_matching
            }
        )

        self.logger.info(f"Diff complete: {len(changes)} changes, {len(review_queue)} items need review")
        return result

    def _extract_products(self, book_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract normalized product data from book."""
        products = []

        # Extract from different possible locations
        raw_products = (
            book_data.get('products', []) or
            book_data.get('items', []) or
            book_data.get('product_data', []) or
            []
        )

        for product in raw_products:
            # Normalize product structure
            if hasattr(product, 'value') and isinstance(product.value, dict):
                # ParsedItem format
                normalized = product.value.copy()
                normalized['_provenance'] = getattr(product, 'provenance', None)
                normalized['_confidence'] = getattr(product, 'confidence', 1.0)
            elif isinstance(product, dict):
                # Direct dict format
                normalized = product.copy()
            else:
                continue

            # Ensure required fields
            if not normalized.get('model') and not normalized.get('sku'):
                continue

            # Create matching keys
            normalized['_match_key'] = self._create_match_key(normalized)
            normalized['_search_text'] = self._create_search_text(normalized)

            products.append(normalized)

        return products

    def _create_match_key(self, product: Dict[str, Any]) -> str:
        """Create normalized matching key for product."""
        manufacturer = str(product.get('manufacturer', '')).lower()
        family = str(product.get('family', product.get('series', ''))).lower()

        # Primary key components
        model = str(product.get('model', product.get('sku', ''))).upper()
        size = str(product.get('size', product.get('size_attr', ''))).lower()
        finish = str(product.get('finish', product.get('finish_code', ''))).upper()

        # Normalize common variations
        model = re.sub(r'[\s\-_]', '', model)  # Remove separators
        size = re.sub(r'["\']', '', size)      # Remove quotes from sizes
        finish = re.sub(r'[^A-Z0-9]', '', finish)  # Keep only alphanumeric for finish

        # Block key: manufacturer + family (must match)
        block_key = f"{manufacturer}#{family}"

        # Item key: model + size + finish
        item_key = f"{model}#{size}#{finish}"

        return f"{block_key}#{item_key}"

    def _create_search_text(self, product: Dict[str, Any]) -> str:
        """Create searchable text for fuzzy matching."""
        text_parts = []

        # Key identifiers
        for field in ['model', 'sku', 'description', 'series', 'family']:
            value = product.get(field)
            if value:
                text_parts.append(str(value))

        # Size and finish
        for field in ['size', 'size_attr', 'finish', 'finish_code']:
            value = product.get(field)
            if value:
                text_parts.append(str(value))

        return ' '.join(text_parts).upper()

    def _match_products(self, old_products: List[Dict], new_products: List[Dict]) -> List[MatchResult]:
        """Match products between old and new books."""
        matches = []
        unmatched_old = old_products.copy()
        unmatched_new = new_products.copy()

        # Phase 1: Exact key matching
        exact_matches = self._exact_key_matching(unmatched_old, unmatched_new)
        matches.extend(exact_matches)

        # Remove exact matches from unmatched lists
        matched_old_keys = {match.old_item['_match_key'] for match in exact_matches if match.new_item}
        matched_new_keys = {match.new_item['_match_key'] for match in exact_matches if match.new_item}

        unmatched_old = [p for p in unmatched_old if p['_match_key'] not in matched_old_keys]
        unmatched_new = [p for p in unmatched_new if p['_match_key'] not in matched_new_keys]

        # Phase 2: Fuzzy matching for potential renames
        if self.enable_fuzzy_matching and unmatched_old and unmatched_new:
            fuzzy_matches = self._fuzzy_matching(unmatched_old, unmatched_new)
            matches.extend(fuzzy_matches)

            # Remove fuzzy matches
            fuzzy_old_keys = {match.old_item['_match_key'] for match in fuzzy_matches if match.new_item}
            fuzzy_new_keys = {match.new_item['_match_key'] for match in fuzzy_matches if match.new_item}

            unmatched_old = [p for p in unmatched_old if p['_match_key'] not in fuzzy_old_keys]
            unmatched_new = [p for p in unmatched_new if p['_match_key'] not in fuzzy_new_keys]

        # Phase 3: Mark remaining as added/removed
        for old_product in unmatched_old:
            matches.append(MatchResult(
                old_item=old_product,
                new_item=None,
                confidence=1.0,
                confidence_level=MatchConfidence.EXACT,
                match_key=old_product['_match_key'],
                match_method='removed',
                match_reasons=['Item not found in new book']
            ))

        for new_product in unmatched_new:
            matches.append(MatchResult(
                old_item=None,
                new_item=new_product,
                confidence=1.0,
                confidence_level=MatchConfidence.EXACT,
                match_key=new_product['_match_key'],
                match_method='added',
                match_reasons=['New item not in old book']
            ))

        return matches

    def _exact_key_matching(self, old_products: List[Dict], new_products: List[Dict]) -> List[MatchResult]:
        """Perform exact key matching."""
        matches = []

        # Create lookup for new products
        new_lookup = {product['_match_key']: product for product in new_products}

        for old_product in old_products:
            match_key = old_product['_match_key']

            if match_key in new_lookup:
                new_product = new_lookup[match_key]
                matches.append(MatchResult(
                    old_item=old_product,
                    new_item=new_product,
                    confidence=1.0,
                    confidence_level=MatchConfidence.EXACT,
                    match_key=match_key,
                    match_method='exact_key',
                    match_reasons=['Exact match key match']
                ))

        return matches

    def _fuzzy_matching(self, old_products: List[Dict], new_products: List[Dict]) -> List[MatchResult]:
        """Perform fuzzy matching for potential renames."""
        if not RAPIDFUZZ_AVAILABLE:
            return []

        matches = []
        new_search_texts = [p['_search_text'] for p in new_products]
        new_lookup = {p['_search_text']: p for p in new_products}

        used_new_products = set()

        for old_product in old_products:
            old_search_text = old_product['_search_text']

            # Find best fuzzy matches
            fuzzy_results = process.extract(
                old_search_text,
                new_search_texts,
                scorer=fuzz.ratio,
                limit=3
            )

            best_match = None
            best_score = 0

            for match_text, score, _ in fuzzy_results:
                if score >= self.fuzzy_threshold and match_text not in used_new_products:
                    # Additional validation for fuzzy matches
                    # Safety check: ensure match_text exists in lookup
                    if match_text not in new_lookup:
                        continue

                    new_product = new_lookup[match_text]

                    if self._validate_fuzzy_match(old_product, new_product):
                        best_match = new_product
                        best_score = score
                        break

            if best_match:
                used_new_products.add(best_match['_search_text'])

                # Convert fuzzy score to confidence
                confidence = min(best_score / 100.0, 0.95)  # Cap at 0.95 for fuzzy
                confidence_level = self._score_to_confidence_level(confidence)

                matches.append(MatchResult(
                    old_item=old_product,
                    new_item=best_match,
                    confidence=confidence,
                    confidence_level=confidence_level,
                    match_key=old_product['_match_key'],
                    match_method='fuzzy',
                    match_reasons=[f'Fuzzy match with {best_score}% similarity'],
                    fuzzy_score=best_score
                ))

        return matches

    def _validate_fuzzy_match(self, old_product: Dict, new_product: Dict) -> bool:
        """Validate that fuzzy match makes sense."""
        # Must have same manufacturer and family (blocking key)
        old_key_parts = old_product['_match_key'].split('#')
        new_key_parts = new_product['_match_key'].split('#')

        if len(old_key_parts) >= 2 and len(new_key_parts) >= 2:
            old_block = f"{old_key_parts[0]}#{old_key_parts[1]}"
            new_block = f"{new_key_parts[0]}#{new_key_parts[1]}"

            if old_block != new_block:
                return False

        # Additional semantic validation
        old_model = str(old_product.get('model', '')).upper()
        new_model = str(new_product.get('model', '')).upper()

        # Should have some common characters in model (relaxed from 30% to 20%)
        if old_model and new_model:
            # Remove all separators for comparison (CTW-4 vs CTW4)
            old_normalized = re.sub(r'[\s\-_]', '', old_model)
            new_normalized = re.sub(r'[\s\-_]', '', new_model)

            common_chars = set(old_normalized) & set(new_normalized)
            min_length = min(len(old_normalized), len(new_normalized))
            if min_length > 0 and len(common_chars) < min_length * 0.2:  # At least 20% common characters
                return False

        return True

    def _score_to_confidence_level(self, score: float) -> MatchConfidence:
        """Convert numeric confidence to confidence level."""
        if score >= self.exact_match_threshold:
            return MatchConfidence.EXACT
        elif score >= self.high_confidence_threshold:
            return MatchConfidence.HIGH
        elif score >= self.medium_confidence_threshold:
            return MatchConfidence.MEDIUM
        elif score >= self.low_confidence_threshold:
            return MatchConfidence.LOW
        else:
            return MatchConfidence.VERY_LOW

    def _detect_changes(self, matches: List[MatchResult], old_book: Dict, new_book: Dict) -> List[Change]:
        """Detect all types of changes from matches."""
        changes = []

        for match in matches:
            if not match.old_item or not match.new_item:
                # Added or removed items
                if not match.new_item:
                    changes.append(Change(
                        change_type=ChangeType.REMOVED,
                        confidence=1.0,
                        old_value=match.old_item,
                        new_value=None,
                        field_name='item',
                        description=f"Item {match.old_item.get('model', 'Unknown')} removed",
                        match_key=match.match_key,
                        old_ref=self._get_item_reference(match.old_item)
                    ))
                else:
                    changes.append(Change(
                        change_type=ChangeType.ADDED,
                        confidence=1.0,
                        old_value=None,
                        new_value=match.new_item,
                        field_name='item',
                        description=f"Item {match.new_item.get('model', 'Unknown')} added",
                        match_key=match.match_key,
                        new_ref=self._get_item_reference(match.new_item)
                    ))
                continue

            # Detect changes between matched items
            item_changes = self._detect_item_changes(match)
            changes.extend(item_changes)

        # Detect rule and option changes
        rule_changes = self._detect_rule_changes(old_book, new_book)
        changes.extend(rule_changes)

        option_changes = self._detect_option_changes(old_book, new_book)
        changes.extend(option_changes)

        return changes

    def _detect_item_changes(self, match: MatchResult) -> List[Change]:
        """Detect changes within a matched item pair."""
        changes = []
        old_item = match.old_item
        new_item = match.new_item

        # Price changes
        old_price = self._extract_price(old_item)
        new_price = self._extract_price(new_item)

        if old_price != new_price:
            # Calculate percentage change
            if old_price and old_price > 0:
                percent_change = ((new_price - old_price) / old_price) * 100
                description = f"Price changed {percent_change:+.1f}%: ${old_price:.2f} → ${new_price:.2f}"
            else:
                description = f"Price changed: ${old_price:.2f} → ${new_price:.2f}"

            changes.append(Change(
                change_type=ChangeType.PRICE_CHANGED,
                confidence=match.confidence,
                old_value=old_price,
                new_value=new_price,
                field_name='price',
                description=description,
                match_key=match.match_key,
                old_ref=self._get_item_reference(old_item),
                new_ref=self._get_item_reference(new_item),
                metadata={'percent_change': percent_change if old_price else None}
            ))

        # Description changes
        old_desc = str(old_item.get('description', '')).strip()
        new_desc = str(new_item.get('description', '')).strip()

        if old_desc != new_desc and old_desc and new_desc:
            changes.append(Change(
                change_type=ChangeType.DESCRIPTION_CHANGED,
                confidence=match.confidence,
                old_value=old_desc,
                new_value=new_desc,
                field_name='description',
                description=f"Description changed",
                match_key=match.match_key,
                old_ref=self._get_item_reference(old_item),
                new_ref=self._get_item_reference(new_item)
            ))

        # Model number changes (renames)
        old_model = str(old_item.get('model', '')).strip()
        new_model = str(new_item.get('model', '')).strip()

        if old_model != new_model and match.match_method == 'fuzzy':
            changes.append(Change(
                change_type=ChangeType.RENAMED,
                confidence=match.confidence,
                old_value=old_model,
                new_value=new_model,
                field_name='model',
                description=f"Model renamed: {old_model} → {new_model}",
                match_key=match.match_key,
                old_ref=self._get_item_reference(old_item),
                new_ref=self._get_item_reference(new_item),
                metadata={'fuzzy_score': match.fuzzy_score}
            ))

        return changes

    def _detect_rule_changes(self, old_book: Dict, new_book: Dict) -> List[Change]:
        """Detect changes in pricing rules."""
        changes = []

        old_rules = self._extract_rules(old_book)
        new_rules = self._extract_rules(new_book)

        # Create lookup by rule signature
        old_rule_lookup = {self._get_rule_signature(rule): rule for rule in old_rules}
        new_rule_lookup = {self._get_rule_signature(rule): rule for rule in new_rules}

        # Find rule changes
        all_signatures = set(old_rule_lookup.keys()) | set(new_rule_lookup.keys())

        for signature in all_signatures:
            old_rule = old_rule_lookup.get(signature)
            new_rule = new_rule_lookup.get(signature)

            if not old_rule and new_rule:
                # Rule added
                changes.append(Change(
                    change_type=ChangeType.RULE_CHANGED,
                    confidence=1.0,
                    old_value=None,
                    new_value=new_rule,
                    field_name='rules',
                    description=f"Rule added: {self._describe_rule(new_rule)}",
                    match_key=signature
                ))
            elif old_rule and not new_rule:
                # Rule removed
                changes.append(Change(
                    change_type=ChangeType.RULE_CHANGED,
                    confidence=1.0,
                    old_value=old_rule,
                    new_value=None,
                    field_name='rules',
                    description=f"Rule removed: {self._describe_rule(old_rule)}",
                    match_key=signature
                ))
            elif old_rule and new_rule:
                # Check for rule modifications
                if self._rules_differ(old_rule, new_rule):
                    changes.append(Change(
                        change_type=ChangeType.RULE_CHANGED,
                        confidence=1.0,
                        old_value=old_rule,
                        new_value=new_rule,
                        field_name='rules',
                        description=f"Rule modified: {self._describe_rule(new_rule)}",
                        match_key=signature
                    ))

        return changes

    def _detect_option_changes(self, old_book: Dict, new_book: Dict) -> List[Change]:
        """Detect changes in options and additions."""
        changes = []

        old_options = self._extract_options(old_book)
        new_options = self._extract_options(new_book)

        # Create lookup by option code
        old_option_lookup = {option.get('option_code', option.get('code')): option for option in old_options}
        new_option_lookup = {option.get('option_code', option.get('code')): option for option in new_options}

        all_codes = set(old_option_lookup.keys()) | set(new_option_lookup.keys())

        for code in all_codes:
            if not code:  # Skip empty codes
                continue

            old_option = old_option_lookup.get(code)
            new_option = new_option_lookup.get(code)

            if not old_option and new_option:
                # Option added
                changes.append(Change(
                    change_type=ChangeType.OPTION_ADDED,
                    confidence=1.0,
                    old_value=None,
                    new_value=new_option,
                    field_name='options',
                    description=f"Option {code} added: {new_option.get('option_name', 'Unknown')}",
                    match_key=code
                ))
            elif old_option and not new_option:
                # Option removed
                changes.append(Change(
                    change_type=ChangeType.OPTION_REMOVED,
                    confidence=1.0,
                    old_value=old_option,
                    new_value=None,
                    field_name='options',
                    description=f"Option {code} removed: {old_option.get('option_name', 'Unknown')}",
                    match_key=code
                ))
            elif old_option and new_option:
                # Check for amount changes
                old_amount = self._extract_option_amount(old_option)
                new_amount = self._extract_option_amount(new_option)

                if old_amount != new_amount:
                    changes.append(Change(
                        change_type=ChangeType.OPTION_AMOUNT_CHANGED,
                        confidence=1.0,
                        old_value=old_amount,
                        new_value=new_amount,
                        field_name='option_amount',
                        description=f"Option {code} amount changed: ${old_amount:.2f} → ${new_amount:.2f}",
                        match_key=code,
                        metadata={'option_name': new_option.get('option_name', 'Unknown')}
                    ))

        return changes

    def _extract_price(self, item: Dict) -> float:
        """Extract numeric price from item."""
        for field in ['base_price', 'price', 'list_price', 'net_price']:
            value = item.get(field)
            if value is not None:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    continue
        return 0.0

    def _extract_rules(self, book: Dict) -> List[Dict]:
        """Extract rules from book data."""
        rules = []

        raw_rules = (
            book.get('price_rules', []) or
            book.get('rules', []) or
            []
        )

        for rule in raw_rules:
            if hasattr(rule, 'value') and isinstance(rule.value, dict):
                rules.append(rule.value)
            elif isinstance(rule, dict):
                rules.append(rule)

        return rules

    def _extract_options(self, book: Dict) -> List[Dict]:
        """Extract options from book data."""
        options = []

        raw_options = (
            book.get('hinge_additions', []) or
            book.get('options', []) or
            book.get('additions', []) or
            []
        )

        for option in raw_options:
            if hasattr(option, 'value') and isinstance(option.value, dict):
                options.append(option.value)
            elif isinstance(option, dict):
                options.append(option)

        return options

    def _get_rule_signature(self, rule: Dict) -> str:
        """Get unique signature for a rule."""
        rule_type = rule.get('rule_type', 'unknown')

        if rule_type == 'price_mapping':
            source = rule.get('source_finish', '')
            target = rule.get('target_finish', '')
            return f"mapping:{source}:{target}"
        elif rule_type == 'percentage_markup':
            percentage = rule.get('percentage', 0)
            base = rule.get('base_finish', '')
            return f"percentage:{percentage}:{base}"
        else:
            description = rule.get('description', '')
            return f"rule:{rule_type}:{description[:50]}"

    def _describe_rule(self, rule: Dict) -> str:
        """Get human-readable description of rule."""
        return rule.get('description', str(rule)[:100])

    def _rules_differ(self, old_rule: Dict, new_rule: Dict) -> bool:
        """Check if two rules are different."""
        # Compare key fields
        key_fields = ['rule_type', 'percentage', 'source_finish', 'target_finish', 'description']

        for field in key_fields:
            if old_rule.get(field) != new_rule.get(field):
                return True

        return False

    def _extract_option_amount(self, option: Dict) -> float:
        """Extract numeric amount from option."""
        for field in ['adder_value', 'amount', 'price', 'cost']:
            value = option.get(field)
            if value is not None:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    continue
        return 0.0

    def _get_item_reference(self, item: Dict) -> str:
        """Get reference string for item."""
        model = item.get('model', item.get('sku', 'Unknown'))
        finish = item.get('finish', item.get('finish_code', ''))
        if finish:
            return f"{model}({finish})"
        return model

    def _generate_summary(self, matches: List[MatchResult], changes: List[Change]) -> Dict[str, int]:
        """Generate summary statistics."""
        summary = {
            'total_matches': len(matches),
            'exact_matches': len([m for m in matches if m.confidence_level == MatchConfidence.EXACT]),
            'fuzzy_matches': len([m for m in matches if m.match_method == 'fuzzy']),
            'items_added': len([c for c in changes if c.change_type == ChangeType.ADDED]),
            'items_removed': len([c for c in changes if c.change_type == ChangeType.REMOVED]),
            'price_changes': len([c for c in changes if c.change_type == ChangeType.PRICE_CHANGED]),
            'renames': len([c for c in changes if c.change_type == ChangeType.RENAMED]),
            'rule_changes': len([c for c in changes if c.change_type == ChangeType.RULE_CHANGED]),
            'option_changes': len([c for c in changes if c.change_type.value.startswith('option_')]),
            'total_changes': len(changes),
            'needs_review': len([m for m in matches if m.confidence < self.review_threshold])
        }

        return summary