"""
CORS (Cross-Origin Resource Sharing) Configuration Module

Implements secure cross-origin request handling for the Flask application.
Only allows requests from specified origins with restricted HTTP methods.

Reference: MDN CORS - https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
"""

import os
from typing import List
from flask import Flask
from flask_cors import CORS


def init_cors(app: Flask) -> None:
    """
    Configure CORS for the Flask application with security restrictions.
    
    Security Rationale:
    - CORS is necessary for frontend apps on different domains/ports
    - Restricting origins prevents unauthorized access from malicious sites
    - Limiting HTTP methods reduces attack surface
    - Credentials require explicit allow (secure mode only)
    
    Configuration:
    - Only allows origin specified in CORS_ORIGIN environment variable
    - Default: http://localhost:4200 (typical Angular dev server)
    - Allows credentials (authentication tokens in requests/responses)
    - Restricted to safe HTTP methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
    
    Args:
        app (Flask): The Flask application instance
    """
    
    # Get allowed origin from environment variable
    # Default to localhost for development
    cors_origin: str = os.getenv('CORS_ORIGIN', 'http://localhost:4200')
    
    # Security: Convert single origin to list format required by CORS
    # In production, use comma-separated origins if multiple are needed
    allowed_origins: List[str] = [origin.strip() for origin in cors_origin.split(',')]
    
    # Configure CORS with restricted settings
    CORS(
        app,
        resources={
            r"/*": {
                # Only allow requests from specified origins
                "origins": allowed_origins,
                
                # Allow credentials (cookies, authorization headers)
                # Important: When credentials are allowed, origins cannot be '*'
                "allow_headers": ["Content-Type", "Authorization"],
                
                # Allow only safe, restricted HTTP methods
                "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                
                # Allow credentials in requests (cookies, auth headers)
                "supports_credentials": True,
                
                # Client can access these response headers
                "expose_headers": ["Content-Type", "X-Total-Count"],
                
                # Browser caches preflight response for 1 hour
                "max_age": 3600,
            }
        }
    )
    
    app.logger.info(
        f"CORS configured with allowed origins: {', '.join(allowed_origins)}"
    )
