"""
Client service tests - tests for business logic layer.
"""
import pytest
from unittest.mock import MagicMock, patch
from bson import ObjectId

from src.services.client_service import (
    ClientService,
    ClientError,
    ClientValidationError,
    ClientNotFoundError,
    ClientAlreadyExistsError,
)


@pytest.fixture
def mock_repository():
    """Create a mock ClientRepository."""
    return MagicMock()


@pytest.fixture
def client_service(mock_repository):
    """Create a ClientService instance with mock repository."""
    return ClientService(mock_repository)


@pytest.fixture
def valid_client_data():
    """Create valid client data."""
    return {
        "nit": "123456789-1",
        "legal_name": "ABC Logistica Ltd",
        "trade_name": "ABC Logistics",
        "address": "Cra 1 #1-1",
        "city": "Bogota",
        "phone": "+57 1 1234567",
        "email": "contact@abc.com",
        "contact_name": "John Doe",
    }


@pytest.fixture
def sample_client():
    """Create a sample client document."""
    return {
        "_id": str(ObjectId()),
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


class TestClientServiceValidation:
    """Tests for client data validation."""
    
    def test_validate_client_data_missing_nit(self, client_service, valid_client_data):
        """Test validation fails with missing NIT."""
        del valid_client_data["nit"]
        
        with pytest.raises(ClientValidationError, match="Missing required field"):
            client_service._validate_client_data(valid_client_data)
    
    def test_validate_client_data_missing_legal_name(self, client_service, valid_client_data):
        """Test validation fails with missing legal name."""
        del valid_client_data["legal_name"]
        
        with pytest.raises(ClientValidationError, match="Missing required field"):
            client_service._validate_client_data(valid_client_data)
    
    def test_validate_client_data_invalid_nit_format(self, client_service, valid_client_data):
        """Test validation fails with invalid NIT format."""
        valid_client_data["nit"] = "ABC"
        
        with pytest.raises(ClientValidationError, match="Invalid NIT format"):
            client_service._validate_client_data(valid_client_data)
    
    def test_validate_client_data_invalid_email(self, client_service, valid_client_data):
        """Test validation fails with invalid email."""
        valid_client_data["email"] = "invalid-email"
        
        with pytest.raises(ClientValidationError, match="Invalid email format"):
            client_service._validate_client_data(valid_client_data)
    
    def test_validate_client_data_invalid_phone(self, client_service, valid_client_data):
        """Test validation fails with invalid phone."""
        valid_client_data["phone"] = "123"
        
        with pytest.raises(ClientValidationError, match="Invalid phone format"):
            client_service._validate_client_data(valid_client_data)
    
    def test_validate_client_data_valid(self, client_service, valid_client_data):
        """Test validation passes with valid data."""
        # Should not raise
        client_service._validate_client_data(valid_client_data)


class TestClientServiceCreate:
    """Tests for create_client method."""
    
    def test_create_client_success(self, client_service, mock_repository, valid_client_data):
        """Test creating a client successfully."""
        client_id = str(ObjectId())
        mock_repository.find_by_nit.return_value = None
        mock_repository.find_by_email.return_value = None
        mock_repository.insert_one.return_value = client_id
        
        result = client_service.create_client(valid_client_data)
        
        assert result["_id"] == client_id
        assert result["nit"] == "123456789-1"
        assert result["email"] == "contact@abc.com"
        assert result["is_active"] is True
        mock_repository.insert_one.assert_called_once()
    
    def test_create_client_nit_already_exists(self, client_service, mock_repository, valid_client_data):
        """Test creating a client with existing NIT."""
        existing = {"_id": str(ObjectId()), "nit": "123456789-1"}
        mock_repository.find_by_nit.return_value = existing
        
        with pytest.raises(ClientAlreadyExistsError, match="already exists"):
            client_service.create_client(valid_client_data)
    
    def test_create_client_email_already_exists(self, client_service, mock_repository, valid_client_data):
        """Test creating a client with existing email."""
        existing = {"_id": str(ObjectId()), "email": "contact@abc.com"}
        mock_repository.find_by_nit.return_value = None
        mock_repository.find_by_email.return_value = existing
        
        with pytest.raises(ClientAlreadyExistsError, match="already exists"):
            client_service.create_client(valid_client_data)
    
    def test_create_client_invalid_data(self, client_service, mock_repository):
        """Test creating a client with invalid data."""
        invalid_data = {"nit": "INVALID"}
        
        with pytest.raises(ClientValidationError):
            client_service.create_client(invalid_data)


class TestClientServiceGet:
    """Tests for get_client method."""
    
    def test_get_client_success(self, client_service, mock_repository, sample_client):
        """Test getting a client successfully."""
        mock_repository.find_by_id.return_value = sample_client
        
        result = client_service.get_client(sample_client["_id"])
        
        assert result == sample_client
        mock_repository.find_by_id.assert_called_once_with(sample_client["_id"])
    
    def test_get_client_not_found(self, client_service, mock_repository):
        """Test getting a client that doesn't exist."""
        client_id = str(ObjectId())
        mock_repository.find_by_id.return_value = None
        
        result = client_service.get_client(client_id)
        
        assert result is None


class TestClientServiceGetByNit:
    """Tests for get_client_by_nit method."""
    
    def test_get_client_by_nit_success(self, client_service, mock_repository, sample_client):
        """Test getting a client by NIT successfully."""
        mock_repository.find_by_nit.return_value = sample_client
        
        result = client_service.get_client_by_nit("123456789-1")
        
        assert result == sample_client
        mock_repository.find_by_nit.assert_called_once()
    
    def test_get_client_by_nit_not_found(self, client_service, mock_repository):
        """Test getting a client by NIT when not found."""
        mock_repository.find_by_nit.return_value = None
        
        result = client_service.get_client_by_nit("999999999-9")
        
        assert result is None


class TestClientServiceList:
    """Tests for list_clients method."""
    
    def test_list_clients_active_only(self, client_service, mock_repository, sample_client):
        """Test listing active clients."""
        clients = [sample_client]
        mock_repository.find_active.return_value = clients
        
        result = client_service.list_clients(active_only=True, limit=100, skip=0)
        
        assert result == clients
        mock_repository.find_active.assert_called_once()
    
    def test_list_clients_all(self, client_service, mock_repository, sample_client):
        """Test listing all clients."""
        clients = [sample_client]
        mock_repository.find_many.return_value = clients
        
        result = client_service.list_clients(active_only=False, limit=100, skip=0)
        
        assert result == clients
        mock_repository.find_many.assert_called_once()
    
    def test_list_clients_empty(self, client_service, mock_repository):
        """Test listing clients when none exist."""
        mock_repository.find_active.return_value = []
        
        result = client_service.list_clients(active_only=True)
        
        assert result == []


class TestClientServiceUpdate:
    """Tests for update_client method."""
    
    def test_update_client_success(self, client_service, mock_repository, sample_client):
        """Test updating a client successfully."""
        update_data = {"legal_name": "New Name", "email": "new@example.com"}
        updated_client = {**sample_client, **update_data}
        mock_repository.find_by_id.return_value = sample_client
        mock_repository.find_by_email.return_value = None
        mock_repository.update.return_value = True
        mock_repository.find_by_id.return_value = updated_client
        
        result = client_service.update_client(sample_client["_id"], update_data)
        
        assert result["legal_name"] == "New Name"
        mock_repository.update.assert_called_once()
    
    def test_update_client_not_found(self, client_service, mock_repository):
        """Test updating a client that doesn't exist."""
        client_id = str(ObjectId())
        mock_repository.find_by_id.return_value = None
        
        with pytest.raises(ClientNotFoundError):
            client_service.update_client(client_id, {"legal_name": "New Name"})
    
    def test_update_client_nit_duplicate(self, client_service, mock_repository, sample_client):
        """Test updating a client with duplicate NIT."""
        other_client = {"_id": str(ObjectId()), "nit": "987654321-0"}
        update_data = {"nit": "987654321-0"}
        mock_repository.find_by_id.return_value = sample_client
        mock_repository.find_by_nit.return_value = other_client
        
        with pytest.raises(ClientAlreadyExistsError, match="already exists"):
            client_service.update_client(sample_client["_id"], update_data)
    
    def test_update_client_email_duplicate(self, client_service, mock_repository, sample_client):
        """Test updating a client with duplicate email."""
        other_client = {"_id": str(ObjectId()), "email": "other@example.com"}
        update_data = {"email": "other@example.com"}
        mock_repository.find_by_id.return_value = sample_client
        mock_repository.find_by_email.return_value = other_client
        
        with pytest.raises(ClientAlreadyExistsError, match="already exists"):
            client_service.update_client(sample_client["_id"], update_data)


class TestClientServiceDelete:
    """Tests for delete_client method."""
    
    def test_delete_client_success(self, client_service, mock_repository):
        """Test deleting a client successfully."""
        client_id = str(ObjectId())
        mock_repository.soft_delete.return_value = True
        
        result = client_service.delete_client(client_id)
        
        assert result is True
        mock_repository.soft_delete.assert_called_once_with(client_id)
    
    def test_delete_client_not_found(self, client_service, mock_repository):
        """Test deleting a client that doesn't exist."""
        client_id = str(ObjectId())
        mock_repository.soft_delete.return_value = False
        
        result = client_service.delete_client(client_id)
        
        assert result is False
