"""
Diff service for managing price book comparisons and review workflows.

Handles diff creation, review queue management, and applying approved changes.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from pathlib import Path

from core.diff_engine_v2 import DiffEngineV2, DiffResult, MatchResult, Change, ChangeType, MatchConfidence
from core.database import get_db_session
from models.price_books import PriceBook
from models.diff_results import DiffResultModel, DiffChangeModel, DiffMatchModel

logger = logging.getLogger(__name__)


class DiffService:
    """
    Service for managing price book diffs and review workflows.

    Provides high-level interface for creating, reviewing, and applying
    price book differences with confidence-based review queues.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.diff_engine = DiffEngineV2(config.get('diff_engine', {}))
        self.logger = logging.getLogger(__name__)

    def create_diff(self, old_book_id: str, new_book_id: str,
                   options: Dict[str, Any] = None) -> DiffResult:
        """
        Create a comprehensive diff between two price books.

        Args:
            old_book_id: ID of the older price book
            new_book_id: ID of the newer price book
            options: Additional options for diff creation

        Returns:
            DiffResult with all changes and review queue
        """
        self.logger.info(f"Creating diff: {old_book_id} -> {new_book_id}")

        with get_db_session() as session:
            # Load price books
            old_book = session.query(PriceBook).filter_by(id=old_book_id).first()
            new_book = session.query(PriceBook).filter_by(id=new_book_id).first()

            if not old_book:
                raise ValueError(f"Old book not found: {old_book_id}")
            if not new_book:
                raise ValueError(f"New book not found: {new_book_id}")

            # Convert to diff-compatible format
            old_data = self._price_book_to_diff_data(old_book)
            new_data = self._price_book_to_diff_data(new_book)

            # Create diff
            diff_result = self.diff_engine.create_diff(old_data, new_data)

            # Store diff result in database
            self._store_diff_result(session, diff_result)

            self.logger.info(f"Diff created: {len(diff_result.changes)} changes, "
                           f"{len(diff_result.review_queue)} items need review")

            return diff_result

    def get_diff_result(self, old_book_id: str, new_book_id: str) -> Optional[DiffResult]:
        """
        Retrieve existing diff result from database.

        Args:
            old_book_id: ID of the older price book
            new_book_id: ID of the newer price book

        Returns:
            DiffResult if found, None otherwise
        """
        with get_db_session() as session:
            diff_model = session.query(DiffResultModel).filter_by(
                old_book_id=old_book_id,
                new_book_id=new_book_id
            ).order_by(DiffResultModel.created_at.desc()).first()

            if not diff_model:
                return None

            return self._model_to_diff_result(diff_model)

    def get_review_queue(self, old_book_id: str, new_book_id: str,
                        filters: Dict[str, Any] = None) -> List[MatchResult]:
        """
        Get filtered review queue for manual review.

        Args:
            old_book_id: ID of the older price book
            new_book_id: ID of the newer price book
            filters: Optional filters (confidence_level, change_type, etc.)

        Returns:
            Filtered list of matches needing review
        """
        diff_result = self.get_diff_result(old_book_id, new_book_id)
        if not diff_result:
            return []

        review_queue = diff_result.review_queue.copy()

        # Apply filters
        if filters:
            if 'confidence_level' in filters:
                target_level = MatchConfidence(filters['confidence_level'])
                review_queue = [m for m in review_queue if m.confidence_level == target_level]

            if 'min_confidence' in filters:
                min_conf = float(filters['min_confidence'])
                review_queue = [m for m in review_queue if m.confidence >= min_conf]

            if 'max_confidence' in filters:
                max_conf = float(filters['max_confidence'])
                review_queue = [m for m in review_queue if m.confidence <= max_conf]

            if 'match_method' in filters:
                method = filters['match_method']
                review_queue = [m for m in review_queue if m.match_method == method]

        return review_queue

    def get_changes_summary(self, old_book_id: str, new_book_id: str,
                          filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get summary of changes with optional filtering.

        Args:
            old_book_id: ID of the older price book
            new_book_id: ID of the newer price book
            filters: Optional filters for change types

        Returns:
            Summary dictionary with change counts and statistics
        """
        diff_result = self.get_diff_result(old_book_id, new_book_id)
        if not diff_result:
            return {'total_changes': 0}

        changes = diff_result.changes.copy()

        # Apply filters
        if filters:
            if 'change_types' in filters:
                target_types = [ChangeType(ct) for ct in filters['change_types']]
                changes = [c for c in changes if c.change_type in target_types]

            if 'min_confidence' in filters:
                min_conf = float(filters['min_confidence'])
                changes = [c for c in changes if c.confidence >= min_conf]

        # Calculate summary
        summary = {
            'total_changes': len(changes),
            'change_breakdown': {},
            'confidence_distribution': {},
            'price_change_stats': {}
        }

        # Count by change type
        for change in changes:
            change_type = change.change_type.value
            summary['change_breakdown'][change_type] = summary['change_breakdown'].get(change_type, 0) + 1

        # Count by confidence level
        for change in changes:
            conf_bucket = self._confidence_to_bucket(change.confidence)
            summary['confidence_distribution'][conf_bucket] = summary['confidence_distribution'].get(conf_bucket, 0) + 1

        # Price change statistics
        price_changes = [c for c in changes if c.change_type == ChangeType.PRICE_CHANGED]
        if price_changes:
            price_deltas = []
            for change in price_changes:
                old_price = change.old_value or 0
                new_price = change.new_value or 0
                if old_price > 0:
                    percent_change = ((new_price - old_price) / old_price) * 100
                    price_deltas.append(percent_change)

            if price_deltas:
                summary['price_change_stats'] = {
                    'count': len(price_deltas),
                    'avg_percent_change': sum(price_deltas) / len(price_deltas),
                    'min_percent_change': min(price_deltas),
                    'max_percent_change': max(price_deltas),
                    'increases': len([d for d in price_deltas if d > 0]),
                    'decreases': len([d for d in price_deltas if d < 0])
                }

        return summary

    def approve_match(self, old_book_id: str, new_book_id: str, match_key: str,
                     reviewer: str, notes: str = "") -> bool:
        """
        Approve a match from the review queue.

        Args:
            old_book_id: ID of the older price book
            new_book_id: ID of the newer price book
            match_key: Key of the match to approve
            reviewer: Username/ID of reviewer
            notes: Optional review notes

        Returns:
            True if successful
        """
        with get_db_session() as session:
            # Find the match in database
            diff_model = session.query(DiffResultModel).filter_by(
                old_book_id=old_book_id,
                new_book_id=new_book_id
            ).order_by(DiffResultModel.created_at.desc()).first()

            if not diff_model:
                return False

            match_model = session.query(DiffMatchModel).filter_by(
                diff_result_id=diff_model.id,
                match_key=match_key
            ).first()

            if not match_model:
                return False

            # Update match status
            match_model.review_status = 'approved'
            match_model.reviewer = reviewer
            match_model.review_notes = notes
            match_model.reviewed_at = datetime.now()

            session.commit()
            self.logger.info(f"Match {match_key} approved by {reviewer}")
            return True

    def reject_match(self, old_book_id: str, new_book_id: str, match_key: str,
                    reviewer: str, reason: str) -> bool:
        """
        Reject a match from the review queue.

        Args:
            old_book_id: ID of the older price book
            new_book_id: ID of the newer price book
            match_key: Key of the match to reject
            reviewer: Username/ID of reviewer
            reason: Reason for rejection

        Returns:
            True if successful
        """
        with get_db_session() as session:
            # Find the match in database
            diff_model = session.query(DiffResultModel).filter_by(
                old_book_id=old_book_id,
                new_book_id=new_book_id
            ).order_by(DiffResultModel.created_at.desc()).first()

            if not diff_model:
                return False

            match_model = session.query(DiffMatchModel).filter_by(
                diff_result_id=diff_model.id,
                match_key=match_key
            ).first()

            if not match_model:
                return False

            # Update match status
            match_model.review_status = 'rejected'
            match_model.reviewer = reviewer
            match_model.review_notes = reason
            match_model.reviewed_at = datetime.now()

            session.commit()
            self.logger.info(f"Match {match_key} rejected by {reviewer}: {reason}")
            return True

    def apply_diff(self, old_book_id: str, new_book_id: str, reviewer: str,
                  options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Apply approved diff changes to create new version.

        Args:
            old_book_id: ID of the older price book
            new_book_id: ID of the newer price book
            reviewer: Username/ID of reviewer applying changes
            options: Additional options (dry_run, etc.)

        Returns:
            Summary of applied changes
        """
        options = options or {}
        dry_run = options.get('dry_run', False)

        diff_result = self.get_diff_result(old_book_id, new_book_id)
        if not diff_result:
            raise ValueError("No diff result found")

        with get_db_session() as session:
            # Load target book
            target_book = session.query(PriceBook).filter_by(id=new_book_id).first()
            if not target_book:
                raise ValueError(f"Target book not found: {new_book_id}")

            # Get approved matches only
            approved_changes = self._get_approved_changes(session, diff_result)

            if dry_run:
                return {
                    'dry_run': True,
                    'changes_to_apply': len(approved_changes),
                    'changes': [self._change_to_dict(c) for c in approved_changes[:10]]  # Preview
                }

            # Apply changes
            applied_count = 0
            errors = []

            for change in approved_changes:
                try:
                    self._apply_change(session, target_book, change)
                    applied_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to apply change {change.match_key}: {e}")
                    errors.append(str(e))

            # Update book metadata
            target_book.version = target_book.version + 1 if target_book.version else 1
            target_book.last_modified = datetime.now()
            target_book.modified_by = reviewer

            session.commit()

            result = {
                'applied_changes': applied_count,
                'errors': errors,
                'new_version': target_book.version,
                'applied_by': reviewer,
                'applied_at': datetime.now().isoformat()
            }

            self.logger.info(f"Applied {applied_count} changes to book {new_book_id}")
            return result

    def _price_book_to_diff_data(self, book: PriceBook) -> Dict[str, Any]:
        """Convert PriceBook model to diff-compatible data structure."""
        # This would need to be implemented based on your actual PriceBook model
        # For now, return a structure that matches what the diff engine expects
        return {
            'id': book.id,
            'manufacturer': book.manufacturer,
            'effective_date': book.effective_date,
            'products': [],  # Would extract from book.products or related tables
            'price_rules': [],  # Would extract from book.price_rules
            'hinge_additions': []  # Would extract from book.options
        }

    def _store_diff_result(self, session, diff_result: DiffResult):
        """Store diff result in database."""
        # Create main diff result record
        diff_model = DiffResultModel(
            old_book_id=diff_result.old_book_id,
            new_book_id=diff_result.new_book_id,
            created_at=diff_result.timestamp,
            summary=json.dumps(diff_result.summary),
            metadata=json.dumps(diff_result.metadata)
        )
        session.add(diff_model)
        session.flush()  # Get ID

        # Store matches
        for match in diff_result.matches:
            match_model = DiffMatchModel(
                diff_result_id=diff_model.id,
                match_key=match.match_key,
                confidence=match.confidence,
                confidence_level=match.confidence_level.value,
                match_method=match.match_method,
                old_item_data=json.dumps(match.old_item) if match.old_item else None,
                new_item_data=json.dumps(match.new_item) if match.new_item else None,
                match_reasons=json.dumps(match.match_reasons),
                fuzzy_score=match.fuzzy_score,
                review_status='pending' if match.confidence < self.diff_engine.review_threshold else 'auto_approved'
            )
            session.add(match_model)

        # Store changes
        for change in diff_result.changes:
            change_model = DiffChangeModel(
                diff_result_id=diff_model.id,
                change_type=change.change_type.value,
                confidence=change.confidence,
                field_name=change.field_name,
                old_value=json.dumps(change.old_value) if change.old_value is not None else None,
                new_value=json.dumps(change.new_value) if change.new_value is not None else None,
                description=change.description,
                match_key=change.match_key,
                old_ref=change.old_ref,
                new_ref=change.new_ref,
                metadata=json.dumps(change.metadata)
            )
            session.add(change_model)

        session.commit()

    def _model_to_diff_result(self, diff_model: DiffResultModel) -> DiffResult:
        """Convert database model back to DiffResult."""
        # Load matches
        matches = []
        for match_model in diff_model.matches:
            match = MatchResult(
                old_item=json.loads(match_model.old_item_data) if match_model.old_item_data else None,
                new_item=json.loads(match_model.new_item_data) if match_model.new_item_data else None,
                confidence=match_model.confidence,
                confidence_level=MatchConfidence(match_model.confidence_level),
                match_key=match_model.match_key,
                match_method=match_model.match_method,
                match_reasons=json.loads(match_model.match_reasons) if match_model.match_reasons else [],
                fuzzy_score=match_model.fuzzy_score
            )
            matches.append(match)

        # Load changes
        changes = []
        for change_model in diff_model.changes:
            change = Change(
                change_type=ChangeType(change_model.change_type),
                confidence=change_model.confidence,
                old_value=json.loads(change_model.old_value) if change_model.old_value else None,
                new_value=json.loads(change_model.new_value) if change_model.new_value else None,
                field_name=change_model.field_name,
                description=change_model.description,
                match_key=change_model.match_key,
                old_ref=change_model.old_ref,
                new_ref=change_model.new_ref,
                metadata=json.loads(change_model.metadata) if change_model.metadata else {}
            )
            changes.append(change)

        # Create review queue (low confidence matches)
        review_queue = [m for m in matches if m.confidence < self.diff_engine.review_threshold]

        return DiffResult(
            old_book_id=diff_model.old_book_id,
            new_book_id=diff_model.new_book_id,
            timestamp=diff_model.created_at,
            matches=matches,
            changes=changes,
            summary=json.loads(diff_model.summary) if diff_model.summary else {},
            review_queue=review_queue,
            metadata=json.loads(diff_model.metadata) if diff_model.metadata else {}
        )

    def _confidence_to_bucket(self, confidence: float) -> str:
        """Convert confidence score to bucket name."""
        if confidence >= 0.9:
            return 'very_high'
        elif confidence >= 0.7:
            return 'high'
        elif confidence >= 0.5:
            return 'medium'
        elif confidence >= 0.3:
            return 'low'
        else:
            return 'very_low'

    def _get_approved_changes(self, session, diff_result: DiffResult) -> List[Change]:
        """Get only approved changes from diff result."""
        # This would query the database for approved matches and return corresponding changes
        # For now, return all changes with high confidence
        return [c for c in diff_result.changes if c.confidence >= 0.8]

    def _apply_change(self, session, target_book: PriceBook, change: Change):
        """Apply a single change to the target book."""
        # This would implement the actual change application logic
        # depending on the change type and your database schema

        if change.change_type == ChangeType.PRICE_CHANGED:
            # Update price in products table
            pass
        elif change.change_type == ChangeType.OPTION_AMOUNT_CHANGED:
            # Update option amount in options table
            pass
        # etc.

    def _change_to_dict(self, change: Change) -> Dict[str, Any]:
        """Convert Change object to dictionary."""
        return {
            'change_type': change.change_type.value,
            'confidence': change.confidence,
            'field_name': change.field_name,
            'old_value': change.old_value,
            'new_value': change.new_value,
            'description': change.description,
            'match_key': change.match_key,
            'metadata': change.metadata
        }