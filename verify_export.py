"""Verify SELECT parser export quality."""
import pandas as pd
import json

# Load results
with open(r'exports_final\select hinges_parsing_results_20251025_160818.json') as f:
    results = json.load(f)

print('=== Parsing Results ===')
print(f'Effective Date: {results.get("effective_date", {}).get("value")}')
print(f'Total Products: {len(results.get("products", []))}')
print(f'Manufacturer: {results.get("manufacturer")}')

# Load products CSV
df = pd.read_csv(r'exports_final\select hinges_products_20251025_160818.csv')

print(f'\n=== Data Quality Checks ===')
print(f'Total rows in CSV: {len(df)}')

# Check for duplicates
duplicates = df[df.duplicated(subset=['sku'], keep=False)]
print(f'Duplicate SKUs: {len(duplicates)}')
if len(duplicates) > 0:
    print('\nDuplicates found:')
    print(duplicates[['sku', 'description', 'base_price']].to_string(index=False))

# Check for suspicious prices
suspicious = df[(df['base_price'] < 10) | (df['base_price'] > 5000)]
print(f'\nSuspicious prices (<$10 or >$5000): {len(suspicious)}')
if len(suspicious) > 0:
    print(suspicious[['sku', 'description', 'base_price']].to_string(index=False))

# Check for garbage patterns in descriptions
garbage_patterns = ['800', 'Select-Hinges.com', 'February', 'April', 'Net 30', 'Shipping']
garbage_rows = df[df['description'].str.contains('|'.join(garbage_patterns), case=False, na=False)]
print(f'\nGarbage data rows: {len(garbage_rows)}')
if len(garbage_rows) > 0:
    print(garbage_rows[['sku', 'description']].to_string(index=False))

print('\n=== Sample Products by Series ===')
for series in df['series'].unique()[:5]:
    print(f'\n{series} products:')
    series_df = df[df['series'] == series].head(5)
    print(series_df[['sku', 'description', 'base_price']].to_string(index=False))
