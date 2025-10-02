# Parser Method Name Fix

## Issue
Both Hager and SELECT parsers had a typo where they called `_extract_text_content()` but the actual method is named `_combine_text_content()`.

## Error
```
AttributeError: 'HagerParser' object has no attribute '_extract_text_content'
```

## Files Fixed
1. `parsers/hager/parser.py` line 492
2. `parsers/select/parser.py` line 372

## Changes Made
Changed:
```python
text = self._extract_text_content()
```

To:
```python
text = self._combine_text_content()
```

## Status
✅ Fixed - Both parsers should now work correctly
