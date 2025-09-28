"""
Comprehensive tests for exception handling and resilience patterns.

Tests exception hierarchy, circuit breakers, retries, timeouts,
and failure scenarios to ensure robust error handling.
"""
import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

# Import the components we're testing
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.exceptions import (
    BaseArcException, ValidationError, ParseError, ProcessingError,
    ExternalServiceError, SystemError, SecurityError, BusinessLogicError,
    FileNotFoundError, PDFCorruptedError, OCRError, BaserowError,
    NetworkTimeoutError, RateLimitError, ErrorCategory
)

from core.resilience import (
    CircuitBreaker, CircuitState, CircuitBreakerConfig,
    RetryConfig, TimeoutManager, RateLimiter,
    retry_with_backoff, circuit_breaker, with_timeout, rate_limit,
    resilient, get_circuit_breaker, timeout_manager
)

from core.observability import (
    StructuredLogger, MetricsCollector, LogEntry, MetricEntry, MetricType,
    log_operation, track_performance, JSONFormatter
)


class TestExceptionHierarchy:
    """Test the exception hierarchy and error categorization."""

    def test_base_exception_properties(self):
        """Test BaseArcException basic properties."""
        exc = BaseArcException(
            message="Test error",
            error_code="TEST_ERROR",
            http_status=422,
            category=ErrorCategory.PROCESSING,
            context={'key': 'value'},
            user_message="User-friendly message"
        )

        assert exc.message == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.http_status == 422
        assert exc.category == ErrorCategory.PROCESSING
        assert exc.context == {'key': 'value'}
        assert exc.user_message == "User-friendly message"

    def test_exception_to_dict(self):
        """Test exception serialization to dictionary."""
        exc = ValidationError(
            message="Invalid input",
            field="email",
            context={'provided_value': 'invalid-email'}
        )

        exc_dict = exc.to_dict()

        assert exc_dict['error_code'] == 'ValidationError'
        assert exc_dict['message'] == 'Invalid input'
        assert exc_dict['category'] == 'validation'
        assert exc_dict['http_status'] == 400
        assert exc_dict['context']['field'] == 'email'
        assert exc_dict['context']['provided_value'] == 'invalid-email'

    def test_exception_json_serialization(self):
        """Test exception JSON serialization."""
        exc = ParseError(
            message="PDF parse failed",
            error_code="PDF_PARSE_ERROR",
            context={'page': 5}
        )

        json_str = exc.to_json()
        parsed = json.loads(json_str)

        assert parsed['message'] == "PDF parse failed"
        assert parsed['error_code'] == "PDF_PARSE_ERROR"
        assert parsed['category'] == 'parsing'
        assert parsed['context']['page'] == 5

    def test_file_not_found_error(self):
        """Test FileNotFoundError specific behavior."""
        exc = FileNotFoundError("/path/to/missing.pdf")

        assert exc.error_code == "FILE_NOT_FOUND"
        assert exc.http_status == 404
        assert exc.category == ErrorCategory.VALIDATION
        assert exc.context['file_path'] == "/path/to/missing.pdf"
        assert "not found" in exc.user_message.lower()

    def test_ocr_error_with_retry(self):
        """Test OCRError includes retry information."""
        exc = OCRError(page_number=5, reason="Poor image quality")

        assert exc.error_code == "OCR_FAILED"
        assert exc.category == ErrorCategory.PARSING
        assert exc.context['page_number'] == 5
        assert exc.context['reason'] == "Poor image quality"
        assert exc.retry_after == 30  # OCR can be retried

    def test_baserow_error_categorization(self):
        """Test BaserowError categorization as external service."""
        exc = BaserowError(
            operation="upsert_rows",
            status_code=429,
            response="Rate limit exceeded"
        )

        assert exc.category == ErrorCategory.EXTERNAL
        assert exc.context['service'] == 'Baserow'
        assert exc.context['operation'] == 'upsert_rows'
        assert exc.context['status_code'] == 429
        assert exc.retry_after == 60  # External errors can be retried

    def test_rate_limit_error_retry_after(self):
        """Test RateLimitError includes proper retry timing."""
        exc = RateLimitError(
            service="test_api",
            limit=100,
            reset_time=120
        )

        assert exc.http_status == 429
        assert exc.retry_after == 120
        assert exc.context['limit'] == 100
        assert exc.context['reset_time'] == 120

    def test_exception_with_cause(self):
        """Test exception chaining with cause."""
        root_cause = ValueError("Invalid value")
        exc = ProcessingError(
            message="Processing failed",
            cause=root_cause
        )

        exc_dict = exc.to_dict()
        assert exc_dict['cause'] == str(root_cause)
        assert exc_dict['cause_type'] == 'ValueError'

    def test_security_error_defaults(self):
        """Test SecurityError default behavior."""
        exc = SecurityError("Access denied")

        assert exc.http_status == 403
        assert exc.category == ErrorCategory.SECURITY
        assert exc.user_message == "Access denied"

    def test_business_logic_error_mapping(self):
        """Test BusinessLogicError HTTP status mapping."""
        exc = BusinessLogicError("Invalid operation")

        assert exc.http_status == 422
        assert exc.category == ErrorCategory.BUSINESS


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_normal_operation(self):
        """Test circuit breaker in normal (closed) state."""
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=10)
        breaker = CircuitBreaker("test", config)

        # Should allow calls in closed state
        result = breaker.call(lambda: "success")
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=10)
        breaker = CircuitBreaker("test", config)

        # First failure
        with pytest.raises(ValueError):
            breaker.call(lambda: self._failing_function())

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 1

        # Second failure should open the circuit
        with pytest.raises(ValueError):
            breaker.call(lambda: self._failing_function())

        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 2

    def test_circuit_breaker_blocks_when_open(self):
        """Test circuit breaker blocks calls when open."""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=60)
        breaker = CircuitBreaker("test", config)

        # Trigger failure to open circuit
        with pytest.raises(ValueError):
            breaker.call(lambda: self._failing_function())

        assert breaker.state == CircuitState.OPEN

        # Should block subsequent calls
        with pytest.raises(ExternalServiceError) as exc_info:
            breaker.call(lambda: "should not execute")

        assert "Circuit breaker is open" in str(exc_info.value)
        assert exc_info.value.error_code == "CIRCUIT_BREAKER_OPEN"

    def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker half-open recovery."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.1,  # Very short for testing
            success_threshold=2
        )
        breaker = CircuitBreaker("test", config)

        # Open the circuit
        with pytest.raises(ValueError):
            breaker.call(lambda: self._failing_function())

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.2)

        # First call should transition to half-open
        result = breaker.call(lambda: "success1")
        assert result == "success1"
        assert breaker.state == CircuitState.HALF_OPEN

        # Second success should close the circuit
        result = breaker.call(lambda: "success2")
        assert result == "success2"
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_breaker_excluded_exceptions(self):
        """Test circuit breaker excludes certain exceptions."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            excluded_exceptions=[ValidationError]
        )
        breaker = CircuitBreaker("test", config)

        # ValidationError should not trigger circuit breaker
        with pytest.raises(ValidationError):
            breaker.call(lambda: self._validation_error_function())

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    def test_circuit_breaker_status(self):
        """Test circuit breaker status reporting."""
        breaker = CircuitBreaker("test")
        status = breaker.get_status()

        assert status['name'] == 'test'
        assert status['state'] == 'closed'
        assert status['failure_count'] == 0
        assert status['success_count'] == 0

    def test_circuit_breaker_decorator(self):
        """Test circuit breaker decorator."""
        @circuit_breaker("test_decorator", CircuitBreakerConfig(failure_threshold=1))
        def test_function(should_fail=False):
            if should_fail:
                raise ValueError("Forced failure")
            return "success"

        # Should work normally
        result = test_function(False)
        assert result == "success"

        # Should open circuit after failure
        with pytest.raises(ValueError):
            test_function(True)

        # Should block subsequent calls
        with pytest.raises(ExternalServiceError):
            test_function(False)

    def _failing_function(self):
        """Helper function that always fails."""
        raise ValueError("Simulated failure")

    def _validation_error_function(self):
        """Helper function that raises ValidationError."""
        raise ValidationError("Validation failed")


class TestRetryMechanism:
    """Test retry with backoff functionality."""

    def test_basic_retry_success(self):
        """Test basic retry mechanism with eventual success."""
        call_count = 0

        @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=0.01))
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert call_count == 3

    def test_retry_max_attempts_exceeded(self):
        """Test retry gives up after max attempts."""
        call_count = 0

        @retry_with_backoff(RetryConfig(max_attempts=2, base_delay=0.01))
        def always_failing():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            always_failing()

        assert call_count == 2

    def test_retry_non_retryable_exception(self):
        """Test retry doesn't retry non-retryable exceptions."""
        call_count = 0

        @retry_with_backoff(RetryConfig(
            max_attempts=3,
            retryable_exceptions=[ConnectionError]  # Only ConnectionError is retryable
        ))
        def function_with_validation_error():
            nonlocal call_count
            call_count += 1
            raise ValidationError("Not retryable")

        with pytest.raises(ValidationError):
            function_with_validation_error()

        assert call_count == 1  # Should not retry

    def test_retry_delay_calculation(self):
        """Test retry delay calculation with exponential backoff."""
        from core.resilience import _calculate_delay

        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=10.0,
            jitter=False
        )

        # Test exponential progression
        assert _calculate_delay(0, config) == 1.0   # 1.0 * 2^0
        assert _calculate_delay(1, config) == 2.0   # 1.0 * 2^1
        assert _calculate_delay(2, config) == 4.0   # 1.0 * 2^2
        assert _calculate_delay(3, config) == 8.0   # 1.0 * 2^3
        assert _calculate_delay(4, config) == 10.0  # Capped at max_delay

    def test_retry_with_jitter(self):
        """Test retry delay includes jitter."""
        from core.resilience import _calculate_delay

        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            jitter=True
        )

        # With jitter, delays should vary
        delays = [_calculate_delay(1, config) for _ in range(10)]
        assert len(set(delays)) > 1  # Should have variation
        assert all(1.5 <= d <= 2.5 for d in delays)  # Within jitter range


class TestTimeoutManager:
    """Test timeout management functionality."""

    def test_timeout_manager_basic_operations(self):
        """Test basic timeout manager operations."""
        tm = TimeoutManager()
        tm.set_timeout('test_op', 30)

        # Start operation
        success = tm.start_operation('op1', 'test_op')
        assert success

        # Check not timed out immediately
        timed_out = tm.check_timeout('op1', 'test_op')
        assert not timed_out

        # Finish operation
        tm.finish_operation('op1')

        # Should not be tracked anymore
        active = tm.get_active_operations()
        assert 'op1' not in active

    def test_timeout_detection(self):
        """Test timeout detection."""
        tm = TimeoutManager()
        tm.set_timeout('fast_op', 0.1)  # 100ms timeout

        tm.start_operation('op1', 'fast_op')

        # Should not be timed out immediately
        assert not tm.check_timeout('op1', 'fast_op')

        # Wait for timeout
        time.sleep(0.2)

        # Should be timed out now
        assert tm.check_timeout('op1', 'fast_op')

    def test_timeout_decorator(self):
        """Test timeout decorator."""
        @with_timeout('test_timeout')
        def test_function():
            return "completed"

        # Should work normally
        result = test_function()
        assert result == "completed"

    def test_active_operations_tracking(self):
        """Test tracking of active operations."""
        tm = TimeoutManager()

        tm.start_operation('op1', 'test_op')
        tm.start_operation('op2', 'test_op')

        active = tm.get_active_operations()
        assert 'op1' in active
        assert 'op2' in active
        assert 'elapsed_seconds' in active['op1']

        tm.finish_operation('op1')

        active = tm.get_active_operations()
        assert 'op1' not in active
        assert 'op2' in active


class TestRateLimiter:
    """Test rate limiting functionality."""

    def test_rate_limiter_basic_operation(self):
        """Test basic rate limiter operation."""
        limiter = RateLimiter(rate=10.0, burst=10)  # 10 tokens/sec, 10 burst

        # Should allow initial burst
        for _ in range(10):
            assert limiter.acquire(1, timeout=0.1)

        # Should block additional requests
        assert not limiter.acquire(1, timeout=0.01)

    def test_rate_limiter_token_replenishment(self):
        """Test rate limiter token replenishment over time."""
        limiter = RateLimiter(rate=5.0, burst=5)  # 5 tokens/sec

        # Use all tokens
        for _ in range(5):
            assert limiter.acquire()

        # Should block immediately
        assert not limiter.acquire(timeout=0.01)

        # Wait for token replenishment
        time.sleep(0.3)  # Should get ~1.5 tokens

        # Should allow at least 1 request
        assert limiter.acquire()

    def test_rate_limiter_status(self):
        """Test rate limiter status reporting."""
        limiter = RateLimiter(rate=5.0, burst=10, name="test_limiter")

        status = limiter.get_status()
        assert status['name'] == 'test_limiter'
        assert status['rate'] == 5.0
        assert status['burst'] == 10
        assert 'available_tokens' in status

    def test_rate_limit_decorator(self):
        """Test rate limit decorator."""
        # Use a very restrictive limiter for testing
        from core.resilience import _rate_limiters
        _rate_limiters['test_limiter'] = RateLimiter(rate=1.0, burst=1)

        @rate_limit('test_limiter', tokens=1, timeout=0.01)
        def limited_function():
            return "success"

        # First call should succeed
        result = limited_function()
        assert result == "success"

        # Second call should fail due to rate limit
        with pytest.raises(RateLimitError):
            limited_function()


class TestObservability:
    """Test structured logging and metrics."""

    def test_structured_logger_basic(self):
        """Test basic structured logging functionality."""
        logger = StructuredLogger("test_logger")

        # Test context setting
        logger.set_context(user_id="123", session_id="abc")

        # Create a log entry (we can't easily test the actual output)
        with patch.object(logger.logger, 'info') as mock_info:
            logger.info("Test message", extra_field="value")
            mock_info.assert_called_once()

    def test_log_entry_creation(self):
        """Test log entry structure."""
        entry = LogEntry(
            timestamp="2023-01-01T12:00:00Z",
            level="info",
            message="Test message",
            logger_name="test",
            user_id="123",
            file_path="/test.pdf",
            extra_fields={"key": "value"}
        )

        entry_dict = entry.to_dict()
        assert entry_dict['timestamp'] == "2023-01-01T12:00:00Z"
        assert entry_dict['level'] == "info"
        assert entry_dict['message'] == "Test message"
        assert entry_dict['user_id'] == "123"
        assert entry_dict['file_path'] == "/test.pdf"
        assert entry_dict['extra_fields'] == {"key": "value"}

    def test_json_formatter(self):
        """Test JSON log formatting."""
        formatter = JSONFormatter()

        # Create a mock log record
        record = Mock()
        record.levelname = "INFO"
        record.getMessage.return_value = "Test message"
        record.name = "test_logger"
        record.module = "test_module"
        record.funcName = "test_function"
        record.lineno = 42
        record.exc_info = None

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed['level'] == 'info'
        assert parsed['message'] == 'Test message'
        assert parsed['logger_name'] == 'test_logger'
        assert parsed['line_number'] == 42

    def test_metrics_collector_counters(self):
        """Test metrics collector counter functionality."""
        collector = MetricsCollector()

        collector.increment_counter("test_counter", 5.0)
        collector.increment_counter("test_counter", 3.0)

        summary = collector.get_metrics_summary()
        assert summary['counters']['test_counter'] == 8.0

    def test_metrics_collector_gauges(self):
        """Test metrics collector gauge functionality."""
        collector = MetricsCollector()

        collector.set_gauge("test_gauge", 42.5)
        collector.set_gauge("test_gauge", 37.8)  # Should overwrite

        summary = collector.get_metrics_summary()
        assert summary['gauges']['test_gauge'] == 37.8

    def test_metrics_collector_histograms(self):
        """Test metrics collector histogram functionality."""
        collector = MetricsCollector()

        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        for value in values:
            collector.record_histogram("test_histogram", value)

        summary = collector.get_metrics_summary()
        hist_stats = summary['histograms']['test_histogram']

        assert hist_stats['count'] == 5
        assert hist_stats['sum'] == 15.0
        assert hist_stats['avg'] == 3.0
        assert hist_stats['min'] == 1.0
        assert hist_stats['max'] == 5.0

    def test_performance_tracker(self):
        """Test performance tracking context manager."""
        collector = MetricsCollector()

        with track_performance("test_operation") as tracker:
            tracker.add_metric("items_processed", 100)
            time.sleep(0.01)  # Simulate work

        # Should have recorded timing metric
        recent_metrics = collector.get_recent_metrics()
        assert "test_operation_duration" in recent_metrics

    def test_log_operation_decorator(self):
        """Test operation logging decorator."""
        @log_operation("test_operation")
        def test_function():
            return "success"

        with patch('core.observability.structured_logger') as mock_logger:
            result = test_function()
            assert result == "success"

            # Should have logged start and completion
            assert mock_logger.info.call_count >= 2


class TestResilientDecorator:
    """Test the combined resilient decorator."""

    def test_resilient_decorator_success_path(self):
        """Test resilient decorator on success path."""
        @resilient(
            circuit_breaker_name="test_resilient",
            retry_config=RetryConfig(max_attempts=2, base_delay=0.01),
            timeout_operation="test_op"
        )
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"

    def test_resilient_decorator_failure_handling(self):
        """Test resilient decorator failure handling."""
        call_count = 0

        @resilient(
            circuit_breaker_name="test_resilient_fail",
            retry_config=RetryConfig(
                max_attempts=2,
                base_delay=0.01,
                retryable_exceptions=[ConnectionError]
            )
        )
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Retryable failure")
            return "success"

        result = failing_function()
        assert result == "success"
        assert call_count == 2

    def test_resilient_decorator_non_retryable_failure(self):
        """Test resilient decorator with non-retryable failure."""
        call_count = 0

        @resilient(
            retry_config=RetryConfig(
                max_attempts=3,
                retryable_exceptions=[ConnectionError]  # ValidationError not retryable
            )
        )
        def function_with_validation_error():
            nonlocal call_count
            call_count += 1
            raise ValidationError("Not retryable")

        with pytest.raises(ValidationError):
            function_with_validation_error()

        assert call_count == 1  # Should not retry


class TestFailureScenarios:
    """Test various failure scenarios and error conditions."""

    def test_network_timeout_scenario(self):
        """Test network timeout handling."""
        def slow_network_call():
            time.sleep(2)  # Simulate slow network
            return "success"

        timeout_manager.set_timeout('network_call', 1)  # 1 second timeout

        with pytest.raises(NetworkTimeoutError):
            with timeout_manager.start_operation('op1', 'network_call'):
                if timeout_manager.check_timeout('op1', 'network_call'):
                    raise NetworkTimeoutError('network_call', 1)
                slow_network_call()

    def test_rate_limit_handling(self):
        """Test rate limit error handling."""
        from core.resilience import _rate_limiters

        # Create a very restrictive rate limiter
        _rate_limiters['test_api'] = RateLimiter(rate=0.1, burst=1)  # Very slow

        @rate_limit('test_api')
        def api_call():
            return "success"

        # First call should succeed
        result = api_call()
        assert result == "success"

        # Second call should trigger rate limit
        with pytest.raises(RateLimitError) as exc_info:
            api_call()

        assert exc_info.value.error_code == "RATE_LIMIT_EXCEEDED"
        assert exc_info.value.http_status == 429

    def test_cascade_failure_prevention(self):
        """Test circuit breaker prevents cascade failures."""
        failure_count = 0

        def unreliable_service():
            nonlocal failure_count
            failure_count += 1
            raise ExternalServiceError("service", "Service unavailable")

        breaker = CircuitBreaker("cascade_test", CircuitBreakerConfig(failure_threshold=2))

        # Trigger circuit breaker to open
        for _ in range(2):
            with pytest.raises(ExternalServiceError):
                breaker.call(unreliable_service)

        assert breaker.state == CircuitState.OPEN

        # Additional calls should be blocked, not reach the service
        initial_failure_count = failure_count
        with pytest.raises(ExternalServiceError) as exc_info:
            breaker.call(unreliable_service)

        assert "Circuit breaker is open" in str(exc_info.value)
        assert failure_count == initial_failure_count  # Service not called

    def test_error_categorization_standard_exceptions(self):
        """Test categorization of standard Python exceptions."""
        from core.exceptions import categorize_exception

        # Test FileNotFoundError
        exc_info = categorize_exception(FileNotFoundError("missing.txt"))
        assert exc_info['error_code'] == 'FILE_NOT_FOUND'
        assert exc_info['category'] == 'validation'
        assert exc_info['http_status'] == 404

        # Test ValueError
        exc_info = categorize_exception(ValueError("Invalid value"))
        assert exc_info['error_code'] == 'VALUE_ERROR'
        assert exc_info['category'] == 'validation'
        assert exc_info['http_status'] == 400

        # Test ConnectionError
        exc_info = categorize_exception(ConnectionError("Network error"))
        assert exc_info['error_code'] == 'CONNECTION_ERROR'
        assert exc_info['category'] == 'external'
        assert exc_info['http_status'] == 502

    def test_exception_context_preservation(self):
        """Test that exception context is preserved through the stack."""
        def level3():
            raise PDFCorruptedError("/test.pdf", "Invalid header")

        def level2():
            try:
                level3()
            except PDFCorruptedError as e:
                # Re-raise with additional context
                e.context['processing_stage'] = 'header_validation'
                raise

        def level1():
            try:
                level2()
            except PDFCorruptedError as e:
                e.context['user_action'] = 'file_upload'
                raise

        with pytest.raises(PDFCorruptedError) as exc_info:
            level1()

        assert exc_info.value.context['processing_stage'] == 'header_validation'
        assert exc_info.value.context['user_action'] == 'file_upload'
        assert exc_info.value.context['file_path'] == '/test.pdf'

    def test_memory_and_resource_cleanup(self):
        """Test that failed operations clean up resources."""
        # This is a conceptual test - in practice you'd test actual resource cleanup
        operation_id = "test_cleanup"
        timeout_manager.start_operation(operation_id, "test_op")

        # Verify operation is tracked
        active = timeout_manager.get_active_operations()
        assert operation_id in active

        # Simulate failure and cleanup
        try:
            raise ProcessingError("Simulated failure")
        except ProcessingError:
            timeout_manager.finish_operation(operation_id)

        # Verify cleanup occurred
        active = timeout_manager.get_active_operations()
        assert operation_id not in active


if __name__ == "__main__":
    pytest.main([__file__, "-v"])