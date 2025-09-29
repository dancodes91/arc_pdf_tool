"""
Exception hierarchy for predictable error handling and observability.

Provides structured exceptions with HTTP status code mapping,
error categories, and detailed context for debugging and user feedback.
"""
from typing import Dict, Any, Optional, List
from enum import Enum
import traceback
import json


class ErrorCategory(Enum):
    """High-level error categories for classification."""
    VALIDATION = "validation"           # Input validation errors
    PARSING = "parsing"                # PDF parsing errors
    PROCESSING = "processing"          # Data processing errors
    EXTERNAL = "external"              # External service errors
    SYSTEM = "system"                  # System/infrastructure errors
    BUSINESS = "business"              # Business logic errors
    SECURITY = "security"              # Security/authorization errors


class BaseArcException(Exception):
    """
    Base exception for all ARC PDF tool errors.

    Provides structured error information with context, categorization,
    and HTTP status code mapping for API responses.
    """

    def __init__(
        self,
        message: str,
        error_code: str = None,
        http_status: int = 500,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        context: Dict[str, Any] = None,
        cause: Exception = None,
        user_message: str = None,
        retry_after: Optional[int] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.http_status = http_status
        self.category = category
        self.context = context or {}
        self.cause = cause
        self.user_message = user_message or message
        self.retry_after = retry_after
        self.timestamp = None  # Will be set by error handler

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/API response."""
        result = {
            'error_code': self.error_code,
            'message': self.message,
            'user_message': self.user_message,
            'category': self.category.value,
            'http_status': self.http_status,
            'context': self.context,
            'timestamp': self.timestamp
        }

        if self.retry_after:
            result['retry_after'] = self.retry_after

        if self.cause:
            result['cause'] = str(self.cause)
            result['cause_type'] = type(self.cause).__name__

        return result

    def to_json(self) -> str:
        """Convert exception to JSON string."""
        return json.dumps(self.to_dict(), default=str, indent=2)


# Validation Errors (4xx)
class ValidationError(BaseArcException):
    """Base class for input validation errors."""

    def __init__(self, message: str, field: str = None, http_status: int = 400, **kwargs):
        super().__init__(
            message=message,
            http_status=http_status,
            category=ErrorCategory.VALIDATION,
            **kwargs
        )
        if field:
            self.context['field'] = field


class FileNotFoundError(ValidationError):
    """File not found or inaccessible."""

    def __init__(self, file_path: str, **kwargs):
        super().__init__(
            message=f"File not found: {file_path}",
            error_code="FILE_NOT_FOUND",
            http_status=404,
            context={'file_path': file_path},
            user_message=f"The file '{file_path}' was not found",
            **kwargs
        )


class InvalidFileFormatError(ValidationError):
    """Invalid or unsupported file format."""

    def __init__(self, file_path: str, expected_format: str = None, **kwargs):
        super().__init__(
            message=f"Invalid file format: {file_path}",
            error_code="INVALID_FILE_FORMAT",
            context={
                'file_path': file_path,
                'expected_format': expected_format
            },
            user_message=f"The file format is not supported. Expected: {expected_format}",
            **kwargs
        )


class MissingParameterError(ValidationError):
    """Required parameter is missing."""

    def __init__(self, parameter: str, **kwargs):
        super().__init__(
            message=f"Missing required parameter: {parameter}",
            error_code="MISSING_PARAMETER",
            field=parameter,
            user_message=f"The parameter '{parameter}' is required",
            **kwargs
        )


class InvalidParameterError(ValidationError):
    """Parameter value is invalid."""

    def __init__(self, parameter: str, value: Any, reason: str = None, **kwargs):
        super().__init__(
            message=f"Invalid parameter {parameter}: {value}",
            error_code="INVALID_PARAMETER",
            field=parameter,
            context={
                'parameter': parameter,
                'value': str(value),
                'reason': reason
            },
            user_message=f"Invalid value for '{parameter}': {reason or 'Invalid format'}",
            **kwargs
        )


# Parsing Errors (422)
class ParseError(BaseArcException):
    """Base class for PDF parsing errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            http_status=422,
            category=ErrorCategory.PARSING,
            **kwargs
        )


class PDFCorruptedError(ParseError):
    """PDF file is corrupted or unreadable."""

    def __init__(self, file_path: str, details: str = None, **kwargs):
        super().__init__(
            message=f"PDF file is corrupted: {file_path}",
            error_code="PDF_CORRUPTED",
            context={
                'file_path': file_path,
                'details': details
            },
            user_message="The PDF file appears to be corrupted and cannot be processed",
            **kwargs
        )


class OCRError(ParseError):
    """OCR processing failed."""

    def __init__(self, page_number: int = None, reason: str = None, **kwargs):
        super().__init__(
            message=f"OCR failed{f' on page {page_number}' if page_number else ''}: {reason}",
            error_code="OCR_FAILED",
            context={
                'page_number': page_number,
                'reason': reason
            },
            user_message="Text recognition failed. The image quality may be too poor",
            retry_after=30,  # OCR can be retried
            **kwargs
        )


class TableShapeError(ParseError):
    """Table structure is invalid or cannot be processed."""

    def __init__(self, table_index: int = None, page_number: int = None,
                 reason: str = None, **kwargs):
        super().__init__(
            message=f"Invalid table structure{f' (table {table_index}, page {page_number})' if table_index and page_number else ''}: {reason}",
            error_code="TABLE_SHAPE_ERROR",
            context={
                'table_index': table_index,
                'page_number': page_number,
                'reason': reason
            },
            user_message="Table structure could not be recognized",
            **kwargs
        )


class RuleExtractionError(ParseError):
    """Failed to extract pricing rules."""

    def __init__(self, rule_type: str = None, pattern: str = None, **kwargs):
        super().__init__(
            message=f"Failed to extract {rule_type or 'pricing'} rules",
            error_code="RULE_EXTRACTION_ERROR",
            context={
                'rule_type': rule_type,
                'pattern': pattern
            },
            user_message="Pricing rules could not be extracted from the document",
            **kwargs
        )


# Processing Errors (422)
class ProcessingError(BaseArcException):
    """Base class for data processing errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            http_status=422,
            category=ErrorCategory.PROCESSING,
            **kwargs
        )


class DataNormalizationError(ProcessingError):
    """Failed to normalize extracted data."""

    def __init__(self, data_type: str, value: Any, reason: str = None, **kwargs):
        super().__init__(
            message=f"Failed to normalize {data_type}: {value}",
            error_code="DATA_NORMALIZATION_ERROR",
            context={
                'data_type': data_type,
                'value': str(value),
                'reason': reason
            },
            user_message=f"Could not process {data_type} data",
            **kwargs
        )


class DiffMatchError(ProcessingError):
    """Failed to match items during diff operation."""

    def __init__(self, old_item: str = None, confidence: float = None, **kwargs):
        super().__init__(
            message=f"Failed to match item: {old_item}",
            error_code="DIFF_MATCH_ERROR",
            context={
                'old_item': old_item,
                'confidence': confidence
            },
            user_message="Could not match items between price books",
            **kwargs
        )


class ConfidenceThresholdError(ProcessingError):
    """Data confidence is below acceptable threshold."""

    def __init__(self, data_type: str, confidence: float, threshold: float, **kwargs):
        super().__init__(
            message=f"{data_type} confidence {confidence:.2f} below threshold {threshold:.2f}",
            error_code="CONFIDENCE_THRESHOLD_ERROR",
            context={
                'data_type': data_type,
                'confidence': confidence,
                'threshold': threshold
            },
            user_message=f"Data quality for {data_type} is below acceptable standards",
            **kwargs
        )


# External Service Errors (5xx with retry)
class ExternalServiceError(BaseArcException):
    """Base class for external service errors."""

    def __init__(self, service: str, message: str, http_status: int = 502,
                 context: Dict[str, Any] = None, retry_after: Optional[int] = 60, **kwargs):
        merged_context = {'service': service}
        if context:
            merged_context.update(context)
        super().__init__(
            message=f"{service} error: {message}",
            http_status=http_status,
            category=ErrorCategory.EXTERNAL,
            context=merged_context,
            retry_after=retry_after,
            **kwargs
        )


class BaserowError(ExternalServiceError):
    """Baserow API errors."""

    def __init__(self, operation: str, status_code: int = None,
                 response: str = None, **kwargs):
        context = {
            'operation': operation,
            'status_code': status_code,
            'response': response
        }
        super().__init__(
            service="Baserow",
            message=f"Baserow {operation} failed",
            error_code="BASEROW_ERROR",
            context=context,
            user_message="External database service is temporarily unavailable",
            **kwargs
        )


class NetworkTimeoutError(ExternalServiceError):
    """Network operation timed out."""

    def __init__(self, operation: str, timeout: int, **kwargs):
        super().__init__(
            service="Network",
            message=f"{operation} timed out after {timeout}s",
            error_code="NETWORK_TIMEOUT",
            context={
                'operation': operation,
                'timeout': timeout
            },
            user_message="Network operation timed out. Please try again",
            retry_after=30,
            **kwargs
        )


class RateLimitError(ExternalServiceError):
    """Rate limit exceeded."""

    def __init__(self, service: str, limit: int = None, reset_time: int = None, **kwargs):
        context = {
            'limit': limit,
            'reset_time': reset_time
        }
        super().__init__(
            service=service,
            message=f"Rate limit exceeded for {service}",
            error_code="RATE_LIMIT_EXCEEDED",
            http_status=429,
            context=context,
            user_message="Request rate limit exceeded. Please wait before retrying",
            retry_after=reset_time or 60,
            **kwargs
        )


# Export Errors (422)
class ExportError(BaseArcException):
    """Base class for export operation errors."""

    def __init__(self, format_type: str, message: str, **kwargs):
        super().__init__(
            message=f"Export to {format_type} failed: {message}",
            error_code="EXPORT_ERROR",
            http_status=422,
            category=ErrorCategory.PROCESSING,
            context={'format_type': format_type},
            user_message=f"Failed to export data as {format_type}",
            **kwargs
        )


class UnsupportedExportFormatError(ExportError):
    """Unsupported export format."""

    def __init__(self, format_type: str, supported_formats: List[str] = None, **kwargs):
        super().__init__(
            format_type=format_type,
            message=f"Unsupported export format: {format_type}",
            error_code="UNSUPPORTED_EXPORT_FORMAT",
            http_status=400,
            category=ErrorCategory.VALIDATION,
            context={
                'requested_format': format_type,
                'supported_formats': supported_formats
            },
            user_message=f"Export format '{format_type}' is not supported",
            **kwargs
        )


# System Errors (5xx)
class SystemError(BaseArcException):
    """Base class for system-level errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            http_status=500,
            category=ErrorCategory.SYSTEM,
            user_message="An internal system error occurred",
            **kwargs
        )


class DatabaseError(SystemError):
    """Database operation failed."""

    def __init__(self, operation: str, details: str = None, **kwargs):
        super().__init__(
            message=f"Database {operation} failed: {details}",
            error_code="DATABASE_ERROR",
            context={
                'operation': operation,
                'details': details
            },
            user_message="Database operation failed. Please try again",
            retry_after=30,
            **kwargs
        )


class ConfigurationError(SystemError):
    """Invalid system configuration."""

    def __init__(self, config_key: str, issue: str = None, **kwargs):
        super().__init__(
            message=f"Configuration error: {config_key} - {issue}",
            error_code="CONFIGURATION_ERROR",
            context={
                'config_key': config_key,
                'issue': issue
            },
            user_message="System configuration error",
            **kwargs
        )


class ResourceExhaustedError(SystemError):
    """System resources exhausted."""

    def __init__(self, resource: str, limit: str = None, **kwargs):
        super().__init__(
            message=f"Resource exhausted: {resource}",
            error_code="RESOURCE_EXHAUSTED",
            http_status=503,
            context={
                'resource': resource,
                'limit': limit
            },
            user_message="System is temporarily overloaded. Please try again later",
            retry_after=120,
            **kwargs
        )


# Security Errors (4xx)
class SecurityError(BaseArcException):
    """Base class for security-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            http_status=403,
            category=ErrorCategory.SECURITY,
            user_message="Access denied",
            **kwargs
        )


class AuthenticationError(SecurityError):
    """Authentication failed."""

    def __init__(self, reason: str = None, **kwargs):
        super().__init__(
            message=f"Authentication failed: {reason}",
            error_code="AUTHENTICATION_FAILED",
            http_status=401,
            context={'reason': reason},
            user_message="Authentication required",
            **kwargs
        )


class AuthorizationError(SecurityError):
    """Authorization failed."""

    def __init__(self, resource: str, action: str, **kwargs):
        super().__init__(
            message=f"Not authorized to {action} {resource}",
            error_code="AUTHORIZATION_FAILED",
            context={
                'resource': resource,
                'action': action
            },
            user_message="You don't have permission to perform this action",
            **kwargs
        )


# Business Logic Errors (422)
class BusinessLogicError(BaseArcException):
    """Base class for business logic violations."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            http_status=422,
            category=ErrorCategory.BUSINESS,
            **kwargs
        )


class DuplicateEntityError(BusinessLogicError):
    """Entity already exists."""

    def __init__(self, entity_type: str, identifier: str, **kwargs):
        super().__init__(
            message=f"Duplicate {entity_type}: {identifier}",
            error_code="DUPLICATE_ENTITY",
            http_status=409,
            context={
                'entity_type': entity_type,
                'identifier': identifier
            },
            user_message=f"A {entity_type} with this identifier already exists",
            **kwargs
        )


class InvalidStateError(BusinessLogicError):
    """Operation invalid for current state."""

    def __init__(self, entity: str, current_state: str, required_state: str, **kwargs):
        super().__init__(
            message=f"Invalid state for {entity}: {current_state} (required: {required_state})",
            error_code="INVALID_STATE",
            context={
                'entity': entity,
                'current_state': current_state,
                'required_state': required_state
            },
            user_message=f"Operation not allowed in current state: {current_state}",
            **kwargs
        )


class BusinessRuleViolationError(BusinessLogicError):
    """Business rule violated."""

    def __init__(self, rule: str, details: str = None, **kwargs):
        super().__init__(
            message=f"Business rule violation: {rule}",
            error_code="BUSINESS_RULE_VIOLATION",
            context={
                'rule': rule,
                'details': details
            },
            user_message=f"Operation violates business rule: {rule}",
            **kwargs
        )


# Utility functions for exception handling
def get_exception_hierarchy() -> Dict[str, List[str]]:
    """Get the complete exception hierarchy for documentation."""
    hierarchy = {}

    def add_exception(exc_class, parent=None):
        class_name = exc_class.__name__
        if parent:
            if parent not in hierarchy:
                hierarchy[parent] = []
            hierarchy[parent].append(class_name)

        # Add subclasses
        for subclass in exc_class.__subclasses__():
            add_exception(subclass, class_name)

    # Start with base exception
    add_exception(BaseArcException)

    return hierarchy


def categorize_exception(exc: Exception) -> Dict[str, Any]:
    """Categorize any exception (including non-Arc exceptions)."""
    if isinstance(exc, BaseArcException):
        return exc.to_dict()

    # Handle standard Python exceptions
    exc_type = type(exc).__name__

    if isinstance(exc, FileNotFoundError):
        return {
            'error_code': 'FILE_NOT_FOUND',
            'message': str(exc),
            'category': ErrorCategory.VALIDATION.value,
            'http_status': 404
        }
    elif isinstance(exc, PermissionError):
        return {
            'error_code': 'PERMISSION_DENIED',
            'message': str(exc),
            'category': ErrorCategory.SECURITY.value,
            'http_status': 403
        }
    elif isinstance(exc, ValueError):
        return {
            'error_code': 'VALUE_ERROR',
            'message': str(exc),
            'category': ErrorCategory.VALIDATION.value,
            'http_status': 400
        }
    elif isinstance(exc, ConnectionError):
        return {
            'error_code': 'CONNECTION_ERROR',
            'message': str(exc),
            'category': ErrorCategory.EXTERNAL.value,
            'http_status': 502
        }
    elif isinstance(exc, TimeoutError):
        return {
            'error_code': 'TIMEOUT_ERROR',
            'message': str(exc),
            'category': ErrorCategory.EXTERNAL.value,
            'http_status': 504
        }
    else:
        # Generic system error
        return {
            'error_code': 'SYSTEM_ERROR',
            'message': str(exc),
            'category': ErrorCategory.SYSTEM.value,
            'http_status': 500,
            'exception_type': exc_type
        }