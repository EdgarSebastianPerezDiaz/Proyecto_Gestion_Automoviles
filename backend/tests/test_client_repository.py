"""
Client repository tests - tests for data access layer.
"""
import pytest
from unittest.mock import MagicMock
from bson import ObjectId

from src.repositories.client_repository import ClientRepository


@pytest.fixture
def mock_connection():
    """Create a mock MongoDB connection."""
    return MagicMock()


@pytest.fixture
def sample_client():
    """Create a sample client document."""
    return {
        "nit": "123456789-1",
        "legal_name": "ABC Logistica Ltd",
        "trade_name": "ABC Logistics",
        "address": "Cra 1 #1-1",
        "city": "Bogota",
        "phone": "+57 1 1234567",
        "email": "contact@abc.com",
        "contact_name": "John Doe",
        "is_active": True,
        "created_at": "2024-01-15T10:00:00",
        "updated_at": "2024-01-15T10:00:00",
    }


@pytest.fixture
def sample_client_2():
    """Create a second sample client document."""
    return {
        "nit": "987654321-0",
        "legal_name": "XYZ Transport",
        "trade_name": None,
        "address": "Cra 2 #2-2",
        "city": "Medellin",
        "phone": "+57 4 3334567",
        "email": "info@xyz.com",
        "contact_name": "Jane Smith",
        "is_active": True,
        "created_at": "2024-01-16T10:00:00",
        "updated_at": "2024-01-16T10:00:00",
    }


@pytest.fixture
def client_repository(mock_connection):
    """Create a ClientRepository instance with mock connection."""
    return ClientRepository(mock_connection)


class TestClientRepository:
    """Tests for ClientRepository."""
    
    def test_find_by_nit_success(self, client_repository, sample_client):
        """Test finding a client by NIT."""
        sample_client["_id"] = str(ObjectId())
        client_repository.find_one = MagicMock(return_value=sample_client)
        
        result = client_repository.find_by_nit("123456789-1")
        
        assert result == sample_client
        client_repository.find_one.assert_called_once()
    
    def test_find_by_nit_not_found(self, client_repository):
        """Test finding a client by NIT when not found."""
        client_repository.find_one = MagicMock(return_value=None)
        
        result = client_repository.find_by_nit("999999999-9")
        
        assert result is None
    
    def test_find_active_success(self, client_repository, sample_client, sample_client_2):
        """Test listing active clients."""
        sample_client["_id"] = str(ObjectId())
        sample_client_2["_id"] = str(ObjectId())
        clients = [sample_client, sample_client_2]
        client_repository.find_many = MagicMock(return_value=clients)
        
        result = client_repository.find_active(limit=100, skip=0)
        
        assert len(result) == 2
        assert result == clients
        client_repository.find_many.assert_called_once()
    
    def test_find_active_with_pagination(self, client_repository, sample_client):
        """Test finding active clients with pagination."""
        sample_client["_id"] = str(ObjectId())
        client_repository.find_many = MagicMock(return_value=[sample_client])
        
        result = client_repository.find_active(limit=10, skip=5)
        
        assert len(result) == 1
    
    def test_find_active_empty(self, client_repository):
        """Test finding active clients when none exist."""
        client_repository.find_many = MagicMock(return_value=[])
        
        result = client_repository.find_active()
        
        assert result == []
    
    def test_soft_delete_success(self, client_repository):
        """Test soft deleting a client."""
        client_id = str(ObjectId())
        client_repository.update_one = MagicMock(return_value=True)
        
        result = client_repository.soft_delete(client_id)
        
        assert result is True
        client_repository.update_one.assert_called_once()
    
    def test_soft_delete_not_found(self, client_repository):
        """Test soft deleting a client that doesn't exist."""
        client_id = str(ObjectId())
        client_repository.update_one = MagicMock(return_value=False)
        
        result = client_repository.soft_delete(client_id)
        
        assert result is False
    
    def test_update_success(self, client_repository):
        """Test updating a client."""
        client_id = str(ObjectId())
        update_data = {"legal_name": "New Name", "email": "new@example.com"}
        client_repository.update_one = MagicMock(return_value=True)
        
        result = client_repository.update(client_id, update_data)
        
        assert result is True
        client_repository.update_one.assert_called_once()
    
    def test_update_not_found(self, client_repository):
        """Test updating a client that doesn't exist."""
        client_id = str(ObjectId())
        update_data = {"legal_name": "New Name"}
        client_repository.update_one = MagicMock(return_value=False)
        
        result = client_repository.update(client_id, update_data)
        
        assert result is False
    
    def test_find_by_email_success(self, client_repository, sample_client):
        """Test finding a client by email."""
        sample_client["_id"] = str(ObjectId())
        client_repository.find_one = MagicMock(return_value=sample_client)
        
        result = client_repository.find_by_email("contact@abc.com")
        
        assert result == sample_client
    
    def test_find_by_email_not_found(self, client_repository):
        """Test finding a client by email when not found."""
        client_repository.find_one = MagicMock(return_value=None)
        
        result = client_repository.find_by_email("notfound@example.com")
        
        assert result is None
