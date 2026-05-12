"""
Tests for AuthService

Tests authentication business logic including registration, login, and token management.
"""

import pytest
import os
from datetime import datetime, timedelta
from mongomock import MongoClient as MockMongoClient
from unittest.mock import patch
from src.services.auth_service import (
    AuthService,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    AuthError,
)
from src.infrastructure.database import MongoDBConnection


@pytest.fixture
def mock_connection():
    """Create a mock MongoDB connection using mongomock."""
    with patch('src.infrastructure.database.MongoClient', MockMongoClient):
        MongoDBConnection._instance = None
        connection = MongoDBConnection()
        connection.client = MockMongoClient()
        connection.db = connection.client.test_db
        connection._initialized = True
        connection._create_indexes()
        return connection


@pytest.fixture
def auth_service(mock_connection):
    """Create an AuthService instance with mock connection."""
    # Set environment variables for JWT
    os.environ['JWT_SECRET_KEY'] = 'test_secret_key_for_jwt'
    os.environ['JWT_ALGORITHM'] = 'HS256'
    os.environ['JWT_EXPIRATION_HOURS'] = '8'
    os.environ['BCRYPT_ROUNDS'] = '4'  # Lower rounds for faster testing
    
    return AuthService(mock_connection)


class TestAuthServicePasswordHashing:
    """Tests for password hashing and verification."""
    
    def test_hash_password_creates_hash(self, auth_service):
        """Test that password hashing creates a valid bcrypt hash."""
        password = "secure_password_123"
        hashed = auth_service.hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0
    
    def test_verify_password_correct(self, auth_service):
        """Test password verification with correct password."""
        password = "secure_password_123"
        hashed = auth_service.hash_password(password)
        
        result = auth_service.verify_password(password, hashed)
        assert result is True
    
    def test_verify_password_incorrect(self, auth_service):
        """Test password verification with incorrect password."""
        password = "secure_password_123"
        wrong_password = "wrong_password"
        hashed = auth_service.hash_password(password)
        
        result = auth_service.verify_password(wrong_password, hashed)
        assert result is False
    
    def test_password_hash_different_each_time(self, auth_service):
        """Test that same password produces different hashes (due to salt)."""
        password = "secure_password_123"
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)
        
        assert hash1 != hash2
        # But both should verify with the same password
        assert auth_service.verify_password(password, hash1)
        assert auth_service.verify_password(password, hash2)


class TestAuthServiceRegistration:
    """Tests for user registration."""
    
    def test_register_success(self, auth_service):
        """Test successful user registration."""
        user = auth_service.register(
            email="john@example.com",
            password="secure_password_123",
            full_name="John Doe",
            role="operator"
        )
        
        assert user is not None
        assert user['email'] == 'john@example.com'
        assert user['full_name'] == 'John Doe'
        assert user['role'] == 'operator'
        assert 'password_hash' not in user  # Password should not be returned
        assert 'id' in user
    
    def test_register_duplicate_email(self, auth_service):
        """Test registration fails with duplicate email."""
        # Register first user
        auth_service.register(
            email="john@example.com",
            password="password1",
            full_name="John Doe"
        )
        
        # Try to register with same email
        with pytest.raises(UserAlreadyExistsError):
            auth_service.register(
                email="john@example.com",
                password="password2",
                full_name="John Smith"
            )
    
    def test_register_duplicate_email_case_insensitive(self, auth_service):
        """Test that duplicate check is case-insensitive."""
        # Register with lowercase
        auth_service.register(
            email="john@example.com",
            password="password1",
            full_name="John Doe"
        )
        
        # Try to register with uppercase
        with pytest.raises(UserAlreadyExistsError):
            auth_service.register(
                email="JOHN@EXAMPLE.COM",
                password="password2",
                full_name="John Smith"
            )
    
    def test_register_password_too_short(self, auth_service):
        """Test registration fails with short password."""
        with pytest.raises(AuthError) as exc_info:
            auth_service.register(
                email="john@example.com",
                password="short",
                full_name="John Doe"
            )
        
        assert "8 characters" in str(exc_info.value)
    
    def test_register_email_normalized_to_lowercase(self, auth_service):
        """Test that email is normalized to lowercase."""
        user = auth_service.register(
            email="JOHN@EXAMPLE.COM",
            password="secure_password_123",
            full_name="John Doe"
        )
        
        assert user['email'] == 'john@example.com'


class TestAuthServiceLogin:
    """Tests for user login."""
    
    def test_login_success(self, auth_service):
        """Test successful login returns access token."""
        # Register user
        auth_service.register(
            email="john@example.com",
            password="secure_password_123",
            full_name="John Doe"
        )
        
        # Login
        result = auth_service.login(
            email="john@example.com",
            password="secure_password_123"
        )
        
        assert 'access_token' in result
        assert result['token_type'] == 'Bearer'
        assert 'expires_in' in result
        assert 'user' in result
        assert result['user']['email'] == 'john@example.com'
        assert 'password_hash' not in result['user']
    
    def test_login_wrong_password(self, auth_service):
        """Test login fails with wrong password."""
        # Register user
        auth_service.register(
            email="john@example.com",
            password="secure_password_123",
            full_name="John Doe"
        )
        
        # Try login with wrong password
        with pytest.raises(InvalidCredentialsError):
            auth_service.login(
                email="john@example.com",
                password="wrong_password"
            )
    
    def test_login_nonexistent_email(self, auth_service):
        """Test login fails for non-existent email."""
        with pytest.raises(InvalidCredentialsError):
            auth_service.login(
                email="nonexistent@example.com",
                password="any_password"
            )
    
    def test_login_case_insensitive_email(self, auth_service):
        """Test login works with different email case."""
        # Register
        auth_service.register(
            email="john@example.com",
            password="secure_password_123",
            full_name="John Doe"
        )
        
        # Login with uppercase
        result = auth_service.login(
            email="JOHN@EXAMPLE.COM",
            password="secure_password_123"
        )
        
        assert result['user']['email'] == 'john@example.com'
    
    def test_login_inactive_user(self, auth_service):
        """Test login fails for inactive user."""
        from src.repositories.user_repository import UserRepository
        from bson import ObjectId
        
        # Register user
        auth_service.register(
            email="john@example.com",
            password="secure_password_123",
            full_name="John Doe"
        )
        
        # Deactivate user - use direct collection access to bypass filter sanitization issues
        repo = UserRepository(auth_service.connection)
        user = repo.find_by_email('john@example.com')
        
        # Convert string _id back to ObjectId for update
        user_oid = ObjectId(user['_id'])
        repo.collection.update_one(
            {"_id": user_oid},
            {"$set": {"is_active": False}}
        )
        
        # Try login
        with pytest.raises(InvalidCredentialsError):
            auth_service.login(
                email="john@example.com",
                password="secure_password_123"
            )
    
    def test_login_updates_last_login(self, auth_service):
        """Test that successful login updates last_login timestamp."""
        from src.repositories.user_repository import UserRepository
        
        # Register user
        auth_service.register(
            email="john@example.com",
            password="secure_password_123",
            full_name="John Doe"
        )
        
        # Login
        auth_service.login(
            email="john@example.com",
            password="secure_password_123"
        )
        
        # Check last_login was updated
        repo = UserRepository(auth_service.connection)
        user = repo.find_by_email('john@example.com')
        assert user['last_login'] is not None
        assert isinstance(user['last_login'], datetime)


class TestAuthServiceTokens:
    """Tests for JWT token generation and verification."""
    
    def test_token_contains_required_claims(self, auth_service):
        """Test that generated token contains required claims."""
        # Register and login
        auth_service.register(
            email="john@example.com",
            password="secure_password_123",
            full_name="John Doe"
        )
        result = auth_service.login(
            email="john@example.com",
            password="secure_password_123"
        )
        
        # Get and verify token
        token = result['access_token']
        payload = auth_service.verify_token(token)
        
        assert 'user_id' in payload
        assert payload['email'] == 'john@example.com'
        assert 'role' in payload
        assert 'exp' in payload
        assert 'iat' in payload
    
    def test_verify_valid_token(self, auth_service):
        """Test token verification succeeds for valid token."""
        auth_service.register(
            email="john@example.com",
            password="secure_password_123",
            full_name="John Doe"
        )
        result = auth_service.login(
            email="john@example.com",
            password="secure_password_123"
        )
        
        token = result['access_token']
        payload = auth_service.verify_token(token)
        
        assert payload is not None
        assert isinstance(payload, dict)
    
    def test_verify_invalid_token(self, auth_service):
        """Test token verification fails for invalid token."""
        from src.services.auth_service import InvalidTokenError
        
        with pytest.raises(InvalidTokenError):
            auth_service.verify_token("invalid_token_string")
    
    def test_verify_token_with_wrong_secret(self, auth_service):
        """Test token verification fails with different secret key."""
        from src.services.auth_service import InvalidTokenError
        
        # Register and login with correct secret
        auth_service.register(
            email="john@example.com",
            password="secure_password_123",
            full_name="John Doe"
        )
        result = auth_service.login(
            email="john@example.com",
            password="secure_password_123"
        )
        token = result['access_token']
        
        # Create new service with different secret
        os.environ['JWT_SECRET_KEY'] = 'different_secret_key'
        auth_service2 = AuthService(auth_service.connection)
        
        # Token verification should fail
        with pytest.raises(InvalidTokenError):
            auth_service2.verify_token(token)
        
        # Restore original secret
        os.environ['JWT_SECRET_KEY'] = 'test_secret_key_for_jwt'
    
    def test_token_expiration(self, auth_service):
        """Test that token includes expiration time."""
        auth_service.register(
            email="john@example.com",
            password="secure_password_123",
            full_name="John Doe"
        )
        result = auth_service.login(
            email="john@example.com",
            password="secure_password_123"
        )
        
        # Check expires_in is approximately 8 hours * 3600 seconds
        assert abs(result['expires_in'] - (8 * 3600)) < 10
