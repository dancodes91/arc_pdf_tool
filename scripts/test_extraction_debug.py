#!/usr/bin/env python3
"""
Debug extraction step by step.
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.universal.pattern_extractor import SmartPatternExtractor

# Create test DataFrame
df = pd.DataFrame({
    0: ['Model', 'LGO83 CL', 'LGO95 CL'],
    1: ['83"', '255', '-'],
    2: ['95"', '-', '285']
})

print("Test DataFrame:")
print(df)
print()

extractor = SmartPatternExtractor()

# Test each row
for idx, row in df.iterrows():
    print(f"\n--- Row {idx} ---")
    row_text = " ".join(str(cell) for cell in row if pd.notna(cell))
    print(f"Row text: '{row_text}'")

    sku = extractor._extract_sku(row_text)
    price = extractor._extract_price(row_text)

    print(f"  SKU: {sku}")
    print(f"  Price: {price}")
    print(f"  Passes check: {bool(sku and price and price > 0)}")
