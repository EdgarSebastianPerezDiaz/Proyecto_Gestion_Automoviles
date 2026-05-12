"""
Tests for FinalRecipientRepository - data access layer
"""
import pytest
from datetime import datetime, timezone
from mongomock import MongoClient as MockMongoClient
from unittest.mock import patch
from bson.objectid import ObjectId
from copy import deepcopy

from src.repositories.final_recipient_repository import FinalRecipientRepository
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
    """Final Recipients repository instance with mongomock."""
    return FinalRecipientRepository(mock_connection)


@pytest.fixture
def sample_recipient():
    """Sample recipient document."""
    return {
        "name": "ACME Corp",
        "address": "123 Main St",
        "city": "New York",
        "contact_name": "John Doe",
        "phone": "5551234567",
        "email": "info@acme.com",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


class TestFindActive:
    """Tests for find_active method."""
    
    def test_find_active_returns_active_recipients(self, repository, sample_recipient):
        """Test finding active recipients."""
        # Insert active recipient
        recipient_id = repository.insert_one(sample_recipient)
        
        result = repository.find_active(limit=10, skip=0)
        
        assert len(result) == 1
        assert result[0]["is_active"] is True
        assert result[0]["_id"] == recipient_id
    
    def test_find_active_with_pagination(self, repository, sample_recipient):
        """Test pagination in find_active."""
        # Insert multiple recipients
        for i in range(15):
            recipient = deepcopy(sample_recipient)
            recipient["name"] = f"Recipient {i}"
            repository.insert_one(recipient)
        
        result = repository.find_active(limit=5, skip=10)
        
        assert len(result) == 5
    
    def test_find_active_excludes_inactive(self, repository, sample_recipient):
        """Test that inactive recipients are excluded."""
        # Insert active
        repository.insert_one(deepcopy(sample_recipient))
        
        # Insert inactive
        inactive = deepcopy(sample_recipient)
        inactive["is_active"] = False
        repository.insert_one(inactive)
        
        result = repository.find_active()
        
        assert len(result) == 1
        assert result[0]["is_active"] is True


class TestFindByName:
    """Tests for find_by_name method."""
    
    def test_find_by_name_case_insensitive(self, repository, sample_recipient):
        """Test case-insensitive name search."""
        repository.insert_one(sample_recipient)
        
        result = repository.find_by_name("acme corp")
        
        # find_by_name returns list
        assert len(result) > 0
        assert result[0]["name"] == "ACME Corp"
    
    def test_find_by_name_with_empty_string(self, repository):
        """Test find_by_name with empty name."""
        result = repository.find_by_name("")
        
        assert result == []
    
    def test_find_by_name_with_partial_match(self, repository, sample_recipient):
        """Test find_by_name with partial match."""
        repository.insert_one(sample_recipient)
        
        result = repository.find_by_name("acme")
        
        assert len(result) > 0
        assert result[0]["name"] == "ACME Corp"
    
    def test_find_by_name_returns_only_active(self, repository, sample_recipient):
        """Test that find_by_name returns only active recipients."""
        # Insert active
        repository.insert_one(deepcopy(sample_recipient))
        
        # Insert inactive
        inactive = deepcopy(sample_recipient)
        inactive["is_active"] = False
        repository.insert_one(inactive)
        
        result = repository.find_by_name("ACME")
        
        # Should only return active ones
        assert len(result) == 1
        assert result[0]["is_active"] is True


class TestInsertOne:
    """Tests for insert_one method."""
    
    def test_insert_one_returns_string_id(self, repository, sample_recipient):
        """Test inserting a recipient returns string ID."""
        recipient_id = repository.insert_one(sample_recipient)
        
        assert recipient_id is not None
        assert isinstance(recipient_id, str)
        
        # Verify it was actually inserted
        retrieved = repository.find_by_id(recipient_id)
        assert retrieved is not None
        assert retrieved["name"] == sample_recipient["name"]


class TestFindById:
    """Tests for find_by_id method."""
    
    def test_find_by_id_success(self, repository, sample_recipient):
        """Test finding recipient by ID."""
        recipient_id = repository.insert_one(sample_recipient)
        
        result = repository.find_by_id(recipient_id)
        
        assert result is not None
        assert result["_id"] == recipient_id
        assert result["name"] == sample_recipient["name"]
    
    def test_find_by_id_not_found(self, repository):
        """Test finding non-existent recipient."""
        fake_id = str(ObjectId())
        
        result = repository.find_by_id(fake_id)
        
        assert result is None


class TestDeleteById:
    """Tests for delete_by_id method."""
    
    def test_delete_by_id_success(self, repository, sample_recipient):
        """Test deleting a recipient by ID."""
        recipient_id = repository.insert_one(sample_recipient)
        
        # Verify it exists
        assert repository.find_by_id(recipient_id) is not None
        
        # Delete it
        result = repository.delete_by_id(recipient_id)
        
        assert result is True
        assert repository.find_by_id(recipient_id) is None
    
    def test_delete_by_id_not_found(self, repository):
        """Test deleting non-existent recipient."""
        fake_id = str(ObjectId())
        
        result = repository.delete_by_id(fake_id)
        
        assert result is False


class TestFindMany:
    """Tests for find_many method."""
    
    def test_find_many_with_filter(self, repository, sample_recipient):
        """Test finding multiple recipients with filter."""
        # Insert 5 active and 2 inactive
        for i in range(5):
            recipient = deepcopy(sample_recipient)
            recipient["name"] = f"Active Recipient {i}"
            repository.insert_one(recipient)
        
        for i in range(2):
            recipient = deepcopy(sample_recipient)
            recipient["name"] = f"Inactive Recipient {i}"
            recipient["is_active"] = False
            repository.insert_one(recipient)
        
        # Find all active
        result = repository.find_many({"is_active": True})
        
        assert len(result) == 5
        assert all(doc["is_active"] is True for doc in result)

