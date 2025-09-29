# Baserow Integration Guide

## Overview

Baserow integration syncs parsed price book data to Baserow database for collaboration and downstream use.

## Setup

### 1. Get Baserow Credentials

1. Log into your Baserow account
2. Go to Settings → API tokens
3. Create new token with database access
4. Note your database ID (visible in URL)

### 2. Configure Environment

Add to `.env`:
```bash
BASEROW_TOKEN=your_token_here
BASEROW_DATABASE_ID=12345
BASEROW_API_URL=https://api.baserow.io  # Default
```

### 3. Table Schema

Create tables in Baserow with these schemas:

**Products Table**:
- `sku` (Text, primary key)
- `model` (Text)
- `series` (Text)
- `finish` (Text)
- `base_price` (Number, 2 decimals)
- `description` (Long text)
- `manufacturer` (Single select: Hager, SELECT)
- `is_active` (Boolean)
- `page_ref` (Number)

**Finishes Table**:
- `code` (Text, primary key)
- `label` (Text)
- `bhma` (Text)
- `manufacturer` (Single select)

**Options Table**:
- `code` (Text, primary key)
- `label` (Text)
- `adder_value` (Number, 2 decimals)
- `adder_type` (Single select: net_add, percentage)
- `constraints_json` (Long text)

## Usage

### Publish Price Book to Baserow

```bash
# Dry run (no changes)
uv run python scripts/publish_baserow.py \
  --book-id 123 \
  --dry-run

# Actual publish
uv run python scripts/publish_baserow.py \
  --book-id 123

# Publish specific tables only
uv run python scripts/publish_baserow.py \
  --book-id 123 \
  --tables products finishes
```

### Programmatic Usage

```python
from integrations.baserow_client import BaserowClient

# Initialize client
client = BaserowClient(
    token=os.getenv('BASEROW_TOKEN'),
    database_id=os.getenv('BASEROW_DATABASE_ID')
)

# Test connection
if await client.test_connection():
    print("Connected to Baserow")

# Upsert products (idempotent)
await client.upsert_rows(
    table_id="products_table_id",
    rows=[
        {'sku': 'BB1100-US10B', 'base_price': 125.50, ...},
        {'sku': 'BB1101-US3', 'base_price': 135.75, ...}
    ],
    key_field='sku'
)
```

## Natural Key Strategy

**Products**: `sku` is natural key
- Composite: model + finish + size
- Example: BB1100-US10B

**Finishes**: `code` is natural key
- BHMA standard codes
- Example: US10B

**Options**: `code` is natural key
- Manufacturer code
- Example: EPT, ETW

## Idempotent Upserts

The integration uses natural keys for idempotent operations:

```python
# First run: INSERT
await client.upsert_rows(table_id, [
    {'sku': 'BB1100-US10B', 'base_price': 125.50}
], key_field='sku')

# Second run: UPDATE (not duplicate)
await client.upsert_rows(table_id, [
    {'sku': 'BB1100-US10B', 'base_price': 128.00}  # Price updated
], key_field='sku')
```

## Rate Limiting

Baserow API has rate limits (varies by plan):

**Built-in handling**:
- Circuit breaker pattern
- Exponential backoff on 429 errors
- Automatic retry on 5xx errors
- Batch processing (200 rows/request)

```python
# Configure retries
config = {
    'max_retries': 3,
    'retry_delay': 1.0,
    'batch_size': 200
}

client = BaserowClient(token, database_id, config=config)
```

## Error Handling

```python
from core.exceptions import BaserowError, NetworkError

try:
    await client.upsert_rows(table_id, rows, key_field='sku')
except BaserowError as e:
    logger.error(f"Baserow API error: {e}")
    # Handle specific error
except NetworkError as e:
    logger.error(f"Network error: {e}")
    # Retry logic
```

## Monitoring

### Publish Status

Check publish history in database:
```sql
SELECT * FROM baserow_syncs
WHERE price_book_id = 123
ORDER BY sync_timestamp DESC;
```

### Audit Trail

All publishes are logged:
```json
{
  "sync_id": "uuid",
  "price_book_id": 123,
  "tables_synced": ["products", "finishes", "options"],
  "rows_inserted": 150,
  "rows_updated": 25,
  "errors": 0,
  "sync_timestamp": "2025-09-30T01:00:00Z",
  "status": "completed"
}
```

## Best Practices

1. **Use dry-run first** - Validate before publishing
2. **Publish incrementally** - Start with small datasets
3. **Monitor rate limits** - Check API quota usage
4. **Validate schemas** - Ensure Baserow tables match data
5. **Handle failures** - Implement retry logic for transient errors
6. **Audit publishes** - Track all sync operations

## Troubleshooting

### Connection Failures

```bash
# Test connection
python -c "
from integrations.baserow_client import BaserowClient
import asyncio
import os

async def test():
    client = BaserowClient(os.getenv('BASEROW_TOKEN'), os.getenv('BASEROW_DATABASE_ID'))
    result = await client.test_connection()
    print('Connected!' if result else 'Failed')

asyncio.run(test())
"
```

### Schema Mismatches

Error: "Field 'base_price' not found"

**Solution**: Verify field names in Baserow match data:
```python
# Get table schema
fields = await client.get_table_fields(table_id)
print([f['name'] for f in fields])
```

### Rate Limit Errors

Error: "429 Too Many Requests"

**Solution**: Reduce batch size or add delays:
```python
config = {
    'batch_size': 100,  # Reduced from 200
    'retry_delay': 2.0   # Increased from 1.0
}
```

## See Also

- [DIFF.md](DIFF.md) - Generate diffs to sync
- [OPERATIONS.md](OPERATIONS.md) - Production sync workflows