"""
FastAPI Application Entry Point
Serverless FastAPI Application for Freight Transport Platform

This module initializes the FastAPI application with all routes and middleware.
Mangum adapter wraps it for AWS Lambda HTTP API v2 deployment.

Environment Variables:
    FLASK_ENV: Application environment (development/staging/production)
    JWT_SECRET_KEY: Secret key for JWT token generation
    MONGO_URI: MongoDB connection string
    CORS_ORIGIN: Allowed CORS origin
    LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
"""

import os
import sys
import json
import logging
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# AWS SDK for Secrets Manager
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None
    ClientError = None

# Initialize logging BEFORE all other imports
from src.infrastructure.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

# Import infrastructure modules
from src.infrastructure.database import MongoDBConnection
from src.infrastructure.rate_limiter import RateLimiter

# ================================================================================
# SECRETS MANAGEMENT - AWS Secrets Manager Integration
# ================================================================================

def _get_secret(secret_name: str, default: Optional[str] = None) -> str:
    """
    Retrieve a secret from AWS Secrets Manager or environment variables.
    
    Priority order:
    1. AWS Secrets Manager (production in Lambda)
    2. Environment variable prefixed with HEAVY_FREIGHT_ (for local/testing)
    3. Default value (if provided)
    4. Raise error (if critical and no fallback)
    
    Args:
        secret_name: Name of the secret (e.g., 'JWT_SECRET_KEY', 'MONGO_URI')
        default: Default value if secret not found (optional)
        
    Returns:
        str: The secret value
        
    Raises:
        ValueError: If secret not found and no default provided in production
    """
    flask_env = os.getenv('FLASK_ENV', 'development')
    is_test_env = is_testing()
    is_lambda = 'AWS_LAMBDA_FUNCTION_NAME' in os.environ
    
    # ===== TIER 1: AWS Secrets Manager (Production/Lambda) =====
    if is_lambda and boto3:
        try:
            client = boto3.client('secretsmanager')
            secret_arn = f"heavy-freight/{flask_env}/{secret_name}"
            response = client.get_secret_value(SecretId=secret_arn)
            
            if 'SecretString' in response:
                secret_value = response['SecretString']
                try:
                    parsed = json.loads(secret_value)
                    if isinstance(parsed, dict) and secret_name in parsed:
                        logger.debug(f"Secret '{secret_name}' loaded from AWS Secrets Manager")
                        return parsed[secret_name]
                    else:
                        logger.debug(f"Secret '{secret_name}' loaded from AWS Secrets Manager")
                        return secret_value
                except json.JSONDecodeError:
                    logger.debug(f"Secret '{secret_name}' loaded from AWS Secrets Manager")
                    return secret_value
            else:
                logger.warning(f"Secret '{secret_name}' not found as SecretString in AWS Secrets Manager")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                logger.warning(f"Secret '{secret_name}' not found in AWS Secrets Manager")
            else:
                logger.error(f"AWS Secrets Manager error for '{secret_name}': {error_code}")
        except Exception as e:
            logger.error(f"Error retrieving secret '{secret_name}' from AWS: {str(e)}")
    
    # ===== TIER 2: Environment Variables with HEAVY_FREIGHT_ prefix =====
    env_var_name = f"HEAVY_FREIGHT_{secret_name}"
    if env_var_name in os.environ:
        logger.debug(f"Secret '{secret_name}' loaded from environment variable {env_var_name}")
        return os.getenv(env_var_name)
    
    # ===== TIER 3: Direct environment variable (legacy) =====
    if secret_name in os.environ:
        logger.debug(f"Secret '{secret_name}' loaded from environment variable")
        return os.getenv(secret_name)
    
    # ===== TIER 4: Default fallback =====
    if default is not None:
        if not is_test_env:
            logger.warning(f"Secret '{secret_name}' not found - using default value")
        return default
    
    # ===== TIER 5: CRITICAL ERROR =====
    error_msg = (
        f"CRITICAL: Secret '{secret_name}' not found in AWS Secrets Manager, "
        f"environment variables, or defaults. Application cannot start."
    )
    logger.critical(error_msg)
    raise ValueError(error_msg)


def is_testing() -> bool:
    """Detect if running under pytest or in testing mode."""
    return 'pytest' in sys.modules or os.getenv('FLASK_ENV') == 'testing'


def validate_env_vars() -> None:
    """Validate critical environment variables are present and valid."""
    flask_env = os.getenv('FLASK_ENV', 'development')
    is_test_env = is_testing()
    
    logger.info(f"Validating environment for: {flask_env}" + (" (testing)" if is_test_env else ""))
    
    critical_vars = ['MONGO_URI', 'JWT_SECRET_KEY']
    
    if is_test_env:
        logger.debug("Running in testing mode - dummy values will be allowed")
        return
    
    if flask_env == 'development':
        logger.debug("Running in development mode - will set defaults if missing")
        return
    
    # PRODUCTION: Strict validation
    if flask_env == 'production':
        missing_vars = []
        for var_name in critical_vars:
            value = os.getenv(var_name)
            if not value or value.startswith('test_'):
                missing_vars.append(var_name)
                logger.error(f"Missing or invalid (test) value for PRODUCTION: {var_name}")
        
        if missing_vars:
            error_msg = (
                f"PRODUCTION STARTUP ERROR: Missing critical environment variables: "
                f"{', '.join(missing_vars)}. Application will not start."
            )
            logger.critical(error_msg)
            raise ValueError(error_msg)
        
        logger.info("✓ All critical environment variables validated for production")


# Load environment variables from .env file (development only)
if os.getenv('FLASK_ENV', 'development') != 'production':
    load_dotenv()

validate_env_vars()

# Get configuration
MONGO_URI = _get_secret('MONGO_URI', 'mongodb://localhost:27017/freight')
JWT_SECRET_KEY = _get_secret('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
CORS_ORIGIN = _get_secret('CORS_ORIGIN', '*')

# Initialize database connection
# Note: MongoDBConnection reads MONGO_URI from environment
db_connection = MongoDBConnection()

# Initialize rate limiter with MONGO_URI
rate_limiter = RateLimiter(MONGO_URI)

# ================================================================================
# LIFESPAN EVENTS
# ================================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting FastAPI application...")
    
    # Try to connect to MongoDB, but don't fail in development if unavailable
    flask_env = os.getenv('FLASK_ENV', 'development')
    try:
        db_connection.connect()
        logger.info("[OK] Connected to MongoDB")
    except Exception as e:
        # Always log but never crash at startup — health endpoints must remain up.
        # Auth/resource endpoints will return 500 when DB is unreachable, but the
        # app stays alive so /health/live can signal readiness to load balancers.
        logger.error(f"[WARN] MongoDB connection failed ({flask_env}): {str(e)}")
        logger.error("App starting in degraded mode — auth endpoints may fail")
    
    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI application...")
    try:
        db_connection.disconnect()
        logger.info("[OK] Disconnected from MongoDB")
    except Exception as e:
        logger.warning(f"Error during MongoDB disconnect: {str(e)}")


# ================================================================================
# CREATE FASTAPI APP
# ================================================================================

app = FastAPI(
    title="Heavy Freight Platform API",
    description="Serverless FastAPI for freight transport platform and logistics",
    version="0.2.0",
    lifespan=lifespan
)

# ================================================================================
# MIDDLEWARE
# ================================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGIN.split(",") if CORS_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================================================================
# IMPORT AND REGISTER ROUTERS
# ================================================================================

# Import Services (needed for routers)
from src.services.auth_service import AuthService

# Import FastAPI routers
from src.api.fastapi_routers.health import router as health_router
from src.api.fastapi_routers import auth as auth_module
from src.api.fastapi_routers.companies import router as companies_router
from src.api.fastapi_routers.clients import router as clients_router
from src.api.fastapi_routers.drivers import router as drivers_router
from src.api.fastapi_routers.vehicles import router as vehicles_router
from src.api.fastapi_routers.trips import router as trips_router
from src.api.fastapi_routers.invoices import router as invoices_router
from src.api.fastapi_routers.cargo_types import router as cargo_types_router
from src.api.fastapi_routers.final_recipients import router as final_recipients_router
from src.api.fastapi_routers.trip_statuses import router as trip_statuses_router

# Set dependencies for auth router
auth_module.set_dependencies(db_connection, rate_limiter)

# Register routers
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(auth_module.router, prefix="/auth", tags=["authentication"])
app.include_router(companies_router, prefix="/companies", tags=["companies"])
app.include_router(clients_router, prefix="/clients", tags=["clients"])
app.include_router(drivers_router, prefix="/drivers", tags=["drivers"])
app.include_router(vehicles_router, prefix="/vehicles", tags=["vehicles"])
app.include_router(trips_router, prefix="/trips", tags=["trips"])
app.include_router(invoices_router, prefix="/invoices", tags=["invoices"])
app.include_router(cargo_types_router, prefix="/cargo-types", tags=["cargo-types"])
app.include_router(final_recipients_router, prefix="/final-recipients", tags=["final-recipients"])
app.include_router(trip_statuses_router, prefix="/trip-statuses", tags=["trip-statuses"])

# ================================================================================
# EXCEPTION HANDLERS
# ================================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for all unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


# ================================================================================
# HEALTH CHECK ROOT ENDPOINT
# ================================================================================

@app.get("/")
async def root():
    """Root endpoint - returns API info."""
    return {
        "service": "Heavy Freight Platform API",
        "version": "0.2.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
