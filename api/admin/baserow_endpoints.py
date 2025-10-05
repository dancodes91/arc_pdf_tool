"""
Admin API endpoints for Baserow publishing and synchronization management.

Provides REST API for publishing price books to Baserow, monitoring sync status,
and managing synchronization operations with comprehensive status tracking.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
import json

from services.publish_baserow import BaserowPublisher, PublishOptions
from integrations.baserow_client import BaserowConfig
from models.baserow_syncs import BaserowSync
from core.database import get_db_session, PriceBook, Manufacturer
from api.auth import get_current_user
from api.schemas import ResponseModel
from core.observability import get_logger

router = APIRouter(prefix="/admin/baserow", tags=["baserow"])
logger = get_logger("baserow_admin")


# Request/Response Models
class PublishRequest(BaseModel):
    price_book_id: str = Field(..., description="ID of the price book to publish")
    dry_run: bool = Field(default=False, description="Perform validation without actual sync")
    tables_to_sync: Optional[List[str]] = Field(
        default=None, description="Tables to sync (default: all)"
    )
    force_full_sync: bool = Field(default=False, description="Force full re-sync of all data")
    chunk_size: Optional[int] = Field(default=None, description="Batch size for processing")
    max_retries: int = Field(default=3, description="Maximum retry attempts")


class PublishResponse(BaseModel):
    sync_id: str
    status: str
    message: str
    started_at: datetime


class SyncStatusResponse(BaseModel):
    sync_id: str
    price_book_id: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    rows_processed: int
    rows_created: int
    rows_updated: int
    tables_synced: List[str]
    errors: List[str]
    warnings: List[str]
    summary: Dict[str, Any]


class SyncListResponse(BaseModel):
    sync_id: str
    price_book_id: str
    manufacturer: Optional[str]
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    rows_processed: int
    initiated_by: Optional[str]


class BaserowConfigResponse(BaseModel):
    api_url: str
    workspace_id: Optional[str]
    database_id: Optional[str]
    is_configured: bool
    connection_status: str


def get_baserow_config() -> BaserowConfig:
    """Get Baserow configuration from environment."""
    import os

    api_url = os.getenv("BASEROW_API_URL", "https://api.baserow.io")
    api_token = os.getenv("BASEROW_API_TOKEN")

    if not api_token:
        raise HTTPException(
            status_code=503,
            detail="Baserow API token not configured. Please set BASEROW_API_TOKEN environment variable.",
        )

    return BaserowConfig(
        api_url=api_url,
        api_token=api_token,
        workspace_id=os.getenv("BASEROW_WORKSPACE_ID"),
        database_id=os.getenv("BASEROW_DATABASE_ID"),
        timeout_seconds=int(os.getenv("BASEROW_TIMEOUT", "300")),
        max_retries=int(os.getenv("BASEROW_MAX_RETRIES", "3")),
        rate_limit_requests_per_minute=int(os.getenv("BASEROW_RATE_LIMIT", "60")),
    )


@router.get("/config", response_model=ResponseModel[BaserowConfigResponse])
async def get_baserow_configuration(current_user: str = Depends(get_current_user)):
    """Get current Baserow configuration and connection status."""
    try:
        import os

        api_token = os.getenv("BASEROW_API_TOKEN")
        is_configured = bool(api_token)

        config_data = {
            "api_url": os.getenv("BASEROW_API_URL", "https://api.baserow.io"),
            "workspace_id": os.getenv("BASEROW_WORKSPACE_ID"),
            "database_id": os.getenv("BASEROW_DATABASE_ID"),
            "is_configured": is_configured,
            "connection_status": "unknown",
        }

        if is_configured:
            try:
                baserow_config = get_baserow_config()
                # Test connection
                from integrations.baserow_client import BaserowClient

                async with BaserowClient(baserow_config) as client:
                    connection_ok = await client.test_connection()
                    config_data["connection_status"] = "connected" if connection_ok else "error"
            except Exception as e:
                logger.warning(f"Failed to test Baserow connection: {e}")
                config_data["connection_status"] = "error"
        else:
            config_data["connection_status"] = "not_configured"

        return ResponseModel(
            success=True,
            data=BaserowConfigResponse(**config_data),
            message="Configuration retrieved successfully",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {str(e)}")


@router.post("/publish", response_model=ResponseModel[PublishResponse])
async def publish_to_baserow(
    request: PublishRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
):
    """
    Publish a price book to Baserow.

    This operation runs in the background and can be monitored via the sync status endpoint.
    """
    try:
        # Validate price book exists
        with get_db_session() as session:
            price_book = session.query(PriceBook).filter_by(id=request.price_book_id).first()
            if not price_book:
                raise HTTPException(
                    status_code=404, detail=f"Price book not found: {request.price_book_id}"
                )

        # Get Baserow configuration
        baserow_config = get_baserow_config()

        # Create publish options
        options = PublishOptions(
            dry_run=request.dry_run,
            tables_to_sync=request.tables_to_sync,
            force_full_sync=request.force_full_sync,
            chunk_size=request.chunk_size,
            max_retries=request.max_retries,
        )

        # Start background task
        if request.dry_run:
            # For dry runs, execute immediately and return result
            publisher = BaserowPublisher(baserow_config)
            result = await publisher.publish_price_book(
                price_book_id=request.price_book_id, options=options, user_id=current_user
            )

            return ResponseModel(
                success=True,
                data=PublishResponse(
                    sync_id="dry_run",
                    status="completed",
                    message=(
                        "Dry run completed successfully" if result.success else "Dry run failed"
                    ),
                    started_at=datetime.utcnow(),
                ),
                message="Dry run executed immediately",
            )
        else:
            # Create sync record
            with get_db_session() as session:
                sync_record = BaserowSync.create_for_operation(
                    price_book_id=request.price_book_id,
                    user_id=current_user,
                    options=options.__dict__,
                    dry_run=request.dry_run,
                )
                sync_record.status = "running"
                session.add(sync_record)
                session.commit()
                sync_id = sync_record.id

            # Start background task
            background_tasks.add_task(
                _publish_background_task,
                sync_id,
                request.price_book_id,
                options,
                baserow_config,
                current_user,
            )

            return ResponseModel(
                success=True,
                data=PublishResponse(
                    sync_id=sync_id,
                    status="running",
                    message="Publishing started in background",
                    started_at=datetime.utcnow(),
                ),
                message=f"Publish operation started. Monitor progress at /admin/baserow/sync/{sync_id}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start publish operation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start publish operation: {str(e)}")


@router.get("/sync/{sync_id}", response_model=ResponseModel[SyncStatusResponse])
async def get_sync_status(sync_id: str, current_user: str = Depends(get_current_user)):
    """Get detailed status of a sync operation."""
    try:
        with get_db_session() as session:
            sync = session.query(BaserowSync).filter_by(id=sync_id).first()
            if not sync:
                raise HTTPException(status_code=404, detail=f"Sync operation not found: {sync_id}")

            sync_data = sync.to_dict(include_details=True)

            return ResponseModel(
                success=True,
                data=SyncStatusResponse(
                    sync_id=sync_data["id"],
                    price_book_id=sync_data["price_book_id"],
                    status=sync_data["status"],
                    started_at=(
                        datetime.fromisoformat(sync_data["started_at"])
                        if sync_data["started_at"]
                        else None
                    ),
                    completed_at=(
                        datetime.fromisoformat(sync_data["completed_at"])
                        if sync_data["completed_at"]
                        else None
                    ),
                    duration_seconds=sync_data["duration_seconds"],
                    rows_processed=sync_data["rows_processed"] or 0,
                    rows_created=sync_data["rows_created"] or 0,
                    rows_updated=sync_data["rows_updated"] or 0,
                    tables_synced=sync_data["tables_synced"],
                    errors=sync_data["errors"],
                    warnings=sync_data["warnings"],
                    summary=sync_data["summary"],
                ),
                message="Sync status retrieved successfully",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sync status: {str(e)}")


@router.get("/syncs", response_model=ResponseModel[List[SyncListResponse]])
async def list_sync_operations(
    price_book_id: Optional[str] = Query(None, description="Filter by price book ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Maximum number of results"),
    offset: int = Query(0, description="Number of results to skip"),
    current_user: str = Depends(get_current_user),
):
    """List recent sync operations with optional filtering."""
    try:
        with get_db_session() as session:
            query = session.query(BaserowSync).join(
                PriceBook, BaserowSync.price_book_id == PriceBook.id
            )

            # Apply filters
            if price_book_id:
                query = query.filter(BaserowSync.price_book_id == price_book_id)
            if status:
                query = query.filter(BaserowSync.status == status)

            # Apply pagination and ordering
            query = query.order_by(BaserowSync.started_at.desc()).offset(offset).limit(limit)

            syncs = query.all()

            # Convert to response format
            sync_list = []
            for sync in syncs:
                sync_list.append(
                    SyncListResponse(
                        sync_id=sync.id,
                        price_book_id=sync.price_book_id,
                        manufacturer=sync.price_book.manufacturer if sync.price_book else None,
                        status=sync.status,
                        started_at=sync.started_at,
                        completed_at=sync.completed_at,
                        duration_seconds=sync.duration_seconds,
                        rows_processed=sync.rows_processed or 0,
                        initiated_by=sync.initiated_by,
                    )
                )

            return ResponseModel(
                success=True, data=sync_list, message=f"Retrieved {len(sync_list)} sync operations"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sync operations: {str(e)}")


@router.delete("/sync/{sync_id}", response_model=ResponseModel[Dict[str, str]])
async def cancel_sync_operation(sync_id: str, current_user: str = Depends(get_current_user)):
    """Cancel a running sync operation."""
    try:
        with get_db_session() as session:
            sync = session.query(BaserowSync).filter_by(id=sync_id).first()
            if not sync:
                raise HTTPException(status_code=404, detail=f"Sync operation not found: {sync_id}")

            if sync.status not in ["running", "pending"]:
                raise HTTPException(
                    status_code=400, detail=f"Cannot cancel sync in status: {sync.status}"
                )

            # Update status to cancelled
            sync.status = "cancelled"
            sync.completed_at = datetime.utcnow()
            session.commit()

            return ResponseModel(
                success=True,
                data={"sync_id": sync_id, "status": "cancelled"},
                message="Sync operation cancelled successfully",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel sync operation: {str(e)}")


@router.get("/price-books", response_model=ResponseModel[List[Dict[str, Any]]])
async def list_price_books_for_publishing(
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer"),
    limit: int = Query(50, description="Maximum number of results"),
    current_user: str = Depends(get_current_user),
):
    """List available price books that can be published to Baserow."""
    try:
        with get_db_session() as session:
            query = session.query(PriceBook)

            if manufacturer:
                query = query.join(PriceBook.manufacturer).filter(
                    Manufacturer.name.ilike(f"%{manufacturer}%")
                )

            query = query.order_by(PriceBook.effective_date.desc(), PriceBook.upload_date.desc())
            query = query.limit(limit)

            books = query.all()

            # Get recent sync status for each book
            book_list = []
            for book in books:
                # Get most recent sync for this book
                recent_sync = (
                    session.query(BaserowSync)
                    .filter_by(price_book_id=book.id)
                    .order_by(BaserowSync.started_at.desc())
                    .first()
                )

                book_info = {
                    "id": book.id,
                    "manufacturer": book.manufacturer.name if book.manufacturer else "Unknown",
                    "effective_date": (
                        book.effective_date.isoformat() if book.effective_date else None
                    ),
                    "filename": book.file_path.split("/")[-1] if book.file_path else "Unknown",
                    "created_at": book.upload_date.isoformat() if book.upload_date else None,
                    "processing_status": book.status,
                    "last_sync": None,
                }

                if recent_sync:
                    book_info["last_sync"] = {
                        "sync_id": recent_sync.id,
                        "status": recent_sync.status,
                        "started_at": (
                            recent_sync.started_at.isoformat() if recent_sync.started_at else None
                        ),
                        "completed_at": (
                            recent_sync.completed_at.isoformat()
                            if recent_sync.completed_at
                            else None
                        ),
                        "rows_processed": recent_sync.rows_processed or 0,
                    }

                book_list.append(book_info)

            return ResponseModel(
                success=True, data=book_list, message=f"Retrieved {len(book_list)} price books"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list price books: {str(e)}")


@router.get("/tables", response_model=ResponseModel[List[Dict[str, Any]]])
async def list_available_tables(current_user: str = Depends(get_current_user)):
    """List available tables for Baserow synchronization."""
    try:
        from integrations.baserow_client import ARC_SCHEMA_DEFINITIONS

        tables = []
        for table_name, schema in ARC_SCHEMA_DEFINITIONS.items():
            tables.append(
                {
                    "name": table_name,
                    "description": schema.description,
                    "field_count": len(schema.fields),
                    "natural_key_fields": schema.natural_key_fields,
                    "required_fields": [f.name for f in schema.fields if f.required],
                }
            )

        return ResponseModel(
            success=True, data=tables, message=f"Retrieved {len(tables)} available tables"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tables: {str(e)}")


@router.post("/test-connection", response_model=ResponseModel[Dict[str, Any]])
async def test_baserow_connection(current_user: str = Depends(get_current_user)):
    """Test connection to Baserow API."""
    try:
        baserow_config = get_baserow_config()

        from integrations.baserow_client import BaserowClient

        async with BaserowClient(baserow_config) as client:
            connection_ok = await client.test_connection()

            if connection_ok:
                # Get workspace info if available
                workspace_info = None
                if baserow_config.workspace_id:
                    try:
                        workspace_info = await client.get_workspace_info()
                    except Exception as e:
                        logger.warning(f"Failed to get workspace info: {e}")

                return ResponseModel(
                    success=True,
                    data={
                        "connection_status": "success",
                        "api_url": baserow_config.api_url,
                        "workspace_id": baserow_config.workspace_id,
                        "database_id": baserow_config.database_id,
                        "workspace_info": workspace_info,
                    },
                    message="Connection to Baserow successful",
                )
            else:
                return ResponseModel(
                    success=False,
                    data={"connection_status": "failed"},
                    message="Failed to connect to Baserow API",
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")


# Background task function
async def _publish_background_task(
    sync_id: str,
    price_book_id: str,
    options: PublishOptions,
    baserow_config: BaserowConfig,
    user_id: str,
):
    """Background task to execute the publish operation."""
    try:
        logger.info(f"Starting background publish task for sync {sync_id}")

        # Create publisher and execute
        publisher = BaserowPublisher(baserow_config)
        result = await publisher.publish_price_book(
            price_book_id=price_book_id, options=options, user_id=user_id
        )

        # Update sync record with final results
        with get_db_session() as session:
            sync = session.query(BaserowSync).filter_by(id=sync_id).first()
            if sync:
                sync.update_from_result(result)
                session.commit()

        logger.info(
            f"Background publish task completed for sync {sync_id}, success: {result.success}"
        )

    except Exception as e:
        logger.error(f"Background publish task failed for sync {sync_id}: {e}")

        # Update sync record with error
        try:
            with get_db_session() as session:
                sync = session.query(BaserowSync).filter_by(id=sync_id).first()
                if sync:
                    sync.status = "failed"
                    sync.completed_at = datetime.utcnow()
                    sync.errors = json.dumps([str(e)])
                    session.commit()
        except Exception as update_error:
            logger.error(f"Failed to update sync record after error: {update_error}")


# Statistics endpoint
@router.get("/stats", response_model=ResponseModel[Dict[str, Any]])
async def get_baserow_statistics(current_user: str = Depends(get_current_user)):
    """Get Baserow synchronization statistics."""
    try:
        with get_db_session() as session:
            # Get basic counts
            total_syncs = session.query(BaserowSync).count()
            successful_syncs = session.query(BaserowSync).filter_by(status="completed").count()
            failed_syncs = session.query(BaserowSync).filter_by(status="failed").count()
            running_syncs = session.query(BaserowSync).filter_by(status="running").count()

            # Get recent activity (last 30 days)
            from datetime import timedelta

            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_syncs = (
                session.query(BaserowSync).filter(BaserowSync.started_at >= thirty_days_ago).count()
            )

            # Calculate average duration for completed syncs
            completed_syncs = session.query(BaserowSync).filter_by(status="completed").all()
            avg_duration = None
            if completed_syncs:
                durations = [
                    sync.duration_seconds for sync in completed_syncs if sync.duration_seconds
                ]
                if durations:
                    avg_duration = sum(durations) / len(durations)

            # Get total rows processed
            total_rows_processed = (
                session.query(BaserowSync)
                .filter(BaserowSync.rows_processed.isnot(None))
                .with_entities(BaserowSync.rows_processed)
                .all()
            )
            total_rows = sum(row[0] for row in total_rows_processed if row[0])

            stats = {
                "total_syncs": total_syncs,
                "successful_syncs": successful_syncs,
                "failed_syncs": failed_syncs,
                "running_syncs": running_syncs,
                "recent_syncs_30_days": recent_syncs,
                "success_rate": (successful_syncs / total_syncs * 100) if total_syncs > 0 else 0,
                "average_duration_seconds": avg_duration,
                "total_rows_processed": total_rows,
                "last_updated": datetime.utcnow().isoformat(),
            }

            return ResponseModel(
                success=True, data=stats, message="Statistics retrieved successfully"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")
