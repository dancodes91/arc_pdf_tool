"""
Fix cascade delete by recreating foreign key with ON DELETE CASCADE.
"""
import sqlite3

def fix_cascade_delete():
    """Add ON DELETE CASCADE to products.price_book_id foreign key."""
    conn = sqlite3.connect('price_books.db')
    cursor = conn.cursor()

    print("Fixing cascade delete for products table...")

    # SQLite doesn't support ALTER TABLE for foreign keys
    # We need to recreate the products table

    # Step 1: Create new products table with CASCADE (match current structure)
    cursor.execute("""
        CREATE TABLE products_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_id INTEGER,
            price_book_id INTEGER NOT NULL,
            sku VARCHAR(100) NOT NULL,
            model VARCHAR(100),
            description TEXT,
            base_price DECIMAL(10, 2),
            effective_date DATE,
            retired_date DATE,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME,
            updated_at DATETIME,
            FOREIGN KEY(family_id) REFERENCES product_families(id),
            FOREIGN KEY(price_book_id) REFERENCES price_books(id) ON DELETE CASCADE
        )
    """)
    print("  - Created new products table with CASCADE")

    # Step 2: Copy data (only columns that exist in both tables)
    cursor.execute("""
        INSERT INTO products_new (
            id, family_id, price_book_id, sku, model, description,
            base_price, effective_date, retired_date, is_active,
            created_at, updated_at
        )
        SELECT
            id, family_id, price_book_id, sku, model, description,
            base_price, effective_date, retired_date, is_active,
            created_at, updated_at
        FROM products
    """)
    print(f"  - Copied {cursor.rowcount} products")

    # Step 3: Drop old table
    cursor.execute("DROP TABLE products")
    print("  - Dropped old products table")

    # Step 4: Rename new table
    cursor.execute("ALTER TABLE products_new RENAME TO products")
    print("  - Renamed new table to products")

    conn.commit()
    print("\n✅ Cascade delete fixed successfully!")
    conn.close()

if __name__ == '__main__':
    fix_cascade_delete()
