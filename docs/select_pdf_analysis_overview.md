# SELECT Hinges Price Book PDF - Structure Analysis

**Document**: 2025-select-hinges-price-book.pdf
**Total Pages**: 20
**Effective Date**: April 7, 2025
**Analysis Date**: 2025-10-04

## Executive Summary

The SELECT Hinges Price Book is a compact 20-page catalog containing:
- 93 distinct product SKUs (after enhancement)
- 3 product families: Geared Continuous, Pin & Barrel, Toilet Partition
- 11 unique base models
- 7 pages with pricing data
- 14 pages with tables

### Extraction Results
- Previous: 99 products (no length differentiation)
- Enhanced: 93 products (with proper SKU generation)
- Improvement: model x finish x duty x length combinations

## Complete Page Mapping (1-20)

Page 1: Cover (April 7, 2025)
Pages 2-6: Policies & Accessories
Page 7: SL11 Geared Hinge Pricing (~40 products)
Pages 8-11: SL27, SL54, SL71, SL82 Specifications
Page 12: Part Number Interchange (Cross-reference)
Page 13: Pin & Barrel Overview
Pages 15-18: Pin & Barrel Pricing (~25 products)  
Pages 19-20: Legal & Contact

## Product Taxonomy

Model Pattern: {BASE_MODEL} {FINISH} {DUTY}
SKU Pattern: {BASE}_{FINISH}_{DUTY}_{LENGTH}

Finish Codes: CL (Clear), BR (Bronze), BK (Black)
Duty Codes: HD300, HD600, LL (Long Leaf)
Lengths: 57", 79", 83", 85", 95", 119", 120"

Examples:
- SL11_CL_HD300_83 = SL11 Clear HD300 in 83", $167
- SL300__83 = SL300 in 83" (Pin & Barrel), $1,380

## Extraction Statistics

Total Products: 93
Geared Hinges: ~65
Pin & Barrel: ~25
Toilet Partition: ~3
Price Range: $11 - $2,012

## Analysis Complete
All 20 pages processed successfully with 0 errors.
