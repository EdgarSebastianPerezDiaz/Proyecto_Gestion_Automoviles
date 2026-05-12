"""
Tests for MongoDB Database Connection

Tests the MongoDBConnection singleton and index creation using mongomock.
"""

import pytest
from unittest.mock import patch, MagicMock
from mongomock import MongoClient as MockMongoClient
from src.infrastructure.database import (
    MongoDBConnection,
    DatabaseConnectionError,
    RepositoryError
)


@pytest.fixture
def reset_singleton():
    """Reset the singleton instance before each test."""
    MongoDBConnection._instance = None
    yield
    MongoDBConnection._instance = None


@pytest.fixture
def mock_mongo_env(monkeypatch):
    """Mock MONGO_URI environment variable."""
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017/test_db")


@pytest.fixture
def no_mongo_env(monkeypatch):
    """Ensure MONGO_URI environment variable is not set."""
    monkeypatch.delenv("MONGO_URI", raising=False)


class TestMongoDBConnection:
    """Test suite for MongoDBConnection."""
    
    def test_singleton_instance(self, reset_singleton):
        """Test that MongoDBConnection follows singleton pattern."""
        instance1 = MongoDBConnection.get_instance()
        instance2 = MongoDBConnection.get_instance()
        
        assert instance1 is instance2
        assert id(instance1) == id(instance2)
    
    def test_connect_without_mongo_uri(self, reset_singleton, no_mongo_env):
        """Test that connect() raises error when MONGO_URI env var not set."""
        connection = MongoDBConnection.get_instance()
        
        with pytest.raises(DatabaseConnectionError) as exc_info:
            connection.connect()
        
        assert "MONGO_URI" in str(exc_info.value)
        assert connection._initialized is False
    
    @patch("src.infrastructure.database.MongoClient")
    def test_connect_creates_indexes(self, mock_client_class, reset_singleton, mock_mongo_env):
        """Test that connect() creates necessary indexes."""
        # Mock the MongoClient and its methods
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        
        mock_db = MagicMock()
        mock_client_instance.get_database.return_value = mock_db
        
        mock_rate_limits = MagicMock()
        mock_db.__getitem__.return_value = mock_rate_limits  # For db['rate_limits']
        
        connection = MongoDBConnection.get_instance()
        connection.connect()
        
        # Verify connection was established
        assert connection._initialized is True
        assert connection.client is mock_client_instance
        assert connection.db is mock_db
        
        # Verify indexes were created
        mock_rate_limits.create_index.assert_called()
    
    @patch("src.infrastructure.database.MongoClient")
    def test_get_collection(self, mock_client_class, reset_singleton, mock_mongo_env):
        """Test that get_collection() returns a collection."""
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        
        mock_db = MagicMock()
        mock_client_instance.get_database.return_value = mock_db
        
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        
        connection = MongoDBConnection.get_instance()
        connection.connect()
        
        # Get a collection
        collection = connection.get_collection("test_collection")
        
        # Verify collection was returned
        assert collection is not None
        mock_db.__getitem__.assert_called_with("test_collection")
    
    def test_get_collection_not_connected(self, reset_singleton):
        """Test that get_collection() raises error if not connected."""
        connection = MongoDBConnection.get_instance()
        
        with pytest.raises(DatabaseConnectionError) as exc_info:
            connection.get_collection("test_collection")
        
        assert "not initialized" in str(exc_info.value).lower()
    
    @patch("src.infrastructure.database.MongoClient")
    def test_close_connection(self, mock_client_class, reset_singleton, mock_mongo_env):
        """Test that close() properly closes the connection."""
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        
        mock_db = MagicMock()
        mock_client_instance.get_database.return_value = mock_db
        
        mock_rate_limits = MagicMock()
        mock_db.__getitem__.return_value = mock_rate_limits
        
        connection = MongoDBConnection.get_instance()
        connection.connect()
        
        assert connection._initialized is True
        
        # Close connection
        connection.close()
        
        # Verify connection was closed
        assert connection._initialized is False
        assert connection.client is None
        assert connection.db is None
        mock_client_instance.close.assert_called_once()
    
    @patch("src.infrastructure.database.MongoClient")
    def test_is_connected(self, mock_client_class, reset_singleton, mock_mongo_env):
        """Test that is_connected() returns correct status."""
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        
        mock_db = MagicMock()
        mock_client_instance.get_database.return_value = mock_db
        
        mock_rate_limits = MagicMock()
        mock_db.__getitem__.return_value = mock_rate_limits
        
        connection = MongoDBConnection.get_instance()
        
        # Before connecting
        assert connection.is_connected() is False
        
        # After connecting
        connection.connect()
        assert connection.is_connected() is True
        
        # After closing
        connection.close()
        assert connection.is_connected() is False
    
    @patch("src.infrastructure.database.MongoClient")
    def test_admin_ping_verification(self, mock_client_class, reset_singleton, mock_mongo_env):
        """Test that connect() verifies connection with admin ping."""
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        
        mock_admin = MagicMock()
        mock_client_instance.admin = mock_admin
        
        mock_db = MagicMock()
        mock_client_instance.get_database.return_value = mock_db
        
        mock_rate_limits = MagicMock()
        mock_db.__getitem__.return_value = mock_rate_limits
        
        connection = MongoDBConnection.get_instance()
        connection.connect()
        
        # Verify admin command was called
        mock_admin.command.assert_called_with("ping")
    
    @patch("src.infrastructure.database.MongoClient")
    def test_connection_timeout(self, mock_client_class, reset_singleton, mock_mongo_env):
        """Test that connection timeout raises proper error."""
        from pymongo.errors import ServerSelectionTimeoutError
        
        # Simulate timeout
        mock_client_class.side_effect = ServerSelectionTimeoutError("Timeout")
        
        connection = MongoDBConnection.get_instance()
        
        with pytest.raises(DatabaseConnectionError) as exc_info:
            connection.connect()
        
        assert "Failed to connect" in str(exc_info.value)
        assert connection._initialized is False
