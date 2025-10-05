"""
Observability framework for structured logging and metrics.

Provides JSON logging, metrics collection, and integration with
external monitoring systems like Sentry and Prometheus.
"""

import logging
import json
import time
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from functools import wraps
from collections import defaultdict
import sys
import traceback

try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration

    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

from .exceptions import BaseArcException, categorize_exception


class LogLevel(Enum):
    """Log levels for structured logging."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics to collect."""

    COUNTER = "counter"  # Monotonic counter
    GAUGE = "gauge"  # Current value
    HISTOGRAM = "histogram"  # Distribution of values
    TIMING = "timing"  # Duration measurements


@dataclass
class LogEntry:
    """Structured log entry."""

    timestamp: str
    level: str
    message: str
    logger_name: str
    module: str = ""
    function: str = ""
    line_number: int = 0

    # Context fields
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    operation_id: Optional[str] = None

    # PDF processing context
    file_path: Optional[str] = None
    page_number: Optional[int] = None
    table_index: Optional[int] = None
    extractor: Optional[str] = None

    # Error context
    error_code: Optional[str] = None
    error_category: Optional[str] = None
    exception_type: Optional[str] = None
    stack_trace: Optional[str] = None

    # Performance context
    duration_ms: Optional[float] = None
    memory_usage_mb: Optional[float] = None

    # Additional context
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        # Remove None values and empty extra_fields
        result = {k: v for k, v in result.items() if v is not None}
        if not result.get("extra_fields"):
            result.pop("extra_fields", None)
        return result

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class MetricEntry:
    """Metric data point."""

    name: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


class StructuredLogger:
    """
    Structured logger with JSON output and context management.

    Provides rich context for debugging and monitoring in production.
    """

    def __init__(self, name: str = "arc_pdf_tool", level: LogLevel = LogLevel.INFO):
        self.name = name
        self.level = level
        self.context: Dict[str, Any] = {}
        self._lock = threading.Lock()

        # Configure Python logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.value.upper()))

        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Add JSON handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)

    def set_context(self, **kwargs):
        """Set persistent context for all log entries."""
        with self._lock:
            self.context.update(kwargs)

    def clear_context(self):
        """Clear all persistent context."""
        with self._lock:
            self.context.clear()

    def _create_log_entry(self, level: LogLevel, message: str, **kwargs) -> LogEntry:
        """Create structured log entry with context."""
        frame = sys._getframe(2)  # Get caller's frame

        # Merge context and kwargs
        all_context = {**self.context, **kwargs}

        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=level.value,
            message=message,
            logger_name=self.name,
            module=frame.f_globals.get("__name__", ""),
            function=frame.f_code.co_name,
            line_number=frame.f_lineno,
        )

        # Map known context fields
        for field_name in [
            "user_id",
            "session_id",
            "request_id",
            "operation_id",
            "file_path",
            "page_number",
            "table_index",
            "extractor",
            "error_code",
            "error_category",
            "exception_type",
            "duration_ms",
            "memory_usage_mb",
        ]:
            if field_name in all_context:
                setattr(entry, field_name, all_context.pop(field_name))

        # Add remaining fields as extra
        if all_context:
            entry.extra_fields = all_context

        return entry

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        if self.level.value != "debug":
            return
        entry = self._create_log_entry(LogLevel.DEBUG, message, **kwargs)
        self.logger.debug(entry.to_json())

    def info(self, message: str, **kwargs):
        """Log info message."""
        entry = self._create_log_entry(LogLevel.INFO, message, **kwargs)
        self.logger.info(entry.to_json())

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        entry = self._create_log_entry(LogLevel.WARNING, message, **kwargs)
        self.logger.warning(entry.to_json())

    def error(self, message: str, exception: Exception = None, **kwargs):
        """Log error message with optional exception details."""
        if exception:
            if isinstance(exception, BaseArcException):
                kwargs.update(
                    {
                        "error_code": exception.error_code,
                        "error_category": exception.category.value,
                        "exception_type": type(exception).__name__,
                    }
                )
            else:
                exc_info = categorize_exception(exception)
                # Remove 'message' from exc_info to avoid duplicate argument error
                exc_info.pop("message", None)
                kwargs.update(exc_info)

            kwargs["stack_trace"] = traceback.format_exc()

        entry = self._create_log_entry(LogLevel.ERROR, message, **kwargs)
        self.logger.error(entry.to_json())

    def critical(self, message: str, exception: Exception = None, **kwargs):
        """Log critical message."""
        if exception:
            kwargs["stack_trace"] = traceback.format_exc()

        entry = self._create_log_entry(LogLevel.CRITICAL, message, **kwargs)
        self.logger.critical(entry.to_json())


class JSONFormatter(logging.Formatter):
    """JSON formatter for log records."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # If message is already JSON (from StructuredLogger), return as-is
        if hasattr(record, "getMessage"):
            message = record.getMessage()
            try:
                json.loads(message)  # Test if already JSON
                return message
            except (json.JSONDecodeError, ValueError):
                pass

        # Create basic JSON structure for non-structured logs
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "logger_name": record.name,
            "module": record.module if hasattr(record, "module") else "",
            "function": record.funcName,
            "line_number": record.lineno,
        }

        if record.exc_info:
            log_data["stack_trace"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


class MetricsCollector:
    """
    Metrics collector for application performance monitoring.

    Collects counters, gauges, histograms, and timings for analysis.
    """

    def __init__(self):
        self.metrics: Dict[str, List[MetricEntry]] = defaultdict(list)
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def increment_counter(self, name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """Increment a counter metric."""
        with self._lock:
            self.counters[name] += value

        self._add_metric(
            MetricEntry(
                name=name,
                metric_type=MetricType.COUNTER,
                value=value,
                timestamp=datetime.utcnow(),
                tags=tags or {},
            )
        )

    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric value."""
        with self._lock:
            self.gauges[name] = value

        self._add_metric(
            MetricEntry(
                name=name,
                metric_type=MetricType.GAUGE,
                value=value,
                timestamp=datetime.utcnow(),
                tags=tags or {},
            )
        )

    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a value in a histogram."""
        with self._lock:
            self.histograms[name].append(value)

        self._add_metric(
            MetricEntry(
                name=name,
                metric_type=MetricType.HISTOGRAM,
                value=value,
                timestamp=datetime.utcnow(),
                tags=tags or {},
            )
        )

    def record_timing(self, name: str, duration_ms: float, tags: Dict[str, str] = None):
        """Record a timing measurement."""
        self._add_metric(
            MetricEntry(
                name=name,
                metric_type=MetricType.TIMING,
                value=duration_ms,
                timestamp=datetime.utcnow(),
                tags=tags or {},
                unit="ms",
            )
        )

    def _add_metric(self, metric: MetricEntry):
        """Add metric to collection."""
        with self._lock:
            self.metrics[metric.name].append(metric)

        # Keep only recent metrics (last 1000 per metric)
        if len(self.metrics[metric.name]) > 1000:
            self.metrics[metric.name] = self.metrics[metric.name][-1000:]

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        with self._lock:
            summary = {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {},
            }

            # Calculate histogram statistics
            for name, values in self.histograms.items():
                if values:
                    summary["histograms"][name] = {
                        "count": len(values),
                        "sum": sum(values),
                        "avg": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                    }

            return summary

    def get_recent_metrics(self, since: datetime = None) -> Dict[str, List[Dict]]:
        """Get recent metrics as dictionaries."""
        if since is None:
            since = datetime.utcnow() - timedelta(minutes=5)

        result = {}
        with self._lock:
            for name, metrics in self.metrics.items():
                recent = [
                    {
                        "timestamp": m.timestamp.isoformat(),
                        "value": m.value,
                        "type": m.metric_type.value,
                        "tags": m.tags,
                        "unit": m.unit,
                    }
                    for m in metrics
                    if m.timestamp >= since
                ]
                if recent:
                    result[name] = recent

        return result

    def clear_metrics(self):
        """Clear all collected metrics."""
        with self._lock:
            self.metrics.clear()
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()


# Global instances
structured_logger = StructuredLogger()
metrics_collector = MetricsCollector()


def get_logger(name: str = None) -> StructuredLogger:
    """Get or create a structured logger."""
    if name:
        return StructuredLogger(name)
    return structured_logger


def log_operation(operation_name: str, include_timing: bool = True):
    """Decorator to log operation start/end with timing."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            start_time = time.time()

            logger.info(f"Starting {operation_name}", operation=operation_name)

            try:
                result = func(*args, **kwargs)

                if include_timing:
                    duration_ms = (time.time() - start_time) * 1000
                    logger.info(
                        f"Completed {operation_name}",
                        operation=operation_name,
                        duration_ms=duration_ms,
                    )
                    metrics_collector.record_timing(
                        f"operation_{operation_name}_duration", duration_ms
                    )
                else:
                    logger.info(f"Completed {operation_name}", operation=operation_name)

                metrics_collector.increment_counter(f"operation_{operation_name}_success")
                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Failed {operation_name}",
                    exception=e,
                    operation=operation_name,
                    duration_ms=duration_ms,
                )
                metrics_collector.increment_counter(f"operation_{operation_name}_error")
                raise

        return wrapper

    return decorator


def setup_sentry(dsn: str, environment: str = "production", release: str = None):
    """Setup Sentry error reporting."""
    if not SENTRY_AVAILABLE:
        structured_logger.warning("Sentry SDK not available")
        return

    sentry_logging = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR,  # Send errors as events
    )

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        integrations=[sentry_logging],
        traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
        attach_stacktrace=True,
        send_default_pii=False,  # Don't send personally identifiable information
    )

    structured_logger.info("Sentry error reporting initialized")


def capture_exception(exception: Exception, extra_context: Dict[str, Any] = None):
    """Capture exception to Sentry with additional context."""
    if SENTRY_AVAILABLE:
        with sentry_sdk.push_scope() as scope:
            if extra_context:
                for key, value in extra_context.items():
                    scope.set_extra(key, value)

            if isinstance(exception, BaseArcException):
                scope.set_tag("error_category", exception.category.value)
                scope.set_extra("error_code", exception.error_code)
                scope.set_extra("context", exception.context)

            sentry_sdk.capture_exception(exception)


class PerformanceTracker:
    """Track performance metrics for operations."""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.metrics = {}

    def __enter__(self):
        self.start_time = time.time()
        metrics_collector.increment_counter(f"{self.operation_name}_started")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000

        if exc_type is None:
            metrics_collector.increment_counter(f"{self.operation_name}_completed")
            structured_logger.info(
                f"Performance: {self.operation_name} completed",
                operation=self.operation_name,
                duration_ms=duration_ms,
                **self.metrics,
            )
        else:
            metrics_collector.increment_counter(f"{self.operation_name}_failed")
            structured_logger.error(
                f"Performance: {self.operation_name} failed",
                operation=self.operation_name,
                duration_ms=duration_ms,
                exception=exc_val,
                **self.metrics,
            )

        metrics_collector.record_timing(f"{self.operation_name}_duration", duration_ms)

    def add_metric(self, key: str, value: Any):
        """Add additional metric to track."""
        self.metrics[key] = value


def track_performance(operation_name: str):
    """Context manager for performance tracking."""
    return PerformanceTracker(operation_name)


# Application-specific metrics helpers
def track_pdf_processing(file_path: str, page_count: int = None):
    """Track PDF processing metrics."""
    metrics_collector.increment_counter("pdf_files_processed")
    if page_count:
        metrics_collector.record_histogram("pdf_page_count", float(page_count))

    get_logger().info("PDF processing started", file_path=file_path, page_count=page_count)


def track_extraction_results(extractor: str, items_extracted: int, confidence: float):
    """Track extraction result metrics."""
    metrics_collector.increment_counter(f"extraction_{extractor}_runs")
    metrics_collector.record_histogram(f"extraction_{extractor}_items", float(items_extracted))
    metrics_collector.record_histogram(f"extraction_{extractor}_confidence", confidence)


def track_diff_operation(old_book_id: str, new_book_id: str, changes_count: int):
    """Track diff operation metrics."""
    metrics_collector.increment_counter("diff_operations")
    metrics_collector.record_histogram("diff_changes_count", float(changes_count))

    get_logger().info(
        "Diff operation completed",
        old_book_id=old_book_id,
        new_book_id=new_book_id,
        changes_count=changes_count,
    )


def get_observability_status() -> Dict[str, Any]:
    """Get current observability status and metrics."""
    return {
        "metrics_summary": metrics_collector.get_metrics_summary(),
        "recent_metrics": metrics_collector.get_recent_metrics(),
        "sentry_enabled": SENTRY_AVAILABLE,
        "log_level": structured_logger.level.value,
        "context": structured_logger.context,
    }
