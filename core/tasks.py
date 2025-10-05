"""
Celery tasks for asynchronous PDF processing.

This module defines all background tasks that can be executed
by Celery workers for processing PDF files and other long-running operations.
"""

import os
from typing import Dict, Any
from datetime import datetime

try:
    from celery import Celery

    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

from core.observability import get_logger

logger = get_logger("core.tasks")

# Initialize Celery app
if CELERY_AVAILABLE:
    celery_app = Celery("arc_pdf_tool")

    # Configure Celery
    celery_app.conf.update(
        broker_url=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        result_backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,  # 30 minutes
        task_soft_time_limit=25 * 60,  # 25 minutes
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
    )

    @celery_app.task(bind=True, name="core.tasks.process_pdf")
    def process_pdf_task(self, file_path: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process PDF file asynchronously.

        Args:
            file_path: Path to the PDF file to process
            options: Processing options and configuration

        Returns:
            Dict containing processing results and metadata
        """
        logger.info(f"Starting PDF processing task for: {file_path}")

        try:
            # Update task state
            self.update_state(
                state="PROGRESS",
                meta={"current": 0, "total": 100, "status": "Starting processing..."},
            )

            # TODO: Import and use actual PDF processing logic
            # from parsers.pdf_processor import PDFProcessor
            # processor = PDFProcessor()
            # result = processor.process(file_path, options)

            # Placeholder processing logic
            import time

            for i in range(1, 11):
                time.sleep(1)  # Simulate processing
                self.update_state(
                    state="PROGRESS",
                    meta={"current": i * 10, "total": 100, "status": f"Processing step {i}/10..."},
                )

            result = {
                "success": True,
                "file_path": file_path,
                "processed_at": datetime.utcnow().isoformat(),
                "items_extracted": 150,
                "options_extracted": 25,
                "rules_extracted": 8,
                "processing_time_seconds": 10.0,
            }

            logger.info(f"PDF processing completed for: {file_path}")
            return result

        except Exception as exc:
            logger.error(f"PDF processing failed for {file_path}: {exc}")
            self.update_state(state="FAILURE", meta={"error": str(exc), "traceback": None})
            raise

    @celery_app.task(bind=True, name="core.tasks.publish_to_baserow")
    def publish_to_baserow_task(
        self, price_book_id: str, options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Publish price book data to Baserow asynchronously.

        Args:
            price_book_id: ID of the price book to publish
            options: Publishing options and configuration

        Returns:
            Dict containing publishing results and metadata
        """
        logger.info(f"Starting Baserow publish task for price book: {price_book_id}")

        try:
            # Update task state
            self.update_state(
                state="PROGRESS",
                meta={"current": 0, "total": 100, "status": "Initializing Baserow client..."},
            )

            # TODO: Import and use actual Baserow publishing logic
            # from services.publish_baserow import publish_price_book_to_baserow
            # from integrations.baserow_client import BaserowConfig
            # config = BaserowConfig(...)
            # result = await publish_price_book_to_baserow(price_book_id, config, options)

            # Placeholder publishing logic
            import time

            steps = [
                "Loading price book data...",
                "Transforming data for Baserow...",
                "Creating/updating tables...",
                "Uploading items...",
                "Uploading options...",
                "Uploading rules...",
                "Finalizing sync...",
            ]

            for i, step in enumerate(steps):
                time.sleep(2)  # Simulate processing
                progress = int((i + 1) / len(steps) * 100)
                self.update_state(
                    state="PROGRESS", meta={"current": progress, "total": 100, "status": step}
                )

            result = {
                "success": True,
                "price_book_id": price_book_id,
                "sync_id": f"sync_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "tables_synced": ["Items", "Options", "Rules"],
                "rows_processed": 183,
                "rows_created": 120,
                "rows_updated": 63,
                "sync_time_seconds": 14.0,
            }

            logger.info(f"Baserow publish completed for price book: {price_book_id}")
            return result

        except Exception as exc:
            logger.error(f"Baserow publish failed for {price_book_id}: {exc}")
            self.update_state(state="FAILURE", meta={"error": str(exc), "traceback": None})
            raise

    @celery_app.task(name="core.tasks.health_check")
    def health_check_task() -> Dict[str, Any]:
        """
        Health check task for worker monitoring.

        Returns:
            Dict containing worker health information
        """
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "worker_id": os.getenv("HOSTNAME", "unknown"),
            "celery_version": celery_app.version if hasattr(celery_app, "version") else "unknown",
        }

    @celery_app.task(name="core.tasks.cleanup_old_files")
    def cleanup_old_files_task(days: int = 7) -> Dict[str, Any]:
        """
        Clean up old processed files.

        Args:
            days: Number of days to keep files

        Returns:
            Dict containing cleanup results
        """
        logger.info(f"Starting cleanup of files older than {days} days")

        try:
            import os
            import time

            cleanup_paths = ["/app/data/processed", "/app/data/exports", "/app/logs"]

            deleted_count = 0
            deleted_size = 0

            cutoff_time = time.time() - (days * 24 * 60 * 60)

            for cleanup_path in cleanup_paths:
                if os.path.exists(cleanup_path):
                    for root, dirs, files in os.walk(cleanup_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            if os.path.getmtime(file_path) < cutoff_time:
                                try:
                                    file_size = os.path.getsize(file_path)
                                    os.remove(file_path)
                                    deleted_count += 1
                                    deleted_size += file_size
                                except OSError as e:
                                    logger.warning(f"Failed to delete {file_path}: {e}")

            result = {
                "success": True,
                "deleted_files": deleted_count,
                "deleted_size_bytes": deleted_size,
                "deleted_size_mb": round(deleted_size / (1024 * 1024), 2),
                "cleanup_days": days,
            }

            logger.info(f"Cleanup completed: {deleted_count} files, {result['deleted_size_mb']} MB")
            return result

        except Exception as exc:
            logger.error(f"Cleanup task failed: {exc}")
            raise

else:
    # Celery not available - create stub functions
    def process_pdf_task(*args, **kwargs):
        raise RuntimeError("Celery not available - install with: pip install celery")

    def publish_to_baserow_task(*args, **kwargs):
        raise RuntimeError("Celery not available - install with: pip install celery")

    def health_check_task(*args, **kwargs):
        raise RuntimeError("Celery not available - install with: pip install celery")

    def cleanup_old_files_task(*args, **kwargs):
        raise RuntimeError("Celery not available - install with: pip install celery")

    celery_app = None


# Export functions for use by the API
__all__ = [
    "celery_app",
    "process_pdf_task",
    "publish_to_baserow_task",
    "health_check_task",
    "cleanup_old_files_task",
]
