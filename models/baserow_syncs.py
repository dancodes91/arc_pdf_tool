"""
Database model for tracking Baserow synchronization operations.

Provides audit trail and status tracking for price book publishing
operations to Baserow with detailed outcome and error information.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
import uuid

from database.models import Base


class BaserowSync(Base):
    """
    Track Baserow synchronization operations.

    Provides comprehensive audit trail for publishing operations
    including status, timing, row counts, and error information.
    """
    __tablename__ = "baserow_syncs"

    # Primary identification
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    price_book_id = Column(Integer, ForeignKey("price_books.id"), nullable=False, index=True)

    # Operation tracking
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending, running, completed, failed
    initiated_by = Column(String(100), nullable=True)  # User ID or system identifier
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Configuration
    options = Column(Text, nullable=True)  # Publishing options as JSON string
    dry_run = Column(Boolean, nullable=False, default=False)

    # Results tracking
    rows_processed = Column(Integer, nullable=True, default=0)
    rows_created = Column(Integer, nullable=True, default=0)
    rows_updated = Column(Integer, nullable=True, default=0)
    tables_synced = Column(Text, nullable=True)  # List of table names synced as JSON string

    # Error and status information
    errors = Column(Text, nullable=True)  # JSON array of error messages
    warnings = Column(Text, nullable=True)  # JSON array of warning messages
    summary = Column(Text, nullable=True)  # Detailed operation summary as JSON string

    # Baserow-specific tracking
    baserow_workspace_id = Column(String(50), nullable=True, index=True)
    baserow_database_id = Column(String(50), nullable=True, index=True)

    # Relationships (note: PriceBook doesn't have back reference yet)
    # price_book = relationship("PriceBook")

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<BaserowSync(id={self.id}, price_book_id={self.price_book_id}, status={self.status})>"

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate operation duration in seconds."""
        if not self.started_at:
            return None

        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()

    @property
    def is_completed(self) -> bool:
        """Check if the sync operation is completed (success or failure)."""
        return self.status in ["completed", "failed"]

    @property
    def is_successful(self) -> bool:
        """Check if the sync operation completed successfully."""
        return self.status == "completed"

    @property
    def is_running(self) -> bool:
        """Check if the sync operation is currently running."""
        return self.status == "running"

    def to_dict(self, include_details: bool = True) -> dict:
        """
        Convert sync record to dictionary format.

        Args:
            include_details: Whether to include detailed error/summary information

        Returns:
            Dictionary representation of the sync record
        """
        base_data = {
            "id": self.id,
            "price_book_id": self.price_book_id,
            "status": self.status,
            "initiated_by": self.initiated_by,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "dry_run": self.dry_run,
            "rows_processed": self.rows_processed,
            "rows_created": self.rows_created,
            "rows_updated": self.rows_updated,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

        if include_details:
            import json
            base_data.update({
                "options": json.loads(self.options) if self.options else {},
                "tables_synced": json.loads(self.tables_synced) if self.tables_synced else [],
                "errors": json.loads(self.errors) if self.errors else [],
                "warnings": json.loads(self.warnings) if self.warnings else [],
                "summary": json.loads(self.summary) if self.summary else {},
                "baserow_workspace_id": self.baserow_workspace_id,
                "baserow_database_id": self.baserow_database_id
            })

        return base_data

    def update_from_result(self, result) -> None:
        """
        Update sync record from a PublishResult object.

        Args:
            result: PublishResult instance with operation outcome
        """
        import json

        self.status = "completed" if result.success else "failed"
        self.completed_at = datetime.utcnow()
        self.rows_processed = result.total_rows_processed
        self.rows_created = result.total_rows_created
        self.rows_updated = result.total_rows_updated

        if result.tables_synced:
            self.tables_synced = json.dumps(result.tables_synced)

        if result.errors:
            self.errors = json.dumps(result.errors)

        if result.warnings:
            self.warnings = json.dumps(result.warnings)

        if result.sync_summary:
            self.summary = json.dumps(result.sync_summary)

    @classmethod
    def create_for_operation(
        cls,
        price_book_id: str,
        user_id: str = None,
        options: dict = None,
        dry_run: bool = False
    ) -> "BaserowSync":
        """
        Create a new sync record for an operation.

        Args:
            price_book_id: ID of the price book being synced
            user_id: User initiating the operation
            options: Publishing options
            dry_run: Whether this is a dry run operation

        Returns:
            New BaserowSync instance
        """
        import json

        return cls(
            price_book_id=price_book_id,
            initiated_by=user_id,
            status="pending",
            dry_run=dry_run,
            options=json.dumps(options) if options else None,
            started_at=datetime.utcnow()
        )

    @classmethod
    def get_recent_syncs(
        cls,
        session,
        price_book_id: str = None,
        limit: int = 50,
        status: str = None
    ) -> list:
        """
        Get recent sync operations.

        Args:
            session: Database session
            price_book_id: Optional filter by price book
            limit: Maximum number of records to return
            status: Optional filter by status

        Returns:
            List of BaserowSync instances
        """
        query = session.query(cls).order_by(cls.started_at.desc())

        if price_book_id:
            query = query.filter(cls.price_book_id == price_book_id)

        if status:
            query = query.filter(cls.status == status)

        return query.limit(limit).all()

    @classmethod
    def get_active_syncs(cls, session) -> list:
        """
        Get all currently active (running) sync operations.

        Args:
            session: Database session

        Returns:
            List of active BaserowSync instances
        """
        return session.query(cls).filter(cls.status == "running").all()

    @classmethod
    def cleanup_old_syncs(
        cls,
        session,
        days_to_keep: int = 30,
        keep_failed: bool = True
    ) -> int:
        """
        Clean up old sync records.

        Args:
            session: Database session
            days_to_keep: Number of days of records to keep
            keep_failed: Whether to preserve failed syncs longer

        Returns:
            Number of records deleted
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        query = session.query(cls).filter(cls.created_at < cutoff_date)

        if keep_failed:
            # Only delete successful/completed operations
            query = query.filter(cls.status == "completed")

        count = query.count()
        query.delete(synchronize_session=False)
        session.commit()

        return count


# Add relationship to PriceBook model (this would go in the price_books.py file)
# This is here for reference - you'd need to add this to the actual PriceBook model:
"""
# In models/price_books.py, add this relationship:
baserow_syncs = relationship("BaserowSync", back_populates="price_book", cascade="all, delete-orphan")
"""