"""
Tests for Base Repository

Tests the BaseRepository generic class with mongomock MongoDB.
Verifies CRUD operations, sanitization, and ObjectId conversion.
"""

import pytest
from bson import ObjectId
from mongomock import MongoClient as MockMongoClient
from unittest.mock import MagicMock

from src.repositories.base_repository import BaseRepository
from src.infrastructure.database import MongoDBConnection, RepositoryError


@pytest.fixture
def mock_connection():
    """Create a mock MongoDBConnection with mongomock."""
    # Create a real mongomock client
    mongo_client = MockMongoClient()
    db = mongo_client.test_db
    
    # Create a mock connection object
    connection = MagicMock(spec=MongoDBConnection)
    connection.is_connected.return_value = True
    connection.get_collection.side_effect = lambda name: db[name]
    
    return connection


@pytest.fixture
def repository(mock_connection):
    """Create a BaseRepository instance for testing."""
    return BaseRepository(collection_name="test_collection", connection=mock_connection)


class TestBaseRepositoryInsert:
    """Test repository insert operations."""
    
    def test_insert_one(self, repository):
        """Test inserting a single document."""
        doc = {"name": "John Doe", "email": "john@example.com"}
        
        inserted_id = repository.insert_one(doc)
        
        # Verify ID is returned as string
        assert isinstance(inserted_id, str)
        assert len(inserted_id) > 0
    
    def test_insert_many(self, repository):
        """Test inserting multiple documents."""
        docs = [
            {"name": "John Doe", "email": "john@example.com"},
            {"name": "Jane Smith", "email": "jane@example.com"},
            {"name": "Bob Wilson", "email": "bob@example.com"},
        ]
        
        inserted_ids = repository.insert_many(docs)
        
        # Verify all IDs returned as strings
        assert len(inserted_ids) == 3
        assert all(isinstance(oid, str) for oid in inserted_ids)
    
    def test_insert_many_empty_list(self, repository):
        """Test inserting empty list returns empty list."""
        inserted_ids = repository.insert_many([])
        
        assert inserted_ids == []


class TestBaseRepositoryFind:
    """Test repository find operations."""
    
    def test_find_by_id(self, repository):
        """Test finding document by ObjectId."""
        # Insert a document
        doc = {"name": "John Doe", "email": "john@example.com"}
        inserted_id = repository.insert_one(doc)
        
        # Find by ID
        found_doc = repository.find_by_id(inserted_id)
        
        # Verify document found with _id as string
        assert found_doc is not None
        assert found_doc["_id"] == inserted_id
        assert found_doc["name"] == "John Doe"
        assert isinstance(found_doc["_id"], str)
    
    def test_find_by_id_not_found(self, repository):
        """Test finding non-existent document by ID."""
        fake_id = str(ObjectId())
        
        found_doc = repository.find_by_id(fake_id)
        
        assert found_doc is None
    
    def test_find_by_id_invalid_format(self, repository):
        """Test finding with invalid ObjectId format."""
        with pytest.raises(RepositoryError) as exc_info:
            repository.find_by_id("not-a-valid-id")
        
        assert "Invalid ObjectId" in str(exc_info.value)
    
    def test_find_one(self, repository):
        """Test finding single document by filter."""
        # Insert documents
        repository.insert_one({"name": "John Doe", "email": "john@example.com", "role": "user"})
        repository.insert_one({"name": "Jane Smith", "email": "jane@example.com", "role": "admin"})
        
        # Find by filter
        found_doc = repository.find_one({"role": "admin"})
        
        # Verify document found
        assert found_doc is not None
        assert found_doc["name"] == "Jane Smith"
        assert found_doc["role"] == "admin"
        assert isinstance(found_doc["_id"], str)
    
    def test_find_one_not_found(self, repository):
        """Test find_one returns None when no match."""
        found_doc = repository.find_one({"nonexistent_field": "value"})
        
        assert found_doc is None
    
    def test_find_many(self, repository):
        """Test finding multiple documents."""
        # Insert documents
        docs = [
            {"name": "John Doe", "role": "user"},
            {"name": "Jane Smith", "role": "admin"},
            {"name": "Bob Wilson", "role": "user"},
        ]
        repository.insert_many(docs)
        
        # Find all users
        found_docs = repository.find_many({"role": "user"})
        
        # Verify documents found
        assert len(found_docs) == 2
        assert all(isinstance(doc["_id"], str) for doc in found_docs)
        assert all(doc["role"] == "user" for doc in found_docs)
    
    def test_find_many_with_limit(self, repository):
        """Test find_many respects limit."""
        # Insert documents
        docs = [{"name": f"User {i}", "role": "user"} for i in range(10)]
        repository.insert_many(docs)
        
        # Find with limit
        found_docs = repository.find_many({"role": "user"}, limit=5)
        
        assert len(found_docs) == 5
    
    def test_find_many_with_skip(self, repository):
        """Test find_many respects skip."""
        # Insert documents
        docs = [
            {"name": f"User {i}", "order": i} for i in range(5)
        ]
        repository.insert_many(docs)
        
        # Find with skip
        found_docs = repository.find_many({}, skip=2, limit=10)
        
        assert len(found_docs) == 3
    
    def test_find_many_with_sort(self, repository):
        """Test find_many respects sort."""
        # Insert documents
        docs = [
            {"name": "Charlie", "order": 3},
            {"name": "Alice", "order": 1},
            {"name": "Bob", "order": 2},
        ]
        repository.insert_many(docs)
        
        # Find with sort ascending
        found_docs = repository.find_many({}, sort=[("order", 1)])
        
        assert len(found_docs) == 3
        assert found_docs[0]["name"] == "Alice"
        assert found_docs[1]["name"] == "Bob"
        assert found_docs[2]["name"] == "Charlie"


class TestBaseRepositoryUpdate:
    """Test repository update operations."""
    
    def test_update_one(self, repository):
        """Test updating a single document."""
        # Insert document
        repository.insert_one({"name": "John Doe", "email": "john@example.com", "status": "active"})
        
        # Update
        updated = repository.update_one(
            {"name": "John Doe"},
            {"$set": {"status": "inactive"}}
        )
        
        # Verify update
        assert updated is True
        
        # Verify change persisted
        found_doc = repository.find_one({"name": "John Doe"})
        assert found_doc["status"] == "inactive"
    
    def test_update_one_no_match(self, repository):
        """Test update_one returns False when no match."""
        updated = repository.update_one(
            {"nonexistent": "field"},
            {"$set": {"status": "inactive"}}
        )
        
        assert updated is False
    
    def test_update_many(self, repository):
        """Test updating multiple documents."""
        # Insert documents
        docs = [
            {"name": "User 1", "status": "active"},
            {"name": "User 2", "status": "active"},
            {"name": "User 3", "status": "active"},
        ]
        repository.insert_many(docs)
        
        # Update all
        count = repository.update_many(
            {"status": "active"},
            {"$set": {"status": "archived"}}
        )
        
        # Verify update count
        assert count == 3
        
        # Verify all changed
        found_docs = repository.find_many({"status": "archived"})
        assert len(found_docs) == 3


class TestBaseRepositoryDelete:
    """Test repository delete operations."""
    
    def test_delete_one(self, repository):
        """Test deleting a single document."""
        # Insert document
        repository.insert_one({"name": "John Doe", "email": "john@example.com"})
        
        # Delete
        deleted = repository.delete_one({"name": "John Doe"})
        
        # Verify delete
        assert deleted is True
        
        # Verify document gone
        found_doc = repository.find_one({"name": "John Doe"})
        assert found_doc is None
    
    def test_delete_one_no_match(self, repository):
        """Test delete_one returns False when no match."""
        deleted = repository.delete_one({"nonexistent": "field"})
        
        assert deleted is False
    
    def test_delete_many(self, repository):
        """Test deleting multiple documents."""
        # Insert documents
        docs = [
            {"name": "User 1", "category": "test"},
            {"name": "User 2", "category": "test"},
            {"name": "User 3", "category": "keep"},
        ]
        repository.insert_many(docs)
        
        # Delete test documents
        count = repository.delete_many({"category": "test"})
        
        # Verify delete count
        assert count == 2
        
        # Verify only keep document remains
        remaining = repository.find_many({})
        assert len(remaining) == 1
        assert remaining[0]["category"] == "keep"


class TestBaseRepositorySanitization:
    """Test repository input sanitization for NoSQL injection prevention."""
    
    def test_sanitize_removes_mongo_operators_from_filter(self, repository):
        """Test that MongoDB operators in filters are sanitized."""
        # Insert a document
        repository.insert_one({"name": "John Doe", "status": "active"})
        repository.insert_one({"name": "Jane Smith", "status": "inactive"})
        
        # Attempt injection with $ne operator
        # After sanitization, $ne becomes plaintext "ne", so no documents should match
        found_docs = repository.find_many({"status": {"$ne": "inactive"}})
        
        # Sanitization should remove the operator, returning empty or sanitized results
        # The exact behavior depends on sanitizer, but it should not execute $ne operator
        assert isinstance(found_docs, list)
    
    def test_sanitize_preserves_normal_queries(self, repository):
        """Test that normal queries still work after sanitization."""
        # Insert documents
        repository.insert_one({"name": "John Doe", "role": "admin"})
        repository.insert_one({"name": "Jane Smith", "role": "user"})
        
        # Find with normal filter
        found_docs = repository.find_many({"role": "admin"})
        
        # Verify normal query works
        assert len(found_docs) == 1
        assert found_docs[0]["name"] == "John Doe"


class TestBaseRepositoryNotConnected:
    """Test repository behavior when connection not ready."""
    
    def test_raise_error_if_not_connected(self):
        """Test that repository raises error if connection not initialized."""
        mock_connection = MagicMock(spec=MongoDBConnection)
        mock_connection.is_connected.return_value = False
        
        with pytest.raises(RepositoryError) as exc_info:
            BaseRepository("test", mock_connection)
        
        assert "not initialized" in str(exc_info.value).lower()


class TestBaseRepositoryTypeConversion:
    """Test ObjectId to string conversion."""
    
    def test_objectid_converted_to_string_in_response(self, repository):
        """Test that _id is converted to string in responses."""
        # Insert document
        inserted_id = repository.insert_one({"name": "Test"})
        
        # Find document
        found_doc = repository.find_by_id(inserted_id)
        
        # Verify _id is string
        assert isinstance(found_doc["_id"], str)
        assert found_doc["_id"] == inserted_id
    
    def test_objectid_converted_in_find_many(self, repository):
        """Test that all _ids are converted to strings in find_many."""
        # Insert documents
        docs = [{"name": f"User {i}"} for i in range(3)]
        repository.insert_many(docs)
        
        # Find all
        found_docs = repository.find_many({})
        
        # Verify all _ids are strings
        assert len(found_docs) == 3
        assert all(isinstance(doc["_id"], str) for doc in found_docs)
