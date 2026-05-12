"""
Authentication API Blueprint

Implements REST endpoints for user registration and login.
Integrates rate limiting and Pydantic validation for security.

Endpoints:
- POST /auth/register: Register new user
- POST /auth/login: Authenticate user and get token
"""

from flask import Blueprint, request, jsonify, current_app
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest, Conflict
from src.services.auth_service import (
    AuthService,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    AuthError,
    InvalidTokenError,
)
from src.schemas.auth import LoginRequest, RegisterRequest
from src.infrastructure.rate_limiter import RateLimiter, rate_limit, get_client_ip
from src.infrastructure.database import MongoDBConnection


auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user with Pydantic validation.
    
    Request body (JSON):
    {
        "email": "user@example.com",
        "password": "SecurePass123!",
        "full_name": "John Doe"
    }
    
    Response (201):
    {
        "id": "user_id_string",
        "email": "user@example.com",
        "full_name": "John Doe",
        "role": "operator",
        "is_active": true,
        "created_at": "2024-01-01T12:00:00"
    }
    
    Errors:
    - 400: Validation error (weak password, invalid email, etc.)
    - 409: Email already registered
    - 422: Invalid request data
    - 500: Server error
    """
    try:
        # Parse JSON request
        data = request.get_json() or {}
        
        # Validate using Pydantic schema
        # This will raise ValidationError if invalid
        validated_data = RegisterRequest(**data)
        
        # Get auth service from app context
        connection = current_app.mongo_connection
        auth_service = AuthService(connection)
        
        # Attempt registration
        user = auth_service.register(
            email=validated_data.email,
            password=validated_data.password,
            full_name=validated_data.full_name,
            role='operator'  # Always operator for registration
        )
        
        return jsonify(user), 201
        
    except ValidationError as e:
        # Pydantic validation error - return 422
        # Convert Pydantic errors to JSON-serializable format
        error_details = []
        for error in e.errors():
            error_details.append({
                "loc": list(error.get("loc", [])),
                "msg": error.get("msg", "Validation error"),
                "type": error.get("type", "value_error")
            })
        return jsonify({
            "error": "validation_error",
            "details": error_details
        }), 422
    
    except UserAlreadyExistsError as e:
        return jsonify({"error": "Email already registered"}), 409
    
    except AuthError as e:
        return jsonify({"error": str(e)}), 400
    
    except Exception as e:
        current_app.logger.error(f"Registration error: {str(e)}")
        return jsonify({"error": "Registration failed"}), 500


@auth_bp.route('/login', methods=['POST'])
@rate_limit(limit=5, window=900)  # 5 attempts per 15 minutes
def login():
    """
    Authenticate user and return JWT token with Pydantic validation.
    
    Rate limited to 5 attempts per IP per 15 minutes.
    
    Request body (JSON):
    {
        "email": "user@example.com",
        "password": "SecurePass123!"
    }
    
    Response (200):
    {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "refresh_token": "opaque_token_string",
        "token_type": "Bearer",
        "expires_in": 900,
        "user": {
            "id": "user_id",
            "email": "user@example.com",
            "full_name": "John Doe",
            "role": "operator"
        }
    }
    
    Errors:
    - 401: Invalid email or password
    - 422: Invalid request data
    - 429: Rate limit exceeded (too many failed attempts)
    - 500: Server error
    """
    try:
        # Parse JSON request
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Validate using Pydantic schema
        # Email is normalized to lowercase automatically
        validated_data = LoginRequest(**data)
        
        # Get auth service from app context
        connection = current_app.mongo_connection
        auth_service = AuthService(connection)
        
        # Get client IP and user agent for audit logging (with X-Forwarded-For support)
        client_ip = get_client_ip(request)
        user_agent = request.headers.get('User-Agent', '')
        
        # Attempt authentication with refresh token
        result = auth_service.login_with_refresh(
            email=validated_data.email,
            password=validated_data.password,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        return jsonify(result), 200
        
    except ValidationError as e:
        # Pydantic validation error - return 422
        # Convert Pydantic errors to JSON-serializable format
        error_details = []
        for error in e.errors():
            error_details.append({
                "loc": list(error.get("loc", [])),
                "msg": error.get("msg", "Validation error"),
                "type": error.get("type", "value_error")
            })
        return jsonify({
            "error": "validation_error",
            "details": error_details
        }), 422
    
    except InvalidCredentialsError as e:
        return jsonify({"error": "Invalid email or password"}), 401
    
    except AuthError as e:
        return jsonify({"error": str(e)}), 400
    
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({"error": "Login failed"}), 500


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """
    Generate a new access token using a valid refresh token.
    
    Request body (JSON):
    {
        "refresh_token": "opaque_token_string"
    }
    
    Response (200):
    {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "token_type": "Bearer",
        "expires_in": 900
    }
    
    Errors:
    - 400: Refresh token is missing or invalid
    - 401: Refresh token expired or invalid
    - 422: Invalid request data
    - 500: Server error
    """
    try:
        # Parse JSON request
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        refresh_token = data.get('refresh_token', '').strip()
        if not refresh_token:
            return jsonify({"error": "refresh_token is required"}), 400
        
        # Get auth service from app context
        connection = current_app.mongo_connection
        auth_service = AuthService(connection)
        
        # Attempt token refresh
        result = auth_service.refresh_access_token(refresh_token)
        
        return jsonify(result), 200
        
    except InvalidTokenError as e:
        return jsonify({"error": str(e)}), 401
    
    except AuthError as e:
        return jsonify({"error": str(e)}), 400
    
    except Exception as e:
        current_app.logger.error(f"Token refresh error: {str(e)}")
        return jsonify({"error": "Token refresh failed"}), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Invalidate user tokens (access and optionally refresh).
    
    Request body (JSON):
    {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "refresh_token": "opaque_token_string"  (optional)
    }
    
    Response (200):
    {
        "success": true,
        "message": "Logged out successfully"
    }
    
    Errors:
    - 400: Access token is missing
    - 401: Invalid or expired access token
    - 422: Invalid request data
    - 500: Server error
    """
    try:
        # Parse JSON request
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        access_token = data.get('access_token', '').strip()
        refresh_token = data.get('refresh_token', '').strip() or None
        
        if not access_token:
            return jsonify({"error": "access_token is required"}), 400
        
        # Get auth service from app context
        connection = current_app.mongo_connection
        auth_service = AuthService(connection)
        
        # Attempt logout
        auth_service.logout(access_token, refresh_token)
        
        return jsonify({
            "success": True,
            "message": "Logged out successfully"
        }), 200
        
    except InvalidTokenError as e:
        return jsonify({"error": str(e)}), 401
    
    except AuthError as e:
        return jsonify({"error": str(e)}), 400
    
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        return jsonify({"error": "Logout failed"}), 500
