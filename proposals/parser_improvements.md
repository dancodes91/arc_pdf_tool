# SELECT Parser Improvement Proposals

## Priority 1: SKU Expansion (IMPLEMENTED)

**Problem**: Parser extracted 99 products without length differentiation
**Solution**: Generate separate product for each model x length combination

```python
# For each pricing table row:
for length, col_idx in length_columns.items():
    price = extract_price(row[col_idx])
    if price and price != '-':
        sku = f"{base}_{finish}_{duty}_{length}".strip('_')
        products.append({
            'sku': sku,
            'base_price': price,
            'length': length
        })
```

**Result**: 93 properly structured products with length-specific SKUs

## Priority 2: Header Parsing

**Problem**: Merged cells cause column misalignment
**Solution**: Detect length values in headers

```python
def parse_header_lengths(headers):
    length_columns = {}
    for col_idx, header in enumerate(headers):
        # Handle "83" / 85"" format
        lengths = re.findall(r'(\d+)"', str(header))
        for length in lengths:
            length_columns[length] = col_idx
    return length_columns
```

## Priority 3: Price Normalization

**Problem**: Prices have commas (1,380)
**Solution**: Strip commas before conversion

```python
def normalize_price(price_str):
    price_str = price_str.replace(',', '')
    return float(price_str) if price_str != '-' else None
```

## Priority 4: Model Component Extraction

**Problem**: Model cell may contain extraneous text
**Solution**: Use precise regex with word boundaries

```python
pattern = r'(SL\d+)\s*([A-Z]{2})?\s*([A-Z]+\d*)?\s*(?:WEB|SITE|$)'
match = re.search(pattern, model_cell)
if match:
    base, finish, duty = match.groups()
```

## Priority 5: Cross-Reference Extraction

**Recommendation**: Extract page 12 as separate data structure

```python
# Store competitor mappings
cross_ref = {
    'SL11 HD300': {
        'NGP': '780-112',
        'ROTON': 'FMSLF/KFM',
        'PEMKO': '661'
    }
}
```

## Code Snippets

### Complete Table Extraction

```python
def extract_pricing_table(table, page_num):
    products = []
    headers = table[0]
    
    # Find length columns
    length_cols = parse_header_lengths(headers)
    
    for row in table[1:]:
        model_match = re.search(r'(SL\d+)\s*([A-Z]{2})?\s*([A-Z]+\d*)?', str(row[0]))
        if not model_match:
            continue
        
        base, finish, duty = model_match.groups()
        
        for length, col_idx in length_cols.items():
            price_str = str(row[col_idx])
            if price_str.strip() != '-':
                price = float(price_str.replace(',', ''))
                
                products.append({
                    'sku': f"{base}_{finish or ''}_{duty or ''}_{length}".strip('_'),
                    'model': f"{base} {finish or ''} {duty or ''}".strip(),
                    'base_price': price,
                    'length': length,
                    'page': page_num
                })
    
    return products
```
