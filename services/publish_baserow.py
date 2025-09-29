"""
Baserow publishing service for synchronized data management.

Handles conversion of normalized price book data to Baserow format,
orchestrates table creation and data upserts, and tracks sync status.
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from core.database import get_db_session, PriceBook
from core.exceptions import BaserowError, ProcessingError
from core.observability import get_logger, track_performance, metrics_collector
from integrations.baserow_client import BaserowClient, BaserowConfig, ARC_SCHEMA_DEFINITIONS
from models.baserow_syncs import BaserowSync  # We'll need to create this model

logger = get_logger("publish_baserow")


@dataclass
class PublishOptions:
    """Options for publishing to Baserow."""
    dry_run: bool = False
    tables_to_sync: Optional[List[str]] = None  # None = all tables
    force_full_sync: bool = False  # Re-sync all data even if unchanged
    chunk_size: Optional[int] = None
    max_retries: int = 3


@dataclass
class PublishResult:
    """Result of publishing operation."""
    success: bool
    sync_id: Optional[str]
    tables_synced: List[str]
    total_rows_processed: int
    total_rows_created: int
    total_rows_updated: int
    errors: List[str]
    warnings: List[str]
    duration_seconds: float
    sync_summary: Dict[str, Any]


class BaserowPublisher:
    """
    Service for publishing price book data to Baserow.

    Handles complete workflow of data extraction, transformation,
    and synchronization with comprehensive error handling and status tracking.
    """

    def __init__(self, baserow_config: BaserowConfig):
        self.baserow_config = baserow_config
        self.logger = get_logger("baserow_publisher")

    async def publish_price_book(
        self,
        price_book_id: str,
        options: PublishOptions = None,
        user_id: str = None
    ) -> PublishResult:
        """
        Publish a complete price book to Baserow.

        Args:
            price_book_id: ID of the price book to publish
            options: Publishing options and configuration
            user_id: User initiating the publish operation

        Returns:
            PublishResult with detailed outcome information
        """
        options = options or PublishOptions()
        start_time = datetime.utcnow()

        self.logger.info(
            f"Starting Baserow publish",
            price_book_id=price_book_id,
            dry_run=options.dry_run,
            user_id=user_id
        )

        with track_performance("baserow_publish") as perf:
            try:
                # Load price book data
                price_book_data = await self._load_price_book_data(price_book_id)
                perf.add_metric("price_book_loaded", True)

                # Create sync record
                sync_record = await self._create_sync_record(
                    price_book_id, options, user_id, start_time
                )
                perf.add_metric("sync_id", sync_record.id if sync_record else None)

                if options.dry_run:
                    # Dry run - validate data but don't sync
                    result = await self._perform_dry_run(price_book_data, options)
                else:
                    # Perform actual sync
                    result = await self._perform_sync(price_book_data, options, sync_record)

                # Update sync record with results
                if sync_record:
                    await self._update_sync_record(sync_record, result)

                duration = (datetime.utcnow() - start_time).total_seconds()
                result.duration_seconds = duration

                self.logger.info(
                    f"Baserow publish completed",
                    price_book_id=price_book_id,
                    success=result.success,
                    duration_seconds=duration,
                    rows_processed=result.total_rows_processed
                )

                # Track metrics
                metrics_collector.increment_counter(
                    f"baserow_publish_{'success' if result.success else 'failure'}"
                )
                metrics_collector.record_timing("baserow_publish_duration", duration * 1000)

                return result

            except Exception as e:
                self.logger.error(
                    f"Baserow publish failed",
                    price_book_id=price_book_id,
                    exception=e
                )

                # Create error result
                duration = (datetime.utcnow() - start_time).total_seconds()
                return PublishResult(
                    success=False,
                    sync_id=None,
                    tables_synced=[],
                    total_rows_processed=0,
                    total_rows_created=0,
                    total_rows_updated=0,
                    errors=[str(e)],
                    warnings=[],
                    duration_seconds=duration,
                    sync_summary={"error": str(e)}
                )

    async def _load_price_book_data(self, price_book_id: str) -> Dict[str, Any]:
        """Load all relevant data for a price book."""
        with get_db_session() as session:
            price_book = session.query(PriceBook).filter_by(id=price_book_id).first()
            if not price_book:
                raise ProcessingError(f"Price book not found: {price_book_id}")

            # Extract all related data
            # This would need to be implemented based on your actual database schema
            data = {
                "price_book": price_book,
                "items": [],      # Extract from related tables
                "prices": [],     # Extract price data
                "options": [],    # Extract options/additions
                "rules": [],      # Extract pricing rules
                "metadata": {
                    "id": price_book_id,
                    "manufacturer": price_book.manufacturer,
                    "effective_date": price_book.effective_date,
                    "extracted_at": datetime.utcnow().isoformat()
                }
            }

            return data

    async def _create_sync_record(
        self,
        price_book_id: str,
        options: PublishOptions,
        user_id: str,
        start_time: datetime
    ) -> Optional[Any]:
        """Create a sync tracking record."""
        if options.dry_run:
            return None

        try:
            with get_db_session() as session:
                sync_record = BaserowSync(
                    price_book_id=price_book_id,
                    initiated_by=user_id,
                    started_at=start_time,
                    status="running",
                    options=json.dumps({
                        "tables_to_sync": options.tables_to_sync,
                        "force_full_sync": options.force_full_sync,
                        "chunk_size": options.chunk_size
                    })
                )
                session.add(sync_record)
                session.commit()
                return sync_record

        except Exception as e:
            self.logger.warning(f"Failed to create sync record: {e}")
            return None

    async def _perform_dry_run(
        self,
        price_book_data: Dict[str, Any],
        options: PublishOptions
    ) -> PublishResult:
        """Perform a dry run validation without actual sync."""
        self.logger.info("Performing dry run validation")

        # Transform data to Baserow format
        transformed_data = await self._transform_data_for_baserow(price_book_data)

        # Validate data structure
        validation_errors = []
        validation_warnings = []
        total_rows = 0

        tables_to_process = options.tables_to_sync or list(ARC_SCHEMA_DEFINITIONS.keys())

        for table_name in tables_to_process:
            if table_name not in transformed_data:
                validation_warnings.append(f"No data for table: {table_name}")
                continue

            rows = transformed_data[table_name]
            total_rows += len(rows)

            # Validate each row against schema
            schema = ARC_SCHEMA_DEFINITIONS[table_name]
            for i, row in enumerate(rows):
                row_errors = self._validate_row_against_schema(row, schema, f"{table_name}[{i}]")
                validation_errors.extend(row_errors)

        return PublishResult(
            success=len(validation_errors) == 0,
            sync_id=None,
            tables_synced=tables_to_process,
            total_rows_processed=total_rows,
            total_rows_created=0,  # Dry run doesn't create
            total_rows_updated=0,  # Dry run doesn't update
            errors=validation_errors,
            warnings=validation_warnings,
            duration_seconds=0,  # Will be set by caller
            sync_summary={
                "dry_run": True,
                "validation_passed": len(validation_errors) == 0,
                "total_rows_validated": total_rows
            }
        )

    async def _perform_sync(
        self,
        price_book_data: Dict[str, Any],
        options: PublishOptions,
        sync_record: Any
    ) -> PublishResult:
        """Perform actual synchronization to Baserow."""
        self.logger.info("Performing actual sync to Baserow")

        # Transform data
        transformed_data = await self._transform_data_for_baserow(price_book_data)

        # Initialize results
        result = PublishResult(
            success=True,
            sync_id=sync_record.id if sync_record else None,
            tables_synced=[],
            total_rows_processed=0,
            total_rows_created=0,
            total_rows_updated=0,
            errors=[],
            warnings=[],
            duration_seconds=0,
            sync_summary={}
        )

        async with BaserowClient(self.baserow_config) as client:
            # Test connection first
            if not await client.test_connection():
                result.success = False
                result.errors.append("Failed to connect to Baserow API")
                return result

            tables_to_process = options.tables_to_sync or list(ARC_SCHEMA_DEFINITIONS.keys())

            # Process each table
            for table_name in tables_to_process:
                try:
                    table_result = await self._sync_table(
                        client, table_name, transformed_data.get(table_name, []), options
                    )

                    result.tables_synced.append(table_name)
                    result.total_rows_processed += table_result["total_rows"]
                    result.total_rows_created += table_result["rows_created"]
                    result.total_rows_updated += table_result["rows_updated"]

                    if table_result["errors"]:
                        result.errors.extend(table_result["errors"])

                    result.sync_summary[table_name] = table_result

                except Exception as e:
                    error_msg = f"Failed to sync table {table_name}: {str(e)}"
                    self.logger.error(error_msg, exception=e)
                    result.errors.append(error_msg)
                    result.success = False

        # Overall success if no errors
        if result.errors:
            result.success = False

        return result

    async def _sync_table(
        self,
        client: BaserowClient,
        table_name: str,
        rows: List[Dict[str, Any]],
        options: PublishOptions
    ) -> Dict[str, Any]:
        """Sync a single table to Baserow."""
        self.logger.info(f"Syncing table {table_name} with {len(rows)} rows")

        if not rows:
            return {
                "table_name": table_name,
                "total_rows": 0,
                "rows_created": 0,
                "rows_updated": 0,
                "errors": [],
                "skipped": "No data to sync"
            }

        try:
            # Get or create table
            schema = ARC_SCHEMA_DEFINITIONS[table_name]
            table_info = await client.get_or_create_table(schema)

            # Generate natural key hashes for all rows
            for row in rows:
                row["natural_key_hash"] = client.generate_natural_key_hash(
                    row, schema.natural_key_fields
                )

            # Perform upsert
            upsert_result = await client.upsert_rows(
                table_info["id"],
                rows,
                chunk_size=options.chunk_size
            )

            return {
                "table_name": table_name,
                "table_id": table_info["id"],
                "total_rows": upsert_result["total_rows"],
                "rows_created": upsert_result["rows_created"],
                "rows_updated": upsert_result["rows_updated"],
                "chunks_processed": upsert_result["chunks_processed"],
                "errors": upsert_result["errors"]
            }

        except Exception as e:
            self.logger.error(f"Table sync failed for {table_name}", exception=e)
            return {
                "table_name": table_name,
                "total_rows": len(rows),
                "rows_created": 0,
                "rows_updated": 0,
                "errors": [str(e)]
            }

    async def _transform_data_for_baserow(self, price_book_data: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """Transform price book data to Baserow table format."""
        self.logger.info("Transforming data for Baserow format")

        transformed = {}

        # Transform Items
        transformed["Items"] = self._transform_items(price_book_data)

        # Transform ItemPrices
        transformed["ItemPrices"] = self._transform_item_prices(price_book_data)

        # Transform Options
        transformed["Options"] = self._transform_options(price_book_data)

        # Transform ItemOptions (relationships)
        transformed["ItemOptions"] = self._transform_item_options(price_book_data)

        # Transform Rules
        transformed["Rules"] = self._transform_rules(price_book_data)

        # ChangeLog would be populated during diff operations
        transformed["ChangeLog"] = []

        return transformed

    def _transform_items(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform items data to Baserow format."""
        items = []
        metadata = data["metadata"]

        for item_data in data.get("items", []):
            # This would need to be implemented based on your actual data structure
            item = {
                "manufacturer": metadata.get("manufacturer", ""),
                "family": item_data.get("family", ""),
                "model": item_data.get("model", ""),
                "finish": item_data.get("finish", ""),
                "size": item_data.get("size", ""),
                "description": item_data.get("description", ""),
                "series": item_data.get("series", ""),
                "duty": item_data.get("duty", ""),
                "base_price": float(item_data.get("base_price", 0)),
                "effective_date": metadata.get("effective_date"),
                "confidence_score": float(item_data.get("confidence", 0.5)),
                "extraction_method": item_data.get("extraction_method", ""),
                "source_page": int(item_data.get("page_number", 0)),
            }
            items.append(item)

        return items

    def _transform_item_prices(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform price data to Baserow format."""
        prices = []
        metadata = data["metadata"]

        for price_data in data.get("prices", []):
            price = {
                "item_natural_key": self._generate_item_key(price_data),
                "finish": price_data.get("finish", ""),
                "price_type": price_data.get("price_type", "base"),
                "price": float(price_data.get("price", 0)),
                "currency": price_data.get("currency", "USD"),
                "effective_date": metadata.get("effective_date"),
                "confidence_score": float(price_data.get("confidence", 0.5)),
            }
            prices.append(price)

        return prices

    def _transform_options(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform options data to Baserow format."""
        options = []
        metadata = data["metadata"]

        for option_data in data.get("options", []):
            option = {
                "manufacturer": metadata.get("manufacturer", ""),
                "option_code": option_data.get("option_code", ""),
                "option_name": option_data.get("option_name", ""),
                "description": option_data.get("description", ""),
                "option_type": option_data.get("option_type", ""),
                "adder_value": float(option_data.get("adder_value", 0)),
                "adder_type": option_data.get("adder_type", "fixed"),
                "constraints": json.dumps(option_data.get("constraints", {})),
                "effective_date": metadata.get("effective_date"),
                "confidence_score": float(option_data.get("confidence", 0.5)),
            }
            options.append(option)

        return options

    def _transform_item_options(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform item-option relationships to Baserow format."""
        # This would create relationships between items and compatible options
        # Implementation depends on how you store compatibility information
        return []

    def _transform_rules(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform pricing rules to Baserow format."""
        rules = []
        metadata = data["metadata"]

        for rule_data in data.get("rules", []):
            rule = {
                "manufacturer": metadata.get("manufacturer", ""),
                "rule_type": rule_data.get("rule_type", ""),
                "source_identifier": rule_data.get("source_finish", rule_data.get("source", "")),
                "target_identifier": rule_data.get("target_finish", rule_data.get("target", "")),
                "rule_data": json.dumps(rule_data),
                "description": rule_data.get("description", ""),
                "effective_date": metadata.get("effective_date"),
                "confidence_score": float(rule_data.get("confidence", 0.5)),
            }
            rules.append(rule)

        return rules

    def _generate_item_key(self, item_data: Dict[str, Any]) -> str:
        """Generate a natural key for an item."""
        key_parts = [
            item_data.get("manufacturer", ""),
            item_data.get("family", ""),
            item_data.get("model", ""),
            item_data.get("finish", ""),
            item_data.get("size", "")
        ]
        key_string = "|".join(str(part).strip().lower() for part in key_parts)
        import hashlib
        return hashlib.sha256(key_string.encode('utf-8')).hexdigest()

    def _validate_row_against_schema(
        self,
        row: Dict[str, Any],
        schema: Any,
        row_identifier: str
    ) -> List[str]:
        """Validate a row against the table schema."""
        errors = []

        for field_def in schema.fields:
            if field_def.required and field_def.name not in row:
                errors.append(f"{row_identifier}: Missing required field '{field_def.name}'")

            if field_def.name in row:
                value = row[field_def.name]

                # Type validation
                if field_def.field_type == "number" and value is not None:
                    try:
                        float(value)
                    except (ValueError, TypeError):
                        errors.append(f"{row_identifier}: Invalid number for field '{field_def.name}': {value}")

                # Length validation for text fields
                if field_def.field_type == "text" and "max_length" in field_def.type_config:
                    max_length = field_def.type_config["max_length"]
                    if value and len(str(value)) > max_length:
                        errors.append(f"{row_identifier}: Field '{field_def.name}' exceeds max length {max_length}")

        return errors

    async def _update_sync_record(self, sync_record: Any, result: PublishResult):
        """Update sync record with final results."""
        try:
            with get_db_session() as session:
                sync_record.completed_at = datetime.utcnow()
                sync_record.status = "completed" if result.success else "failed"
                sync_record.rows_processed = result.total_rows_processed
                sync_record.rows_created = result.total_rows_created
                sync_record.rows_updated = result.total_rows_updated
                sync_record.errors = json.dumps(result.errors) if result.errors else None
                sync_record.summary = json.dumps(result.sync_summary)

                session.commit()

        except Exception as e:
            self.logger.error(f"Failed to update sync record: {e}")

    async def get_sync_status(self, sync_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a sync operation."""
        try:
            with get_db_session() as session:
                sync_record = session.query(BaserowSync).filter_by(id=sync_id).first()
                if not sync_record:
                    return None

                return {
                    "id": sync_record.id,
                    "price_book_id": sync_record.price_book_id,
                    "status": sync_record.status,
                    "started_at": sync_record.started_at.isoformat() if sync_record.started_at else None,
                    "completed_at": sync_record.completed_at.isoformat() if sync_record.completed_at else None,
                    "rows_processed": sync_record.rows_processed,
                    "rows_created": sync_record.rows_created,
                    "rows_updated": sync_record.rows_updated,
                    "errors": json.loads(sync_record.errors) if sync_record.errors else [],
                    "summary": json.loads(sync_record.summary) if sync_record.summary else {}
                }

        except Exception as e:
            self.logger.error(f"Failed to get sync status: {e}")
            return None


# Convenience function for simple publishing
async def publish_price_book_to_baserow(
    price_book_id: str,
    baserow_config: BaserowConfig,
    options: PublishOptions = None,
    user_id: str = None
) -> PublishResult:
    """
    Convenience function to publish a price book to Baserow.

    Args:
        price_book_id: ID of price book to publish
        baserow_config: Baserow connection configuration
        options: Publishing options
        user_id: User initiating the operation

    Returns:
        PublishResult with operation outcome
    """
    publisher = BaserowPublisher(baserow_config)
    return await publisher.publish_price_book(price_book_id, options, user_id)