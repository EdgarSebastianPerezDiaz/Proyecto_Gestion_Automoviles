"""
Pytest Configuration and Fixtures

This module configures the testing environment and provides fixtures for tests.
It runs before any tests and sets up mock environments.
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch


# ═══════════════════════════════════════════════════════════════════════════
# Global Test Configuration
# ═══════════════════════════════════════════════════════════════════════════

def pytest_configure(config):
    """Pytest hook: sets up testing environment and registers custom markers."""
    # Testing environment
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['LOG_LEVEL'] = 'WARNING'
    os.environ['TESTING'] = 'true'

    # Dummy credentials — never real values
    os.environ.setdefault('MONGO_URI', 'mongodb://localhost:27017/heavy_freight_test')
    os.environ.setdefault('JWT_SECRET_KEY', 'test_secret_key_for_testing_only')
    os.environ.setdefault('JWT_ALGORITHM', 'HS256')
    os.environ.setdefault('JWT_EXPIRATION_HOURS', '8')
    os.environ.setdefault('BCRYPT_ROUNDS', '4')
    os.environ.setdefault('CORS_ORIGIN', 'http://localhost:4200')

    # Custom markers
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow")
    config.addinivalue_line("markers", "api: mark test as API endpoint test")


# ═══════════════════════════════════════════════════════════════════════════
# Flask App Fixture
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def app():
    """
    Create and configure a Flask application instance for testing.
    
    Yields:
        Flask: Configured Flask app instance ready for testing
    """
    from wsgi import create_app
    
    # Create app with testing=True to ensure FLASK_ENV='testing' is set
    app = create_app(testing=True)
    app.config['TESTING'] = True
    
    yield app


@pytest.fixture
def client(app):
    """
    Create a test client for making requests to the app.
    
    Args:
        app: Flask app fixture
        
    Yields:
        FlaskClient: Test client
    """
    yield app.test_client()


@pytest.fixture(autouse=True)
def cleanup_collections(app):
    """
    Cleanup test data before each test to prevent duplicate key errors.
    
    Clears collections that may have unique indexes to prevent collision
    across tests that generate similar test data.
    """
    yield  # Run test first
    
    # After test, clean up collections with unique indexes
    try:
        db = app.mongo_connection.db
        collections_to_clear = ['drivers', 'vehicles', 'clients', 'trips', 'rate_limits', 'users', 'token_blacklist']
        for collection_name in collections_to_clear:
            if collection_name in ['rate_limits', 'token_blacklist']:
                # Clear all entries to prevent rate limiting and blacklist carry-over between tests
                db[collection_name].delete_many({})
            elif collection_name == 'users':
                # Clear test users created during testing
                db[collection_name].delete_many({'email': {'$regex': '^(refresh_test|timing_test|test_|john@)'}})
            else:
                # Clear test data created by operators and admins
                db[collection_name].delete_many({'created_by': {'$in': ['operator@example.com', 'operator2@example.com', 'admin@example.com']}})
    except Exception:
        pass  # Cleanup is best-effort, don't fail the test if cleanup fails


@pytest.fixture(autouse=True)
def cleanup_environment_variables():
    """
    Cleanup environment variables after each test to prevent test pollution.
    
    Preserves critical testing environment variables while cleaning up
    any temporary variables created during test execution.
    
    This prevents one test's environment modifications from affecting
    subsequent tests, especially important for secrets manager tests
    that mock environment variables.
    """
    # Store the baseline testing environment
    baseline_env = {
        'FLASK_ENV': os.environ.get('FLASK_ENV', 'testing'),
        'LOG_LEVEL': os.environ.get('LOG_LEVEL', 'WARNING'),
        'TESTING': os.environ.get('TESTING', 'true'),
        'MONGO_URI': os.environ.get('MONGO_URI'),
        'JWT_SECRET_KEY': os.environ.get('JWT_SECRET_KEY'),
        'JWT_ALGORITHM': os.environ.get('JWT_ALGORITHM'),
        'JWT_EXPIRATION_HOURS': os.environ.get('JWT_EXPIRATION_HOURS'),
        'BCRYPT_ROUNDS': os.environ.get('BCRYPT_ROUNDS'),
        'CORS_ORIGIN': os.environ.get('CORS_ORIGIN'),
    }
    
    # Store any keys that were in os.environ before test
    env_before_test = set(os.environ.keys())
    
    yield  # Run test
    
    # After test, restore baseline environment
    # First, remove any new environment variables added during the test
    env_after_test = set(os.environ.keys())
    new_vars_added = env_after_test - env_before_test
    for var in new_vars_added:
        if var not in baseline_env:
            os.environ.pop(var, None)
    
    # Then, restore all baseline variables to their original values
    for key, value in baseline_env.items():
        if value is not None:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)


@pytest.fixture
def runner(app):
    """
    Create a CLI runner for testing CLI commands.
    
    Args:
        app: Flask app fixture
        
    Yields:
        CliRunner: CLI runner
    """
    yield app.test_cli_runner()


# ═══════════════════════════════════════════════════════════════════════════
# Database Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_mongo_connection():
    """
    Create a mock MongoDB connection for testing.
    
    Yields:
        Mock: Mocked MongoDBConnection
    """
    with patch('src.infrastructure.database.MongoDBConnection') as mock:
        instance = Mock()
        instance.get_collection = Mock(return_value=Mock())
        instance.connect = Mock()
        mock.get_instance.return_value = instance
        yield instance


@pytest.fixture
def mock_repository():
    """
    Create a mock repository for testing services.
    
    Yields:
        Mock: Mocked repository
    """
    mock = Mock()
    mock.create = Mock(return_value={'_id': 'test_id', 'name': 'Test'})
    mock.find_by_id = Mock(return_value={'_id': 'test_id', 'name': 'Test'})
    mock.update = Mock(return_value={'_id': 'test_id', 'name': 'Test Updated'})
    mock.delete = Mock(return_value=True)
    mock.find_all = Mock(return_value=[])
    yield mock


# ═══════════════════════════════════════════════════════════════════════════
# Authentication Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def auth_headers():
    """
    Create authorization headers with a test JWT token.
    
    Yields:
        dict: Headers dict with Authorization
    """
    # Generate a simple test token
    test_token = "Bearer test_jwt_token_for_testing"
    yield {"Authorization": test_token}


@pytest.fixture
def valid_user_data():
    """
    Provide valid user data for testing.
    
    Yields:
        dict: User data
    """
    yield {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User",
        "role": "driver"
    }


@pytest.fixture
def valid_company_data():
    """
    Provide valid company data for testing.
    
    Yields:
        dict: Company data
    """
    yield {
        "nit": "123456789-1",
        "legal_name": "Test Company S.A.S.",
        "address": "Calle 1 # 2-3",
        "city": "Bogotá",
        "phone": "+57 1 1234567",
        "email": "company@example.com",
        "contact_name": "John Doe",
        "is_active": True
    }


@pytest.fixture
def valid_driver_data():
    """
    Provide valid driver data for testing.
    
    Yields:
        dict: Driver data
    """
    yield {
        "first_name": "Juan",
        "last_name": "Pérez",
        "id_number": "1234567890",
        "license_number": "DL123456789",
        "license_expiry": "2027-12-31",
        "license_category": "C",
        "phone": "+57 3001234567",
        "email": "driver@example.com",
        "is_active": True
    }


# ═══════════════════════════════════════════════════════════════════════════
# Request/Response Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def json_headers():
    """
    Provide standard JSON content-type headers.
    
    Yields:
        dict: Headers dict
    """
    yield {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


@pytest.fixture
def error_response():
    """
    Provide a standard error response format.
    
    Yields:
        dict: Error response
    """
    yield {
        "error": "Test error message",
        "error_code": "TEST_ERROR"
    }


# ═══════════════════════════════════════════════════════════════════════════
# Utility Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def freeze_time():
    """
    Freeze time for consistent timestamps in tests.
    
    Yields:
        function: freeze time context manager
    """
    from freezegun import freeze_time as _freeze_time
    yield _freeze_time


# ═══════════════════════════════════════════════════════════════════════════
# Assertion Helpers
# ═══════════════════════════════════════════════════════════════════════════

def assert_response_error(response, expected_status, expected_error_msg=None):
    """
    Assert that response is an error with expected status and message.
    
    Args:
        response: Flask test client response
        expected_status: Expected HTTP status code
        expected_error_msg: Optional expected error message
    """
    assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
    data = response.get_json()
    assert "error" in data, f"Response missing 'error' field: {data}"
    if expected_error_msg:
        assert expected_error_msg.lower() in data.get("error", "").lower(), \
            f"Expected error containing '{expected_error_msg}', got: {data['error']}"


def assert_response_success(response, expected_status=200):
    """
    Assert that response is successful with expected status.
    
    Args:
        response: Flask test client response
        expected_status: Expected HTTP status code
    """
    assert response.status_code == expected_status, \
        f"Expected {expected_status}, got {response.status_code}\nResponse: {response.get_json()}"
    data = response.get_json()
    assert data is not None, "Response body should not be empty"


# Export assertion helpers for use in tests
pytest.assert_response_error = assert_response_error
pytest.assert_response_success = assert_response_success


# ═══════════════════════════════════════════════════════════════════════════
# Authorization Test Fixtures (for test_authorization.py)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def db_connection(app):
    """Get the database connection from the app."""
    from src.infrastructure.database import MongoDBConnection
    return MongoDBConnection.get_instance()


@pytest.fixture
def auth_headers_operator(app):
    """Create auth headers for an operator user."""
    from jose import jwt
    from datetime import datetime, timedelta, timezone

    secret = os.getenv('JWT_SECRET_KEY', 'test_secret_key_for_testing_only')
    algorithm = os.getenv('JWT_ALGORITHM', 'HS256')

    payload = {
        'user_id': 'operator@example.com',
        'role': 'operator',
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(hours=8)
    }

    token = jwt.encode(payload, secret, algorithm=algorithm)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_operator2(app):
    """Create auth headers for a second operator user."""
    from jose import jwt
    from datetime import datetime, timedelta, timezone

    secret = os.getenv('JWT_SECRET_KEY', 'test_secret_key_for_testing_only')
    algorithm = os.getenv('JWT_ALGORITHM', 'HS256')

    payload = {
        'user_id': 'operator2@example.com',
        'role': 'operator',
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(hours=8)
    }

    token = jwt.encode(payload, secret, algorithm=algorithm)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_admin(app):
    """Create auth headers for an admin user."""
    from jose import jwt
    from datetime import datetime, timedelta, timezone

    secret = os.getenv('JWT_SECRET_KEY', 'test_secret_key_for_testing_only')
    algorithm = os.getenv('JWT_ALGORITHM', 'HS256')
    
    payload = {
        'user_id': 'admin@example.com',
        'role': 'admin',
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(hours=8)
    }
    
    token = jwt.encode(payload, secret, algorithm=algorithm)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def create_trip(db_connection):
    """Factory fixture to create trips for testing."""
    from src.repositories.trip_repository import TripRepository
    from datetime import datetime, timezone
    from bson.objectid import ObjectId
    
    repo = TripRepository(db_connection)
    
    def _create_trip(user_id=None, **kwargs):
        """Create a trip with provided user_id."""
        trip_data = {
            '_id': ObjectId(),
            'origin': kwargs.get('origin', 'Bogotá'),
            'destination': kwargs.get('destination', 'Medellín'),
            'departure_date': kwargs.get('departure_date', datetime.now(timezone.utc)),
            'weight_tons': kwargs.get('weight_tons', 10.5),
            'vehicle_id': kwargs.get('vehicle_id', 'vehicle_1'),
            'driver_id': kwargs.get('driver_id', 'driver_1'),
            'cargo_id': kwargs.get('cargo_id', 'cargo_1'),
            'client_id': kwargs.get('client_id', 'client_1'),
            'recipient_id': kwargs.get('recipient_id', 'recipient_1'),
            'status_id': kwargs.get('status_id', 'scheduled'),
            'created_by': user_id,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
        }
        
        # Insert and return
        trip_id = repo.insert_one(trip_data)
        trip_data['_id'] = trip_id
        return trip_data
    
    return _create_trip


@pytest.fixture
def create_driver(db_connection):
    """Factory fixture to create drivers for testing."""
    from src.repositories.driver_repository import DriverRepository
    from datetime import datetime, timezone
    from bson.objectid import ObjectId
    
    repo = DriverRepository(db_connection)
    counter = [0]  # Use list to allow modification in nested function
    
    def _create_driver(user_id=None, **kwargs):
        """Create a driver with provided user_id."""
        from time import time
        counter[0] += 1  # Increment counter for each call
        timestamp = int(time() * 1000000) + counter[0]  # Add counter to ensure uniqueness
        
        driver_data = {
            '_id': ObjectId(),
            'id_number': kwargs.get('id_number', f'ID{timestamp:016d}'[-10:]),
            'first_name': kwargs.get('first_name', f'Driver{timestamp}'),
            'last_name': kwargs.get('last_name', 'TestDriver'),
            'license_number': kwargs.get('license_number', f'LIC{timestamp:06d}'[-6:]),
            'license_category': kwargs.get('license_category', 'C'),
            'license_expiry': kwargs.get('license_expiry', '2027-12-31'),
            'phone': kwargs.get('phone', '3101234567'),
            'address': kwargs.get('address', 'Calle 1'),
            'email': kwargs.get('email', f'driver{timestamp}@example.com'),
            'is_active': kwargs.get('is_active', True),
            'created_by': user_id,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
        }
        
        # Insert and return
        driver_id = repo.insert_one(driver_data)
        driver_data['_id'] = driver_id
        return driver_data
    
    return _create_driver


@pytest.fixture
def create_vehicle(db_connection):
    """Factory fixture to create vehicles for testing."""
    from src.repositories.vehicle_repository import VehicleRepository
    from datetime import datetime, timezone
    from bson.objectid import ObjectId
    
    repo = VehicleRepository(db_connection)
    
    def _create_vehicle(user_id=None, **kwargs):
        """Create a vehicle with provided user_id."""
        from time import time
        timestamp = int(time() * 1000000)  # microseconds for uniqueness
        
        vehicle_data = {
            '_id': ObjectId(),
            'plate': kwargs.get('plate', f'PL{timestamp:08d}'[-7:]),
            'vehicle_type': kwargs.get('vehicle_type', 'Truck'),
            'brand': kwargs.get('brand', 'Volvo'),
            'model_year': kwargs.get('model_year', 2020),
            'capacity_tons': kwargs.get('capacity_tons', 25),
            'volume_m3': kwargs.get('volume_m3', 60),
            'status': kwargs.get('status', 'available'),
            'company_id': kwargs.get('company_id', 'company_1'),
            'is_active': kwargs.get('is_active', True),
            'created_by': user_id,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
        }
        
        # Insert and return
        vehicle_id = repo.insert_one(vehicle_data)
        vehicle_data['_id'] = vehicle_id
        return vehicle_data
    
    return _create_vehicle


@pytest.fixture
def create_client(db_connection):
    """Factory fixture to create clients for testing."""
    from src.repositories.client_repository import ClientRepository
    from datetime import datetime, timezone
    from bson.objectid import ObjectId
    
    repo = ClientRepository(db_connection)
    
    def _create_client(user_id=None, **kwargs):
        """Create a client with provided user_id."""
        from time import time
        timestamp = int(time() * 1000000)  # microseconds for uniqueness
        
        client_data = {
            '_id': ObjectId(),
            'nit': kwargs.get('nit', f'{timestamp:09d}'[-9:]),
            'legal_name': kwargs.get('legal_name', f'Client {timestamp}'),
            'trade_name': kwargs.get('trade_name', f'Client Trade {timestamp}'),
            'address': kwargs.get('address', 'Calle 1'),
            'city': kwargs.get('city', 'Bogotá'),
            'phone': kwargs.get('phone', '3101234567'),
            'email': kwargs.get('email', f'client{timestamp}@example.com'),
            'contact_name': kwargs.get('contact_name', 'John Doe'),
            'is_active': kwargs.get('is_active', True),
            'created_by': user_id,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
        }
        
        # Insert and return
        client_id = repo.insert_one(client_data)
        client_data['_id'] = client_id
        return client_data
    
    return _create_client

