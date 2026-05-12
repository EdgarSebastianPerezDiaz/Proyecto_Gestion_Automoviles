"""
Global Error Handler Module

Implements centralized error handling and structured logging for all application exceptions.
Ensures consistent error responses and CloudWatch-compatible JSON logging.

Security:
- Never exposes stack traces to clients (prevents information disclosure)
- Logs detailed errors server-side for debugging
- Returns minimal error information to frontend

Handles:
- Application exceptions (NotFoundError, ValidationError, DuplicateError, BusinessRuleError)
- HTTP exceptions (404, 400, 409, 422, etc.)
- Unhandled exceptions (logged with full traceback)
"""

import logging
import traceback
from typing import Dict, Any, Tuple, Optional
from flask import Flask, request, jsonify, g, has_request_context
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge
from pydantic import ValidationError
from src.domain.exceptions import ApplicationError

logger = logging.getLogger(__name__)


def init_error_handler(app: Flask) -> None:
    """
    Register global error handlers with the Flask application.
    
    Registers handlers for:
    - ApplicationError (domain exceptions)
    - HTTPException (HTTP errors)
    - Generic Exception (unhandled errors)
    
    Args:
        app (Flask): The Flask application instance
    """
    
    @app.errorhandler(ApplicationError)
    def handle_application_error(error: ApplicationError) -> Tuple[Dict[str, Any], int]:
        """
        Handle custom application errors (NotFoundError, ValidationError, etc.).
        
        Args:
            error (ApplicationError): Application-specific exception
            
        Returns:
            Tuple[Dict, int]: JSON response and HTTP status code
        """
        request_data = _extract_request_data()
        
        # Log with application error details
        logger.error(
            f"ApplicationError: {error.error_code} - {error.message}",
            extra={
                "error_code": error.error_code,
                "status_code": error.status_code,
                "request": request_data,
                "details": error.details,
            },
        )
        
        # Return appropriate response
        response = {"error": error.message}
        if error.error_code:
            response["error_code"] = error.error_code
        
        return jsonify(response), error.status_code
    
    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_entity_too_large(error: RequestEntityTooLarge) -> Tuple[Dict[str, Any], int]:
        """
        Handle request payload exceeding MAX_CONTENT_LENGTH (10 MB).
        
        Prevents DoS attacks and resource exhaustion.
        
        Args:
            error (RequestEntityTooLarge): Werkzeug HTTP 413 exception
            
        Returns:
            Tuple[Dict, int]: JSON response and HTTP status 413
        """
        request_data = _extract_request_data()
        
        content_length = request.content_length or 0
        max_length = 10 * 1024 * 1024  # 10 MB
        
        logger.warning(
            "Request payload exceeds maximum size (413 Payload Too Large)",
            extra={
                "status_code": 413,
                "content_length": content_length,
                "max_length": max_length,
                "request": request_data,
            },
        )
        
        return (
            jsonify({
                "error": "Request payload exceeds maximum size limit (10 MB)",
                "status": "error",
                "received_bytes": content_length,
                "max_bytes": max_length,
            }),
            413,
        )
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException) -> Tuple[Dict[str, Any], int]:
        """
        Handle HTTP exceptions (404, 405, etc.).
        
        Args:
            error (HTTPException): HTTP exception raised
            
        Returns:
            Tuple[Dict, int]: JSON response and HTTP status code
        """
        request_data = _extract_request_data()
        
        # Log HTTP error
        logger.warning(
            f"HTTPException: {error.code} - {error.description or str(error)}",
            extra={
                "status_code": error.code,
                "request": request_data,
            },
        )
        
        # For 5xx errors, return generic message
        if error.code >= 500:
            return jsonify({"error": "Internal server error"}), error.code
        
        # For 4xx errors, return provided description
        return (
            jsonify({"error": error.description or "Request error"}),
            error.code,
        )
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError) -> Tuple[Dict[str, Any], int]:
        """
        Handle Pydantic ValidationError (query parameter validation failures).
        
        Converts Pydantic errors to user-friendly 422 response without exposing internals.
        
        Args:
            error (ValidationError): Pydantic validation error
            
        Returns:
            Tuple[Dict, int]: JSON response and HTTP status 422
        """
        request_data = _extract_request_data()
        
        # Extract and sanitize validation errors
        error_details = []
        for err in error.errors():
            field = ".".join(str(x) for x in err.get("loc", []))
            msg = err.get("msg", "Validation error")
            
            error_details.append({
                "field": field,
                "message": msg,
                "type": err.get("type", "unknown"),
            })
        
        # Log detailed error for backend debugging
        logger.warning(
            "Query parameter validation failed",
            extra={
                "status_code": 422,
                "error_count": len(error_details),
                "errors": error_details,
                "request": request_data,
            },
        )
        
        # Return user-friendly response (without exposing internal details)
        return (
            jsonify({
                "error": "Invalid request parameters",
                "status": "error",
                "errors": error_details,
            }),
            422,
        )
    
    @app.errorhandler(Exception)
    def handle_generic_exception(error: Exception) -> Tuple[Dict[str, Any], int]:
        """
        Handle all unhandled exceptions.
        
        Last line of defense for unexpected errors.
        Logs full traceback for debugging.
        
        Args:
            error (Exception): Unhandled exception
            
        Returns:
            Tuple[Dict, int]: JSON response and status 500
        """
        request_data = _extract_request_data()
        
        # Log with full traceback
        logger.error(
            f"Unhandled {error.__class__.__name__}: {str(error)}",
            exc_info=True,
            extra={
                "status_code": 500,
                "request": request_data,
                "traceback": traceback.format_exc(),
            },
        )
        
        # Return generic error (never expose internals)
        return jsonify({"error": "Internal server error"}), 500




def _extract_request_data() -> Dict[str, Any]:
    """
    Extract relevant request information for logging.
    
    Includes correlation_id from Flask context if available (set by request_tracing middleware).
    Falls back to headers if context is not available.
    
    Returns:
        Dict with endpoint, method, path, remote_addr, correlation_id, etc.
    """
    try:
        # Try to get correlation_id from Flask context (set by request_tracing middleware)
        correlation_id = None
        if has_request_context() and hasattr(g, 'correlation_id'):
            correlation_id = g.correlation_id
        else:
            # Fall back to headers (X-Correlation-ID or AWS trace ID)
            correlation_id = request.headers.get(
                "X-Correlation-ID",
                request.headers.get("X-Amzn-Trace-Id", "unknown"),
            )
        
        data = {
            "endpoint": request.endpoint or request.path,
            "method": request.method,
            "path": request.path,
            "remote_addr": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", "unknown"),
            "correlation_id": correlation_id,
        }
        
        # Check for authorization
        if request.headers.get("Authorization", "").startswith("Bearer "):
            data["has_auth"] = True
        
        return data
    except Exception as e:
        logger.error(f"Failed to extract request data: {str(e)}")
        return {"error": "Could not extract request data", "correlation_id": "unknown"}
