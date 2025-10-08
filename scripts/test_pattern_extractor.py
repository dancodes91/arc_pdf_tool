#!/usr/bin/env python3
"""
Test pattern extractor directly on DataFrame.
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.universal.pattern_extractor import SmartPatternExtractor

# Create test DataFrame matching our debug output
df = pd.DataFrame({
    0: ['Model', 'LGO83 CL', 'LGO95 CL', 'LGO83 BR', 'LGO95 BR'],
    1: ['83"', '255', '-', '266', '-'],
    2: ['95"', '-', '285', '-', '296']
})

print("Test DataFrame:")
print(df)
print()

extractor = SmartPatternExtractor()
products = extractor.extract_from_table(df, page_num=5)

print(f"\nExtracted {len(products)} products:")
for i, p in enumerate(products, 1):
    print(f"  {i}. SKU: {p.get('sku')}, Price: ${p.get('base_price')}, Confidence: {p.get('confidence'):.2%}")
