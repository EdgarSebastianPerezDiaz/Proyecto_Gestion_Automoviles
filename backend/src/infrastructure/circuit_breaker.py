"""
Circuit Breaker Pattern for MongoDB Connections

Prevents cascading failures when MongoDB is temporarily unavailable.
Implements a state machine: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
"""

import time
import logging
from enum import Enum
from datetime import datetime, timedelta, timezone
from typing import Callable, Any, TypeVar, Optional

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"          # Normal operation, requests pass through
    OPEN = "open"              # Failures exceeded, requests blocked
    HALF_OPEN = "half_open"    # Testing if service recovered


class CircuitBreaker:
    """
    Circuit Breaker implementation for MongoDB operations.
    
    Prevents cascading failures by failing fast when a service is down.
    
    States:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Too many failures, requests immediately fail
    - HALF_OPEN: Attempting recovery, next request is trial
    
    Args:
        failure_threshold: Number of failures before opening (default: 5)
        recovery_timeout: Seconds before attempting recovery (default: 60)
        expected_exception: Exception type to catch (default: Exception)
    
    Example:
        ```python
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        
        @breaker.call
        def query_mongodb():
            return collection.find_one({"id": 123})
        ```
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        """Initialize circuit breaker."""
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitBreakerState.CLOSED
        
        logger.info(
            f"CircuitBreaker initialized: "
            f"failures={failure_threshold}, timeout={recovery_timeout}s"
        )
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Callable to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpen: If circuit is open
            Original exception: If func raises expected_exception
        """
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info("CircuitBreaker: attempting recovery (HALF_OPEN)")
            else:
                raise CircuitBreakerOpen(
                    f"Circuit breaker is OPEN. "
                    f"Service unavailable for {self.recovery_timeout}s"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if not self.last_failure_time:
            return False
        
        elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED
            logger.info("CircuitBreaker: service recovered (CLOSED)")
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)
        
        logger.warning(
            f"CircuitBreaker failure: {self.failure_count}/{self.failure_threshold}",
            extra={
                "failure_count": self.failure_count,
                "threshold": self.failure_threshold,
                "state": self.state.value,
            }
        )
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.error(
                "CircuitBreaker: threshold exceeded, opening circuit (OPEN)",
                extra={
                    "failure_count": self.failure_count,
                    "threshold": self.failure_threshold,
                }
            )
    
    def reset(self):
        """Manually reset the circuit breaker."""
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        logger.info("CircuitBreaker manually reset")
    
    def get_state(self) -> dict:
        """Get current circuit breaker state for monitoring."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
        }


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open and prevents request."""
    pass


class MongoDBCircuitBreaker:
    """
    MongoDB-specific circuit breaker wrapper.
    
    Automatically applies circuit breaker pattern to MongoDB operations
    with appropriate error handling and logging.
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """Initialize MongoDB circuit breaker."""
        self.breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=Exception,
        )
    
    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute MongoDB operation with circuit breaker.
        
        Args:
            func: MongoDB operation to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Operation result
            
        Raises:
            CircuitBreakerOpen: If service is unavailable
        """
        try:
            return self.breaker.call(func, *args, **kwargs)
        except CircuitBreakerOpen as e:
            logger.error(
                f"MongoDB circuit breaker open: {str(e)}",
                extra={"circuit_state": self.breaker.get_state()}
            )
            raise
