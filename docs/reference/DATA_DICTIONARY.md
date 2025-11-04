# Data Dictionary

Complete data model documentation for Arc PDF Tool database schema.

---

## Entity Relationship Diagram (ERD)

```
┌─────────────────┐
│  Manufacturer   │
├─────────────────┤
│ id (PK)         │
│ name            │
│ code (UK)       │
│ created_at      │
└────────┬────────┘
         │
         │ 1:N
         │
    ┌────▼─────────────────────────┐
    │                              │
┌───▼────────────┐     ┌───────────▼────────┐     ┌────────────────┐
│  PriceBook     │     │ ProductFamily      │     │    Finish      │
├────────────────┤     ├────────────────────┤     ├────────────────┤
│ id (PK)        │     │ id (PK)            │     │ id (PK)        │
│ manufacturer_id│     │ manufacturer_id (FK│     │ manufacturer_id│
│ edition        │     │ name               │     │ code           │
│ effective_date │     │ category           │     │ name           │
│ upload_date    │     │ description        │     │ bhma_code      │
│ file_path      │     │ created_at         │     │ description    │
│ file_size      │     └────────┬───────────┘     └────────────────┘
│ status         │              │
│ parsing_notes  │              │ 1:N
└────────┬───────┘              │
         │                      │
         │ 1:N                  │
         │                      │
    ┌────▼──────────────────────▼───┐
    │         Product               │
    ├───────────────────────────────┤
    │ id (PK)                       │
    │ family_id (FK)                │
    │ price_book_id (FK, CASCADE)   │◄─── ON DELETE CASCADE
    │ sku                           │
    │ model                         │
    │ description                   │
    │ base_price                    │
    │ effective_date                │
    │ retired_date                  │
    │ is_active                     │
    │ created_at                    │
    │ updated_at                    │
    └────────┬──────────┬───────────┘
             │          │
             │ 1:N      │ 1:N
             │          │
┌────────────▼─────┐  ┌─▼──────────────┐
│ ProductOption    │  │ ProductPrice   │
├──────────────────┤  ├────────────────┤
│ id (PK)          │  │ id (PK)        │
│ product_id (FK?) │  │ product_id (FK)│
│ option_type      │  │ base_price     │
│ option_code      │  │ finish_adder   │
│ option_name      │  │ size_adder     │
│ adder_type       │  │ option_adder   │
│ adder_value      │  │ prep_adder     │
│ requires_option  │  │ total_price    │
│ excludes_option  │  │ effective_date │
│ is_required      │  │ created_at     │
│ sort_order       │  └────────────────┘
│ created_at       │
└──────────────────┘

┌─────────────────────┐
│    ChangeLog        │
├─────────────────────┤
│ id (PK)             │
│ old_price_book_id   │──┐
│ new_price_book_id   │──┼──► References PriceBook
│ change_type         │  │
│ product_id (FK)     │──┘
│ old_value           │
│ new_value           │
│ change_percentage   │
│ description         │
│ created_at          │
└─────────────────────┘
```

---

## Tables

### 1. manufacturers

Stores manufacturer information (Hager, SELECT Hinges, etc.).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| `name` | VARCHAR(255) | NOT NULL | Full manufacturer name |
| `code` | VARCHAR(50) | UNIQUE, NOT NULL | Short code (e.g., 'HAG', 'SEL') |
| `created_at` | DATETIME | DEFAULT NOW | Record creation timestamp |

**Indexes**:
- PRIMARY KEY: `id`
- UNIQUE: `code`

**Relationships**:
- `1:N` with `price_books`
- `1:N` with `product_families`
- `1:N` with `finishes`

---

### 2. price_books

Stores price book editions and metadata.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| `manufacturer_id` | INTEGER | FOREIGN KEY(manufacturers.id), NOT NULL | Manufacturer reference |
| `edition` | VARCHAR(100) | NULL | Edition name (e.g., '2025 Edition') |
| `effective_date` | DATE | NULL | When prices become effective |
| `upload_date` | DATETIME | DEFAULT NOW | When PDF was uploaded |
| `file_path` | TEXT | NULL | Path to original PDF file |
| `file_size` | INTEGER | NULL | File size in bytes |
| `status` | VARCHAR(50) | DEFAULT 'processing' | Processing status: processing, completed, failed, processed |
| `parsing_notes` | TEXT | NULL | Notes/warnings from parsing |

**Indexes**:
- PRIMARY KEY: `id`
- FOREIGN KEY: `manufacturer_id` → `manufacturers(id)`
- INDEX: `status`
- INDEX: `effective_date`

**Relationships**:
- `N:1` with `manufacturers`
- `1:N` with `products` (CASCADE DELETE)
- Referenced by `change_logs`

**Notes**:
- When a price_book is deleted, all associated products are automatically deleted (CASCADE)
- Status values: 'processing', 'completed', 'failed', 'processed'

---

### 3. product_families

Product families/categories (BB1100, CTW, etc.).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| `manufacturer_id` | INTEGER | FOREIGN KEY(manufacturers.id), NOT NULL | Manufacturer reference |
| `name` | VARCHAR(255) | NOT NULL | Family name (e.g., 'BB1100 Series') |
| `category` | VARCHAR(100) | NULL | Category (e.g., 'Hinges', 'Levers') |
| `description` | TEXT | NULL | Detailed description |
| `created_at` | DATETIME | DEFAULT NOW | Record creation timestamp |

**Indexes**:
- PRIMARY KEY: `id`
- FOREIGN KEY: `manufacturer_id` → `manufacturers(id)`
- INDEX: `name`

**Relationships**:
- `N:1` with `manufacturers`
- `1:N` with `products`

---

### 4. products

Individual products/SKUs with pricing.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| `family_id` | INTEGER | FOREIGN KEY(product_families.id), NULL | Family reference (optional) |
| `price_book_id` | INTEGER | FOREIGN KEY(price_books.id, ON DELETE CASCADE), NOT NULL | Price book reference |
| `sku` | VARCHAR(100) | NOT NULL | Stock keeping unit |
| `model` | VARCHAR(100) | NULL | Model number |
| `description` | TEXT | NULL | Product description |
| `base_price` | DECIMAL(10,2) | NULL | Base list price |
| `effective_date` | DATE | NULL | Price effective date |
| `retired_date` | DATE | NULL | When product was retired |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status |
| `created_at` | DATETIME | DEFAULT NOW | Record creation |
| `updated_at` | DATETIME | DEFAULT NOW, ON UPDATE NOW | Last modification |

**Indexes**:
- PRIMARY KEY: `id`
- FOREIGN KEY: `family_id` → `product_families(id)`
- FOREIGN KEY: `price_book_id` → `price_books(id)` **ON DELETE CASCADE**
- INDEX: `sku`
- INDEX: `model`
- INDEX: `price_book_id, is_active`

**Relationships**:
- `N:1` with `product_families`
- `N:1` with `price_books` (CASCADE DELETE)
- `1:N` with `product_options`
- `1:N` with `product_prices`
- Referenced by `change_logs`

**Important**:
- **ON DELETE CASCADE**: When a price_book is deleted, all products are automatically deleted

---

### 5. finishes

Finish options and BHMA codes (US3, US4, etc.).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| `manufacturer_id` | INTEGER | FOREIGN KEY(manufacturers.id), NOT NULL | Manufacturer reference |
| `code` | VARCHAR(20) | NOT NULL | Finish code (e.g., 'US3') |
| `name` | VARCHAR(100) | NOT NULL | Finish name (e.g., 'Satin Chrome') |
| `bhma_code` | VARCHAR(20) | NULL | BHMA standard code |
| `description` | TEXT | NULL | Detailed description |
| `created_at` | DATETIME | DEFAULT NOW | Record creation |

**Indexes**:
- PRIMARY KEY: `id`
- FOREIGN KEY: `manufacturer_id` → `manufacturers(id)`
- INDEX: `code`
- INDEX: `bhma_code`

**Relationships**:
- `N:1` with `manufacturers`

---

### 6. product_options

Product options, adders, and pricing rules.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| `product_id` | INTEGER | FOREIGN KEY(products.id), **NULLABLE** | Product reference (nullable for global options) |
| `option_type` | VARCHAR(50) | NOT NULL | Option type: 'finish', 'size', 'preparation', 'net_add' |
| `option_code` | VARCHAR(50) | NULL | Option code |
| `option_name` | VARCHAR(255) | NULL | Option name |
| `adder_type` | VARCHAR(20) | NULL | Adder type: 'net_add', 'percent', 'replace', 'multiply' |
| `adder_value` | DECIMAL(10,2) | NULL | Adder amount |
| `requires_option` | VARCHAR(50) | NULL | Required prerequisite option |
| `excludes_option` | VARCHAR(50) | NULL | Mutually exclusive option |
| `is_required` | BOOLEAN | DEFAULT FALSE | Is this option required? |
| `sort_order` | INTEGER | DEFAULT 0 | Display order |
| `created_at` | DATETIME | DEFAULT NOW | Record creation |

**Indexes**:
- PRIMARY KEY: `id`
- FOREIGN KEY: `product_id` → `products(id)` (NULLABLE)
- INDEX: `option_type`
- INDEX: `product_id`

**Relationships**:
- `N:1` with `products` (optional - can be NULL for global options)

**Notes**:
- `product_id` is NULLABLE to support global options (e.g., SELECT net-add rules)
- Option types: 'finish', 'size', 'preparation', 'net_add'
- Adder types: 'net_add' (add amount), 'percent' (percentage), 'replace' (replace price), 'multiply' (multiply by factor)

---

### 7. product_prices

Price history and calculations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| `product_id` | INTEGER | FOREIGN KEY(products.id), NOT NULL | Product reference |
| `base_price` | DECIMAL(10,2) | NOT NULL | Base price |
| `finish_adder` | DECIMAL(10,2) | DEFAULT 0 | Finish surcharge |
| `size_adder` | DECIMAL(10,2) | DEFAULT 0 | Size surcharge |
| `option_adder` | DECIMAL(10,2) | DEFAULT 0 | Option surcharge |
| `preparation_adder` | DECIMAL(10,2) | DEFAULT 0 | Preparation surcharge |
| `total_price` | DECIMAL(10,2) | NOT NULL | Total calculated price |
| `effective_date` | DATE | NOT NULL | When this price is effective |
| `created_at` | DATETIME | DEFAULT NOW | Record creation |

**Indexes**:
- PRIMARY KEY: `id`
- FOREIGN KEY: `product_id` → `products(id)`
- INDEX: `effective_date`
- INDEX: `product_id, effective_date`

**Relationships**:
- `N:1` with `products`

---

### 8. change_logs

Tracks changes between price book editions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| `old_price_book_id` | INTEGER | FOREIGN KEY(price_books.id), NULL | Previous version reference |
| `new_price_book_id` | INTEGER | FOREIGN KEY(price_books.id), NOT NULL | New version reference |
| `change_type` | VARCHAR(50) | NOT NULL | Change type (see below) |
| `product_id` | INTEGER | FOREIGN KEY(products.id), NULL | Affected product |
| `old_value` | TEXT | NULL | Previous value (JSON) |
| `new_value` | TEXT | NULL | New value (JSON) |
| `change_percentage` | DECIMAL(5,2) | NULL | Percentage change (for prices) |
| `description` | TEXT | NULL | Human-readable description |
| `created_at` | DATETIME | DEFAULT NOW | Change timestamp |

**Change Types**:
- `price_change`: Price modified
- `new_product`: Product added
- `retired_product`: Product removed
- `option_change`: Option modified
- `currency_changed`: Currency conversion
- `renamed`: Product renamed

**Indexes**:
- PRIMARY KEY: `id`
- FOREIGN KEY: `old_price_book_id` → `price_books(id)`
- FOREIGN KEY: `new_price_book_id` → `price_books(id)`
- FOREIGN KEY: `product_id` → `products(id)`
- INDEX: `change_type`
- INDEX: `new_price_book_id`

**Relationships**:
- References `price_books` (old and new)
- References `products`

---

## Data Types

### SQLite Types (Default)

| Type | Description | Example |
|------|-------------|---------|
| `INTEGER` | Signed integer | 12345 |
| `VARCHAR(N)` | Variable-length string | 'BB1100US3' |
| `TEXT` | Unlimited text | 'Long description...' |
| `DECIMAL(M,D)` | Fixed-point decimal | 125.50 |
| `DATE` | Date (YYYY-MM-DD) | '2025-01-15' |
| `DATETIME` | Timestamp | '2025-01-15 14:30:00' |
| `BOOLEAN` | True/False (0/1) | 1 or 0 |

### PostgreSQL Types (Production)

When using PostgreSQL, types map as follows:

| SQLite | PostgreSQL | Notes |
|--------|-----------|-------|
| `INTEGER` | `INTEGER` or `SERIAL` | SERIAL for auto-increment |
| `VARCHAR(N)` | `VARCHAR(N)` | Same |
| `TEXT` | `TEXT` | Same |
| `DECIMAL(M,D)` | `NUMERIC(M,D)` | More precise |
| `DATE` | `DATE` | Same |
| `DATETIME` | `TIMESTAMP` | Timezone-aware: `TIMESTAMPTZ` |
| `BOOLEAN` | `BOOLEAN` | Native type |

---

## Natural Keys

For matching and synchronization (e.g., Baserow), use these **natural keys**:

### Product Natural Key

```
manufacturer_code | family_name | model | finish_code | size
```

Example: `HAG|BB1100|BB1100US3|US3|4.5`

### Components:
- **manufacturer_code**: From `manufacturers.code` (e.g., 'HAG')
- **family_name**: From `product_families.name` (e.g., 'BB1100')
- **model**: From `products.model` (e.g., 'BB1100US3')
- **finish_code**: Extracted from model or explicit field
- **size**: Size attribute (e.g., '4.5')

---

## Migration Notes

### ON DELETE CASCADE

The critical cascade delete constraint was added in migration (see `CASCADE_DELETE_FIX.md`):

```sql
FOREIGN KEY(price_book_id)
REFERENCES price_books(id)
ON DELETE CASCADE
```

This ensures that when a price book is deleted, all associated products are automatically removed.

### Nullable product_id in product_options

The `product_id` column in `product_options` is **NULLABLE** to support:
- Global options (e.g., SELECT net-add rules)
- Manufacturer-wide finish mappings

---

## Example Queries

### Get all products for a price book

```sql
SELECT p.*, pf.name AS family_name, pb.edition
FROM products p
LEFT JOIN product_families pf ON p.family_id = pf.id
LEFT JOIN price_books pb ON p.price_book_id = pb.id
WHERE pb.id = 1
  AND p.is_active = 1
ORDER BY p.sku;
```

### Find price changes between editions

```sql
SELECT
  old_p.model AS old_model,
  new_p.model AS new_model,
  old_p.base_price AS old_price,
  new_p.base_price AS new_price,
  ((new_p.base_price - old_p.base_price) / old_p.base_price * 100) AS pct_change
FROM products old_p
JOIN products new_p ON old_p.sku = new_p.sku
WHERE old_p.price_book_id = 1
  AND new_p.price_book_id = 2
  AND old_p.base_price != new_p.base_price;
```

### Get options for a product

```sql
SELECT po.*
FROM product_options po
WHERE po.product_id = 123
ORDER BY po.sort_order;
```

---

## Schema Version

**Current Version**: 1.1
**Last Updated**: 2025-10-03
**Key Changes**:
- Added ON DELETE CASCADE for products.price_book_id
- Made product_options.product_id NULLABLE

---

**See Also**:
- [INSTALL.md](INSTALL.md) - Installation guide
- [OPERATIONS.md](OPERATIONS.md) - Operations runbook
- [PARSERS.md](PARSERS.md) - Parser architecture
- [BASEROW.md](BASEROW.md) - Baserow integration
