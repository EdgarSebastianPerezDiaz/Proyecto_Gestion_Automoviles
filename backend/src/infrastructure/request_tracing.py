"""
Request Tracing Module - Flask Context Management for Request ID Propagation

Implements request lifecycle management to generate and propagate unique request IDs
throughout the request context for comprehensive logging and debugging.

Key Features:
- Generates UUID4 for each HTTP request
- Stores request ID in Flask's g (application context)
- Propagates to all logs via JSONFormatter
- Exposes request ID in response headers for client-side correlation
- Handles both direct connections and proxied requests (X-Forwarded-For)

Usage:
    from src.infrastructure.request_tracing import init_request_tracing
    
    app = Flask(__name__)
    init_request_tracing(app)
"""

import logging
from uuid import uuid4
from typing import Optional
from flask import Flask, g, request

logger = logging.getLogger(__name__)


def init_request_tracing(app: Flask) -> None:
    """
    Initialize request tracing middleware for the Flask application.
    
    Registers before_request and after_request hooks to manage request IDs
    throughout the request lifecycle.
    
    Args:
        app (Flask): Flask application instance
    """
    
    @app.before_request
    def before_request() -> None:
        """
        Generate and store correlation ID at the beginning of each request.
        
        Checks for client-provided X-Correlation-ID header. If present, uses it;
        otherwise generates a new UUID4. This allows clients to correlate logs
        if they have their own request tracking.
        
        Storage:
        - g.correlation_id: Flask's request context (available to all functions)
        - g.request_start_time: Timestamp for request latency tracking
        """
        # Try to use client-provided correlation ID (if behind proxy with request tracking)
        client_correlation_id = request.headers.get('X-Correlation-ID')
        
        if client_correlation_id and _is_valid_correlation_id(client_correlation_id):
            g.correlation_id = client_correlation_id
            g.correlation_id_source = 'client'
        else:
            # Generate new UUID4 in hex format (standard UUID string format)
            g.correlation_id = str(uuid4())
            g.correlation_id_source = 'generated'
        
        # Store request start time for latency tracking
        from datetime import datetime, timezone
        g.request_start_time = datetime.now(timezone.utc)
        
        # Log request start
        logger.info(
            "Request started",
            extra={
                'correlation_id': g.correlation_id,
                'method': request.method,
                'path': request.path,
                'remote_addr': _get_client_ip(),
                'user_agent': request.headers.get('User-Agent', ''),
            }
        )
    
    @app.after_request
    def after_request(response):
        """
        Add correlation ID to response headers and log request completion.
        
        Args:
            response: Flask response object
            
        Returns:
            Modified response with X-Correlation-ID header
        """
        # Add correlation ID to response headers for client-side correlation
        if hasattr(g, 'correlation_id'):
            response.headers['X-Correlation-ID'] = g.correlation_id
            
            # Calculate request duration
            from datetime import datetime, timezone
            duration_ms = None
            if hasattr(g, 'request_start_time'):
                duration = datetime.now(timezone.utc) - g.request_start_time
                duration_ms = int(duration.total_seconds() * 1000)
                response.headers['X-Request-Duration-MS'] = str(duration_ms)
            
            # Log request completion
            logger.info(
                "Request completed",
                extra={
                    'correlation_id': g.correlation_id,
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'content_length': response.content_length or 0,
                    'duration_ms': duration_ms,
                }
            )
        
        return response
    
    logger.debug("Request tracing middleware initialized")


def _get_client_ip() -> str:
    """
    Extract client IP address from request.
    
    Handles multiple scenarios:
    1. Direct connection: Uses request.remote_addr
    2. Behind load balancer: Uses X-Forwarded-For (takes leftmost IP)
    3. Behind proxy chain: Takes first (leftmost) IP in X-Forwarded-For
    
    Returns:
        Client IP address as string (or 'unknown' if detection fails)
    """
    try:
        # Try X-Forwarded-For first (set by load balancers/proxies)
        # Format: "client, proxy1, proxy2" - we want the leftmost (original client)
        x_forwarded_for = request.headers.get('X-Forwarded-For')
        if x_forwarded_for:
            # Take first IP and remove whitespace
            return x_forwarded_for.split(',')[0].strip()
        
        # Fall back to direct connection IP
        return request.remote_addr or 'unknown'
    
    except Exception as e:
        logger.warning(f"Failed to extract client IP: {str(e)}")
        return 'unknown'


def _is_valid_correlation_id(correlation_id: str) -> bool:
    """
    Validate that correlation ID is in valid format.
    
    Accepts:
    - UUID4 format (xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx)
    - Alphanumeric strings with hyphens
    
    Rejects:
    - Strings longer than 64 characters (prevent ID spoofing)
    - Strings containing SQL injection patterns
    - Empty strings
    
    Args:
        correlation_id: Correlation ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not correlation_id:
        return False
    
    # Check length (UUID4 is 36 chars, but allow custom IDs up to 64)
    if len(correlation_id) > 64:
        return False
    
    # Check character whitelist (alphanumeric, hyphens, underscores)
    import re
    if not re.match(r'^[\w\-]+$', correlation_id):
        return False
    
    return True


def get_correlation_id() -> str:
    """
    Get the current correlation ID from Flask context.
    
    Safe to call from anywhere during request processing.
    Returns 'no-correlation-id' if called outside request context.
    
    Returns:
        Correlation ID string or 'no-correlation-id' if not in request context
    """
    try:
        return g.get('correlation_id', 'no-correlation-id')
    except RuntimeError:
        # Called outside request context
        return 'no-correlation-id'
