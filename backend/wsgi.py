"""
WSGI Application Entry Point
Serverless Flask Application for Freight Transport Platform

This module initializes the Flask application and wraps it with serverless-wsgi
for AWS Lambda deployment. The handler is defined for use in serverless.yml.

Environment Variables:
    FLASK_ENV: Flask environment (development/staging/production)
    JWT_SECRET_KEY: Secret key for JWT token generation
    MONGO_URI: MongoDB connection string
    CORS_ORIGIN: Allowed CORS origin
    LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
"""

import os
import sys
import json
import logging
from flask import Flask, jsonify
from dotenv import load_dotenv
from serverless_wsgi import handle_request
from typing import Optional

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

# Import security infrastructure modules
from src.infrastructure.security_headers import init_security_headers
from src.infrastructure.cors import init_cors
from src.infrastructure.error_handler import init_error_handler
from src.infrastructure.database import MongoDBConnection
from src.infrastructure.rate_limiter import RateLimiter
from src.infrastructure.request_tracing import init_request_tracing

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
        
    Examples:
        >>> jwt_key = _get_secret('JWT_SECRET_KEY')  # From AWS Secrets Manager
        >>> jwt_key = _get_secret('JWT_SECRET_KEY', 'local-dev-key')  # With fallback
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
                # If it's JSON, parse it
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
            elif error_code == 'InvalidRequestException':
                logger.warning(f"Invalid request for secret '{secret_name}' in AWS Secrets Manager")
            elif error_code == 'InvalidParameterException':
                logger.warning(f"Invalid parameter for secret '{secret_name}' in AWS Secrets Manager")
            elif error_code == 'DecryptionFailure':
                logger.error(f"Decryption failed for secret '{secret_name}' - check KMS permissions")
            elif error_code == 'InternalServiceError':
                logger.error(f"AWS Secrets Manager internal error for '{secret_name}'")
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
        if not is_test_env and not is_lambda:
            logger.warning(
                f"Secret '{secret_name}' not found - using default value. "
                f"This should NOT happen in production!"
            )
        return default
    
    # ===== TIER 5: CRITICAL ERROR - No secret found and no default =====
    error_msg = (
        f"CRITICAL: Secret '{secret_name}' not found in AWS Secrets Manager, "
        f"environment variables, or defaults. Application cannot start."
    )
    logger.critical(error_msg)
    raise ValueError(error_msg)


# Import security infrastructure modules
from src.infrastructure.security_headers import init_security_headers
from src.infrastructure.cors import init_cors
from src.infrastructure.error_handler import init_error_handler
from src.infrastructure.database import MongoDBConnection
from src.infrastructure.rate_limiter import RateLimiter
from src.infrastructure.request_tracing import init_request_tracing

# Import API blueprints
from src.api.auth import auth_bp
from src.api.companies import create_companies_blueprint
from src.api.final_recipients import final_recipients_bp, set_service as set_final_recipients_service
from src.api.cargo_types import cargo_types_bp, set_service as set_cargo_types_service
from src.api.trip_statuses import trip_statuses_bp, set_service as set_trip_statuses_service
from src.api.health import health_bp

# Import Services
from src.services.auth_service import AuthService
from src.services.company_service import CompanyService
from src.services.driver_service import DriverService
from src.services.vehicle_service import VehicleService
from src.services.client_service import ClientService
from src.services.final_recipient_service import FinalRecipientService
from src.services.cargo_type_service import CargoTypeService
from src.services.trip_status_service import TripStatusService

# Import Repositories
from src.repositories.user_repository import UserRepository
from src.repositories.company_repository import CompanyRepository
from src.repositories.driver_repository import DriverRepository
from src.repositories.vehicle_repository import VehicleRepository
from src.repositories.client_repository import ClientRepository
from src.repositories.final_recipient_repository import FinalRecipientRepository
from src.repositories.cargo_type_repository import CargoTypeRepository
from src.repositories.trip_status_repository import TripStatusRepository

# Import API Blueprints (besides auth_bp which is already imported)
from src.api.drivers import create_drivers_blueprint
from src.api.vehicles import create_vehicles_blueprint
from src.api.clients import create_clients_blueprint
from src.api.trips import trips_bp, init_trips_routes
from src.api.invoices import invoices_bp, init_invoices_routes

# Load environment variables from .env file (development only)
# En producción (Lambda), las variables vienen de SSM Parameter Store
if os.getenv('FLASK_ENV', 'development') != 'production':
    load_dotenv()


def is_testing() -> bool:
    """
    Detect if running under pytest or in testing mode.
    
    Returns:
        bool: True if in testing environment
    """
    return 'pytest' in sys.modules or os.getenv('FLASK_ENV') == 'testing'


def validate_env_vars() -> None:
    """
    Validate critical environment variables are present and valid.
    Called at module startup BEFORE creating the Flask app.
    
    This is a strict validation function that:
    - Allows dummy values in testing/development
    - Requires all critical variables in production
    - Raises ValueError immediately if validation fails
    
    Raises:
        ValueError: If critical environment variables are missing in production
    """
    flask_env = os.getenv('FLASK_ENV', 'development')
    is_test_env = is_testing()
    
    logger.info(f"Validating environment for: {flask_env}" + (" (testing)" if is_test_env else ""))
    
    # Critical variables - REQUIRED
    critical_vars = ['MONGO_URI', 'JWT_SECRET_KEY']
    
    if is_test_env:
        logger.debug("Running in testing mode - dummy values will be allowed")
        # In testing mode, we don't need to validate as conftest.py sets them
        return
    
    if flask_env == 'development':
        logger.debug("Running in development mode - will set defaults if missing")
        # Development mode is also flexible
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
                f"{', '.join(missing_vars)}. Application will not start. "
                f"Please set these variables via SSM Parameter Store, environment, or secrets manager."
            )
            logger.critical(error_msg)
            raise ValueError(error_msg)
        
        logger.info("✓ All critical environment variables validated for production")


def _validate_environment_variables() -> None:
    """
    Validate critical environment variables are configured.
    Uses _get_secret() to securely retrieve secrets from AWS or environment.
    
    Behavior by environment:
    - Testing: Use dummy values (conftest.py sets them)
    - Development: Use .env values or defaults
    - Production (Lambda): Require secrets from AWS Secrets Manager
    - Production (other): Require secrets from environment
    
    Raises:
        ValueError: In production if critical environment variables are missing
    """
    flask_env = os.getenv('FLASK_ENV', 'development')
    is_test_env = is_testing()
    is_lambda = 'AWS_LAMBDA_FUNCTION_NAME' in os.environ
    
    logger.info(f"Starting application in {flask_env} environment" + 
                (" (Lambda)" if is_lambda else "") +
                (" (testing)" if is_test_env else ""))
    
    critical_secrets = {
        'MONGO_URI': 'mongodb://localhost:27017/test',  # Dummy for testing only
        'JWT_SECRET_KEY': 'test_secret_key_for_testing_only',  # Dummy for testing only
    }
    
    # In testing mode, allow dummy values
    if is_test_env:
        logger.debug("Testing environment detected - allowing dummy values")
        for secret_name, dummy_value in critical_secrets.items():
            os.environ.setdefault(secret_name, dummy_value)
        return
    
    # In development, try .env first, then allow defaults
    if flask_env == 'development':
        logger.debug("Development environment - loading from .env and environment")
        for secret_name in critical_secrets.keys():
            if secret_name not in os.environ:
                logger.warning(f"{secret_name} not set in environment - application may fail")
        return
    
    # PRODUCTION (Lambda or other): Strict validation
    if flask_env == 'production':
        logger.info("Production environment detected - validating critical secrets")
        for secret_name, dummy_value in critical_secrets.items():
            try:
                # Try to get secret - will raise ValueError if not found
                _get_secret(secret_name)
                logger.debug(f"✓ Critical secret '{secret_name}' loaded successfully")
            except ValueError as e:
                logger.critical(f"PRODUCTION STARTUP FAILED: {str(e)}")
                raise
    
    # Optional variables with sensible defaults
    optional_vars = {
        'FLASK_ENV': 'development',
        'CORS_ORIGIN': 'http://localhost:4200',
        'JWT_ALGORITHM': 'HS256',
        'LOG_LEVEL': 'INFO' if not is_test_env else 'WARNING',
        'JWT_EXPIRATION_HOURS': '8',
        'BCRYPT_ROUNDS': '12',
        'S3_BUCKET_NAME': '',
    }
    
    for var_name, default_value in optional_vars.items():
        if var_name not in os.environ:
            os.environ[var_name] = default_value
        if not is_test_env:
            logger.debug(f"{var_name} = {os.environ.get(var_name, default_value)}")
    
    logger.info("✓ Environment variables validation passed")


def create_app(testing: bool = False):
    """
    Application Factory Pattern
    Creates and configures the Flask application instance.
    
    Args:
        testing (bool): If True, configure app for testing environment
        
    Returns:
        Flask: Configured Flask application instance
    """
    # Set testing environment if requested
    if testing:
        os.environ['FLASK_ENV'] = 'testing'
        # Ensure dummy values are set
        os.environ.setdefault('MONGO_URI', 'mongodb://localhost:27017/heavy_freight_test')
        os.environ.setdefault('JWT_SECRET_KEY', 'test_secret_key_for_testing_only')
    
    # Validate environment variables at startup
    _validate_environment_variables()
    
    app = Flask(__name__)
    app.logger = get_logger(f"{app.name}")
    
    logger.info("Creating Flask application instance")
    
    # =========================
    # Configuration Management
    # =========================
    # Security: Load sensitive configuration from AWS Secrets Manager or environment
    # Never hardcode secrets in the application
    app.config['ENV'] = os.getenv('FLASK_ENV', 'development')
    app.config['DEBUG'] = app.config['ENV'] == 'development'
    
    # Load critical secrets using _get_secret()
    try:
        app.config['JWT_SECRET_KEY'] = _get_secret('JWT_SECRET_KEY')
        app.config['MONGO_URI'] = _get_secret('MONGO_URI')
    except ValueError as e:
        logger.critical(f"Cannot start application: {str(e)}")
        raise
    
    # Load optional secrets with fallback defaults
    app.config['JWT_ALGORITHM'] = _get_secret('JWT_ALGORITHM', 'HS256')
    app.config['JWT_EXPIRATION_HOURS'] = int(_get_secret('JWT_EXPIRATION_HOURS', '8'))
    app.config['BCRYPT_ROUNDS'] = int(_get_secret('BCRYPT_ROUNDS', '12'))
    app.config['CORS_ORIGIN'] = _get_secret('CORS_ORIGIN', 'http://localhost:4200')
    app.config['S3_BUCKET_NAME'] = _get_secret('S3_BUCKET_NAME', '')
    
    # =========================
    # Request Size Limits
    # =========================
    # Prevent DoS attacks by limiting request size to 10MB
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB
    logger.debug("Request size limit set to 10 MB")
    
    # =========================
    # Security: Production Checks
    # =========================
    if app.config['ENV'] == 'production':
        # Enforce HTTPS
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        
        # Validate critical secrets are configured
        if not app.config['JWT_SECRET_KEY']:
            raise ValueError(
                "CRITICAL: JWT_SECRET_KEY must be set in production environment"
            )
        if not app.config['MONGO_URI']:
            raise ValueError(
                "CRITICAL: MONGO_URI must be set in production environment"
            )
    
    # =========================
    # Health Check Endpoint
    # =========================
    @app.route('/health', methods=['GET'])
    def health_check():
        """
        Health check endpoint for Lambda/container orchestration.
        Used by load balancers and orchestration platforms to verify service is alive.
        
        Returns:
            Response: JSON with status and message
        """
        return jsonify({"message": "ok"}), 200
    
    # =========================
    # Placeholder Routes (to be implemented)
    # =========================
    # API routes will be registered here as modules are developed:
    # - Authentication (login, register, token refresh)
    # - Shipments (CRUD operations)
    # - Drivers (management, tracking)
    # - Routes (planning, optimization)
    # - Reporting (PDF generation with ReportLab)
    
    
    # =========================
    # Initialize Database Connection
    # =========================
    try:
        logger.info("Initializing MongoDB connection")
        mongo_connection = MongoDBConnection.get_instance()
        mongo_connection.connect()
        app.mongo_connection = mongo_connection
        logger.info("MongoDB connection established successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
        if app.config['ENV'] == 'production':
            raise
    
    # =========================
    # Initialize Rate Limiter
    # =========================
    try:
        logger.info("Initializing rate limiter")
        mongo_uri = os.getenv('MONGO_URI')
        if mongo_uri and hasattr(app, 'mongo_connection'):
            rate_limiter = RateLimiter(mongo_uri)
            rate_limiter.connection = app.mongo_connection
            rate_limiter.collection = app.mongo_connection.get_collection('rate_limits')
            rate_limiter._initialized = True
            app.rate_limiter = rate_limiter
            logger.info("Rate limiter initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize rate limiter: {str(e)}", exc_info=True)
        if app.config['ENV'] == 'production':
            raise
    
    # =========================
    # Register API Blueprints
    # =========================
    logger.info("Registering API blueprints and initializing services")
    app.register_blueprint(auth_bp)
    
    # Initialize services for dependency injection
    try:
        # Initialize auth service
        auth_service = AuthService(app.mongo_connection)
        app.auth_service = auth_service
        logger.debug("Auth service initialized")
        
        # Initialize company service
        company_repository = CompanyRepository(app.mongo_connection)
        company_service = CompanyService(company_repository)
        
        # Register companies blueprint
        companies_bp = create_companies_blueprint(company_service)
        app.register_blueprint(companies_bp)
        logger.debug("Companies service initialized")
        
        # Initialize client service
        client_repository = ClientRepository(app.mongo_connection)
        client_service = ClientService(client_repository)
        
        # Register clients blueprint
        clients_bp = create_clients_blueprint(client_service)
        app.register_blueprint(clients_bp)
        logger.debug("Client service initialized")
        
        # Initialize driver service
        driver_repository = DriverRepository(app.mongo_connection)
        driver_service = DriverService(driver_repository)
        
        # Register drivers blueprint
        drivers_bp = create_drivers_blueprint(driver_service)
        app.register_blueprint(drivers_bp)
        logger.debug("Driver service initialized")
        
        # Initialize vehicle service
        vehicle_repository = VehicleRepository(app.mongo_connection)
        vehicle_service = VehicleService(vehicle_repository)
        
        # Register vehicles blueprint
        vehicles_bp = create_vehicles_blueprint(vehicle_service)
        app.register_blueprint(vehicles_bp)
        logger.debug("Vehicle service initialized")
        
        # Initialize final recipient service
        final_recipient_repository = FinalRecipientRepository(app.mongo_connection)
        final_recipient_service = FinalRecipientService(final_recipient_repository)
        set_final_recipients_service(final_recipient_service)
        
        # Register final recipients blueprint
        app.register_blueprint(final_recipients_bp)
        logger.debug("Final recipient service initialized")
        
        # Initialize cargo type service
        cargo_type_repository = CargoTypeRepository(app.mongo_connection)
        cargo_type_service = CargoTypeService(cargo_type_repository)
        set_cargo_types_service(cargo_type_service)
        
        # Register cargo types blueprint
        app.register_blueprint(cargo_types_bp)
        logger.debug("Cargo type service initialized")
        
        # Initialize trip status service with trips collection for deletion checks
        trip_status_repository = TripStatusRepository(app.mongo_connection)
        trips_collection = app.mongo_connection.get_collection('trips')
        trip_status_service = TripStatusService(trip_status_repository, trips_collection)
        set_trip_statuses_service(trip_status_service)
        
        # Register trip statuses blueprint
        app.register_blueprint(trip_statuses_bp)
        logger.debug("Trip status service initialized")
        
        # Initialize and register trips blueprint
        init_trips_routes(app.mongo_connection)
        app.register_blueprint(trips_bp)
        logger.debug("Trips service initialized")
        
        # Initialize and register invoices blueprint
        init_invoices_routes(app.mongo_connection)
        app.register_blueprint(invoices_bp)
        logger.debug("Invoices service initialized")
        
        # Register health check blueprint (no service needed, always available)
        app.register_blueprint(health_bp)
        logger.debug("Health check endpoints registered")
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}", exc_info=True)
        if app.config['ENV'] == 'production':
            raise
    
    
    # =========================
    # Initialize Security Infrastructure
    # =========================
    logger.info("Initializing security infrastructure")
    
    # Register security headers (CSP, HSTS, X-Frame-Options, etc.)
    init_security_headers(app)
    logger.debug("Security headers configured")
    
    # Configure CORS with allowed origins
    init_cors(app)
    logger.debug("CORS configured")
    
    # Initialize request tracing for end-to-end debugging
    init_request_tracing(app)
    logger.debug("Request tracing initialized")
    
    # Register global error handler with structured logging
    init_error_handler(app)
    logger.debug("Error handlers registered")
    
    logger.info("Flask application created successfully")
    
    return app


# =========================
# Application Startup
# =========================
logger.info("=" * 80)
logger.info("HEAVY FREIGHT PLATFORM - APPLICATION STARTUP")
logger.info("=" * 80)

# Validate critical environment variables BEFORE creating app
try:
    validate_env_vars()
except ValueError as e:
    logger.critical(f"Application startup aborted: {str(e)}")
    raise

# Create the Flask application instance (only at module level for non-testing environments)
# In testing, fixtures will create separate app instances via create_app()
if not ('pytest' in sys.modules or os.getenv('FLASK_ENV') == 'testing'):
    app = create_app()
    logger.info("Application ready to serve requests")
else:
    # For testing: don't create app here, let fixtures handle it
    # Create a placeholder that will be overridden by test fixtures
    app = None

# =========================
# AWS Lambda Handler
# =========================
# serverless-wsgi 3.1.0 handler for AWS Lambda integration.
# NOTE: handler is assigned the function itself, NOT called with app as an argument.
# serverless-wsgi automatically discovers the global 'app' variable at runtime.
handler = handle_request


# For local development with Flask CLI
if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_ENV') == 'development', host='0.0.0.0', port=5000) 
