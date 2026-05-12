"""
Custom Domain Exceptions

Defines application-specific exceptions for domain and business logic errors.
Used by services to communicate failure reasons to error handlers.

Exception to HTTP Status Code Mapping:
    NotFoundError -> 404
    ValidationError -> 422
    DuplicateError -> 409
    BusinessRuleError -> 400
    UnauthorizedError -> 401
    ForbiddenError -> 403
"""

from typing import Optional, Dict, Any


class ApplicationError(Exception):
    """Base exception for all application errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize application error.
        
        Args:
            message: Human-readable error message
            status_code: HTTP status code (default: 500)
            error_code: Machine-readable error code (e.g., 'DUPLICATE_COMPANY')
            details: Additional error details for logging
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(ApplicationError):
    """Resource not found (404)."""
    
    def __init__(self, resource: str, identifier: Optional[str] = None, **kwargs):
        """
        Initialize not found error.
        
        Args:
            resource: Resource type (e.g., 'Company', 'Driver')
            identifier: Resource identifier (ID, email, etc.)
        """
        message = f"{resource} not found"
        if identifier:
            message += f" (ID: {identifier})"
        super().__init__(message, status_code=404, **kwargs)


class ValidationError(ApplicationError):
    """Input validation failed (422)."""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        """
        Initialize validation error.
        
        Args:
            message: Validation error message
            field: Field that failed validation
        """
        if field:
            message = f"Validation failed for '{field}': {message}"
        super().__init__(message, status_code=422, **kwargs)


class DuplicateError(ApplicationError):
    """Resource already exists with unique constraint (409)."""
    
    def __init__(self, resource: str, field: str, value: str, **kwargs):
        """
        Initialize duplicate error.
        
        Args:
            resource: Resource type (e.g., 'Company')
            field: Unique field that caused conflict (e.g., 'nit', 'email')
            value: Conflicting value
        """
        message = f"{resource} with {field}='{value}' already exists"
        super().__init__(message, status_code=409, **kwargs)


class BusinessRuleError(ApplicationError):
    """Business rule violation (400)."""
    
    def __init__(self, message: str, rule_name: Optional[str] = None, **kwargs):
        """
        Initialize business rule error.
        
        Args:
            message: Error message describing the violated rule
            rule_name: Name of the violated business rule
        """
        if rule_name:
            message = f"Business rule '{rule_name}': {message}"
        super().__init__(message, status_code=400, **kwargs)


class UnauthorizedError(ApplicationError):
    """Authentication failed (401)."""
    
    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(message, status_code=401, **kwargs)


class ForbiddenError(ApplicationError):
    """Authorization failed (403)."""
    
    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(message, status_code=403, **kwargs)


class ConflictError(ApplicationError):
    """Resource conflict (409)."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, status_code=409, **kwargs)


class DatabaseError(ApplicationError):
    """Database operation failed (500)."""
    
    def __init__(self, operation: str, resource: str, **kwargs):
        """
        Initialize database error.
        
        Args:
            operation: Operation that failed (insert, update, delete, query)
            resource: Resource affected
        """
        message = f"Database {operation} failed for {resource}"
        super().__init__(message, status_code=500, **kwargs)
