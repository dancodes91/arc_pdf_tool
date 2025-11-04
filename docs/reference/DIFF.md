# Diff Engine v2 Guide

## Overview

Diff Engine v2 detects changes between price book versions using exact matching, fuzzy rename detection, and confidence scoring.

## Quick Start

```python
from core.diff_engine_v2 import DiffEngineV2

# Initialize
diff_engine = DiffEngineV2(config={
    'enable_fuzzy_matching': True,
    'fuzzy_threshold': 70
})

# Create diff
diff_result = diff_engine.create_diff(old_book_data, new_book_data)

# Inspect changes
for change in diff_result.changes:
    print(f"{change.change_type}: {change.description}")
```

## Change Detection

### Change Types
- **ADDED** - New products
- **REMOVED** - Discontinued products
- **PRICE_CHANGED** - Price updates
- **RENAMED** - SKU/model changes (fuzzy matched)
- **OPTION_ADDED** / **OPTION_REMOVED** - Option changes
- **RULE_CHANGED** - Pricing rule modifications

### Matching Strategies

**Phase 1: Exact Matching**
- Creates normalized match keys: `manufacturer#family#model#size#finish`
- Handles minor variations (spaces, dashes, case)

**Phase 2: Fuzzy Matching**
- Uses RapidFuzz for similarity scoring
- Threshold: 70% (configurable)
- Validates: same manufacturer/family, 20% common characters
- Detects renames (CTW-4 → CTW4)

**Phase 3: Unmatched Items**
- Remaining old items = REMOVED
- Remaining new items = ADDED

## Confidence Scoring

```python
# Match confidence levels
MatchConfidence.EXACT       # 0.98+  - Identical keys
MatchConfidence.HIGH        # 0.80+  - Strong fuzzy match
MatchConfidence.MEDIUM      # 0.60+  - Moderate fuzzy match
MatchConfidence.LOW         # 0.40+  - Weak fuzzy match
MatchConfidence.VERY_LOW    # <0.40  - Requires review
```

Items below review threshold (0.6) go to review queue.

## Usage Examples

### Compare Two Price Books

```python
# Load parsed data
old_book = {
    'id': 'hager_2024',
    'products': [...],
    'options': [...],
    'rules': [...]
}

new_book = {
    'id': 'hager_2025',
    'products': [...],
    'options': [...],
    'rules': [...]
}

# Create diff
diff_result = diff_engine.create_diff(old_book, new_book)

# Summary
print(f"Exact matches: {diff_result.summary['exact_matches']}")
print(f"Fuzzy matches: {diff_result.summary['fuzzy_matches']}")
print(f"Additions: {diff_result.summary['additions']}")
print(f"Removals: {diff_result.summary['removals']}")
print(f"Price changes: {diff_result.summary['price_changes']}")
```

### Export Diff Report

```python
import json

# Export to JSON
with open('diff_report.json', 'w') as f:
    json.dump({
        'old_book': diff_result.old_book_id,
        'new_book': diff_result.new_book_id,
        'timestamp': diff_result.timestamp.isoformat(),
        'changes': [
            {
                'type': change.change_type.value,
                'confidence': change.confidence,
                'old_value': change.old_value,
                'new_value': change.new_value,
                'description': change.description
            }
            for change in diff_result.changes
        ],
        'summary': diff_result.summary
    }, f, indent=2)
```

### Review Queue

```python
# Get low-confidence matches needing human review
review_items = diff_result.review_queue

for item in review_items:
    print(f"Confidence: {item.confidence:.2f}")
    print(f"Old: {item.old_item.get('model')}")
    print(f"New: {item.new_item.get('model')}")
    print(f"Reason: {', '.join(item.match_reasons)}")
```

## Configuration

```python
config = {
    # Matching thresholds
    'exact_match_threshold': 0.98,      # Exact match cutoff
    'high_confidence_threshold': 0.8,   # High confidence
    'medium_confidence_threshold': 0.6, # Medium confidence
    'low_confidence_threshold': 0.4,    # Low confidence
    'review_threshold': 0.6,            # Below this = review queue

    # Fuzzy matching
    'enable_fuzzy_matching': True,
    'fuzzy_threshold': 70,              # Minimum similarity %

    # Metadata
    'metadata': {
        'analyst': 'John Doe',
        'notes': 'Q1 2025 update'
    }
}

diff_engine = DiffEngineV2(config=config)
```

## CLI Usage

```bash
# Compare two price books from database
uv run python scripts/compare_price_books.py \
  --old-id 123 \
  --new-id 456 \
  --output diff_report.json

# Dry run mode
uv run python scripts/compare_price_books.py \
  --old-id 123 \
  --new-id 456 \
  --dry-run
```

## Testing

### Synthetic Diff Test

```python
# Create synthetic test data
old_products = [
    {'model': 'BB1100', 'price': 125.00},
    {'model': 'CTW-4', 'price': 45.50}
]

new_products = [
    {'model': 'BB1100', 'price': 128.00},  # Price change
    {'model': 'CTW4', 'price': 47.00}       # Renamed
]

# Run diff
diff_result = diff_engine.create_diff(
    {'id': 'test_old', 'products': old_products},
    {'id': 'test_new', 'products': new_products}
)

# Assertions
assert len([c for c in diff_result.changes if c.change_type == 'price_changed']) == 2
assert len([m for m in diff_result.matches if m.match_method == 'fuzzy']) == 1
```

## Performance

- **Small diffs** (<1000 products): <1 second
- **Medium diffs** (1000-10000 products): 1-10 seconds
- **Large diffs** (10000+ products): 10-60 seconds

Fuzzy matching is the slowest phase. Disable for speed:
```python
config = {'enable_fuzzy_matching': False}
```

## Best Practices

1. **Normalize data first** - Ensure consistent product structure
2. **Set appropriate thresholds** - Balance precision vs recall
3. **Review low-confidence matches** - Human verification for <0.6
4. **Track metadata** - Record analyst, date, notes
5. **Export audit trail** - Save diffs for compliance
6. **Test with synthetic data** - Validate rename detection

## See Also

- [PARSERS.md](PARSERS.md) - Parse price books
- [BASEROW.md](BASEROW.md) - Sync changes to Baserow
- [OPERATIONS.md](OPERATIONS.md) - Production diff workflows