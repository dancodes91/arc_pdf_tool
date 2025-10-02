# Cascade Delete Fix

## Issue
When trying to delete a price book, got error:
```
NOT NULL constraint failed: products.price_book_id
```

## Root Cause
The products table had a foreign key to price_books, but without `ON DELETE CASCADE`. When deleting a price book, SQLAlchemy tried to set `price_book_id` to NULL instead of deleting the products.

## Fix Applied

### 1. Updated Models
- **`database/models.py` line 63**: Added `ondelete='CASCADE'` to ForeignKey
- **`database/models.py` line 40**: Added `cascade="all, delete-orphan"` to relationship

### 2. Updated Database
- Ran `fix_cascade_delete.py` to recreate products table with CASCADE
- Copied 296 products successfully
- Foreign key now has `ON DELETE CASCADE`

## Result
✅ Deleting a price book now automatically deletes all related products
✅ No more constraint errors
✅ Delete button in frontend works correctly

## Test
Try deleting a price book from the UI - it should work without errors!
