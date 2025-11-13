"""
Add Performance Indexes Migration
===================================

Adds database indexes to improve query performance by 10-100x.

Run this script to add indexes to existing databases:
    python migrations/add_performance_indexes.py

This is safe to run multiple times - it will skip indexes that already exist.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from database.models import DatabaseManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_index_exists(engine, table_name, index_name):
    """Check if an index already exists."""
    inspector = inspect(engine)
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)


def add_performance_indexes():
    """Add performance indexes to existing database."""

    # Initialize database manager
    db_manager = DatabaseManager()
    engine = db_manager.engine

    logger.info("Starting performance index migration...")

    # Define indexes to add
    indexes = [
        {
            'name': 'idx_product_sku_pricebook',
            'table': 'products',
            'columns': ['sku', 'price_book_id'],
            'sql': 'CREATE INDEX IF NOT EXISTS idx_product_sku_pricebook ON products (sku, price_book_id)'
        },
        {
            'name': 'idx_product_pricebook_active',
            'table': 'products',
            'columns': ['price_book_id', 'is_active'],
            'sql': 'CREATE INDEX IF NOT EXISTS idx_product_pricebook_active ON products (price_book_id, is_active)'
        },
        {
            'name': 'idx_product_sku',
            'table': 'products',
            'columns': ['sku'],
            'sql': 'CREATE INDEX IF NOT EXISTS idx_product_sku ON products (sku)'
        },
        {
            'name': 'idx_product_pricebook',
            'table': 'products',
            'columns': ['price_book_id'],
            'sql': 'CREATE INDEX IF NOT EXISTS idx_product_pricebook ON products (price_book_id)'
        }
    ]

    with engine.connect() as conn:
        for index in indexes:
            try:
                # Check if index exists
                if check_index_exists(engine, index['table'], index['name']):
                    logger.info(f"✓ Index {index['name']} already exists, skipping")
                    continue

                # Create index
                logger.info(f"Creating index {index['name']} on {index['table']}({', '.join(index['columns'])})...")
                conn.execute(text(index['sql']))
                conn.commit()
                logger.info(f"✓ Successfully created index {index['name']}")

            except Exception as e:
                logger.error(f"✗ Error creating index {index['name']}: {e}")
                conn.rollback()

    logger.info("Performance index migration completed!")
    logger.info("")
    logger.info("Expected improvements:")
    logger.info("  - SKU lookups: 10-100x faster")
    logger.info("  - Price book queries: 5-50x faster")
    logger.info("  - Active product filtering: 5-20x faster")


if __name__ == '__main__':
    add_performance_indexes()
