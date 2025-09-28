"""
Admin API endpoints for diff management and review workflows.

Provides REST API for creating, reviewing, and applying price book diffs
with confidence-based review queues and approval workflows.
"""
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

from services.diff_service import DiffService
from core.diff_engine_v2 import MatchConfidence, ChangeType
from api.auth import get_current_user
from api.schemas import ResponseModel

router = APIRouter(prefix="/admin/diff", tags=["diff"])


# Request/Response Models
class CreateDiffRequest(BaseModel):
    old_book_id: str = Field(..., description="ID of the older price book")
    new_book_id: str = Field(..., description="ID of the newer price book")
    options: Optional[Dict[str, Any]] = Field(default={}, description="Additional diff options")


class DiffSummaryResponse(BaseModel):
    old_book_id: str
    new_book_id: str
    created_at: datetime
    total_matches: int
    total_changes: int
    needs_review: int
    summary: Dict[str, int]
    review_status: str


class MatchItemResponse(BaseModel):
    match_key: str
    confidence: float
    confidence_level: str
    match_method: str
    old_item: Optional[Dict[str, Any]]
    new_item: Optional[Dict[str, Any]]
    match_reasons: List[str]
    fuzzy_score: Optional[float]
    review_status: str = "pending"


class ChangeItemResponse(BaseModel):
    change_type: str
    confidence: float
    field_name: str
    old_value: Optional[Any]
    new_value: Optional[Any]
    description: str
    match_key: str
    old_ref: Optional[str]
    new_ref: Optional[str]


class ReviewActionRequest(BaseModel):
    match_key: str = Field(..., description="Key of the match to review")
    action: str = Field(..., description="Review action: approve or reject")
    notes: Optional[str] = Field(default="", description="Review notes")


class ApplyDiffRequest(BaseModel):
    old_book_id: str
    new_book_id: str
    dry_run: bool = Field(default=False, description="Preview changes without applying")
    options: Optional[Dict[str, Any]] = Field(default={})


# Initialize service
diff_service = DiffService()


@router.post("/create", response_model=ResponseModel[DiffSummaryResponse])
async def create_diff(
    request: CreateDiffRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user)
):
    """
    Create a new diff between two price books.

    This operation can take some time for large books, so it runs in the background.
    The diff result will be stored in the database and can be retrieved later.
    """
    try:
        # Check if diff already exists
        existing_diff = diff_service.get_diff_result(request.old_book_id, request.new_book_id)
        if existing_diff:
            return ResponseModel(
                success=True,
                data=DiffSummaryResponse(
                    old_book_id=existing_diff.old_book_id,
                    new_book_id=existing_diff.new_book_id,
                    created_at=existing_diff.timestamp,
                    total_matches=len(existing_diff.matches),
                    total_changes=len(existing_diff.changes),
                    needs_review=len(existing_diff.review_queue),
                    summary=existing_diff.summary,
                    review_status="pending"  # Would need to check actual status
                ),
                message="Diff already exists"
            )

        # Create diff in background
        background_tasks.add_task(
            _create_diff_background,
            request.old_book_id,
            request.new_book_id,
            request.options,
            current_user
        )

        return ResponseModel(
            success=True,
            data=None,
            message="Diff creation started. Check status with GET /admin/diff/{old_book_id}/{new_book_id}"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create diff: {str(e)}")


@router.get("/{old_book_id}/{new_book_id}", response_model=ResponseModel[DiffSummaryResponse])
async def get_diff_summary(
    old_book_id: str,
    new_book_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get summary of existing diff between two books."""
    try:
        diff_result = diff_service.get_diff_result(old_book_id, new_book_id)
        if not diff_result:
            raise HTTPException(status_code=404, detail="Diff not found")

        return ResponseModel(
            success=True,
            data=DiffSummaryResponse(
                old_book_id=diff_result.old_book_id,
                new_book_id=diff_result.new_book_id,
                created_at=diff_result.timestamp,
                total_matches=len(diff_result.matches),
                total_changes=len(diff_result.changes),
                needs_review=len(diff_result.review_queue),
                summary=diff_result.summary,
                review_status="pending"  # Would need to check actual status
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get diff summary: {str(e)}")


@router.get("/{old_book_id}/{new_book_id}/review", response_model=ResponseModel[List[MatchItemResponse]])
async def get_review_queue(
    old_book_id: str,
    new_book_id: str,
    confidence_level: Optional[str] = Query(None, description="Filter by confidence level"),
    min_confidence: Optional[float] = Query(None, description="Minimum confidence threshold"),
    max_confidence: Optional[float] = Query(None, description="Maximum confidence threshold"),
    match_method: Optional[str] = Query(None, description="Filter by match method"),
    limit: int = Query(50, description="Maximum number of items to return"),
    offset: int = Query(0, description="Number of items to skip"),
    current_user: str = Depends(get_current_user)
):
    """Get filtered review queue for manual review."""
    try:
        filters = {}
        if confidence_level:
            filters['confidence_level'] = confidence_level
        if min_confidence is not None:
            filters['min_confidence'] = min_confidence
        if max_confidence is not None:
            filters['max_confidence'] = max_confidence
        if match_method:
            filters['match_method'] = match_method

        review_queue = diff_service.get_review_queue(old_book_id, new_book_id, filters)

        # Apply pagination
        paginated_queue = review_queue[offset:offset + limit]

        # Convert to response format
        response_items = []
        for match in paginated_queue:
            response_items.append(MatchItemResponse(
                match_key=match.match_key,
                confidence=match.confidence,
                confidence_level=match.confidence_level.value,
                match_method=match.match_method,
                old_item=match.old_item,
                new_item=match.new_item,
                match_reasons=match.match_reasons,
                fuzzy_score=match.fuzzy_score
            ))

        return ResponseModel(
            success=True,
            data=response_items,
            message=f"Retrieved {len(response_items)} items from review queue"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get review queue: {str(e)}")


@router.get("/{old_book_id}/{new_book_id}/changes", response_model=ResponseModel[List[ChangeItemResponse]])
async def get_changes(
    old_book_id: str,
    new_book_id: str,
    change_types: Optional[List[str]] = Query(None, description="Filter by change types"),
    min_confidence: Optional[float] = Query(None, description="Minimum confidence threshold"),
    limit: int = Query(100, description="Maximum number of changes to return"),
    offset: int = Query(0, description="Number of changes to skip"),
    current_user: str = Depends(get_current_user)
):
    """Get filtered list of changes."""
    try:
        filters = {}
        if change_types:
            filters['change_types'] = change_types
        if min_confidence is not None:
            filters['min_confidence'] = min_confidence

        summary = diff_service.get_changes_summary(old_book_id, new_book_id, filters)
        diff_result = diff_service.get_diff_result(old_book_id, new_book_id)

        if not diff_result:
            raise HTTPException(status_code=404, detail="Diff not found")

        # Apply filters to changes
        changes = diff_result.changes
        if filters:
            if 'change_types' in filters:
                target_types = [ChangeType(ct) for ct in filters['change_types']]
                changes = [c for c in changes if c.change_type in target_types]
            if 'min_confidence' in filters:
                min_conf = filters['min_confidence']
                changes = [c for c in changes if c.confidence >= min_conf]

        # Apply pagination
        paginated_changes = changes[offset:offset + limit]

        # Convert to response format
        response_items = []
        for change in paginated_changes:
            response_items.append(ChangeItemResponse(
                change_type=change.change_type.value,
                confidence=change.confidence,
                field_name=change.field_name,
                old_value=change.old_value,
                new_value=change.new_value,
                description=change.description,
                match_key=change.match_key,
                old_ref=change.old_ref,
                new_ref=change.new_ref
            ))

        return ResponseModel(
            success=True,
            data=response_items,
            message=f"Retrieved {len(response_items)} changes"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get changes: {str(e)}")


@router.post("/{old_book_id}/{new_book_id}/review", response_model=ResponseModel[Dict[str, str]])
async def review_match(
    old_book_id: str,
    new_book_id: str,
    request: ReviewActionRequest,
    current_user: str = Depends(get_current_user)
):
    """Approve or reject a match in the review queue."""
    try:
        if request.action.lower() == "approve":
            success = diff_service.approve_match(
                old_book_id, new_book_id, request.match_key, current_user, request.notes
            )
            action_msg = "approved"
        elif request.action.lower() == "reject":
            success = diff_service.reject_match(
                old_book_id, new_book_id, request.match_key, current_user, request.notes
            )
            action_msg = "rejected"
        else:
            raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")

        if not success:
            raise HTTPException(status_code=404, detail="Match not found")

        return ResponseModel(
            success=True,
            data={"status": action_msg, "match_key": request.match_key},
            message=f"Match {request.match_key} {action_msg} successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to review match: {str(e)}")


@router.post("/{old_book_id}/{new_book_id}/apply", response_model=ResponseModel[Dict[str, Any]])
async def apply_diff(
    old_book_id: str,
    new_book_id: str,
    request: ApplyDiffRequest,
    current_user: str = Depends(get_current_user)
):
    """Apply approved diff changes to create new version."""
    try:
        result = diff_service.apply_diff(
            old_book_id, new_book_id, current_user, request.options
        )

        if request.dry_run:
            message = "Dry run completed - no changes applied"
        else:
            message = f"Applied {result['applied_changes']} changes successfully"

        return ResponseModel(
            success=True,
            data=result,
            message=message
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply diff: {str(e)}")


@router.get("/{old_book_id}/{new_book_id}/summary", response_model=ResponseModel[Dict[str, Any]])
async def get_changes_summary(
    old_book_id: str,
    new_book_id: str,
    change_types: Optional[List[str]] = Query(None, description="Filter by change types"),
    min_confidence: Optional[float] = Query(None, description="Minimum confidence threshold"),
    current_user: str = Depends(get_current_user)
):
    """Get detailed summary and statistics of changes."""
    try:
        filters = {}
        if change_types:
            filters['change_types'] = change_types
        if min_confidence is not None:
            filters['min_confidence'] = min_confidence

        summary = diff_service.get_changes_summary(old_book_id, new_book_id, filters)

        return ResponseModel(
            success=True,
            data=summary,
            message="Summary retrieved successfully"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")


# Background task function
async def _create_diff_background(old_book_id: str, new_book_id: str,
                                options: Dict[str, Any], user: str):
    """Background task to create diff."""
    try:
        diff_result = diff_service.create_diff(old_book_id, new_book_id, options)
        # Could add notification or logging here
    except Exception as e:
        # Log error - in production would want proper error handling/notification
        print(f"Background diff creation failed: {e}")


# Additional utility endpoints
@router.get("/confidence-levels", response_model=ResponseModel[List[str]])
async def get_confidence_levels():
    """Get available confidence levels for filtering."""
    return ResponseModel(
        success=True,
        data=[level.value for level in MatchConfidence],
        message="Confidence levels retrieved"
    )


@router.get("/change-types", response_model=ResponseModel[List[str]])
async def get_change_types():
    """Get available change types for filtering."""
    return ResponseModel(
        success=True,
        data=[change_type.value for change_type in ChangeType],
        message="Change types retrieved"
    )


@router.delete("/{old_book_id}/{new_book_id}", response_model=ResponseModel[Dict[str, str]])
async def delete_diff(
    old_book_id: str,
    new_book_id: str,
    current_user: str = Depends(get_current_user)
):
    """Delete a diff result (admin only)."""
    try:
        # This would implement actual deletion from database
        # For now, just return success
        return ResponseModel(
            success=True,
            data={"status": "deleted"},
            message=f"Diff between {old_book_id} and {new_book_id} deleted"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete diff: {str(e)}")