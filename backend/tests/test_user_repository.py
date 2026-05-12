"""
Tests for UserRepository

Tests user-specific repository operations with mongomock.
"""

import pytest
from datetime import datetime, timezone, timezone
from mongomock import MongoClient as MockMongoClient
from src.repositories.user_repository import UserRepository
from src.infrastructure.database import MongoDBConnection, RepositoryError
from unittest.mock import patch


@pytest.fixture
def mock_connection():
    """Create a mock MongoDB connection using mongomock."""
    # Patch MongoClient to use mongomock
    with patch('src.infrastructure.database.MongoClient', MockMongoClient):
        connection = MongoDBConnection.get_instance()
        # Reset singleton for testing
        MongoDBConnection._instance = None
        connection = MongoDBConnection()
        connection.client = MockMongoClient()
        connection.db = connection.client.test_db
        connection._initialized = True
        connection._create_indexes()
        return connection


@pytest.fixture
def user_repo(mock_connection):
    """Create a UserRepository instance with mock connection."""
    return UserRepository(mock_connection)


@pytest.fixture
def sample_user():
    """Create a sample user document."""
    return {
        "email": "john@example.com",
        "password_hash": "hashed_password_123",
        "full_name": "John Doe",
        "role": "operator",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "last_login": None,
    }


class TestUserRepository:
    """Tests for UserRepository operations."""
    
    def test_create_user_success(self, user_repo, sample_user):
        """Test successful user creation."""
        user_id = user_repo.create_user(sample_user)
        
        assert user_id is not None
        assert isinstance(user_id, str)
        
        # Verify user was stored
        user = user_repo.find_by_id(user_id)
        assert user is not None
        assert user['email'] == 'john@example.com'
    
    def test_create_user_email_normalized_to_lowercase(self, user_repo, sample_user):
        """Test that email is normalized to lowercase on creation."""
        sample_user['email'] = 'JOHN@EXAMPLE.COM'
        user_id = user_repo.create_user(sample_user)
        
        user = user_repo.find_by_id(user_id)
        assert user['email'] == 'john@example.com'
    
    def test_find_by_email_success(self, user_repo, sample_user):
        """Test finding a user by email."""
        user_id = user_repo.create_user(sample_user)
        
        # Find by email
        found_user = user_repo.find_by_email('john@example.com')
        
        assert found_user is not None
        assert found_user['email'] == 'john@example.com'
        assert found_user['_id'] == user_id
    
    def test_find_by_email_case_insensitive(self, user_repo, sample_user):
        """Test that email lookup is case-insensitive."""
        user_repo.create_user(sample_user)
        
        # Find with different case
        found_user = user_repo.find_by_email('JOHN@EXAMPLE.COM')
        
        assert found_user is not None
        assert found_user['email'] == 'john@example.com'
    
    def test_find_by_email_not_found(self, user_repo):
        """Test finding non-existent email returns None."""
        result = user_repo.find_by_email('nonexistent@example.com')
        assert result is None
    
    def test_find_by_email_with_password(self, user_repo, sample_user):
        """Test that password_hash is included when needed."""
        user_id = user_repo.create_user(sample_user)
        
        user = user_repo.find_by_email_with_password('john@example.com')
        
        assert user is not None
        assert 'password_hash' in user
        assert user['password_hash'] == 'hashed_password_123'
    
    def test_find_by_email_empty_string(self, user_repo):
        """Test that empty email returns None."""
        result = user_repo.find_by_email('')
        assert result is None
    
    def test_update_last_login_success(self, user_repo, sample_user):
        """Test updating last_login timestamp."""
        user_id = user_repo.create_user(sample_user)
        
        # Initial last_login should be None
        user = user_repo.find_by_id(user_id)
        assert user['last_login'] is None
        
        # Update last_login
        success = user_repo.update_last_login(user_id)
        
        assert success is True
        
        # Verify last_login was updated
        updated_user = user_repo.find_by_id(user_id)
        assert updated_user['last_login'] is not None
        assert isinstance(updated_user['last_login'], datetime)
    
    def test_update_last_login_nonexistent_user(self, user_repo):
        """Test updating last_login for non-existent user returns False."""
        # Use invalid ObjectId format
        result = user_repo.update_last_login('nonexistent_id')
        assert result is False
    
    def test_find_many_users(self, user_repo):
        """Test finding multiple users."""
        # Create multiple users
        user1 = {
            "email": "user1@example.com",
            "password_hash": "hash1",
            "full_name": "User One",
            "role": "operator",
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
        user2 = {
            "email": "user2@example.com",
            "password_hash": "hash2",
            "full_name": "User Two",
            "role": "admin",
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
        
        user_repo.create_user(user1)
        user_repo.create_user(user2)
        
        # Find all users
        users = user_repo.find_many({})
        
        assert len(users) == 2
        emails = [u['email'] for u in users]
        assert 'user1@example.com' in emails
        assert 'user2@example.com' in emails
    
    def test_user_id_converted_to_string(self, user_repo, sample_user):
        """Test that ObjectId is converted to string in responses."""
        user_id = user_repo.create_user(sample_user)
        
        user = user_repo.find_by_id(user_id)
        
        # _id should be a string, not ObjectId
        assert isinstance(user['_id'], str)
        assert user['_id'] == user_id
    
    def test_find_by_role(self, user_repo):
        """Test finding users by role."""
        # Create users with different roles
        user1 = {
            "email": "admin@example.com",
            "password_hash": "hash",
            "full_name": "Admin User",
            "role": "admin",
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
        user2 = {
            "email": "operator@example.com",
            "password_hash": "hash",
            "full_name": "Operator User",
            "role": "operator",
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
        
        user_repo.create_user(user1)
        user_repo.create_user(user2)
        
        # Find by role
        admins = user_repo.find_many({"role": "admin"})
        operators = user_repo.find_many({"role": "operator"})
        
        assert len(admins) == 1
        assert len(operators) == 1
        assert admins[0]['email'] == 'admin@example.com'
        assert operators[0]['email'] == 'operator@example.com'

