"""
Authentication Router - FastAPI
Endpoints for user registration and login with JWT token management.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, status
from pydantic import ValidationError
from datetime import datetime, timezone
import logging

from src.services.auth_service import (
    AuthService,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    AuthError,
)
from src.schemas.auth import LoginRequest, RegisterRequest
from src.infrastructure.database import MongoDBConnection
from src.infrastructure.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)
router = APIRouter()

# Global instances - will be initialized in main.py
_db_connection: MongoDBConnection = None
_rate_limiter: RateLimiter = None


def set_dependencies(db_connection: MongoDBConnection, rate_limiter: RateLimiter):
    """Set global dependencies for this router."""
    global _db_connection, _rate_limiter
    _db_connection = db_connection
    _rate_limiter = rate_limiter


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    if 'x-forwarded-for' in request.headers:
        return request.headers['x-forwarded-for'].split(',')[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, request: Request):
    """
    Register a new user.
    
    - **email**: User email (must be unique)
    - **password**: Password (min 8 chars, must contain uppercase, lowercase, digit)
    - **full_name**: User full name
    
    Returns user object with JWT tokens
    """
    try:
        auth_service = AuthService(_db_connection)
        user = auth_service.register(
            email=data.email,
            password=data.password,
            full_name=data.full_name,
            role='operator'
        )
        return user
        
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(data: LoginRequest, request: Request):
    """
    Authenticate user and get JWT tokens.
    
    Rate limited to 5 attempts per IP per 15 minutes.
    
    - **email**: User email
    - **password**: User password
    
    Returns access_token, refresh_token, and user info
    """
    client_ip = get_client_ip(request)
    
    # Rate limiting check
    if _rate_limiter and not _rate_limiter.is_allowed(client_ip, "login", max_attempts=5, window_seconds=900):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later."
        )
    
    try:
        auth_service = AuthService(_db_connection)
        result = auth_service.login_with_refresh(
            email=data.email,
            password=data.password
        )
        return result
        
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_token(request: Request):
    """
    Refresh JWT access token using refresh token.
    
    Expects: refresh_token in request body or Authorization header
    Returns: new access_token
    """
    try:
        # Get refresh token from body or header
        refresh_token = None
        
        if request.headers.get("Authorization"):
            auth_header = request.headers.get("Authorization")
            if auth_header.startswith("Bearer "):
                refresh_token = auth_header[7:]
        
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token required"
            )
        
        auth_service = AuthService(_db_connection)
        result = auth_service.refresh_token(refresh_token)
        return result
        
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )
