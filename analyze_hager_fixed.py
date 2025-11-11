"""Analyze fixed Hager parser output."""
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

df = pd.read_csv(r'test_exports_hager_fixed\hager_products_20251111_135346.csv')

print('='*70)
print('FIXED HAGER PARSER RESULTS')
print('='*70)

print(f'\n✓ Total products: {len(df)}')
print(f'✓ Duplicates: {df.duplicated(subset=["sku"]).sum()}')
print(f'✓ Unique SKUs: {df["sku"].nunique()}')

print(f'\nPrice Statistics:')
print(f'  - Min: ${df["base_price"].min():.2f}')
print(f'  - Max: ${df["base_price"].max():.2f}')
print(f'  - Average: ${df["base_price"].mean():.2f}')

print(f'\nTop 10 Product Series:')
print(df['series'].value_counts().head(10).to_string())

# Check for malformed SKUs
print(f'\n\nSKU Format Check:')
bad_pattern = df[df['sku'].str.contains(r'([A-Z]{2}\d+)\1', regex=True, na=False)]
print(f'  - Malformed SKUs (BB1100BB1100 pattern): {len(bad_pattern)}')

if len(bad_pattern) > 0:
    print(f'\n  Examples of malformed SKUs:')
    print(bad_pattern[['sku', 'model', 'series']].head(5).to_string(index=False))

print(f'\n\nFirst 20 Products:')
print(df[['sku', 'model', 'base_price', 'series']].head(20).to_string(index=False))

# Compare with old results
print(f'\n\n' + '='*70)
print('COMPARISON WITH OLD PARSER')
print('='*70)

try:
    df_old = pd.read_csv(r'test_exports_hager\hager_products_20251111_125511.csv')
    print(f'\nOLD Parser:')
    print(f'  - Total products: {len(df_old)}')
    print(f'  - Duplicates: {df_old.duplicated(subset=["sku"]).sum()}')
    print(f'  - Unique SKUs: {df_old["sku"].nunique()}')

    print(f'\nNEW Parser (Fixed):')
    print(f'  - Total products: {len(df)}')
    print(f'  - Duplicates: {df.duplicated(subset=["sku"]).sum()}')
    print(f'  - Unique SKUs: {df["sku"].nunique()}')

    print(f'\nImprovement:')
    print(f'  - Duplicates eliminated: {df_old.duplicated(subset=["sku"]).sum() - df.duplicated(subset=["sku"]).sum()}')
    print(f'  - Products reduced by: {len(df_old) - len(df)} (duplicate removal)')

except FileNotFoundError:
    print('\n(Old parser results not found for comparison)')

print('\n' + '='*70)
print('✓ PARSER VALIDATION COMPLETE')
print('='*70)
