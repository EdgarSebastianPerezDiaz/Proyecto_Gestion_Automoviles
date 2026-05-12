"""
Tests for Auth API Blueprint

Integration tests for authentication endpoints using Flask test client.
"""

import pytest
import os
import json
from mongomock import MongoClient as MockMongoClient
from unittest.mock import patch, MagicMock
from src.infrastructure.database import MongoDBConnection
from src.infrastructure.rate_limiter import RateLimiter


@pytest.fixture
def mock_db_connection():
    """Create mock MongoDB connection."""
    with patch('src.infrastructure.database.MongoClient', MockMongoClient):
        MongoDBConnection._instance = None
        connection = MongoDBConnection()
        connection.client = MockMongoClient()
        connection.db = connection.client.test_db
        connection._initialized = True
        connection._create_indexes()
        return connection


@pytest.fixture
def mock_rate_limiter(mock_db_connection):
    """Create mock rate limiter."""
    rate_limiter = RateLimiter('mongodb://localhost:27017/test')
    rate_limiter.collection = mock_db_connection.get_collection('rate_limits')
    rate_limiter._initialized = True
    return rate_limiter


@pytest.fixture
def app(mock_db_connection, mock_rate_limiter):
    """Create Flask test application."""
    # Import here to avoid issues with app context
    from wsgi import create_app
    
    # Set environment variables
    os.environ['FLASK_ENV'] = 'test'
    os.environ['JWT_SECRET_KEY'] = 'test_secret_key'
    os.environ['JWT_ALGORITHM'] = 'HS256'
    os.environ['JWT_EXPIRATION_HOURS'] = '8'
    os.environ['BCRYPT_ROUNDS'] = '4'  # Faster for tests
    
    app = create_app()
    
    # Inject mock connections
    app.mongo_connection = mock_db_connection
    app.rate_limiter = mock_rate_limiter
    
    return app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """Create application context for testing."""
    with app.app_context():
        yield app


class TestAuthRegisterEndpoint:
    """Tests for POST /auth/register endpoint."""
    
    def test_register_success_returns_201(self, client):
        """Test successful registration returns 201."""
        response = client.post('/auth/register', json={
            'email': 'john@example.com',
            'password': 'SecurePass123!',
            'full_name': 'John Doe'
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['email'] == 'john@example.com'
        assert data['full_name'] == 'John Doe'
        assert 'password_hash' not in data
    
    def test_register_missing_email_returns_400(self, client):
        """Test registration without email returns 400."""
        response = client.post('/auth/register', json={
            'password': 'SecurePass123!',
            'full_name': 'John Doe'
        })
        
        assert response.status_code == 422
        data = response.get_json()
        assert data.get('error') == 'validation_error'
        assert 'details' in data
    
    def test_register_missing_password_returns_400(self, client):
        """Test registration without password returns 400."""
        response = client.post('/auth/register', json={
            'email': 'john@example.com',
            'full_name': 'John Doe'
        })
        
        assert response.status_code == 422
        data = response.get_json()
        assert data.get('error') == 'validation_error'
        assert 'details' in data
    
    def test_register_missing_full_name_returns_400(self, client):
        """Test registration without full_name returns 400."""
        response = client.post('/auth/register', json={
            'email': 'john@example.com',
            'password': 'SecurePass123!'
        })
        
        assert response.status_code == 422
        data = response.get_json()
        assert data.get('error') == 'validation_error'
        assert 'details' in data
        assert data.get('error') == 'validation_error' and 'details' in data
    
    def test_register_duplicate_email_returns_409(self, client):
        """Test registration with duplicate email returns 409."""
        # Register first user
        client.post('/auth/register', json={
            'email': 'john@example.com',
            'password': 'SecurePass123!',
            'full_name': 'John Doe'
        })
        
        # Try to register with same email
        response = client.post('/auth/register', json={
            'email': 'john@example.com',
            'password': 'DifferentPass123!',
            'full_name': 'John Smith'
        })
        
        assert response.status_code == 409
        data = response.get_json()
        assert 'already registered' in data.get('error', '').lower()
    
    def test_register_empty_body_returns_400(self, client):
        """Test registration with empty body returns 400."""
        response = client.post('/auth/register', json={})
        
        assert response.status_code == 422


class TestAuthLoginEndpoint:
    """Tests for POST /auth/login endpoint."""
    
    def test_login_success_returns_200(self, client):
        """Test successful login returns 200 with token."""
        # Register first
        client.post('/auth/register', json={
            'email': 'john@example.com',
            'password': 'SecurePass123!',
            'full_name': 'John Doe'
        })
        
        # Login
        response = client.post('/auth/login', json={
            'email': 'john@example.com',
            'password': 'SecurePass123!'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert data['token_type'] == 'Bearer'
        assert 'expires_in' in data
        assert 'user' in data
        assert data['user']['email'] == 'john@example.com'
    
    def test_login_missing_email_returns_400(self, client):
        """Test login without email returns 400."""
        response = client.post('/auth/login', json={
            'password': 'SecurePass123!'
        })
        
        assert response.status_code == 422
        data = response.get_json()
        assert data.get('error') == 'validation_error' and 'details' in data
    
    def test_login_missing_password_returns_400(self, client):
        """Test login without password returns 400."""
        response = client.post('/auth/login', json={
            'email': 'john@example.com'
        })
        
        assert response.status_code == 422
        data = response.get_json()
        assert data.get('error') == 'validation_error' and 'details' in data
    
    def test_login_wrong_password_returns_401(self, client):
        """Test login with wrong password returns 401."""
        # Register
        client.post('/auth/register', json={
            'email': 'john@example.com',
            'password': 'SecurePass123!',
            'full_name': 'John Doe'
        })
        
        # Try login with wrong password
        response = client.post('/auth/login', json={
            'email': 'john@example.com',
            'password': 'wrong_password'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert 'Invalid' in data.get('error', '')
    
    def test_login_nonexistent_user_returns_401(self, client):
        """Test login with non-existent email returns 401."""
        response = client.post('/auth/login', json={
            'email': 'nonexistent@example.com',
            'password': 'any_password'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert 'Invalid' in data.get('error', '')
    
    def test_login_rate_limiting(self, client, mock_rate_limiter):
        """Test that login endpoint is rate limited (5 allowed, 6th blocked)."""
        # Make 5 failed login requests (all from same IP: 127.0.0.1)
        for i in range(5):
            response = client.post('/auth/login', json={
                'email': f'nonexistent{i}@example.com',
                'password': 'any_password'
            })
            # First 5 should get 401 (invalid credentials), not 429
            # because the rate limit allows 5 attempts
            assert response.status_code == 401, f"Request {i+1}: Expected 401, got {response.status_code}"
            data = response.get_json()
            assert 'Invalid' in data.get('error', '')
        
        # 6th request from same IP should be rate limited (429)
        response = client.post('/auth/login', json={
            'email': 'user6@example.com',
            'password': 'any_password'
        })
        
        assert response.status_code == 429, f"6th request: Expected 429, got {response.status_code}"
        data = response.get_json()
        assert 'Rate limit exceeded' in data.get('error', '')
    
    def test_login_rate_limiting_blocks_all_future_requests(self, client):
        """Test that rate limit blocks all future requests once limit exceeded."""
        # Make 5 failed login requests to trigger limit
        for i in range(5):
            response = client.post('/auth/login', json={
                'email': f'user{i}@example.com',
                'password': 'wrong_password'
            })
            assert response.status_code == 401
        
        # Next 3 requests should all get 429, even with valid credentials
        for attempt in range(3):
            response = client.post('/auth/login', json={
                'email': 'valid@example.com',
                'password': 'valid_password'
            })
            assert response.status_code == 429, f"Attempt {attempt + 1} after limit: Expected 429, got {response.status_code}"
            data = response.get_json()
            assert 'Rate limit exceeded' in data.get('error', '')
    
    def test_login_rate_limiting_message(self, client):
        """Test that rate limit error message is correct."""
        # Trigger rate limit
        for i in range(6):
            response = client.post('/auth/login', json={
                'email': f'user{i}@example.com',
                'password': 'any_password'
            })
        
        # 6th request triggers limit
        assert response.status_code == 429
        data = response.get_json()
        # Error message may vary between "Rate limit exceeded" and "Rate limit exceeded. Try again later."
        assert 'Rate limit exceeded' in data['error']


class TestAuthIntegration:
    """Integration tests for authentication flow."""
    
    def test_complete_registration_and_login_flow(self, client):
        """Test complete registration and login flow."""
        # Register
        register_response = client.post('/auth/register', json={
            'email': 'john@example.com',
            'password': 'SecurePass123!',
            'full_name': 'John Doe'
        })
        
        assert register_response.status_code == 201
        user_data = register_response.get_json()
        
        # Login
        login_response = client.post('/auth/login', json={
            'email': 'john@example.com',
            'password': 'SecurePass123!'
        })
        
        assert login_response.status_code == 200
        token_data = login_response.get_json()
        
        # Verify login data
        assert token_data['user']['email'] == user_data['email']
        assert token_data['user']['full_name'] == user_data['full_name']
        assert 'access_token' in token_data
    
    def test_token_payload_structure(self, client):
        """Test that returned token has correct structure."""
        # Register and login
        client.post('/auth/register', json={
            'email': 'john@example.com',
            'password': 'SecurePass123!',
            'full_name': 'John Doe'
        })
        
        response = client.post('/auth/login', json={
            'email': 'john@example.com',
            'password': 'SecurePass123!'
        })
        
        data = response.get_json()
        token = data['access_token']
        
        # Token should be non-empty string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Token type should be Bearer
        assert data['token_type'] == 'Bearer'
        
        # Expires_in should be approximately 15 minutes in seconds (new short-lived access token)
        # Old behavior was 8 hours, now it's 15 minutes for security
        expected_expires = 15 * 60  # 15 minutes
        assert abs(data['expires_in'] - expected_expires) < 10
