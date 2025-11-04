# Hager Price Matrix Format

## Discovery

Analysis of Hager PDF revealed that most products are in **price matrix format** (not simple row tables).

**Example from Page 50:**

```
BB1191                              (Model number)
Brass or Stainless
Full Mortise
Standard Weight
Ball Bearing
Specify if all wood screws are required.

Description  Size              Finish  List    Qty.  Qty.
             3-1/2" x 3-1/2"   US3     117.96  2     100
                               US4     109.86
                               US10    109.86
                               US10B   117.96
                               US15    117.96
                               US26    117.96
                               US26D   115.48
                               US32    163.18
                               US32D   144.19

             4" x 3-1/2"       US3     178.57  3     48
                               US4     136.95
                               ...
```

## Structure

1. **Model Header**: `BB1191`, `BB1100`, etc. (at top of matrix)
2. **Specifications**: Text describing product features
3. **Size Column**: Groups of finishes per size
4. **Finish Column**: US3, US4, US10, etc.
5. **Price Column**: Dollar amounts (may not have $ symbol in matrix)
6. **Quantity Columns**: Box qty, case qty

## Key Characteristics

- **One model** → **Multiple size/finish combinations** → **Hundreds of SKUs**
- Example: `BB1191` × 4 sizes × 9 finishes = **36 products**
- **No $ symbol** in many price cells (just numbers)
- Size is **repeated for groups** of finishes
- Finishes are **listed vertically** under each size

## Parsing Strategy

1. **Detect matrix pages**: Look for pattern of model + repeated finish codes
2. **Extract model number**: Top of page or table title
3. **Parse size groups**: Identify where size changes
4. **Map finish→price**: For each size, pair finish codes with prices
5. **Generate SKUs**: Combine `model-size-finish` into SKU

## SKU Generation

```python
sku = f"{model}-{size_code}-{finish}"
# Example: BB1191-3.5x3.5-US3
```

## Expected Product Count

Current hypothesis for 800-1000+ products:
- ~50-100 unique model numbers (BB1191, BB1100, BB1279, etc.)
- Each model has 4-10 size options
- Each size has 8-15 finish options
- **50 models × 6 sizes × 10 finishes = ~3,000 SKUs!**

But Hager likely deduplicates to ~800-1000 actual catalog items.

## Pages with Price Matrices

Based on analysis:
- Pages with model codes but NO prices in text: likely matrix headers
- Pages 50-300: Main product catalog (matrices)
- Pages 11-40: Accessories (simple tables - already parsed)

## Next Steps

1. Create `_parse_price_matrix()` method
2. Detect matrix pattern: model header + finish list + price column
3. Extract all size/finish/price combinations
4. Generate individual product records for each SKU
5. Test on page 50 first, then expand to all matrix pages
