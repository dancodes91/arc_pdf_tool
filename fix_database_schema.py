"""
Fix database schema to allow NULL product_id in product_options table.
This script can be run while Flask is running.
"""
import sqlite3
import sys

def fix_schema():
    """Alter the product_options table to allow NULL product_id."""
    try:
        # Connect to database
        conn = sqlite3.connect('price_books.db')
        cursor = conn.cursor()

        # Check current schema
        cursor.execute("PRAGMA table_info(product_options)")
        columns = cursor.fetchall()

        print("Current product_options schema:")
        for col in columns:
            print(f"  {col[1]}: {col[2]} (nullable: {col[3] == 0})")

        # Check if product_id is already nullable
        product_id_col = [c for c in columns if c[1] == 'product_id'][0]
        if product_id_col[3] == 0:  # notnull = 0 means nullable
            print("\n[OK] product_id is already nullable!")
            conn.close()
            return True

        print("\n[FIXING] product_id is NOT NULL, need to alter table...")

        # SQLite doesn't support ALTER COLUMN directly, so we need to:
        # 1. Rename old table
        # 2. Create new table with correct schema
        # 3. Copy data
        # 4. Drop old table

        # Step 1: Rename old table
        cursor.execute("ALTER TABLE product_options RENAME TO product_options_old")
        print("  - Renamed old table")

        # Step 2: Create new table with nullable product_id
        cursor.execute("""
            CREATE TABLE product_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                option_type VARCHAR(50) NOT NULL,
                option_code VARCHAR(50),
                option_name VARCHAR(255),
                adder_type VARCHAR(20),
                adder_value DECIMAL(10, 2),
                requires_option VARCHAR(50),
                excludes_option VARCHAR(50),
                is_required BOOLEAN DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                created_at DATETIME,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """)
        print("  - Created new table with nullable product_id")

        # Step 3: Copy data from old table
        cursor.execute("""
            INSERT INTO product_options
            SELECT * FROM product_options_old
        """)
        rows_copied = cursor.rowcount
        print(f"  - Copied {rows_copied} rows")

        # Step 4: Drop old table
        cursor.execute("DROP TABLE product_options_old")
        print("  - Dropped old table")

        # Commit changes
        conn.commit()
        print("\n[SUCCESS] Database schema fixed!")

        # Verify new schema
        cursor.execute("PRAGMA table_info(product_options)")
        columns = cursor.fetchall()
        product_id_col = [c for c in columns if c[1] == 'product_id'][0]

        if product_id_col[3] == 0:
            print("[VERIFIED] product_id is now nullable")
        else:
            print("[ERROR] product_id is still NOT NULL!")
            conn.close()
            return False

        conn.close()
        return True

    except Exception as e:
        print(f"\n[ERROR] Failed to fix schema: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == '__main__':
    success = fix_schema()
    sys.exit(0 if success else 1)
