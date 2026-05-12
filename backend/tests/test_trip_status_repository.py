"""
Tests for TripStatusRepository - data access layer
"""
import pytest
from datetime import datetime, timezone
from mongomock import MongoClient as MockMongoClient
from unittest.mock import patch
from bson.objectid import ObjectId
from copy import deepcopy

from src.repositories.trip_status_repository import TripStatusRepository
from src.infrastructure.database import MongoDBConnection


@pytest.fixture
def mock_connection():
    """Create a mock MongoDB connection using mongomock."""
    # Reset singleton before creating new connection
    MongoDBConnection._instance = None
    
    # Patch MongoClient to use mongomock
    with patch('src.infrastructure.database.MongoClient', MockMongoClient):
        connection = MongoDBConnection()
        connection.client = MockMongoClient()
        connection.db = connection.client.test_db
        connection._initialized = True
        
        yield connection
        
        # Cleanup
        MongoDBConnection._instance = None


@pytest.fixture
def repository(mock_connection):
    """Trip Statuses repository instance with mongomock."""
    return TripStatusRepository(mock_connection)


@pytest.fixture
def sample_trip_status():
    """Sample trip status document."""
    return {
        "code": "scheduled",
        "label": "Scheduled",
        "order": 1,
        "is_terminal": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


class TestFindByCode:
    """Tests for find_by_code method."""
    
    def test_find_by_code_success(self, repository, sample_trip_status):
        """Test finding status by code."""
        repository.insert_one(sample_trip_status)
        
        result = repository.find_by_code("scheduled")
        
        assert result is not None
        assert result["code"] == "scheduled"
    
    def test_find_by_code_not_found(self, repository):
        """Test finding nonexistent code."""
        result = repository.find_by_code("nonexistent")
        
        assert result is None
    
    def test_find_by_code_with_empty_string(self, repository):
        """Test find_by_code with empty code."""
        result = repository.find_by_code("")
        
        assert result is None


class TestFindNonTerminal:
    """Tests for find_non_terminal method."""
    
    def test_find_non_terminal_statuses(self, repository, sample_trip_status):
        """Test finding non-terminal statuses."""
        # Insert non-terminal
        repository.insert_one(sample_trip_status)
        
        # Insert terminal
        terminal = {
            "code": "delivered",
            "label": "Delivered",
            "order": 5,
            "is_terminal": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        repository.insert_one(terminal)
        
        result = repository.find_non_terminal()
        
        # Should only return non-terminal
        assert len(result) == 1
        assert result[0]["is_terminal"] is False
    
    def test_find_non_terminal_excludes_terminal(self, repository):
        """Test that terminal statuses are excluded."""
        # Insert only terminal status
        terminal_status = {
            "code": "delivered",
            "label": "Delivered",
            "order": 5,
            "is_terminal": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        repository.insert_one(terminal_status)
        
        result = repository.find_non_terminal()
        
        assert len(result) == 0


class TestFindAll:
    """Tests for find_all method."""
    
    def test_find_all_returns_all_statuses(self, repository):
        """Test finding all statuses."""
        # Insert multiple statuses
        statuses = [
            {"code": "pending", "label": "Pending", "order": 0, "is_terminal": False},
            {"code": "scheduled", "label": "Scheduled", "order": 1, "is_terminal": False},
            {"code": "delivered", "label": "Delivered", "order": 5, "is_terminal": True},
        ]
        
        for status in statuses:
            repository.insert_one(status)
        
        result = repository.find_all(skip=0, limit=100)
        
        assert len(result) == 3
    
    def test_find_all_paginated(self, repository):
        """Test finding all statuses with pagination."""
        # Insert 10 statuses
        for i in range(10):
            status = {
                "code": f"status_{i}",
                "label": f"Status {i}",
                "order": i,
                "is_terminal": i >= 8  # Last 2 are terminal
            }
            repository.insert_one(status)
        
        result = repository.find_all(skip=5, limit=3)
        
        assert len(result) == 3
    
    def test_find_all_ordered_by_order_field(self, repository):
        """Test that find_all returns results ordered by order field."""
        # Insert statuses out of order
        statuses = [
            {"code": "delivered", "label": "Delivered", "order": 5, "is_terminal": True},
            {"code": "pending", "label": "Pending", "order": 0, "is_terminal": False},
            {"code": "scheduled", "label": "Scheduled", "order": 1, "is_terminal": False},
        ]
        
        for status in statuses:
            repository.insert_one(status)
        
        result = repository.find_all(skip=0, limit=100)
        
        # Should be ordered by order field
        assert result[0]["order"] == 0
        assert result[1]["order"] == 1
        assert result[2]["order"] == 5


class TestInsertOne:
    """Tests for insert_one method."""
    
    def test_insert_one_returns_string_id(self, repository, sample_trip_status):
        """Test inserting a trip status returns string ID."""
        status_id = repository.insert_one(sample_trip_status)
        
        assert status_id is not None
        assert isinstance(status_id, str)
        
        # Verify it was actually inserted
        retrieved = repository.find_by_id(status_id)
        assert retrieved is not None
        assert retrieved["code"] == sample_trip_status["code"]


class TestFindById:
    """Tests for find_by_id method."""
    
    def test_find_by_id_success(self, repository, sample_trip_status):
        """Test finding trip status by ID."""
        status_id = repository.insert_one(sample_trip_status)
        
        result = repository.find_by_id(status_id)
        
        assert result is not None
        assert result["_id"] == status_id
        assert result["code"] == sample_trip_status["code"]
    
    def test_find_by_id_not_found(self, repository):
        """Test finding non-existent trip status."""
        fake_id = str(ObjectId())
        
        result = repository.find_by_id(fake_id)
        
        assert result is None


class TestDeleteById:
    """Tests for delete_by_id method."""
    
    def test_delete_by_id_success(self, repository, sample_trip_status):
        """Test deleting a trip status by ID."""
        status_id = repository.insert_one(sample_trip_status)
        
        # Verify it exists
        assert repository.find_by_id(status_id) is not None
        
        # Delete it
        result = repository.delete_by_id(status_id)
        
        assert result is True
        assert repository.find_by_id(status_id) is None
    
    def test_delete_by_id_not_found(self, repository):
        """Test deleting non-existent trip status."""
        fake_id = str(ObjectId())
        
        result = repository.delete_by_id(fake_id)
        
        assert result is False


class TestFindMany:
    """Tests for find_many method."""
    
    def test_find_many_with_filter(self, repository):
        """Test finding multiple trip statuses with filter."""
        # Insert 3 terminal and 4 non-terminal
        for i in range(4):
            status = {
                "code": f"nonterminal_{i}",
                "label": f"Non-terminal {i}",
                "order": i,
                "is_terminal": False
            }
            repository.insert_one(status)
        
        for i in range(3):
            status = {
                "code": f"terminal_{i}",
                "label": f"Terminal {i}",
                "order": i + 10,
                "is_terminal": True
            }
            repository.insert_one(status)
        
        # Find all terminal
        result = repository.find_many({"is_terminal": True})
        
        assert len(result) == 3
        assert all(doc["is_terminal"] is True for doc in result)

