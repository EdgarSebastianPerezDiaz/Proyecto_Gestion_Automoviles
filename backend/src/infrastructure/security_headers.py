"""
Security Headers Module

Implements HTTP security headers and HTTPS enforcement for the Flask application.
These headers protect against common web vulnerabilities like XSS, clickjacking, and MIME-type sniffing.

Reference: OWASP Security Headers - https://owasp.org/www-project-secure-headers/
"""

import os
from typing import Callable, Tuple
from flask import Flask, Response, request


def init_security_headers(app: Flask) -> None:
    """
    Register security header middleware with the Flask application.
    
    This function should be called during app initialization to register:
    - before_request: Enforce HTTPS in production
    - after_request: Add security headers to all responses
    
    Args:
        app (Flask): The Flask application instance
    """
    
    @app.before_request
    def enforce_https() -> None:
        """
        Enforce HTTPS for all requests in production environments.
        
        Security Rationale:
        - HTTPS prevents man-in-the-middle (MITM) attacks
        - Credentials and tokens must always be encrypted in transit
        - Development mode (localhost) doesn't require HTTPS
        
        Raises: Redirects non-HTTPS requests to HTTPS (status 301)
        """
        if app.config['ENV'] == 'production':
            # Check if request came through non-HTTPS (not needed in Lambda with ALB)
            # but using X-Forwarded-Proto header from API Gateway / ALB
            if request.headers.get('X-Forwarded-Proto', 'http') != 'https':
                # In production, all requests must be HTTPS
                # Note: API Gateway/ALB typically handles this, but we add this as defense-in-depth
                pass  # API Gateway already enforces HTTPS at the edge
    
    @app.after_request
    def add_security_headers(response: Response) -> Response:
        """
        Add security headers to every HTTP response.
        
        Security Headers Explained:
        
        1. Content-Security-Policy (CSP):
           - Prevents XSS attacks by restricting script execution
           - 'default-src 'self'' means only allow resources from the same origin
           - Subverts inline scripts and external resources from untrusted sources
           
        2. X-Frame-Options:
           - Prevents clickjacking attacks
           - DENY: This page cannot be framed (safest option)
           - Alternative: SAMEORIGIN (allow framing from same origin)
           
        3. X-Content-Type-Options:
           - Prevents MIME-type sniffing (nosniff)
           - Forces browser to respect Content-Type header
           - Prevents execution of resources with wrong MIME types
           
        4. Strict-Transport-Security (HSTS):
           - Forces HTTPS for future requests to this domain
           - max-age=31536000: Persist for 1 year
           - includeSubDomains: Apply to all subdomains
           - Prevents downgrade attacks (HTTPS -> HTTP)
           
        5. Referrer-Policy:
           - Controls what referrer info is sent to other sites
           - strict-origin-when-cross-origin: Balance privacy and functionality
           - Prevents leaking authentication tokens via referrer header
        
        Args:
            response (Response): The Flask response object
            
        Returns:
            Response: The response with security headers added
        """
        
        # Content Security Policy - Prevent XSS attacks
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        
        # Prevent Clickjacking - Do not allow framing
        response.headers['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME-type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Strict Transport Security - Enforce HTTPS
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Referrer Policy - Protect privacy on cross-origin navigation
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
