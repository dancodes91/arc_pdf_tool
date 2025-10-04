# SELECT PDF - Table Extraction Findings

## Table Types Encountered

### Type 1: Pricing Tables (Pages 7, 15-18)
- Structure: Model column + length-based price columns
- Header: Merged cells with lengths (79", 83"/85", 95", 120")
- Data: Integer prices or "-" for unavailable
- Challenges: Merged headers, multi-line cells

### Type 2: Cross-Reference (Page 12)
- Structure: 35 rows x 8 columns
- Maps SELECT models to 7 competitor brands
- Text-heavy cells with multiple part numbers

### Type 3: Specification Tables (Pages 8-11)
- Dimensional data with imperial/metric
- Clearance requirements
- Technical diagrams adjacent

## Edge Cases

1. **Merged Headers**: "83" / 85"" in single cell
   - Solution: Split on "/" to get both lengths

2. **Multi-line Cells**: Length + dimension in header
   - Solution: Extract only numeric length value

3. **Unavailable Combinations**: "-" in price cells
   - Solution: Skip (don't create product)

4. **Comma in Prices**: "1,380" 
   - Solution: Remove comma before float conversion

## Proposed Parsing Rules

Rule 1: Detect pricing table by "Model" header or SL pattern
Rule 2: Extract lengths from headers using regex: (\d+)"
Rule 3: For each row, extract model components: (SL\d+)\s*([A-Z]{2})?\s*([A-Z]+\d*)?
Rule 4: Create product for each non-dash price cell
Rule 5: Generate SKU: {base}_{finish}_{duty}_{length}
