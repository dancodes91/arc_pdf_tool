"""
Resilience patterns for reliable operation.

Implements retries, timeouts, circuit breakers, and other patterns
for handling transient failures and external service dependencies.
"""

import asyncio
import time
import random
import logging
from typing import Callable, Any, Optional, Dict, List, Type
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import threading

try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential_jitter,
        retry_if_exception_type,
        before_sleep_log,
    )

    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False

from .exceptions import (
    ExternalServiceError,
    NetworkTimeoutError,
    RateLimitError,
    ResourceExhaustedError,
)

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Failures before opening
    recovery_timeout: int = 60  # Seconds before trying half-open
    success_threshold: int = 3  # Successes to close from half-open
    timeout: int = 30  # Operation timeout in seconds
    excluded_exceptions: List[Type[Exception]] = field(default_factory=list)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    exponential_base: float = 2.0  # Exponential backoff base
    jitter: bool = True  # Add random jitter
    retryable_exceptions: List[Type[Exception]] = field(
        default_factory=lambda: [
            ExternalServiceError,
            NetworkTimeoutError,
            ConnectionError,
            TimeoutError,
            ResourceExhaustedError,
        ]
    )


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Protects against cascading failures by temporarily blocking
    requests to failing services and allowing gradual recovery.
    """

    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        self._lock = threading.Lock()

        self.logger = logging.getLogger(f"{__name__}.{name}")

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    self.logger.info(f"Circuit breaker {self.name}: Attempting half-open")
                else:
                    raise ExternalServiceError(
                        service=self.name,
                        message="Circuit breaker is open",
                        error_code="CIRCUIT_BREAKER_OPEN",
                        retry_after=self._time_until_retry(),
                    )

        try:
            # Execute with timeout
            if asyncio.iscoroutinefunction(func):
                result = asyncio.wait_for(func(*args, **kwargs), timeout=self.config.timeout)
            else:
                # For sync functions, we'd need a different timeout mechanism
                result = func(*args, **kwargs)

            self._on_success()
            return result

        except Exception as e:
            if not any(isinstance(e, exc_type) for exc_type in self.config.excluded_exceptions):
                self._on_failure(e)
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True

        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.config.recovery_timeout

    def _time_until_retry(self) -> int:
        """Calculate seconds until next retry attempt."""
        if self.last_failure_time is None:
            return 0

        elapsed = time.time() - self.last_failure_time
        remaining = self.config.recovery_timeout - elapsed
        return max(0, int(remaining))

    def _on_success(self):
        """Handle successful operation."""
        with self._lock:
            self.last_success_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.logger.info(f"Circuit breaker {self.name}: Closed after recovery")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0  # Reset failure count on success

    def _on_failure(self, exception: Exception):
        """Handle failed operation."""
        with self._lock:
            self.last_failure_time = time.time()
            self.failure_count += 1

            if self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN
                    self.logger.warning(
                        f"Circuit breaker {self.name}: Opened after {self.failure_count} failures"
                    )
            elif self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.logger.warning(
                    f"Circuit breaker {self.name}: Returned to open state after failure in half-open"
                )

    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "time_until_retry": self._time_until_retry() if self.state == CircuitState.OPEN else 0,
        }

    def reset(self):
        """Manually reset circuit breaker to closed state."""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.logger.info(f"Circuit breaker {self.name}: Manually reset")


# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]


def circuit_breaker(name: str, config: CircuitBreakerConfig = None):
    """Decorator to add circuit breaker protection to functions."""
    breaker = get_circuit_breaker(name, config)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)

        return wrapper

    return decorator


def retry_with_backoff(config: RetryConfig = None):
    """
    Decorator to add retry with exponential backoff.

    Uses tenacity if available, otherwise implements basic retry logic.
    """
    config = config or RetryConfig()

    def decorator(func):
        if TENACITY_AVAILABLE:
            # Use tenacity for advanced retry logic
            @retry(
                stop=stop_after_attempt(config.max_attempts),
                wait=wait_exponential_jitter(
                    initial=config.base_delay,
                    max=config.max_delay,
                    exp_base=config.exponential_base,
                    jitter=True if config.jitter else False,
                ),
                retry=retry_if_exception_type(tuple(config.retryable_exceptions)),
                before_sleep=before_sleep_log(logger, logging.WARNING),
            )
            @wraps(func)
            def tenacity_wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return tenacity_wrapper

        else:
            # Basic retry implementation
            @wraps(func)
            def basic_wrapper(*args, **kwargs):
                last_exception = None

                for attempt in range(config.max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e

                        # Check if exception is retryable
                        if not any(
                            isinstance(e, exc_type) for exc_type in config.retryable_exceptions
                        ):
                            raise

                        # Don't sleep on last attempt
                        if attempt < config.max_attempts - 1:
                            delay = _calculate_delay(attempt, config)
                            logger.warning(
                                f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}"
                            )
                            time.sleep(delay)

                # All attempts failed
                raise last_exception

            return basic_wrapper

    return decorator


def _calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for retry attempt."""
    delay = config.base_delay * (config.exponential_base**attempt)
    delay = min(delay, config.max_delay)

    if config.jitter:
        # Add ±25% jitter
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)

    return max(0, delay)


class TimeoutManager:
    """
    Manages timeouts for operations with different time limits.

    Provides per-operation timeout tracking and cancellation.
    """

    def __init__(self):
        self.active_operations: Dict[str, datetime] = {}
        self.timeouts: Dict[str, int] = {
            "pdf_parsing": 300,  # 5 minutes for PDF parsing
            "ocr_processing": 120,  # 2 minutes for OCR
            "table_extraction": 60,  # 1 minute for table extraction
            "diff_creation": 180,  # 3 minutes for diff creation
            "baserow_sync": 300,  # 5 minutes for Baserow sync
            "export": 120,  # 2 minutes for export
        }

    def set_timeout(self, operation_type: str, timeout_seconds: int):
        """Set timeout for operation type."""
        self.timeouts[operation_type] = timeout_seconds

    def start_operation(self, operation_id: str, operation_type: str) -> bool:
        """Start tracking an operation. Returns False if timeout would be exceeded."""
        timeout = self.timeouts.get(operation_type, 60)  # Default 1 minute
        self.active_operations[operation_id] = datetime.now()

        logger.info(f"Started operation {operation_id} ({operation_type}) with {timeout}s timeout")
        return True

    def check_timeout(self, operation_id: str, operation_type: str) -> bool:
        """Check if operation has timed out. Returns True if timed out."""
        if operation_id not in self.active_operations:
            return False

        start_time = self.active_operations[operation_id]
        timeout = self.timeouts.get(operation_type, 60)
        elapsed = (datetime.now() - start_time).total_seconds()

        if elapsed > timeout:
            logger.warning(f"Operation {operation_id} timed out after {elapsed:.1f}s")
            self.finish_operation(operation_id)
            return True

        return False

    def finish_operation(self, operation_id: str):
        """Mark operation as finished."""
        if operation_id in self.active_operations:
            start_time = self.active_operations[operation_id]
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Operation {operation_id} completed in {elapsed:.1f}s")
            del self.active_operations[operation_id]

    def get_active_operations(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all active operations."""
        now = datetime.now()
        result = {}

        for op_id, start_time in self.active_operations.items():
            elapsed = (now - start_time).total_seconds()
            result[op_id] = {"start_time": start_time.isoformat(), "elapsed_seconds": elapsed}

        return result


# Global timeout manager instance
timeout_manager = TimeoutManager()


def with_timeout(operation_type: str, operation_id: str = None):
    """Decorator to add timeout tracking to functions."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_id = operation_id or f"{func.__name__}_{int(time.time())}"

            timeout_manager.start_operation(op_id, operation_type)

            try:
                # Check timeout before starting
                if timeout_manager.check_timeout(op_id, operation_type):
                    raise NetworkTimeoutError(
                        operation=operation_type,
                        timeout=timeout_manager.timeouts.get(operation_type, 60),
                    )

                result = func(*args, **kwargs)
                timeout_manager.finish_operation(op_id)
                return result

            except Exception as e:
                timeout_manager.finish_operation(op_id)
                raise

        return wrapper

    return decorator


class RateLimiter:
    """
    Token bucket rate limiter.

    Limits the rate of operations to prevent overwhelming external services.
    """

    def __init__(self, rate: float, burst: int = None, name: str = "default"):
        self.rate = rate  # Tokens per second
        self.burst = burst or int(rate * 2)  # Bucket capacity
        self.tokens = self.burst
        self.last_update = time.time()
        self.name = name
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1, timeout: float = None) -> bool:
        """
        Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum time to wait for tokens (None = don't wait)

        Returns:
            True if tokens acquired, False if timeout exceeded
        """
        start_time = time.time()

        while True:
            with self._lock:
                now = time.time()
                # Add tokens based on elapsed time
                elapsed = now - self.last_update
                self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
                self.last_update = now

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True

            # Check timeout
            if timeout is not None:
                if time.time() - start_time >= timeout:
                    return False

                # Sleep briefly before trying again
                time.sleep(0.01)
            else:
                return False

    def get_status(self) -> Dict[str, Any]:
        """Get current rate limiter status."""
        return {
            "name": self.name,
            "rate": self.rate,
            "burst": self.burst,
            "available_tokens": self.tokens,
            "last_update": self.last_update,
        }


# Global rate limiters
_rate_limiters: Dict[str, RateLimiter] = {
    "baserow_api": RateLimiter(rate=10.0, burst=20, name="baserow_api"),  # 10 req/sec
    "ocr_processing": RateLimiter(rate=2.0, burst=5, name="ocr_processing"),  # 2 req/sec
    "export": RateLimiter(rate=5.0, burst=10, name="export"),  # 5 req/sec
}


def get_rate_limiter(name: str) -> Optional[RateLimiter]:
    """Get rate limiter by name."""
    return _rate_limiters.get(name)


def rate_limit(limiter_name: str, tokens: int = 1, timeout: float = None):
    """Decorator to add rate limiting to functions."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter = get_rate_limiter(limiter_name)
            if limiter:
                if not limiter.acquire(tokens, timeout):
                    raise RateLimitError(
                        service=limiter_name,
                        limit=int(limiter.rate),
                        reset_time=int(60 / limiter.rate),  # Approximate reset time
                    )

            return func(*args, **kwargs)

        return wrapper

    return decorator


# Combined resilience decorator
def resilient(
    circuit_breaker_name: str = None,
    circuit_config: CircuitBreakerConfig = None,
    retry_config: RetryConfig = None,
    timeout_operation: str = None,
    rate_limiter_name: str = None,
    rate_limit_tokens: int = 1,
):
    """
    Combined decorator for resilience patterns.

    Applies circuit breaker, retry, timeout, and rate limiting as specified.
    """

    def decorator(func):
        # Apply decorators in order (innermost first)
        decorated_func = func

        # Rate limiting (innermost)
        if rate_limiter_name:
            decorated_func = rate_limit(rate_limiter_name, rate_limit_tokens)(decorated_func)

        # Timeout tracking
        if timeout_operation:
            decorated_func = with_timeout(timeout_operation)(decorated_func)

        # Retry logic
        if retry_config or True:  # Default retry
            decorated_func = retry_with_backoff(retry_config)(decorated_func)

        # Circuit breaker (outermost)
        if circuit_breaker_name:
            decorated_func = circuit_breaker(circuit_breaker_name, circuit_config)(decorated_func)

        return decorated_func

    return decorator


def get_resilience_status() -> Dict[str, Any]:
    """Get status of all resilience components."""
    return {
        "circuit_breakers": {name: cb.get_status() for name, cb in _circuit_breakers.items()},
        "rate_limiters": {name: rl.get_status() for name, rl in _rate_limiters.items()},
        "active_operations": timeout_manager.get_active_operations(),
        "timeout_config": timeout_manager.timeouts,
    }
