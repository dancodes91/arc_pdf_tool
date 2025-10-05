"""
Common API schemas and response models.

Provides standardized request/response structures for the FastAPI application.
"""

from typing import TypeVar, Generic, Optional, Any
from pydantic import BaseModel, Field


T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    """
    Standardized API response model.

    Provides consistent response structure across all API endpoints
    with success status, data payload, and optional message.
    """

    success: bool = Field(..., description="Whether the operation was successful")
    data: Optional[T] = Field(None, description="Response data payload")
    message: Optional[str] = Field(None, description="Optional response message")
    error: Optional[str] = Field(None, description="Error message if operation failed")

    class Config:
        """Pydantic configuration."""

        # Allow arbitrary types for generic data field
        arbitrary_types_allowed = True


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated response model for list endpoints.

    Provides consistent pagination structure with data, page info,
    and metadata about the total dataset.
    """

    items: list[T] = Field(..., description="List of items for current page")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number (1-based)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class ErrorResponse(BaseModel):
    """
    Error response model for API errors.

    Provides detailed error information including error code,
    message, and optional additional context.
    """

    success: bool = Field(False, description="Always false for error responses")
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: str = Field(..., description="ISO timestamp when error occurred")

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class HealthResponse(BaseModel):
    """
    Health check response model.

    Provides system health status with optional detailed
    information about system components.
    """

    status: str = Field(..., description="Overall system status: healthy, degraded, unhealthy")
    timestamp: str = Field(..., description="ISO timestamp of health check")
    version: Optional[str] = Field(None, description="Application version")
    checks: Optional[dict[str, Any]] = Field(None, description="Detailed component health checks")

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True
