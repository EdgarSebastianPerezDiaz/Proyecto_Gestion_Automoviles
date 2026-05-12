"""
Retry Logic with Exponential Backoff

Implements automatic retry with exponential backoff for transient failures.
Used for MongoDB operations and other I/O that might temporarily fail.
"""

import logging
import time
from typing import Callable, TypeVar, Optional, List, Type
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryStrategy:
    """
    Configurable retry strategy with exponential backoff.
    
    Attributes:
        max_attempts: Maximum number of retry attempts (default: 3)
        initial_delay_ms: Initial delay in milliseconds (default: 100)
        max_delay_ms: Maximum delay between retries (default: 10000)
        backoff_multiplier: Exponential backoff multiplier (default: 2.0)
        retryable_exceptions: Exception types that trigger retry (default: all)
    
    Example:
        ```python
        strategy = RetryStrategy(max_attempts=3, initial_delay_ms=100)
        result = strategy.execute(
            lambda: db.collection.find_one({"id": 1}),
            operation_name="find_document"
        )
        ```
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay_ms: int = 100,
        max_delay_ms: int = 10000,
        backoff_multiplier: float = 2.0,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
    ):
        """Initialize retry strategy."""
        self.max_attempts = max_attempts
        self.initial_delay_ms = initial_delay_ms
        self.max_delay_ms = max_delay_ms
        self.backoff_multiplier = backoff_multiplier
        
        # Default retryable exceptions: transient network/timeout errors
        default_exceptions = [
            ConnectionError,
            TimeoutError,
            OSError,  # Includes ConnectionRefusedError, ConnectionResetError
        ]
        self.retryable_exceptions = retryable_exceptions or default_exceptions
        
        logger.debug(
            f"RetryStrategy configured: "
            f"attempts={max_attempts}, initial_delay={initial_delay_ms}ms, "
            f"backoff={backoff_multiplier}x"
        )
    
    def execute(
        self,
        func: Callable[..., T],
        *args,
        operation_name: str = "operation",
        **kwargs
    ) -> T:
        """
        Execute function with automatic retry on transient failures.
        
        Args:
            func: Callable to execute
            *args: Positional arguments
            operation_name: Name for logging purposes
            **kwargs: Keyword arguments
            
        Returns:
            Function result on success
            
        Raises:
            Last exception if all retries exhausted
        """
        last_exception = None
        current_delay_ms = self.initial_delay_ms
        
        for attempt in range(self.max_attempts):
            try:
                result = func(*args, **kwargs)
                
                if attempt > 0:
                    logger.debug(
                        f"{operation_name}: succeeded on retry attempt {attempt + 1}",
                        extra={"operation": operation_name, "attempt": attempt + 1}
                    )
                
                return result
            
            except Exception as e:
                # Check if this exception is retryable
                is_retryable = any(
                    isinstance(e, exc_type)
                    for exc_type in self.retryable_exceptions
                )
                
                if not is_retryable or attempt == self.max_attempts - 1:
                    # Not retryable or last attempt - raise immediately
                    logger.error(
                        f"{operation_name}: failed (not retryable or final attempt)",
                        extra={
                            "operation": operation_name,
                            "attempt": attempt + 1,
                            "total_attempts": self.max_attempts,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    )
                    raise
                
                # Retryable error - log and retry with delay
                last_exception = e
                logger.warning(
                    f"{operation_name}: failed on attempt {attempt + 1}/{self.max_attempts}, "
                    f"retrying in {current_delay_ms}ms",
                    extra={
                        "operation": operation_name,
                        "attempt": attempt + 1,
                        "total_attempts": self.max_attempts,
                        "delay_ms": current_delay_ms,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                )
                
                # Sleep with exponential backoff
                time.sleep(current_delay_ms / 1000.0)
                
                # Calculate next delay (with cap at max_delay_ms)
                current_delay_ms = min(
                    int(current_delay_ms * self.backoff_multiplier),
                    self.max_delay_ms
                )
        
        # Should not reach here, but handle gracefully
        if last_exception:
            raise last_exception
        raise RuntimeError(f"Failed to execute {operation_name} after {self.max_attempts} attempts")


# Default retry strategy for common operations
DEFAULT_RETRY = RetryStrategy(
    max_attempts=3,
    initial_delay_ms=100,
    max_delay_ms=5000,
    backoff_multiplier=2.0,
)


def retry_with_backoff(
    func: Callable[..., T],
    *args,
    max_attempts: int = 3,
    initial_delay_ms: int = 100,
    operation_name: str = "operation",
    **kwargs
) -> T:
    """
    Convenience function for one-off retry operations.
    
    Args:
        func: Callable to execute with retry
        *args: Positional arguments
        max_attempts: Number of retry attempts
        initial_delay_ms: Initial delay in milliseconds
        operation_name: Name for logging
        **kwargs: Keyword arguments
        
    Returns:
        Function result
        
    Example:
        ```python
        result = retry_with_backoff(
            lambda: db.command('ping'),
            max_attempts=3,
            operation_name="mongodb_ping"
        )
        ```
    """
    strategy = RetryStrategy(
        max_attempts=max_attempts,
        initial_delay_ms=initial_delay_ms,
    )
    return strategy.execute(func, *args, operation_name=operation_name, **kwargs)
