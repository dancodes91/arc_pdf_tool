"""
Comprehensive tests for Diff Engine v2.

Tests matching algorithms, rename detection, confidence scoring,
and synthetic delta scenarios for robust diff functionality.
"""
import pytest
from datetime import datetime
from unittest.mock import patch
import copy

# Import the components we're testing
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.diff_engine_v2 import (
    DiffEngineV2, ChangeType, MatchConfidence, DiffResult, MatchResult, Change
)


class TestDiffEngineV2:
    """Test the Diff Engine v2 functionality."""

    def setup_method(self):
        self.diff_engine = DiffEngineV2({
            'exact_match_threshold': 0.98,
            'high_confidence_threshold': 0.8,
            'medium_confidence_threshold': 0.6,
            'review_threshold': 0.6,
            'enable_fuzzy_matching': True,
            'fuzzy_threshold': 70
        })

    def test_exact_matching(self):
        """Test exact matching of identical items."""
        old_book = self._create_test_book("old", [
            {'model': 'BB1100US3', 'manufacturer': 'hager', 'family': 'bb1100', 'price': 125.50},
            {'model': 'BB1101US4', 'manufacturer': 'hager', 'family': 'bb1100', 'price': 135.75}
        ])

        new_book = self._create_test_book("new", [
            {'model': 'BB1100US3', 'manufacturer': 'hager', 'family': 'bb1100', 'price': 130.50},  # Price changed
            {'model': 'BB1101US4', 'manufacturer': 'hager', 'family': 'bb1100', 'price': 135.75}   # No change
        ])

        diff_result = self.diff_engine.create_diff(old_book, new_book)

        # Should have 2 exact matches
        exact_matches = [m for m in diff_result.matches if m.confidence_level == MatchConfidence.EXACT]
        assert len(exact_matches) == 2

        # Should detect 1 price change
        price_changes = [c for c in diff_result.changes if c.change_type == ChangeType.PRICE_CHANGED]
        assert len(price_changes) == 1
        assert price_changes[0].old_value == 125.50
        assert price_changes[0].new_value == 130.50

    @patch('core.diff_engine_v2.RAPIDFUZZ_AVAILABLE', True)
    def test_fuzzy_matching_renames(self):
        """Test fuzzy matching for renamed items."""
        old_book = self._create_test_book("old", [
            {'model': 'CTW-4', 'manufacturer': 'hager', 'family': 'ctw', 'price': 45.50},
            {'model': 'BB1100-1', 'manufacturer': 'hager', 'family': 'bb1100', 'price': 125.50}
        ])

        new_book = self._create_test_book("new", [
            {'model': 'CTW4', 'manufacturer': 'hager', 'family': 'ctw', 'price': 47.00},      # Renamed CTW-4 -> CTW4
            {'model': 'BB1100-1A', 'manufacturer': 'hager', 'family': 'bb1100', 'price': 128.00}  # Renamed BB1100-1 -> BB1100-1A
        ])

        with patch('core.diff_engine_v2.process') as mock_process:
            # Mock fuzzy matching results
            mock_process.extract.side_effect = [
                [('CTW4 HAGER CTW', 85, 0)],          # CTW-4 matches CTW4 with 85% similarity
                [('BB1100-1A HAGER BB1100', 90, 1)]   # BB1100-1 matches BB1100-1A with 90% similarity
            ]

            diff_result = self.diff_engine.create_diff(old_book, new_book)

            # Should have fuzzy matches
            fuzzy_matches = [m for m in diff_result.matches if m.match_method == 'fuzzy']
            assert len(fuzzy_matches) == 2

            # Should detect renames
            renames = [c for c in diff_result.changes if c.change_type == ChangeType.RENAMED]
            assert len(renames) == 2

            # Should detect price changes
            price_changes = [c for c in diff_result.changes if c.change_type == ChangeType.PRICE_CHANGED]
            assert len(price_changes) == 2

    def test_added_and_removed_items(self):
        """Test detection of added and removed items."""
        old_book = self._create_test_book("old", [
            {'model': 'BB1100US3', 'manufacturer': 'hager', 'family': 'bb1100', 'price': 125.50},
            {'model': 'BB1101US4', 'manufacturer': 'hager', 'family': 'bb1100', 'price': 135.75},
            {'model': 'REMOVED1', 'manufacturer': 'hager', 'family': 'old', 'price': 50.00}  # Will be removed
        ])

        new_book = self._create_test_book("new", [
            {'model': 'BB1100US3', 'manufacturer': 'hager', 'family': 'bb1100', 'price': 125.50},
            {'model': 'BB1101US4', 'manufacturer': 'hager', 'family': 'bb1100', 'price': 135.75},
            {'model': 'ADDED1', 'manufacturer': 'hager', 'family': 'new', 'price': 75.00}    # New addition
        ])

        diff_result = self.diff_engine.create_diff(old_book, new_book)

        # Should detect 1 addition and 1 removal
        additions = [c for c in diff_result.changes if c.change_type == ChangeType.ADDED]
        removals = [c for c in diff_result.changes if c.change_type == ChangeType.REMOVED]

        assert len(additions) == 1
        assert len(removals) == 1
        assert additions[0].new_value['model'] == 'ADDED1'
        assert removals[0].old_value['model'] == 'REMOVED1'

    def test_option_changes(self):
        """Test detection of option/addition changes."""
        old_book = self._create_test_book("old", [], options=[
            {'option_code': 'EPT', 'option_name': 'Electric Prep', 'adder_value': 25.00},
            {'option_code': 'CTW', 'option_name': 'Continuous Wire', 'adder_value': 35.50},
            {'option_code': 'REMOVED', 'option_name': 'Old Option', 'adder_value': 15.00}
        ])

        new_book = self._create_test_book("new", [], options=[
            {'option_code': 'EPT', 'option_name': 'Electric Prep', 'adder_value': 27.50},  # Price changed
            {'option_code': 'CTW', 'option_name': 'Continuous Wire', 'adder_value': 35.50},  # No change
            {'option_code': 'NEW_OPT', 'option_name': 'New Option', 'adder_value': 45.00}   # Added
        ])

        diff_result = self.diff_engine.create_diff(old_book, new_book)

        # Check option changes
        option_added = [c for c in diff_result.changes if c.change_type == ChangeType.OPTION_ADDED]
        option_removed = [c for c in diff_result.changes if c.change_type == ChangeType.OPTION_REMOVED]
        option_changed = [c for c in diff_result.changes if c.change_type == ChangeType.OPTION_AMOUNT_CHANGED]

        assert len(option_added) == 1
        assert len(option_removed) == 1
        assert len(option_changed) == 1

        assert option_added[0].match_key == 'NEW_OPT'
        assert option_removed[0].match_key == 'REMOVED'
        assert option_changed[0].match_key == 'EPT'
        assert option_changed[0].old_value == 25.00
        assert option_changed[0].new_value == 27.50

    def test_rule_changes(self):
        """Test detection of pricing rule changes."""
        old_book = self._create_test_book("old", [], rules=[
            {'rule_type': 'price_mapping', 'source_finish': 'US10B', 'target_finish': 'US10A', 'description': 'US10B use US10A price'},
            {'rule_type': 'percentage_markup', 'percentage': 20, 'base_finish': 'US10A', 'description': '20% above US10A price'},
            {'rule_type': 'price_mapping', 'source_finish': 'OLD_RULE', 'target_finish': 'US3', 'description': 'Old rule'}
        ])

        new_book = self._create_test_book("new", [], rules=[
            {'rule_type': 'price_mapping', 'source_finish': 'US10B', 'target_finish': 'US10A', 'description': 'US10B use US10A price'},  # No change
            {'rule_type': 'percentage_markup', 'percentage': 25, 'base_finish': 'US10A', 'description': '25% above US10A price'},  # Changed percentage
            {'rule_type': 'price_mapping', 'source_finish': 'NEW_RULE', 'target_finish': 'US4', 'description': 'New rule'}  # Added
        ])

        diff_result = self.diff_engine.create_diff(old_book, new_book)

        # Check rule changes
        rule_changes = [c for c in diff_result.changes if c.change_type == ChangeType.RULE_CHANGED]
        assert len(rule_changes) == 3  # 1 modified, 1 added, 1 removed

        # Verify specific changes
        added_rules = [c for c in rule_changes if c.old_value is None]
        removed_rules = [c for c in rule_changes if c.new_value is None]
        modified_rules = [c for c in rule_changes if c.old_value and c.new_value]

        assert len(added_rules) == 1
        assert len(removed_rules) == 1
        assert len(modified_rules) == 1

    def test_confidence_levels(self):
        """Test confidence level assignment."""
        # Test exact match confidence
        match = MatchResult(
            old_item={'model': 'test'},
            new_item={'model': 'test'},
            confidence=1.0,
            confidence_level=MatchConfidence.EXACT,
            match_key='test',
            match_method='exact_key'
        )
        assert match.confidence_level == MatchConfidence.EXACT

        # Test confidence level calculation
        assert self.diff_engine._score_to_confidence_level(0.99) == MatchConfidence.EXACT
        assert self.diff_engine._score_to_confidence_level(0.85) == MatchConfidence.HIGH
        assert self.diff_engine._score_to_confidence_level(0.65) == MatchConfidence.MEDIUM
        assert self.diff_engine._score_to_confidence_level(0.45) == MatchConfidence.LOW
        assert self.diff_engine._score_to_confidence_level(0.25) == MatchConfidence.VERY_LOW

    def test_review_queue_filtering(self):
        """Test that low confidence items go to review queue."""
        old_book = self._create_test_book("old", [
            {'model': 'EXACT1', 'manufacturer': 'hager', 'family': 'test', 'price': 100.00},
            {'model': 'FUZZY1', 'manufacturer': 'hager', 'family': 'test', 'price': 200.00}
        ])

        new_book = self._create_test_book("new", [
            {'model': 'EXACT1', 'manufacturer': 'hager', 'family': 'test', 'price': 105.00},  # Exact match
            {'model': 'FUZZY1_RENAMED', 'manufacturer': 'hager', 'family': 'test', 'price': 210.00}  # Fuzzy match
        ])

        with patch('core.diff_engine_v2.process') as mock_process:
            # Mock low confidence fuzzy match
            mock_process.extract.return_value = [('FUZZY1_RENAMED HAGER TEST', 55, 0)]  # Below review threshold

            diff_result = self.diff_engine.create_diff(old_book, new_book)

            # Review queue should contain the low confidence match
            assert len(diff_result.review_queue) == 1
            assert diff_result.review_queue[0].confidence < self.diff_engine.review_threshold

    def test_summary_generation(self):
        """Test diff summary statistics generation."""
        old_book = self._create_test_book("old", [
            {'model': 'UNCHANGED', 'manufacturer': 'hager', 'family': 'test', 'price': 100.00},
            {'model': 'PRICE_CHANGE', 'manufacturer': 'hager', 'family': 'test', 'price': 200.00},
            {'model': 'REMOVED', 'manufacturer': 'hager', 'family': 'test', 'price': 300.00}
        ])

        new_book = self._create_test_book("new", [
            {'model': 'UNCHANGED', 'manufacturer': 'hager', 'family': 'test', 'price': 100.00},
            {'model': 'PRICE_CHANGE', 'manufacturer': 'hager', 'family': 'test', 'price': 220.00},
            {'model': 'ADDED', 'manufacturer': 'hager', 'family': 'test', 'price': 400.00}
        ])

        diff_result = self.diff_engine.create_diff(old_book, new_book)

        summary = diff_result.summary
        assert summary['total_matches'] == 4  # 2 exact + 1 removed + 1 added
        assert summary['exact_matches'] == 2
        assert summary['items_added'] == 1
        assert summary['items_removed'] == 1
        assert summary['price_changes'] == 1

    def test_synthetic_price_increase_scenario(self):
        """Test synthetic scenario: +5% price increase across all items."""
        # Create original book
        original_products = [
            {'model': f'BB{1100+i}US3', 'manufacturer': 'hager', 'family': 'bb1100', 'price': 100.00 + i * 10}
            for i in range(10)
        ]
        old_book = self._create_test_book("old", original_products)

        # Create new book with 5% price increase
        updated_products = [
            {**product, 'price': product['price'] * 1.05}
            for product in original_products
        ]
        new_book = self._create_test_book("new", updated_products)

        diff_result = self.diff_engine.create_diff(old_book, new_book)

        # Should have exact matches for all items
        assert len(diff_result.matches) == 10
        exact_matches = [m for m in diff_result.matches if m.confidence_level == MatchConfidence.EXACT]
        assert len(exact_matches) == 10

        # Should detect 10 price changes
        price_changes = [c for c in diff_result.changes if c.change_type == ChangeType.PRICE_CHANGED]
        assert len(price_changes) == 10

        # All price changes should be approximately 5%
        for change in price_changes:
            old_price = change.old_value
            new_price = change.new_value
            percent_change = ((new_price - old_price) / old_price) * 100
            assert abs(percent_change - 5.0) < 0.01  # Within 0.01% tolerance

    def test_synthetic_rename_scenario(self):
        """Test synthetic scenario: systematic renames (SL11 -> SL-11)."""
        # Create original book with compact model names
        original_products = [
            {'model': f'SL{11+i}', 'manufacturer': 'select', 'family': 'sl', 'price': 150.00 + i * 5}
            for i in range(5)
        ]
        old_book = self._create_test_book("old", original_products)

        # Create new book with systematic renames (add dash)
        renamed_products = [
            {**product, 'model': f'SL-{product["model"][2:]}'}  # SL11 -> SL-11
            for product in original_products
        ]
        new_book = self._create_test_book("new", renamed_products)

        with patch('core.diff_engine_v2.process') as mock_process:
            # Mock high confidence fuzzy matches for the renames
            mock_process.extract.side_effect = [
                [('SL-11 SELECT SL', 95, 0)],
                [('SL-12 SELECT SL', 95, 0)],
                [('SL-13 SELECT SL', 95, 0)],
                [('SL-14 SELECT SL', 95, 0)],
                [('SL-15 SELECT SL', 95, 0)]
            ]

            diff_result = self.diff_engine.create_diff(old_book, new_book)

            # Should have high confidence fuzzy matches
            fuzzy_matches = [m for m in diff_result.matches if m.match_method == 'fuzzy']
            assert len(fuzzy_matches) == 5

            # Should detect 5 renames
            renames = [c for c in diff_result.changes if c.change_type == ChangeType.RENAMED]
            assert len(renames) == 5

            # All should be high confidence
            for match in fuzzy_matches:
                assert match.confidence >= 0.9

    def test_match_key_generation(self):
        """Test match key generation for different product types."""
        product1 = {
            'manufacturer': 'Hager',
            'family': 'BB1100',
            'model': 'BB1100-1',
            'size': '4.5" x 4"',
            'finish': 'US3'
        }

        match_key = self.diff_engine._create_match_key(product1)

        # Should normalize manufacturer and family to lowercase
        # Should normalize model by removing separators
        # Should create block#item format
        assert 'hager#bb1100#' in match_key
        assert 'BB11001#' in match_key  # Model normalized
        assert '#US3' in match_key      # Finish preserved

    def test_search_text_generation(self):
        """Test search text generation for fuzzy matching."""
        product = {
            'model': 'BB1100-1',
            'description': 'Ball Bearing Heavy',
            'series': 'BB1100',
            'size': '4.5" x 4"',
            'finish': 'US3'
        }

        search_text = self.diff_engine._create_search_text(product)

        # Should include all relevant fields in uppercase
        assert 'BB1100-1' in search_text
        assert 'BALL BEARING HEAVY' in search_text
        assert 'BB1100' in search_text
        assert 'US3' in search_text

    def test_empty_books_handling(self):
        """Test handling of empty price books."""
        empty_book = self._create_test_book("empty", [])
        populated_book = self._create_test_book("populated", [
            {'model': 'TEST1', 'manufacturer': 'test', 'family': 'test', 'price': 100.00}
        ])

        # Empty -> Populated (should show additions)
        diff_result = self.diff_engine.create_diff(empty_book, populated_book)
        additions = [c for c in diff_result.changes if c.change_type == ChangeType.ADDED]
        assert len(additions) == 1

        # Populated -> Empty (should show removals)
        diff_result = self.diff_engine.create_diff(populated_book, empty_book)
        removals = [c for c in diff_result.changes if c.change_type == ChangeType.REMOVED]
        assert len(removals) == 1

    def test_percentage_change_calculation(self):
        """Test percentage change calculation in price changes."""
        old_book = self._create_test_book("old", [
            {'model': 'TEST1', 'manufacturer': 'test', 'family': 'test', 'price': 100.00}
        ])

        new_book = self._create_test_book("new", [
            {'model': 'TEST1', 'manufacturer': 'test', 'family': 'test', 'price': 125.00}  # 25% increase
        ])

        diff_result = self.diff_engine.create_diff(old_book, new_book)

        price_changes = [c for c in diff_result.changes if c.change_type == ChangeType.PRICE_CHANGED]
        assert len(price_changes) == 1

        change = price_changes[0]
        assert change.old_value == 100.00
        assert change.new_value == 125.00

        # Check description contains percentage
        assert '25.0%' in change.description or '+25.0%' in change.description

    def _create_test_book(self, book_id: str, products: list, options: list = None, rules: list = None) -> dict:
        """Helper to create test book data structure."""
        return {
            'id': book_id,
            'manufacturer': 'test_manufacturer',
            'effective_date': datetime.now(),
            'products': products,
            'hinge_additions': options or [],
            'price_rules': rules or []
        }


class TestPropertyBased:
    """Property-based tests for diff engine."""

    def test_diff_symmetry_property(self):
        """Test that diff(A,B) and diff(B,A) are symmetric."""
        book_a = {
            'id': 'A',
            'products': [
                {'model': 'SHARED', 'manufacturer': 'test', 'family': 'test', 'price': 100.00},
                {'model': 'ONLY_A', 'manufacturer': 'test', 'family': 'test', 'price': 200.00}
            ],
            'hinge_additions': [],
            'price_rules': []
        }

        book_b = {
            'id': 'B',
            'products': [
                {'model': 'SHARED', 'manufacturer': 'test', 'family': 'test', 'price': 110.00},  # Price changed
                {'model': 'ONLY_B', 'manufacturer': 'test', 'family': 'test', 'price': 300.00}
            ],
            'hinge_additions': [],
            'price_rules': []
        }

        engine = DiffEngineV2()

        diff_ab = engine.create_diff(book_a, book_b)
        diff_ba = engine.create_diff(book_b, book_a)

        # Should have same number of changes (but opposite direction)
        assert len(diff_ab.changes) == len(diff_ba.changes)

        # Additions in A->B should be removals in B->A
        additions_ab = len([c for c in diff_ab.changes if c.change_type == ChangeType.ADDED])
        removals_ba = len([c for c in diff_ba.changes if c.change_type == ChangeType.REMOVED])
        assert additions_ab == removals_ba

        removals_ab = len([c for c in diff_ab.changes if c.change_type == ChangeType.REMOVED])
        additions_ba = len([c for c in diff_ba.changes if c.change_type == ChangeType.ADDED])
        assert removals_ab == additions_ba

    def test_idempotent_diff_property(self):
        """Test that diff(A,A) produces no changes."""
        book = {
            'id': 'test',
            'products': [
                {'model': 'TEST1', 'manufacturer': 'test', 'family': 'test', 'price': 100.00},
                {'model': 'TEST2', 'manufacturer': 'test', 'family': 'test', 'price': 200.00}
            ],
            'hinge_additions': [
                {'option_code': 'OPT1', 'adder_value': 25.00}
            ],
            'price_rules': [
                {'rule_type': 'price_mapping', 'source_finish': 'US3', 'target_finish': 'US4'}
            ]
        }

        engine = DiffEngineV2()
        diff_result = engine.create_diff(book, book)

        # Should have matches but no changes
        assert len(diff_result.matches) > 0
        assert len(diff_result.changes) == 0
        assert len(diff_result.review_queue) == 0

        # All matches should be exact
        for match in diff_result.matches:
            assert match.confidence_level == MatchConfidence.EXACT

    def test_transitivity_property(self):
        """Test that if A matches B and B matches C, then relationship is transitive."""
        # This is a more complex property test for fuzzy matching consistency
        # In practice, fuzzy matching isn't perfectly transitive, but should be reasonable

        book_a = {
            'id': 'A',
            'products': [{'model': 'CTW-4', 'manufacturer': 'hager', 'family': 'ctw', 'price': 45.00}],
            'hinge_additions': [],
            'price_rules': []
        }

        book_b = {
            'id': 'B',
            'products': [{'model': 'CTW4', 'manufacturer': 'hager', 'family': 'ctw', 'price': 47.00}],
            'hinge_additions': [],
            'price_rules': []
        }

        book_c = {
            'id': 'C',
            'products': [{'model': 'CTW_4', 'manufacturer': 'hager', 'family': 'ctw', 'price': 49.00}],
            'hinge_additions': [],
            'price_rules': []
        }

        engine = DiffEngineV2()

        with patch('core.diff_engine_v2.process') as mock_process:
            # Mock fuzzy matching to simulate reasonable transitivity
            mock_process.extract.side_effect = [
                [('CTW4 HAGER CTW', 85, 0)],      # A->B: CTW-4 matches CTW4 with 85%
                [('CTW_4 HAGER CTW', 80, 0)],     # B->C: CTW4 matches CTW_4 with 80%
                [('CTW_4 HAGER CTW', 75, 0)]      # A->C: CTW-4 matches CTW_4 with 75%
            ]

            diff_ab = engine.create_diff(book_a, book_b)
            diff_bc = engine.create_diff(book_b, book_c)
            diff_ac = engine.create_diff(book_a, book_c)

            # If A matches B and B matches C, then A should match C with reasonable confidence
            ab_match = diff_ab.matches[0] if diff_ab.matches else None
            bc_match = diff_bc.matches[0] if diff_bc.matches else None
            ac_match = diff_ac.matches[0] if diff_ac.matches else None

            if ab_match and bc_match and ac_match:
                # Transitive confidence should be reasonable (not necessarily perfect)
                assert ac_match.confidence >= 0.5  # Should still be a reasonable match


if __name__ == "__main__":
    pytest.main([__file__, "-v"])