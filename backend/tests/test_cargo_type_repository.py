"""
Tests for CargoTypeRepository - data access layer
"""
import pytest
from datetime import datetime, timezone
from mongomock import MongoClient as MockMongoClient
from unittest.mock import patch
from bson.objectid import ObjectId
from copy import deepcopy

from src.repositories.cargo_type_repository import CargoTypeRepository
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
    """Cargo Types repository instance with mongomock."""
    return CargoTypeRepository(mock_connection)


@pytest.fixture
def sample_cargo_type():
    """Sample cargo type document."""
    return {
        "name": "Electronics",
        "description": "Electronic equipment",
        "price_per_ton": 150.00,
        "requires_special_permit": True,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


class TestFindActive:
    """Tests for find_active method."""
    
    def test_find_active_returns_active_cargo_types(self, repository, sample_cargo_type):
        """Test finding active cargo types."""
        # Insert active cargo type
        cargo_id = repository.insert_one(sample_cargo_type)
        
        result = repository.find_active(limit=10, skip=0)
        
        assert len(result) == 1
        assert result[0]["is_active"] is True
        assert result[0]["_id"] == cargo_id
    
    def test_find_active_with_pagination(self, repository, sample_cargo_type):
        """Test pagination in find_active."""
        # Insert multiple active cargo types
        for i in range(15):
            cargo = deepcopy(sample_cargo_type)
            cargo["name"] = f"Cargo {i}"
            repository.insert_one(cargo)
        
        # Test with skip and limit
        result = repository.find_active(limit=5, skip=10)
        
        assert len(result) == 5
    
    def test_find_active_excludes_inactive(self, repository, sample_cargo_type):
        """Test that inactive cargo types are excluded."""
        # Insert active
        repository.insert_one(deepcopy(sample_cargo_type))
        
        # Insert inactive
        inactive = deepcopy(sample_cargo_type)
        inactive["is_active"] = False
        repository.insert_one(inactive)
        
        result = repository.find_active()
        
        assert len(result) == 1
        assert result[0]["is_active"] is True


class TestFindByName:
    """Tests for find_by_name method."""
    
    def test_find_by_name_case_insensitive(self, repository, sample_cargo_type):
        """Test case-insensitive name search."""
        repository.insert_one(sample_cargo_type)
        
        result = repository.find_by_name("electronics")
        
        assert result is not None
        assert result["name"] == "Electronics"
    
    def test_find_by_name_with_empty_string(self, repository):
        """Test find_by_name with empty name."""
        result = repository.find_by_name("")
        
        assert result is None
    
    def test_find_by_name_returns_only_active(self, repository, sample_cargo_type):
        """Test that only active cargo types are returned."""
        # Insert active
        repository.insert_one(deepcopy(sample_cargo_type))
        
        # Insert inactive with same name
        inactive = deepcopy(sample_cargo_type)
        inactive["is_active"] = False
        repository.insert_one(inactive)
        
        result = repository.find_by_name("Electronics")
        
        # Should only return the active one
        assert result is not None
        assert result["is_active"] is True
    
    def test_find_by_name_not_found(self, repository):
        """Test find_by_name when not found."""
        result = repository.find_by_name("NonExistent")
        
        assert result is None


class TestInsertOne:
    """Tests for insert_one method."""
    
    def test_insert_one_returns_string_id(self, repository, sample_cargo_type):
        """Test inserting a cargo type returns string ID."""
        cargo_id = repository.insert_one(sample_cargo_type)
        
        assert cargo_id is not None
        assert isinstance(cargo_id, str)
        
        # Verify it was actually inserted
        retrieved = repository.find_by_id(cargo_id)
        assert retrieved is not None
        assert retrieved["name"] == sample_cargo_type["name"]


class TestFindById:
    """Tests for find_by_id method."""
    
    def test_find_by_id_success(self, repository, sample_cargo_type):
        """Test finding cargo type by ID."""
        cargo_id = repository.insert_one(sample_cargo_type)
        
        result = repository.find_by_id(cargo_id)
        
        assert result is not None
        assert result["_id"] == cargo_id
        assert result["name"] == sample_cargo_type["name"]
    
    def test_find_by_id_not_found(self, repository):
        """Test finding non-existent cargo type."""
        fake_id = str(ObjectId())
        
        result = repository.find_by_id(fake_id)
        
        assert result is None


class TestDeleteById:
    """Tests for delete_by_id method."""
    
    def test_delete_by_id_success(self, repository, sample_cargo_type):
        """Test deleting a cargo type by ID."""
        cargo_id = repository.insert_one(sample_cargo_type)
        
        # Verify it exists
        assert repository.find_by_id(cargo_id) is not None
        
        # Delete it
        result = repository.delete_by_id(cargo_id)
        
        assert result is True
        assert repository.find_by_id(cargo_id) is None
    
    def test_delete_by_id_not_found(self, repository):
        """Test deleting non-existent cargo type."""
        fake_id = str(ObjectId())
        
        result = repository.delete_by_id(fake_id)
        
        assert result is False


class TestFindMany:
    """Tests for find_many method."""
    
    def test_find_many_with_filter(self, repository, sample_cargo_type):
        """Test finding multiple cargo types with filter."""
        # Insert 5 active and 2 inactive
        for i in range(5):
            cargo = deepcopy(sample_cargo_type)
            cargo["name"] = f"Active Cargo {i}"
            repository.insert_one(cargo)
        
        for i in range(2):
            cargo = deepcopy(sample_cargo_type)
            cargo["name"] = f"Inactive Cargo {i}"
            cargo["is_active"] = False
            repository.insert_one(cargo)
        
        # Find all active
        result = repository.find_many({"is_active": True})
        
        assert len(result) == 5
        assert all(doc["is_active"] is True for doc in result)

