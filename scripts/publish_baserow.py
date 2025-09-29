#!/usr/bin/env python3
"""
CLI script for publishing price book data to Baserow.

Provides command-line interface for synchronizing processed price book
data to Baserow tables with options for dry-run, table selection,
and progress monitoring.
"""
import asyncio
import argparse
import json
import os
import sys
from datetime import datetime
from typing import Optional, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.baserow_client import BaserowConfig
from services.publish_baserow import BaserowPublisher, PublishOptions, PublishResult
from models.baserow_syncs import BaserowSync
from core.database import get_db_session, PriceBook
from core.observability import get_logger


def create_baserow_config_from_env() -> BaserowConfig:
    """Create Baserow configuration from environment variables."""
    api_url = os.getenv("BASEROW_API_URL", "https://api.baserow.io")
    api_token = os.getenv("BASEROW_API_TOKEN")

    if not api_token:
        raise ValueError(
            "BASEROW_API_TOKEN environment variable is required. "
            "Please set it to your Baserow API token."
        )

    workspace_id = os.getenv("BASEROW_WORKSPACE_ID")
    database_id = os.getenv("BASEROW_DATABASE_ID")

    return BaserowConfig(
        api_url=api_url,
        api_token=api_token,
        workspace_id=workspace_id,
        database_id=database_id,
        timeout_seconds=int(os.getenv("BASEROW_TIMEOUT", "300")),
        max_retries=int(os.getenv("BASEROW_MAX_RETRIES", "3")),
        rate_limit_requests_per_minute=int(os.getenv("BASEROW_RATE_LIMIT", "60"))
    )


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    import logging

    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def print_result_summary(result: PublishResult) -> None:
    """Print a formatted summary of the publish operation."""
    print("\n" + "="*60)
    print("BASEROW PUBLISH SUMMARY")
    print("="*60)

    status_emoji = "✅" if result.success else "❌"
    print(f"{status_emoji} Status: {'SUCCESS' if result.success else 'FAILED'}")

    if result.sync_id:
        print(f"📊 Sync ID: {result.sync_id}")

    print(f"⏱️  Duration: {result.duration_seconds:.2f} seconds")
    print(f"📋 Tables Processed: {len(result.tables_synced)}")

    if result.tables_synced:
        for table in result.tables_synced:
            print(f"   • {table}")

    print(f"📊 Total Rows Processed: {result.total_rows_processed:,}")
    print(f"➕ Rows Created: {result.total_rows_created:,}")
    print(f"🔄 Rows Updated: {result.total_rows_updated:,}")

    if result.warnings:
        print(f"\n⚠️  Warnings ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"   • {warning}")

    if result.errors:
        print(f"\n❌ Errors ({len(result.errors)}):")
        for error in result.errors:
            print(f"   • {error}")

    if result.sync_summary:
        print(f"\n📊 Detailed Summary:")
        for table_name, table_summary in result.sync_summary.items():
            if isinstance(table_summary, dict):
                total = table_summary.get("total_rows", 0)
                created = table_summary.get("rows_created", 0)
                updated = table_summary.get("rows_updated", 0)
                print(f"   {table_name}: {total:,} processed ({created:,} created, {updated:,} updated)")

    print("="*60)


def list_price_books() -> List[dict]:
    """List available price books."""
    with get_db_session() as session:

        books = session.query(PriceBook).order_by(PriceBook.upload_date.desc()).all()

        book_list = []
        for book in books:
            book_list.append({
                "id": book.id,
                "manufacturer": book.manufacturer.name if book.manufacturer else "Unknown",
                "effective_date": book.effective_date.isoformat() if book.effective_date else None,
                "filename": book.file_path.split('/')[-1] if book.file_path else 'Unknown',
                "created_at": book.upload_date.isoformat() if book.upload_date else None,
                "status": book.status
            })

        return book_list


def list_recent_syncs(price_book_id: str = None, limit: int = 10) -> List[dict]:
    """List recent Baserow sync operations."""
    with get_db_session() as session:
        syncs = BaserowSync.get_recent_syncs(
            session=session,
            price_book_id=price_book_id,
            limit=limit
        )

        return [sync.to_dict(include_details=False) for sync in syncs]


def get_sync_status(sync_id: str) -> Optional[dict]:
    """Get detailed status of a sync operation."""
    with get_db_session() as session:
        sync = session.query(BaserowSync).filter_by(id=sync_id).first()
        if sync:
            return sync.to_dict(include_details=True)
        return None


def validate_price_book_exists(price_book_id: str) -> bool:
    """Validate that a price book exists."""
    with get_db_session() as session:
        book = session.query(PriceBook).filter_by(id=price_book_id).first()
        return book is not None


async def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Publish price book data to Baserow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available price books
  python scripts/publish_baserow.py --list-books

  # Perform dry run
  python scripts/publish_baserow.py --book abc123 --dry-run

  # Publish specific tables only
  python scripts/publish_baserow.py --book abc123 --tables Items,Options

  # Check sync status
  python scripts/publish_baserow.py --sync-status def456

  # List recent syncs
  python scripts/publish_baserow.py --list-syncs --limit 5

Environment Variables:
  BASEROW_API_TOKEN       - Required: Your Baserow API token
  BASEROW_API_URL         - Optional: Baserow API URL (default: https://api.baserow.io)
  BASEROW_WORKSPACE_ID    - Optional: Target workspace ID
  BASEROW_DATABASE_ID     - Optional: Target database ID
  BASEROW_TIMEOUT         - Optional: Request timeout in seconds (default: 300)
  BASEROW_MAX_RETRIES     - Optional: Max retry attempts (default: 3)
  BASEROW_RATE_LIMIT      - Optional: Requests per minute (default: 60)
        """
    )

    # Main operation group
    operation_group = parser.add_mutually_exclusive_group(required=True)
    operation_group.add_argument(
        "--book", "-b",
        help="Price book ID to publish"
    )
    operation_group.add_argument(
        "--list-books",
        action="store_true",
        help="List available price books"
    )
    operation_group.add_argument(
        "--list-syncs",
        action="store_true",
        help="List recent sync operations"
    )
    operation_group.add_argument(
        "--sync-status",
        help="Get status of a specific sync operation (provide sync ID)"
    )

    # Publishing options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform validation without actual sync"
    )
    parser.add_argument(
        "--tables",
        help="Comma-separated list of tables to sync (default: all)"
    )
    parser.add_argument(
        "--force-full-sync",
        action="store_true",
        help="Re-sync all data even if unchanged"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        help="Number of rows to process per batch"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts for failed operations"
    )

    # Query options
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Limit number of results for list operations"
    )
    parser.add_argument(
        "--book-filter",
        help="Filter syncs by price book ID (for --list-syncs)"
    )

    # Output options
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = get_logger("publish_baserow_cli")

    try:
        # Handle list operations
        if args.list_books:
            books = list_price_books()
            if args.json:
                print(json.dumps(books, indent=2))
            else:
                print("\nAvailable Price Books:")
                print("="*80)
                print(f"{'ID':<38} {'Manufacturer':<15} {'Effective Date':<12} {'Status':<10} {'Created'}")
                print("-"*80)
                for book in books:
                    created = datetime.fromisoformat(book['created_at']).strftime('%Y-%m-%d') if book['created_at'] else 'Unknown'
                    eff_date = book['effective_date'][:10] if book['effective_date'] else 'N/A'
                    print(f"{book['id']:<38} {book['manufacturer']:<15} {eff_date:<12} {book['status']:<10} {created}")
            return

        if args.list_syncs:
            syncs = list_recent_syncs(args.book_filter, args.limit)
            if args.json:
                print(json.dumps(syncs, indent=2))
            else:
                print("\nRecent Sync Operations:")
                print("="*100)
                print(f"{'Sync ID':<38} {'Price Book':<38} {'Status':<10} {'Started':<12} {'Duration'}")
                print("-"*100)
                for sync in syncs:
                    started = datetime.fromisoformat(sync['started_at']).strftime('%Y-%m-%d %H:%M') if sync['started_at'] else 'N/A'
                    duration = f"{sync['duration_seconds']:.1f}s" if sync['duration_seconds'] else 'N/A'
                    print(f"{sync['id']:<38} {sync['price_book_id']:<38} {sync['status']:<10} {started:<12} {duration}")
            return

        if args.sync_status:
            sync_status = get_sync_status(args.sync_status)
            if not sync_status:
                print(f"❌ Sync operation not found: {args.sync_status}")
                sys.exit(1)

            if args.json:
                print(json.dumps(sync_status, indent=2))
            else:
                print(f"\nSync Operation Status: {args.sync_status}")
                print("="*60)
                print(f"Status: {sync_status['status']}")
                print(f"Price Book: {sync_status['price_book_id']}")
                print(f"Started: {sync_status['started_at']}")
                print(f"Completed: {sync_status['completed_at'] or 'In Progress'}")
                if sync_status['duration_seconds']:
                    print(f"Duration: {sync_status['duration_seconds']:.2f} seconds")
                print(f"Rows Processed: {sync_status['rows_processed'] or 0:,}")
                print(f"Rows Created: {sync_status['rows_created'] or 0:,}")
                print(f"Rows Updated: {sync_status['rows_updated'] or 0:,}")

                if sync_status['errors']:
                    print("\nErrors:")
                    for error in sync_status['errors']:
                        print(f"  • {error}")

                if sync_status['warnings']:
                    print("\nWarnings:")
                    for warning in sync_status['warnings']:
                        print(f"  • {warning}")
            return

        # Handle publish operation
        if args.book:
            # Validate price book exists
            if not validate_price_book_exists(args.book):
                print(f"❌ Price book not found: {args.book}")
                sys.exit(1)

            # Create Baserow configuration
            try:
                baserow_config = create_baserow_config_from_env()
            except ValueError as e:
                print(f"❌ Configuration error: {e}")
                sys.exit(1)

            # Create publish options
            tables_to_sync = None
            if args.tables:
                tables_to_sync = [table.strip() for table in args.tables.split(",")]

            options = PublishOptions(
                dry_run=args.dry_run,
                tables_to_sync=tables_to_sync,
                force_full_sync=args.force_full_sync,
                chunk_size=args.chunk_size,
                max_retries=args.max_retries
            )

            # Create publisher and run
            publisher = BaserowPublisher(baserow_config)

            print(f"🚀 Starting Baserow publish for price book: {args.book}")
            if args.dry_run:
                print("🔍 DRY RUN MODE - No data will be modified")

            result = await publisher.publish_price_book(
                price_book_id=args.book,
                options=options,
                user_id="cli_user"
            )

            if args.json:
                # Convert result to JSON-serializable format
                result_dict = {
                    "success": result.success,
                    "sync_id": result.sync_id,
                    "tables_synced": result.tables_synced,
                    "total_rows_processed": result.total_rows_processed,
                    "total_rows_created": result.total_rows_created,
                    "total_rows_updated": result.total_rows_updated,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "duration_seconds": result.duration_seconds,
                    "sync_summary": result.sync_summary
                }
                print(json.dumps(result_dict, indent=2))
            else:
                print_result_summary(result)

            # Exit with appropriate code
            sys.exit(0 if result.success else 1)

    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exception=e)
        print(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())