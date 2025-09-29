"""
Database connection and session management utilities.

Provides a unified interface for database operations across the application
with proper session management and connection pooling.
"""
import os
from contextlib import contextmanager
from database.models import DatabaseManager, Base


# Global database manager instance
_db_manager = None


def get_database_manager() -> DatabaseManager:
    """Get or create the global database manager instance."""
    global _db_manager

    if _db_manager is None:
        database_url = os.getenv('DATABASE_URL', 'sqlite:///price_books.db')
        _db_manager = DatabaseManager(database_url)

        # Ensure tables exist
        _db_manager.create_tables()

    return _db_manager


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.

    Provides automatic session management with proper cleanup
    and error handling.

    Usage:
        with get_db_session() as session:
            # Use session here
            pass
    """
    db_manager = get_database_manager()
    session = db_manager.get_session()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database():
    """Initialize the database with tables and sample data."""
    db_manager = get_database_manager()
    db_manager.init_database()


# Re-export commonly used models for convenience
from database.models import (
    Manufacturer, PriceBook, ProductFamily, Product, Finish, ProductOption, ChangeLog
)

__all__ = [
    'get_db_session',
    'get_database_manager',
    'init_database',
    'Base',
    'Manufacturer',
    'PriceBook',
    'ProductFamily',
    'Product',
    'Finish',
    'ProductOption',
    'ChangeLog'
]