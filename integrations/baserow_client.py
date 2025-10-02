"""
Baserow API client for idempotent data synchronization.

Handles schema mapping, table creation, field management, and chunked upserts
with natural key hashing for stable synchronization between systems.
"""
import hashlib
import json
import time
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from core.exceptions import BaserowError, NetworkTimeoutError, RateLimitError
from core.resilience import resilient, CircuitBreakerConfig, RetryConfig
from core.observability import get_logger, metrics_collector

logger = logging.getLogger(__name__)


@dataclass
class BaserowConfig:
    """Configuration for Baserow client."""
    api_url: str = "https://api.baserow.io"
    api_token: str = ""
    database_id: int = 0
    timeout: int = 30
    max_retries: int = 3
    chunk_size: int = 200
    rate_limit_per_second: float = 10.0


@dataclass
class FieldDefinition:
    """Baserow field definition."""
    name: str
    field_type: str
    type_config: Dict[str, Any] = field(default_factory=dict)
    required: bool = False
    unique: bool = False


@dataclass
class TableSchema:
    """Complete table schema definition."""
    name: str
    fields: List[FieldDefinition]
    natural_key_fields: List[str]  # Fields that compose the natural key


# Standard schema definitions for ARC PDF data
ARC_SCHEMA_DEFINITIONS = {
    "Items": TableSchema(
        name="Items",
        natural_key_fields=["manufacturer", "family", "model", "finish", "size"],
        fields=[
            FieldDefinition("natural_key_hash", "text", {"max_length": 64}, required=True, unique=True),
            FieldDefinition("manufacturer", "text", {"max_length": 50}, required=True),
            FieldDefinition("family", "text", {"max_length": 50}, required=True),
            FieldDefinition("model", "text", {"max_length": 100}, required=True),
            FieldDefinition("finish", "text", {"max_length": 20}),
            FieldDefinition("size", "text", {"max_length": 50}),
            FieldDefinition("description", "long_text"),
            FieldDefinition("series", "text", {"max_length": 50}),
            FieldDefinition("duty", "text", {"max_length": 20}),
            FieldDefinition("base_price", "number", {"number_decimal_places": 2}),
            FieldDefinition("effective_date", "date"),
            FieldDefinition("confidence_score", "number", {"number_decimal_places": 3}),
            FieldDefinition("extraction_method", "text", {"max_length": 50}),
            FieldDefinition("source_page", "number"),
            FieldDefinition("created_at", "date", {"date_include_time": True}),
            FieldDefinition("updated_at", "date", {"date_include_time": True}),
        ]
    ),

    "ItemPrices": TableSchema(
        name="ItemPrices",
        natural_key_fields=["item_natural_key", "finish", "price_type"],
        fields=[
            FieldDefinition("natural_key_hash", "text", {"max_length": 64}, required=True, unique=True),
            FieldDefinition("item_natural_key", "text", {"max_length": 64}, required=True),
            FieldDefinition("finish", "text", {"max_length": 20}, required=True),
            FieldDefinition("price_type", "text", {"max_length": 20}, required=True),  # base, list, net
            FieldDefinition("price", "number", {"number_decimal_places": 2}, required=True),
            FieldDefinition("currency", "text", {"max_length": 3}),
            FieldDefinition("effective_date", "date"),
            FieldDefinition("confidence_score", "number", {"number_decimal_places": 3}),
            FieldDefinition("created_at", "date", {"date_include_time": True}),
            FieldDefinition("updated_at", "date", {"date_include_time": True}),
        ]
    ),

    "Options": TableSchema(
        name="Options",
        natural_key_fields=["manufacturer", "option_code"],
        fields=[
            FieldDefinition("natural_key_hash", "text", {"max_length": 64}, required=True, unique=True),
            FieldDefinition("manufacturer", "text", {"max_length": 50}, required=True),
            FieldDefinition("option_code", "text", {"max_length": 20}, required=True),
            FieldDefinition("option_name", "text", {"max_length": 100}),
            FieldDefinition("description", "long_text"),
            FieldDefinition("option_type", "text", {"max_length": 30}),  # preparation, material, etc.
            FieldDefinition("adder_value", "number", {"number_decimal_places": 2}),
            FieldDefinition("adder_type", "text", {"max_length": 20}),  # fixed, percentage
            FieldDefinition("constraints", "long_text"),  # JSON string
            FieldDefinition("effective_date", "date"),
            FieldDefinition("confidence_score", "number", {"number_decimal_places": 3}),
            FieldDefinition("created_at", "date", {"date_include_time": True}),
            FieldDefinition("updated_at", "date", {"date_include_time": True}),
        ]
    ),

    "ItemOptions": TableSchema(
        name="ItemOptions",
        natural_key_fields=["item_natural_key", "option_natural_key"],
        fields=[
            FieldDefinition("natural_key_hash", "text", {"max_length": 64}, required=True, unique=True),
            FieldDefinition("item_natural_key", "text", {"max_length": 64}, required=True),
            FieldDefinition("option_natural_key", "text", {"max_length": 64}, required=True),
            FieldDefinition("is_compatible", "boolean"),
            FieldDefinition("override_price", "number", {"number_decimal_places": 2}),
            FieldDefinition("notes", "long_text"),
            FieldDefinition("created_at", "date", {"date_include_time": True}),
            FieldDefinition("updated_at", "date", {"date_include_time": True}),
        ]
    ),

    "Rules": TableSchema(
        name="Rules",
        natural_key_fields=["manufacturer", "rule_type", "source_identifier"],
        fields=[
            FieldDefinition("natural_key_hash", "text", {"max_length": 64}, required=True, unique=True),
            FieldDefinition("manufacturer", "text", {"max_length": 50}, required=True),
            FieldDefinition("rule_type", "text", {"max_length": 30}, required=True),  # price_mapping, percentage_markup
            FieldDefinition("source_identifier", "text", {"max_length": 100}, required=True),  # finish, model, etc.
            FieldDefinition("target_identifier", "text", {"max_length": 100}),
            FieldDefinition("rule_data", "long_text"),  # JSON string with rule specifics
            FieldDefinition("description", "long_text"),
            FieldDefinition("effective_date", "date"),
            FieldDefinition("confidence_score", "number", {"number_decimal_places": 3}),
            FieldDefinition("created_at", "date", {"date_include_time": True}),
            FieldDefinition("updated_at", "date", {"date_include_time": True}),
        ]
    ),

    "ChangeLog": TableSchema(
        name="ChangeLog",
        natural_key_fields=["old_book_id", "new_book_id", "change_type", "item_identifier"],
        fields=[
            FieldDefinition("natural_key_hash", "text", {"max_length": 64}, required=True, unique=True),
            FieldDefinition("old_book_id", "text", {"max_length": 50}),
            FieldDefinition("new_book_id", "text", {"max_length": 50}),
            FieldDefinition("change_type", "text", {"max_length": 30}, required=True),
            FieldDefinition("item_identifier", "text", {"max_length": 100}, required=True),
            FieldDefinition("field_name", "text", {"max_length": 50}),
            FieldDefinition("old_value", "long_text"),
            FieldDefinition("new_value", "long_text"),
            FieldDefinition("change_description", "long_text"),
            FieldDefinition("confidence", "number", {"number_decimal_places": 3}),
            FieldDefinition("reviewer", "text", {"max_length": 50}),
            FieldDefinition("review_status", "text", {"max_length": 20}),
            FieldDefinition("applied", "boolean"),
            FieldDefinition("created_at", "date", {"date_include_time": True}),
            FieldDefinition("updated_at", "date", {"date_include_time": True}),
        ]
    )
}


class BaserowClient:
    """
    Baserow API client with comprehensive table and data management.

    Features:
    - Automatic table and field creation
    - Natural key hashing for idempotent upserts
    - Chunked uploads with rate limiting
    - Circuit breaker and retry logic
    - Comprehensive error handling
    """

    def __init__(self, config: BaserowConfig):
        self.config = config
        self.logger = get_logger("baserow_client")

        if not HTTPX_AVAILABLE:
            raise BaserowError(
                operation="initialization",
                response="httpx library not available. Install with: pip install httpx"
            )

        # HTTP client with timeout and retry configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout),
            headers={
                "Authorization": f"Token {self.config.api_token}",
                "Content-Type": "application/json"
            }
        )

        # Cache for table and field information
        self._table_cache: Dict[str, Dict[str, Any]] = {}
        self._field_cache: Dict[int, Dict[str, Any]] = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    @resilient(
        circuit_breaker_name="baserow_api",
        circuit_config=CircuitBreakerConfig(failure_threshold=5, recovery_timeout=120),
        retry_config=RetryConfig(max_attempts=3, base_delay=1.0),
        rate_limiter_name="baserow_api"
    )
    async def get_or_create_table(self, schema: TableSchema) -> Dict[str, Any]:
        """
        Get existing table or create new one based on schema.

        Args:
            schema: Table schema definition

        Returns:
            Table information including ID and fields
        """
        self.logger.info(f"Getting or creating table: {schema.name}")

        # Check cache first
        if schema.name in self._table_cache:
            return self._table_cache[schema.name]

        try:
            # List existing tables
            response = await self.client.get(
                f"{self.config.api_url}/api/database/{self.config.database_id}/tables/"
            )
            response.raise_for_status()

            tables_data = response.json()
            existing_table = None

            for table in tables_data:
                if table["name"] == schema.name:
                    existing_table = table
                    break

            if existing_table:
                self.logger.info(f"Found existing table: {schema.name} (ID: {existing_table['id']})")
                table_info = existing_table
            else:
                # Create new table
                self.logger.info(f"Creating new table: {schema.name}")
                create_response = await self.client.post(
                    f"{self.config.api_url}/api/database/{self.config.database_id}/tables/",
                    json={"name": schema.name}
                )
                create_response.raise_for_status()
                table_info = create_response.json()

            # Ensure all required fields exist
            await self.ensure_fields(table_info["id"], schema.fields)

            # Cache the result
            self._table_cache[schema.name] = table_info
            metrics_collector.increment_counter("baserow_table_operations")

            return table_info

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitError("Baserow API", reset_time=60)
            else:
                raise BaserowError(
                    operation="get_or_create_table",
                    status_code=e.response.status_code,
                    response=e.response.text
                )
        except httpx.TimeoutException:
            raise NetworkTimeoutError("Baserow table operation", self.config.timeout)

    @resilient(
        circuit_breaker_name="baserow_api",
        retry_config=RetryConfig(max_attempts=2)
    )
    async def ensure_fields(self, table_id: int, field_definitions: List[FieldDefinition]):
        """
        Ensure all required fields exist in the table.

        Args:
            table_id: Baserow table ID
            field_definitions: List of field definitions to ensure
        """
        self.logger.info(f"Ensuring fields for table {table_id}")

        try:
            # Get existing fields
            response = await self.client.get(
                f"{self.config.api_url}/api/database/tables/{table_id}/fields/"
            )
            response.raise_for_status()

            existing_fields = {field["name"]: field for field in response.json()}

            # Create missing fields
            for field_def in field_definitions:
                if field_def.name not in existing_fields:
                    self.logger.info(f"Creating field: {field_def.name} ({field_def.field_type})")

                    field_data = {
                        "name": field_def.name,
                        "type": field_def.field_type,
                        **field_def.type_config
                    }

                    create_response = await self.client.post(
                        f"{self.config.api_url}/api/database/tables/{table_id}/fields/",
                        json=field_data
                    )
                    create_response.raise_for_status()

            # Cache field information
            self._field_cache[table_id] = existing_fields
            metrics_collector.increment_counter("baserow_field_operations")

        except httpx.HTTPStatusError as e:
            raise BaserowError(
                operation="ensure_fields",
                status_code=e.response.status_code,
                response=e.response.text
            )

    def generate_natural_key_hash(self, data: Dict[str, Any], key_fields: List[str]) -> str:
        """
        Generate a stable hash from natural key fields.

        Args:
            data: Row data
            key_fields: Fields that compose the natural key

        Returns:
            SHA-256 hash of the natural key
        """
        # Extract and normalize key values
        key_values = []
        for field in key_fields:
            value = data.get(field, "")
            # Normalize value for consistent hashing
            if isinstance(value, str):
                value = value.strip().lower()
            elif value is None:
                value = ""
            key_values.append(str(value))

        # Create stable key string and hash
        key_string = "|".join(key_values)
        return hashlib.sha256(key_string.encode('utf-8')).hexdigest()

    @resilient(
        circuit_breaker_name="baserow_api",
        retry_config=RetryConfig(max_attempts=3, base_delay=2.0)
    )
    async def upsert_rows(
        self,
        table_id: int,
        rows: List[Dict[str, Any]],
        key_field: str = "natural_key_hash",
        chunk_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Upsert rows into table using natural key for deduplication.

        Args:
            table_id: Baserow table ID
            rows: List of row data to upsert
            key_field: Field used for deduplication
            chunk_size: Number of rows per batch (defaults to config)

        Returns:
            Summary of upsert operation
        """
        chunk_size = chunk_size or self.config.chunk_size

        self.logger.info(f"Upserting {len(rows)} rows to table {table_id} in chunks of {chunk_size}")

        summary = {
            "total_rows": len(rows),
            "chunks_processed": 0,
            "rows_created": 0,
            "rows_updated": 0,
            "errors": []
        }

        # Process in chunks
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i:i + chunk_size]
            chunk_start = i + 1
            chunk_end = min(i + chunk_size, len(rows))

            self.logger.info(f"Processing chunk {summary['chunks_processed'] + 1}: rows {chunk_start}-{chunk_end}")

            try:
                chunk_result = await self._upsert_chunk(table_id, chunk, key_field)
                summary["rows_created"] += chunk_result["created"]
                summary["rows_updated"] += chunk_result["updated"]
                summary["chunks_processed"] += 1

                metrics_collector.record_histogram("baserow_chunk_size", len(chunk))
                metrics_collector.increment_counter("baserow_chunks_processed")

                # Rate limiting delay between chunks
                if i + chunk_size < len(rows):
                    await asyncio.sleep(1.0 / self.config.rate_limit_per_second)

            except Exception as e:
                error_msg = f"Chunk {summary['chunks_processed'] + 1} failed: {str(e)}"
                self.logger.error(error_msg, exception=e)
                summary["errors"].append(error_msg)

        self.logger.info(f"Upsert complete: {summary['rows_created']} created, {summary['rows_updated']} updated")
        metrics_collector.record_timing("baserow_upsert_operation", time.time() * 1000)

        return summary

    async def _upsert_chunk(self, table_id: int, chunk: List[Dict], key_field: str) -> Dict[str, int]:
        """Upsert a single chunk of rows."""

        # Get existing rows by key field
        existing_rows = await self._get_existing_rows(table_id,
                                                     [row[key_field] for row in chunk],
                                                     key_field)
        existing_keys = {row[key_field]: row for row in existing_rows}

        created_count = 0
        updated_count = 0

        for row in chunk:
            row_key = row[key_field]

            if row_key in existing_keys:
                # Update existing row
                existing_row = existing_keys[row_key]
                await self._update_row(table_id, existing_row["id"], row)
                updated_count += 1
            else:
                # Create new row
                await self._create_row(table_id, row)
                created_count += 1

        return {"created": created_count, "updated": updated_count}

    async def _get_existing_rows(self, table_id: int, key_values: List[str], key_field: str) -> List[Dict]:
        """Get existing rows by key field values."""
        if not key_values:
            return []

        try:
            # Build filter for the key field
            # Note: This is a simplified approach - Baserow's filtering may require different syntax
            filter_params = {
                f"filter__{key_field}__equal": ",".join(key_values)
            }

            response = await self.client.get(
                f"{self.config.api_url}/api/database/tables/{table_id}/rows/",
                params=filter_params
            )
            response.raise_for_status()

            return response.json().get("results", [])

        except httpx.HTTPStatusError as e:
            # If filtering fails, fall back to fetching all rows (less efficient)
            self.logger.warning(f"Filter query failed, falling back to full scan: {e}")

            response = await self.client.get(
                f"{self.config.api_url}/api/database/tables/{table_id}/rows/"
            )
            response.raise_for_status()

            all_rows = response.json().get("results", [])
            return [row for row in all_rows if row.get(key_field) in key_values]

    async def _create_row(self, table_id: int, row_data: Dict[str, Any]):
        """Create a new row in the table."""
        # Add timestamps
        now = datetime.utcnow().isoformat()
        row_data["created_at"] = now
        row_data["updated_at"] = now

        response = await self.client.post(
            f"{self.config.api_url}/api/database/tables/{table_id}/rows/",
            json=row_data
        )
        response.raise_for_status()
        return response.json()

    async def _update_row(self, table_id: int, row_id: int, row_data: Dict[str, Any]):
        """Update an existing row in the table."""
        # Update timestamp
        row_data["updated_at"] = datetime.utcnow().isoformat()

        response = await self.client.patch(
            f"{self.config.api_url}/api/database/tables/{table_id}/rows/{row_id}/",
            json=row_data
        )
        response.raise_for_status()
        return response.json()

    async def get_table_stats(self, table_id: int) -> Dict[str, Any]:
        """Get statistics about a table."""
        try:
            response = await self.client.get(
                f"{self.config.api_url}/api/database/tables/{table_id}/rows/",
                params={"size": 1}  # Just get count, not actual data
            )
            response.raise_for_status()

            data = response.json()
            return {
                "table_id": table_id,
                "total_rows": data.get("count", 0),
                "has_data": data.get("count", 0) > 0
            }

        except httpx.HTTPStatusError as e:
            raise BaserowError(
                operation="get_table_stats",
                status_code=e.response.status_code,
                response=e.response.text
            )

    async def test_connection(self) -> bool:
        """Test connection to Baserow API."""
        try:
            response = await self.client.get(
                f"{self.config.api_url}/api/database/{self.config.database_id}/"
            )
            response.raise_for_status()

            self.logger.info("Baserow connection test successful")
            return True

        except Exception as e:
            self.logger.error(f"Baserow connection test failed: {e}")
            return False