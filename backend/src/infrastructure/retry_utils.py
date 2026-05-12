"""
Retry utilities - provides decorators and functions for resilient operations.

This module implements exponential backoff retry logic for transient failures
in S3 operations and PDF generation.
"""

import logging
import time
from typing import Callable, Any, Type, Tuple, Union
from functools import wraps
import tenacity
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from botocore.exceptions import ClientError, ConnectionError as BotoConnectionError, EndpointConnectionError
from botocore.parsers import ResponseParserError


logger = logging.getLogger(__name__)


# Exceptions that should trigger a retry (transient errors)
RETRYABLE_EXCEPTIONS = (
    ClientError,  # S3/AWS transient errors
    ConnectionError,  # Python standard library connection errors
    BotoConnectionError,  # Botocore connection errors
    EndpointConnectionError,  # Botocore endpoint errors
    TimeoutError,  # Timeout errors
    IOError,  # I/O errors (disk, network)
    OSError,  # OS-level errors
)


def is_transient_error(exception: Exception) -> bool:
    """
    Determine if an exception is transient (should retry) vs permanent (should fail).
    
    Transient errors include:
    - S3 service errors (500+, throttling)
    - Connection timeouts
    - Temporary network issues
    
    NOT transient:
    - Validation errors
    - File not found (4xx client errors except 429)
    - Authentication errors (403)
    
    Args:
        exception: Exception to check
        
    Returns:
        True if the error should be retried, False otherwise
    """
    # Timeout and connection errors are always transient
    if isinstance(exception, (TimeoutError, BotoConnectionError, EndpointConnectionError)):
        return True
    
    # Python standard library connection error
    if isinstance(exception, ConnectionError):
        return True
    
    # I/O and OS errors (except for specific non-transient cases) are transient
    if isinstance(exception, (IOError, OSError)):
        # Specific exclusions could be added here if needed
        return True
    
    # For ClientError, check if it's a transient HTTP status code
    if isinstance(exception, ClientError):
        error_code = exception.response.get('Error', {}).get('Code', '')
        status_code = exception.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 0)
        
        # Don't retry validation/authentication errors
        if error_code in ['ValidationError', 'InvalidParameterValue', 'InvalidBucketName']:
            return False
        if status_code == 403:  # Forbidden - auth issue
            return False
        if status_code == 404:  # Not found - not transient
            return False
        
        # Retry 500+, 429 (throttling), and connection timeouts
        if status_code >= 500 or status_code == 429:
            return True
        if error_code in ['ServiceUnavailable', 'Throttling', 'RequestLimitExceeded']:
            return True
        
        # Connection-related error codes
        if error_code in [
            'ConnectionError', 
            'ConnectTimeout', 
            'ConnectionTimeout',
            'EndpointConnectionError',
            'IncompleteReadError',
            'HTTPClientError',
            'ProxiesUnavailable'
        ]:
            return True
        
        # 408 Request Timeout - transient
        if status_code == 408:
            return True
    
    return False


def retry_with_backoff(
    max_attempts: int = 3,
    initial_wait_seconds: float = 1.0,
    max_wait_seconds: float = 10.0,
):
    """
    Decorator that retries a function with exponential backoff on transient errors.
    
    - Max 3 attempts by default
    - Backoff: 1s, 2s, 4s (exponential)
    - Only retries transient errors (S3, network, timeout)
    - Logs retry attempts
    
    Args:
        max_attempts: Maximum number of attempts (default: 3)
        initial_wait_seconds: Initial backoff wait time (default: 1.0)
        max_wait_seconds: Maximum backoff wait time (default: 10.0)
        
    Returns:
        Decorator function
        
    Example:
        @retry_with_backoff(max_attempts=3)
        def upload_file(key, content):
            # This will retry up to 3 times with exponential backoff
            return s3_client.put_object(Bucket=bucket, Key=key, Body=content)
    """
    def decorator(func: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                multiplier=initial_wait_seconds,
                min=initial_wait_seconds,
                max=max_wait_seconds,
            ),
            retry=retry_if_exception(is_transient_error),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def manual_retry(
    func: Callable,
    max_attempts: int = 3,
    initial_wait_seconds: float = 1.0,
    operation_name: str = "operation"
) -> Any:
    """
    Manually retry a function with exponential backoff (alternative to decorator).
    
    This is useful when you need to retry inline without a decorator.
    
    Args:
        func: Callable to execute
        max_attempts: Maximum number of attempts
        initial_wait_seconds: Initial backoff time
        operation_name: Name of operation for logging
        
    Returns:
        Result of function call
        
    Raises:
        The last exception raised if all retries fail
        
    Example:
        result = manual_retry(
            lambda: s3_client.put_object(...),
            max_attempts=3,
            operation_name="S3 upload"
        )
    """
    last_exception = None
    wait_time = initial_wait_seconds
    
    for attempt in range(1, max_attempts + 1):
        try:
            logger.debug(f"Attempt {attempt}/{max_attempts} for {operation_name}")
            return func()
        
        except Exception as e:
            last_exception = e
            
            # Check if this is a transient error
            if not is_transient_error(e):
                logger.error(
                    f"Non-transient error in {operation_name} (attempt {attempt}): {type(e).__name__}: {str(e)}"
                )
                raise
            
            # Log retry
            if attempt < max_attempts:
                logger.warning(
                    f"Transient error in {operation_name} (attempt {attempt}/{max_attempts}): {type(e).__name__}. "
                    f"Retrying in {wait_time:.1f}s... {str(e)[:100]}"
                )
                time.sleep(wait_time)
                wait_time = min(wait_time * 2, 10.0)  # Exponential backoff, max 10s
            else:
                logger.error(
                    f"Final attempt {attempt}/{max_attempts} failed for {operation_name}: "
                    f"{type(e).__name__}: {str(e)}"
                )
    
    # All retries exhausted
    if last_exception:
        raise last_exception
    
    raise RuntimeError(f"Unknown error in {operation_name}")


class RetryableTransaction:
    """
    Context manager for transactional operations with automatic retry on failure.
    
    If an operation fails with a transient error, the context manager will retry
    the entire block up to max_attempts times with exponential backoff.
    
    Example:
        try:
            with RetryableTransaction(max_attempts=3) as txn:
                pdf_bytes = generate_pdf(trip)
                url = upload_to_s3(pdf_bytes)
                update_trip(trip_id, {'pdf_url': url})
        except PermanentError:
            # Handle permanent failure (validation, auth, etc.)
            pass
    """
    
    def __init__(self, max_attempts: int = 3, initial_wait_seconds: float = 1.0):
        """
        Initialize retryable transaction.
        
        Args:
            max_attempts: Maximum retry attempts
            initial_wait_seconds: Initial backoff time
        """
        self.max_attempts = max_attempts
        self.initial_wait_seconds = initial_wait_seconds
        self.attempt = 0
        self.last_error = None
    
    def __enter__(self):
        """Enter context (handled by caller managing retries)."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and handle retries."""
        if exc_type is None:
            # Success
            return True
        
        # Check if error is transient
        if not is_transient_error(exc_val):
            # Non-transient error, propagate immediately
            return False
        
        # Transient error - decide if we should retry
        self.attempt += 1
        self.last_error = exc_val
        
        if self.attempt < self.max_attempts:
            wait_time = self.initial_wait_seconds * (2 ** (self.attempt - 1))
            logger.warning(
                f"Transient error in transaction (attempt {self.attempt}/{self.max_attempts}): "
                f"{type(exc_val).__name__}. Retrying in {wait_time:.1f}s... {str(exc_val)[:100]}"
            )
            time.sleep(wait_time)
            # Suppress the exception to retry
            return True
        
        # All retries exhausted
        logger.error(
            f"Transaction failed after {self.max_attempts} attempts: "
            f"{type(exc_val).__name__}: {str(exc_val)}"
        )
        return False
