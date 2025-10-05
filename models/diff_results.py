"""
Database models for storing diff results and review workflows.

Stores diff comparisons, matches, changes, and review status for
price book difference analysis and approval workflows.
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class DiffResultModel(Base):
    """Main diff result between two price books."""

    __tablename__ = "diff_results"

    id = Column(Integer, primary_key=True)
    old_book_id = Column(String(100), nullable=False, index=True)
    new_book_id = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    created_by = Column(String(100))

    # Summary statistics (JSON)
    summary = Column(JSON)

    # Configuration and metadata
    metadata = Column(JSON)

    # Review and approval status
    review_status = Column(String(50), default="pending")  # pending, in_review, approved, rejected
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)

    # Application status
    applied = Column(Boolean, default=False)
    applied_by = Column(String(100))
    applied_at = Column(DateTime)

    # Relationships
    matches = relationship(
        "DiffMatchModel", back_populates="diff_result", cascade="all, delete-orphan"
    )
    changes = relationship(
        "DiffChangeModel", back_populates="diff_result", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<DiffResult({self.old_book_id} -> {self.new_book_id})>"


class DiffMatchModel(Base):
    """Individual item match between old and new books."""

    __tablename__ = "diff_matches"

    id = Column(Integer, primary_key=True)
    diff_result_id = Column(Integer, ForeignKey("diff_results.id"), nullable=False)

    # Match identification
    match_key = Column(String(255), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    confidence_level = Column(String(20), nullable=False)  # exact, high, medium, low, very_low
    match_method = Column(String(50), nullable=False)  # exact_key, fuzzy, removed, added

    # Match details
    match_reasons = Column(JSON)  # List of reasons for this match
    fuzzy_score = Column(Float)  # Fuzzy matching score if applicable

    # Item data (JSON snapshots)
    old_item_data = Column(JSON)
    new_item_data = Column(JSON)

    # Review status
    review_status = Column(
        String(50), default="pending"
    )  # pending, approved, rejected, auto_approved
    reviewer = Column(String(100))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=func.now())

    # Relationships
    diff_result = relationship("DiffResultModel", back_populates="matches")

    def __repr__(self):
        return f"<DiffMatch({self.match_key}, {self.confidence:.2f})>"


class DiffChangeModel(Base):
    """Individual change detected in diff."""

    __tablename__ = "diff_changes"

    id = Column(Integer, primary_key=True)
    diff_result_id = Column(Integer, ForeignKey("diff_results.id"), nullable=False)

    # Change identification
    change_type = Column(String(50), nullable=False)  # added, removed, price_changed, etc.
    confidence = Column(Float, nullable=False)
    field_name = Column(String(100), nullable=False)
    match_key = Column(String(255), nullable=False, index=True)

    # Change values
    old_value = Column(JSON)
    new_value = Column(JSON)
    description = Column(Text)

    # References
    old_ref = Column(String(255))  # Reference to old item
    new_ref = Column(String(255))  # Reference to new item

    # Additional metadata
    metadata = Column(JSON)

    # Application status
    applied = Column(Boolean, default=False)
    applied_at = Column(DateTime)
    applied_by = Column(String(100))

    # Timestamps
    created_at = Column(DateTime, default=func.now())

    # Relationships
    diff_result = relationship("DiffResultModel", back_populates="changes")

    def __repr__(self):
        return f"<DiffChange({self.change_type}, {self.field_name})>"


class DiffReviewSession(Base):
    """Review session for managing diff approval workflows."""

    __tablename__ = "diff_review_sessions"

    id = Column(Integer, primary_key=True)
    diff_result_id = Column(Integer, ForeignKey("diff_results.id"), nullable=False)

    # Session details
    reviewer = Column(String(100), nullable=False)
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime)

    # Review progress
    total_items = Column(Integer, default=0)
    reviewed_items = Column(Integer, default=0)
    approved_items = Column(Integer, default=0)
    rejected_items = Column(Integer, default=0)

    # Session status
    status = Column(String(50), default="active")  # active, completed, abandoned
    notes = Column(Text)

    # Configuration
    review_filters = Column(JSON)  # Filters used for this review session

    def __repr__(self):
        return f"<DiffReviewSession({self.reviewer}, {self.status})>"


class DiffApprovalLog(Base):
    """Log of diff applications and their results."""

    __tablename__ = "diff_approval_log"

    id = Column(Integer, primary_key=True)
    diff_result_id = Column(Integer, ForeignKey("diff_results.id"), nullable=False)

    # Application details
    applied_by = Column(String(100), nullable=False)
    applied_at = Column(DateTime, default=func.now())

    # Results
    changes_applied = Column(Integer, default=0)
    changes_failed = Column(Integer, default=0)
    errors = Column(JSON)  # List of errors if any

    # Configuration
    dry_run = Column(Boolean, default=False)
    options = Column(JSON)  # Application options used

    # Success/failure summary
    success = Column(Boolean, default=True)
    error_message = Column(Text)

    def __repr__(self):
        return f"<DiffApprovalLog({self.applied_by}, {self.changes_applied} changes)>"


class DiffMetrics(Base):
    """Metrics and statistics about diff operations."""

    __tablename__ = "diff_metrics"

    id = Column(Integer, primary_key=True)

    # Time period
    date = Column(DateTime, default=func.now())
    period_type = Column(String(20))  # daily, weekly, monthly

    # Diff statistics
    diffs_created = Column(Integer, default=0)
    diffs_reviewed = Column(Integer, default=0)
    diffs_applied = Column(Integer, default=0)

    # Match statistics
    total_matches = Column(Integer, default=0)
    exact_matches = Column(Integer, default=0)
    fuzzy_matches = Column(Integer, default=0)
    manual_reviews = Column(Integer, default=0)

    # Change statistics
    total_changes = Column(Integer, default=0)
    price_changes = Column(Integer, default=0)
    additions = Column(Integer, default=0)
    removals = Column(Integer, default=0)
    renames = Column(Integer, default=0)

    # Performance metrics
    avg_confidence = Column(Float)
    avg_review_time_hours = Column(Float)
    avg_application_time_minutes = Column(Float)

    # Error rates
    match_error_rate = Column(Float)
    application_error_rate = Column(Float)

    def __repr__(self):
        return f"<DiffMetrics({self.date}, {self.diffs_created} diffs)>"
