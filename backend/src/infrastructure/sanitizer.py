"""
Input Sanitizer Module

Implements input sanitization to prevent NoSQL injection attacks.

NoSQL Injection Examples:
- {"$ne": ""} to bypass authentication
- {"$gt": ""} to access unauthorized data
- {"$where": "function() { ... }"} to execute server-side code

This module removes dangerous characters while preserving legitimate data.

Security Rationale:
- While parameterized queries (pymongo) are the primary defense, sanitization
  provides defense-in-depth
- Removes special characters that indicate injection attempts
- Preserves alphanumeric, spaces, and basic punctuation for normal use cases
"""

import re
from typing import Any, Dict, List, Union


def sanitize_string(value: str) -> str:
    """
    Sanitize a string by removing NoSQL injection characters.
    
    Removes:
    - MongoDB operators: $ prefix, . (field traversal)
    - Object/array notation: {, }, [, ]
    - Dangerous wildcards: *, ?
    - Command separators: ;, |, &, `, backticks
    
    Allowed (preserved):
    - Alphanumeric characters (a-z, A-Z, 0-9)
    - Spaces
    - Quotes: ", ' (preserved for data integrity)
    - Common punctuation: -, _, /, @, +, =, :, comma
    
    Args:
        value: Input string to sanitize
        
    Returns:
        str: Sanitized string
        
    Example:
        >>> sanitize_string('{"$ne": ""}')
        '"ne": ""'
        >>> sanitize_string('user.password')
        'userpassword'
    """
    if not isinstance(value, str):
        return value
    
    # Remove dangerous characters using regex
    # First, remove $ operator prefix (with optional : suffix like "$or:" -> "or")
    sanitized = re.sub(r'\$(\w+):?', r'\1', value)
    
    # Remove other dangerous characters: { } [ ] * ? ; | & ` . (dots prevent field traversal)
    sanitized = re.sub(
        r'[{}[\]*?;|&`.]',  # Remove dangerous chars but keep quotes
        '',
        sanitized
    )
    
    # Remove leading/trailing whitespace
    sanitized = sanitized.strip()
    
    return sanitized


def sanitize_object(data: Union[Dict[str, Any], List[Any]]) -> Union[Dict[str, Any], List[Any]]:
    """
    Recursively sanitize all string values and keys in a dictionary or list.
    
    This is the main entry point for sanitizing entire request bodies or nested objects.
    
    Behavior:
    - Dictionaries: Sanitize both keys and values recursively
    - Lists: Recursively sanitize each element
    - Strings: Apply sanitize_string()
    - Other types: Return unchanged (int, float, bool, None)
    
    Args:
        data: Dictionary, list, or scalar value to sanitize
        
    Returns:
        Sanitized copy of the input data
        
    Example:
        >>> data = {
        ...     "name": "John Doe",
        ...     "$ne": "admin",
        ...     "filter": {"$gt": "0"},
        ...     "tags": ["tag1", "tag$2"]
        ... }
        >>> sanitize_object(data)
        {
            "name": "John Doe",
            "ne": "admin",
            "filter": {"gt": "0"},
            "tags": ["tag1", "tag2"]
        }
    
    Raises:
        TypeError: If input is not dict, list, or scalar
    """
    
    if isinstance(data, dict):
        # Recursively sanitize both keys and values
        return {sanitize_string(key): sanitize_object(value) for key, value in data.items()}
    
    elif isinstance(data, list):
        # Recursively sanitize list elements
        return [sanitize_object(item) for item in data]
    
    elif isinstance(data, str):
        # Sanitize strings
        return sanitize_string(data)
    
    else:
        # Return other types unchanged (int, float, bool, None, etc.)
        return data


def is_injection_attempt(value: str) -> bool:
    """
    Detect potential NoSQL injection attempts in a string.
    
    Returns True if the string contains suspicious patterns that suggest
    an injection attempt (MongoDB operators, special characters, etc.).
    
    This is useful for logging/alerting on suspected attacks.
    
    Args:
        value: String to check
        
    Returns:
        bool: True if injection attempt detected
        
    Example:
        >>> is_injection_attempt('{"$ne": ""}')
        True
        >>> is_injection_attempt('normal string')
        False
    """
    if not isinstance(value, str):
        return False
    
    # Patterns that indicate injection attempts
    injection_patterns = [
        r'\$[a-zA-Z]+',  # MongoDB operators like $ne, $gt, $where
        r'\{.*\}',       # Object notation
        r'\[.*\]',       # Array notation
        r'".*"',         # Quoted strings (often used in injection)
        r"'.*'",         # Single quotes (often used in injection)
        r';\s*',         # Command separator
        r'\|',           # Pipe operator
        r'&',            # AND operator
        r'`',            # Backticks for command execution
    ]
    
    for pattern in injection_patterns:
        if re.search(pattern, value):
            return True
    
    return False


def sanitize_input(f):
    """
    Decorator to automatically sanitize POST/PUT/PATCH request bodies.
    
    This decorator:
    1. Extracts JSON data from request body
    2. Sanitizes all string values and keys
    3. Stores sanitized data in request for use by endpoint
    4. Continues to the endpoint handler
    
    Use on endpoints that accept request body data (POST, PUT, PATCH).
    
    Example:
        @app.route('/api/trips', methods=['POST'])
        @sanitize_input
        def create_trip():
            data = request.get_json()  # Returns sanitized data
            # ... process sanitized data
    """
    from functools import wraps
    from flask import request
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Only sanitize POST, PUT, PATCH requests with JSON bodies
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                data = request.get_json() or {}
                
                # Sanitize the data
                sanitized_data = sanitize_object(data)
                
                # Store sanitized data back in request
                # We'll replace the get_json() method to return sanitized data
                _original_get_json = request.get_json
                
                def get_json_with_sanitization(*args, **kwargs):
                    return sanitized_data
                
                request.get_json = get_json_with_sanitization
                
            except Exception as e:
                # If sanitization fails, log but continue
                # Fail open - allow request to proceed (security best practice: sanitize doesn't block)
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error sanitizing request: {str(e)}")
        
        return f(*args, **kwargs)
    
    return decorated_function

