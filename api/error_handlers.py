"""
FastAPI error handlers for structured exception handling.

Provides consistent error responses with proper HTTP status codes,
logging, and monitoring integration for all application exceptions.
"""
import traceback
from typing import Dict, Any
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.exceptions import BaseArcException, categorize_exception, ErrorCategory
from core.observability import get_logger, capture_exception, metrics_collector
from core.resilience import get_resilience_status


def setup_error_handlers(app: FastAPI):
    """Setup all error handlers for the FastAPI application."""

    @app.exception_handler(BaseArcException)
    async def arc_exception_handler(request: Request, exc: BaseArcException):
        """Handle ARC-specific exceptions."""
        return await handle_arc_exception(request, exc)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle FastAPI HTTP exceptions."""
        return await handle_http_exception(request, exc)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        return await handle_validation_error(request, exc)

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions."""
        return await handle_general_exception(request, exc)


async def handle_arc_exception(request: Request, exc: BaseArcException) -> JSONResponse:
    """
    Handle ARC-specific exceptions with full context.

    Provides structured error responses with proper HTTP status codes,
    logging, and metrics tracking.
    """
    logger = get_logger()

    # Set timestamp if not already set
    if exc.timestamp is None:
        exc.timestamp = datetime.utcnow().isoformat() + 'Z'

    # Extract request context
    request_context = await extract_request_context(request)

    # Log the exception with full context
    logger.error(
        f"ARC Exception: {exc.message}",
        exception=exc,
        **request_context
    )

    # Track metrics
    metrics_collector.increment_counter(f"errors_{exc.category.value}")
    metrics_collector.increment_counter(f"http_status_{exc.http_status}")

    # Capture to external monitoring if available
    capture_exception(exc, extra_context=request_context)

    # Build response
    response_data = {
        "success": False,
        "error": {
            "code": exc.error_code,
            "message": exc.user_message,
            "category": exc.category.value,
            "timestamp": exc.timestamp
        }
    }

    # Add retry information if available
    if exc.retry_after:
        response_data["error"]["retry_after"] = exc.retry_after

    # Add context for debugging (in non-production environments)
    if should_include_debug_info():
        response_data["error"]["debug"] = {
            "internal_message": exc.message,
            "context": exc.context,
            "request_id": request_context.get("request_id")
        }

    # Set retry-after header if specified
    headers = {}
    if exc.retry_after:
        headers["Retry-After"] = str(exc.retry_after)

    return JSONResponse(
        status_code=exc.http_status,
        content=response_data,
        headers=headers
    )


async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    logger = get_logger()
    request_context = await extract_request_context(request)

    logger.warning(
        f"HTTP Exception: {exc.detail}",
        error_code="HTTP_EXCEPTION",
        http_status=exc.status_code,
        **request_context
    )

    metrics_collector.increment_counter(f"http_status_{exc.status_code}")

    response_data = {
        "success": False,
        "error": {
            "code": "HTTP_ERROR",
            "message": exc.detail,
            "category": "validation" if exc.status_code < 500 else "system",
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }
    }

    if should_include_debug_info():
        response_data["error"]["debug"] = {
            "request_id": request_context.get("request_id")
        }

    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors."""
    logger = get_logger()
    request_context = await extract_request_context(request)

    # Extract validation error details
    validation_errors = []
    for error in exc.errors():
        validation_errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(
        "Request validation failed",
        error_code="VALIDATION_ERROR",
        validation_errors=validation_errors,
        **request_context
    )

    metrics_collector.increment_counter("validation_errors")
    metrics_collector.increment_counter("http_status_422")

    response_data = {
        "success": False,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "category": "validation",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "validation_errors": validation_errors
        }
    }

    if should_include_debug_info():
        response_data["error"]["debug"] = {
            "request_id": request_context.get("request_id"),
            "raw_errors": exc.errors()
        }

    return JSONResponse(
        status_code=422,
        content=response_data
    )


async def handle_general_exception(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions."""
    logger = get_logger()
    request_context = await extract_request_context(request)

    # Categorize the exception
    exc_info = categorize_exception(exc)

    logger.error(
        f"Unhandled exception: {str(exc)}",
        exception=exc,
        error_code=exc_info.get("error_code", "UNKNOWN_ERROR"),
        exception_type=type(exc).__name__,
        **request_context
    )

    # Track metrics
    metrics_collector.increment_counter("unhandled_exceptions")
    metrics_collector.increment_counter(f"http_status_{exc_info.get('http_status', 500)}")

    # Capture to external monitoring
    capture_exception(exc, extra_context=request_context)

    response_data = {
        "success": False,
        "error": {
            "code": exc_info.get("error_code", "INTERNAL_ERROR"),
            "message": "An internal error occurred",
            "category": exc_info.get("category", "system"),
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }
    }

    if should_include_debug_info():
        response_data["error"]["debug"] = {
            "internal_message": str(exc),
            "exception_type": type(exc).__name__,
            "stack_trace": traceback.format_exc(),
            "request_id": request_context.get("request_id")
        }

    return JSONResponse(
        status_code=exc_info.get("http_status", 500),
        content=response_data
    )


async def extract_request_context(request: Request) -> Dict[str, Any]:
    """Extract relevant context from the request."""
    context = {
        "method": request.method,
        "url": str(request.url),
        "path": request.url.path,
        "user_agent": request.headers.get("user-agent"),
        "client_ip": request.client.host if request.client else None,
    }

    # Extract request ID if present
    request_id = request.headers.get("x-request-id")
    if request_id:
        context["request_id"] = request_id

    # Extract user context if available
    if hasattr(request.state, "user_id"):
        context["user_id"] = request.state.user_id
    if hasattr(request.state, "session_id"):
        context["session_id"] = request.state.session_id

    # Extract query parameters
    if request.query_params:
        context["query_params"] = dict(request.query_params)

    # Extract path parameters
    if hasattr(request, "path_params") and request.path_params:
        context["path_params"] = request.path_params

    return context


def should_include_debug_info() -> bool:
    """Determine if debug information should be included in error responses."""
    import os
    environment = os.getenv("ENVIRONMENT", "development")
    return environment.lower() in ["development", "testing", "staging"]


# Health check endpoint for monitoring
async def health_check_handler(request: Request) -> JSONResponse:
    """
    Health check endpoint with system status.

    Returns detailed health information including error rates,
    circuit breaker status, and system metrics.
    """
    try:
        # Get system status
        resilience_status = get_resilience_status()
        metrics_summary = metrics_collector.get_metrics_summary()

        # Calculate error rate (last 5 minutes)
        recent_metrics = metrics_collector.get_recent_metrics()
        error_count = sum(
            len(metrics) for name, metrics in recent_metrics.items()
            if name.startswith("errors_") or name.startswith("http_status_5")
        )
        total_requests = sum(
            len(metrics) for name, metrics in recent_metrics.items()
            if name.startswith("http_status_")
        )
        error_rate = (error_count / total_requests) if total_requests > 0 else 0.0

        # Check circuit breaker health
        circuit_breakers_healthy = all(
            cb["state"] != "open" for cb in resilience_status["circuit_breakers"].values()
        )

        # Determine overall health
        is_healthy = error_rate < 0.05 and circuit_breakers_healthy  # < 5% error rate

        health_data = {
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "version": "1.0.0",  # Would come from config
            "checks": {
                "error_rate": {
                    "status": "pass" if error_rate < 0.05 else "fail",
                    "value": f"{error_rate:.2%}",
                    "threshold": "5%"
                },
                "circuit_breakers": {
                    "status": "pass" if circuit_breakers_healthy else "fail",
                    "details": resilience_status["circuit_breakers"]
                },
                "active_operations": {
                    "status": "pass",
                    "count": len(resilience_status["active_operations"])
                }
            },
            "metrics": {
                "requests_total": total_requests,
                "errors_total": error_count,
                "error_rate": error_rate
            }
        }

        return JSONResponse(
            status_code=200 if is_healthy else 503,
            content=health_data
        )

    except Exception as exc:
        logger = get_logger()
        logger.error("Health check failed", exception=exc)

        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat() + 'Z',
                "error": "Health check failed"
            }
        )


# Error reporting endpoint for debugging
async def error_stats_handler(request: Request) -> JSONResponse:
    """
    Error statistics endpoint for monitoring and debugging.

    Returns detailed error statistics and recent error patterns.
    """
    try:
        metrics_summary = metrics_collector.get_metrics_summary()
        recent_metrics = metrics_collector.get_recent_metrics()

        # Aggregate error statistics
        error_stats = {
            "error_counts_by_category": {},
            "error_counts_by_status": {},
            "recent_errors": {},
            "error_trends": {}
        }

        # Process counters
        for name, count in metrics_summary.get("counters", {}).items():
            if name.startswith("errors_"):
                category = name.replace("errors_", "")
                error_stats["error_counts_by_category"][category] = count
            elif name.startswith("http_status_"):
                status = name.replace("http_status_", "")
                if status.startswith(("4", "5")):  # Client and server errors
                    error_stats["error_counts_by_status"][status] = count

        # Process recent metrics
        for name, metrics in recent_metrics.items():
            if "error" in name.lower():
                error_stats["recent_errors"][name] = len(metrics)

        return JSONResponse(
            status_code=200,
            content={
                "timestamp": datetime.utcnow().isoformat() + 'Z',
                "error_statistics": error_stats,
                "resilience_status": get_resilience_status()
            }
        )

    except Exception as exc:
        logger = get_logger()
        logger.error("Error stats endpoint failed", exception=exc)

        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to retrieve error statistics",
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            }
        )