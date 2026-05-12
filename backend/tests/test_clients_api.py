"""
Clients API tests - tests for REST endpoints.
"""
import os
import pytest
from datetime import datetime, timedelta
from time import time
from unittest.mock import MagicMock, patch
from bson import ObjectId
import json
from flask import Flask
from mongomock import MongoClient

from src.services.client_service import ClientService
from src.repositories.client_repository import ClientRepository
from src.api.clients import create_clients_blueprint
from src.services.auth_service import AuthService


@pytest.fixture
def mock_service():
    """Create a mock ClientService."""
    return MagicMock(spec=ClientService)


@pytest.fixture
def mock_db_connection():
    """Create mock MongoDB connection."""
    mock_client = MongoClient()
    mock_db = mock_client['test_db']
    
    mock_conn = MagicMock()
    mock_conn.client = mock_client
    mock_conn.db = mock_db
    mock_conn._initialized = True
    mock_conn.is_connected.return_value = True
    
    def get_collection_side_effect(name):
        return mock_db[name]
    
    mock_conn.get_collection.side_effect = get_collection_side_effect
    
    return mock_conn


@pytest.fixture
def app(mock_service, mock_db_connection):
    """Create Flask app with clients API."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    
    # Set up environment variables for auth service
    os.environ["JWT_SECRET_KEY"] = "test_secret_key"
    os.environ["JWT_ALGORITHM"] = "HS256"
    os.environ["JWT_EXPIRATION_HOURS"] = "8"
    
    # Patch the MongoDBConnection to use our mock
    with patch('src.infrastructure.database.MongoDBConnection.get_instance', return_value=mock_db_connection):
        # Initialize auth service
        auth_service = AuthService(mock_db_connection)
        
        # Attach to app
        app.auth_service = auth_service
        
        # Register the clients blueprint with mock service
        bp = create_clients_blueprint(mock_service)
        app.register_blueprint(bp)
    
    return app


@pytest.fixture
def client_app(app):
    """Create a Flask test client."""
    return app.test_client()


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


@pytest.fixture
def sample_client_for_operator(operator_user):
    """Create a sample client owned by operator."""
    return {
        "_id": str(ObjectId()),
        "nit": f"987654321-{int(time() * 1000) % 10}",
        "legal_name": "Operator Client Ltd",
        "trade_name": "Operator Client",
        "address": "Cra 2 #2-2",
        "city": "Medellin",
        "phone": "+57 4 1234567",
        "email": "contact@operclient.com",
        "contact_name": "Jane Doe",
        "is_active": True,
        "created_by": operator_user["_id"],
        "created_at": "2024-01-15T10:00:00",
        "updated_at": "2024-01-15T10:00:00",
    }


@pytest.fixture
def valid_client_data():
    """Create valid client data for requests."""
    return {
        "name": "ABC Logistics Ltd",
        "phone": "+57 1 1234567",
        "email": "contact@abc.com",
        "address": "Cra 1 #1-1",
        "city": "Bogota",
        "contact_person": "John Doe",
    }


@pytest.fixture
def admin_user():
    """Create admin user."""
    return {
        "_id": str(ObjectId()),
        "email": "admin@example.com",
        "role": "admin",
    }


@pytest.fixture
def operator_user():
    """Create operator user."""
    return {
        "_id": str(ObjectId()),
        "email": "operator@example.com",
        "role": "operator",
    }


@pytest.fixture
def admin_token(app, admin_user):
    """Generate JWT token for admin user."""
    payload = {
        "sub": admin_user["_id"],
        "email": admin_user["email"],
        "role": admin_user["role"],
    }
    token = app.auth_service.generate_token(payload)
    return token


@pytest.fixture
def operator_token(app, operator_user):
    """Generate JWT token for operator user."""
    payload = {
        "sub": operator_user["_id"],
        "email": operator_user["email"],
        "role": operator_user["role"],
    }
    token = app.auth_service.generate_token(payload)
    return token


@pytest.fixture
def auth_headers(admin_token):
    """Create authentication headers with admin token."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def operator_auth_headers(operator_token):
    """Create authentication headers with operator token."""
    return {"Authorization": f"Bearer {operator_token}"}


class TestClientCreateEndpoint:
    """Tests for POST /api/clients/"""
    
    def test_create_client_success(self, client_app, mock_service, sample_client, valid_client_data, auth_headers):
        """Test creating a client successfully."""
        mock_service.create_client.return_value = sample_client
        
        response = client_app.post(
            "/api/clients/",
            json=valid_client_data,
            headers=auth_headers,
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["_id"] == sample_client["_id"]
        mock_service.create_client.assert_called_once()
    
    def test_create_client_empty_request(self, client_app, mock_service, auth_headers):
        """Test creating a client with empty request."""
        
        response = client_app.post(
            "/api/clients/",
            json={},
            headers=auth_headers,
        )
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert "error" in data
        assert data["error"] == "validation_error"
    
    def test_create_client_validation_error(self, client_app, mock_service, auth_headers):
        """Test creating a client with invalid data."""
        from src.services.client_service import ClientValidationError
        invalid_data = {"nit": "INVALID", "legal_name": "Test"}
        mock_service.create_client.side_effect = ClientValidationError("Invalid NIT format")
        
        response = client_app.post(
            "/api/clients/",
            json=invalid_data,
            headers=auth_headers,
        )
        
        assert response.status_code == 422
    
    def test_create_client_duplicate_nit(self, client_app, mock_service, valid_client_data, auth_headers):
        """Test creating a client with duplicate NIT."""
        from src.services.client_service import ClientAlreadyExistsError
        mock_service.create_client.side_effect = ClientAlreadyExistsError("already exists")
        
        response = client_app.post(
            "/api/clients/",
            json=valid_client_data,
            headers=auth_headers,
        )
        
        assert response.status_code == 409
    
    def test_create_client_no_auth(self, client_app, mock_service, valid_client_data):
        """Test creating a client without authentication."""
        response = client_app.post(
            "/api/clients/",
            json=valid_client_data,
        )
        
        assert response.status_code in [401, 403]


class TestClientListEndpoint:
    """Tests for GET /api/clients/"""
    
    def test_list_clients_success(self, client_app, mock_service, sample_client, auth_headers):
        """Test listing clients successfully."""
        mock_service.list_clients.return_value = [sample_client]
        
        response = client_app.get(
            "/api/clients/",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "clients" in data
        assert len(data["clients"]) == 1
        mock_service.list_clients.assert_called_once()
    
    def test_list_clients_empty(self, client_app, mock_service, auth_headers):
        """Test listing clients when none exist."""
        mock_service.list_clients.return_value = []
        
        response = client_app.get(
            "/api/clients/",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data["clients"]) == 0
    
    def test_list_clients_pagination(self, client_app, mock_service, sample_client, auth_headers):
        """Test listing clients with pagination."""
        mock_service.list_clients.return_value = [sample_client]
        
        response = client_app.get(
            "/api/clients/?limit=10&skip=5",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["limit"] == 10
        assert data["skip"] == 5
    
    def test_list_clients_operator_access(self, client_app, mock_service, sample_client, operator_auth_headers):
        """Test listing clients with operator role."""
        mock_service.list_clients.return_value = [sample_client]
        
        response = client_app.get(
            "/api/clients/",
            headers=operator_auth_headers,
        )
        
        assert response.status_code == 200


class TestClientGetEndpoint:
    """Tests for GET /api/clients/<client_id>"""
    
    def test_get_client_success(self, client_app, mock_service, sample_client, auth_headers):
        """Test getting a client successfully."""
        mock_service.get_client.return_value = sample_client
        
        response = client_app.get(
            f"/api/clients/{sample_client['_id']}",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["_id"] == sample_client["_id"]
        mock_service.get_client.assert_called_once()
    
    def test_get_client_not_found(self, client_app, mock_service, auth_headers):
        """Test getting a client that doesn't exist."""
        client_id = str(ObjectId())
        mock_service.get_client.return_value = None
        
        response = client_app.get(
            f"/api/clients/{client_id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data


class TestClientGetByNitEndpoint:
    """Tests for GET /api/clients/by-nit/<nit>"""
    
    def test_get_client_by_nit_success(self, client_app, mock_service, sample_client, auth_headers):
        """Test getting a client by NIT successfully."""
        mock_service.get_client_by_nit.return_value = sample_client
        
        response = client_app.get(
            "/api/clients/by-nit/123456789-1",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["nit"] == "123456789-1"
    
    def test_get_client_by_nit_not_found(self, client_app, mock_service, auth_headers):
        """Test getting a client by NIT when not found."""
        mock_service.get_client_by_nit.return_value = None
        
        response = client_app.get(
            "/api/clients/by-nit/999999999-9",
            headers=auth_headers,
        )
        
        assert response.status_code == 404


class TestClientUpdateEndpoint:
    """Tests for PUT /api/clients/<client_id>"""
    
    def test_update_client_success(self, client_app, mock_service, sample_client, auth_headers):
        """Test updating a client successfully."""
        from src.services.client_service import ClientValidationError, ClientNotFoundError, ClientAlreadyExistsError
        update_data = {"legal_name": "New Name"}
        updated_client = {**sample_client, **update_data}
        mock_service.update_client.return_value = updated_client
        
        response = client_app.put(
            f"/api/clients/{sample_client['_id']}",
            json=update_data,
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["legal_name"] == "New Name"
        mock_service.update_client.assert_called_once()
    
    def test_update_client_not_found(self, client_app, mock_service, auth_headers):
        """Test updating a client that doesn't exist."""
        from src.services.client_service import ClientNotFoundError
        client_id = str(ObjectId())
        update_data = {"legal_name": "New Name"}
        mock_service.update_client.side_effect = ClientNotFoundError("not found")
        
        response = client_app.put(
            f"/api/clients/{client_id}",
            json=update_data,
            headers=auth_headers,
        )
        
        assert response.status_code == 404
    
    def test_update_client_duplicate_nit(self, client_app, mock_service, sample_client, auth_headers):
        """Test updating a client with duplicate NIT."""
        from src.services.client_service import ClientAlreadyExistsError
        update_data = {"nit": "987654321-0"}
        mock_service.update_client.side_effect = ClientAlreadyExistsError("already exists")
        
        response = client_app.put(
            f"/api/clients/{sample_client['_id']}",
            json=update_data,
            headers=auth_headers,
        )
        
        assert response.status_code == 409
    
    def test_update_client_validation_error(self, client_app, mock_service, sample_client, auth_headers):
        """Test updating a client with invalid data."""
        from src.services.client_service import ClientValidationError
        update_data = {"name": ""}  # Empty name should fail Pydantic validation
        
        response = client_app.put(
            f"/api/clients/{sample_client['_id']}",
            json=update_data,
            headers=auth_headers,
        )
        
        # Empty string should fail field min_length validation, returning 422
        assert response.status_code == 422


class TestClientDeleteEndpoint:
    """Tests for DELETE /api/clients/<client_id>"""
    
    def test_delete_client_success(self, client_app, mock_service, sample_client, auth_headers):
        """Test deleting a client successfully."""
        mock_service.delete_client.return_value = True
        
        response = client_app.delete(
            f"/api/clients/{sample_client['_id']}",
            headers=auth_headers,
        )
        
        assert response.status_code == 204
        mock_service.delete_client.assert_called_once()
    
    def test_delete_client_not_found(self, client_app, mock_service, auth_headers):
        """Test deleting a client that doesn't exist."""
        client_id = str(ObjectId())
        mock_service.delete_client.return_value = False
        
        response = client_app.delete(
            f"/api/clients/{client_id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 404


class TestClientApiAuthorization:
    """Tests for authorization on client endpoints."""
    
    def test_create_client_operator_allowed(self, client_app, mock_service, valid_client_data, operator_auth_headers):
        """Test that create allows operator role."""
        mock_service.create_client.return_value = {**valid_client_data, "_id": str(ObjectId())}
        
        response = client_app.post(
            "/api/clients/",
            json=valid_client_data,
            headers=operator_auth_headers,
        )
        
        assert response.status_code == 201
    
    def test_update_client_operator_allowed(self, client_app, mock_service, sample_client_for_operator, operator_auth_headers):
        """Test that update allows operator role for their own client."""
        update_data = {"legal_name": "New Name"}
        updated_client = {**sample_client_for_operator, **update_data}
        
        # Mock get_client to return the client for ownership verification
        mock_service.get_client.return_value = sample_client_for_operator
        mock_service.update_client.return_value = updated_client
        
        response = client_app.put(
            f"/api/clients/{sample_client_for_operator['_id']}",
            json=update_data,
            headers=operator_auth_headers,
        )
        
        assert response.status_code == 200
    
    def test_delete_client_operator_allowed(self, client_app, mock_service, sample_client_for_operator, operator_auth_headers):
        """Test that delete allows operator role for their own client."""
        # Mock get_client to return the client for ownership verification
        mock_service.get_client.return_value = sample_client_for_operator
        mock_service.delete_client.return_value = True
        
        response = client_app.delete(
            f"/api/clients/{sample_client_for_operator['_id']}",
            headers=operator_auth_headers,
        )
        
        assert response.status_code == 204
    
    def test_list_client_allows_operator(self, client_app, mock_service, operator_auth_headers):
        """Test that list allows operator role."""
        mock_service.list_clients.return_value = []
        
        response = client_app.get(
            "/api/clients/",
            headers=operator_auth_headers,
        )
        
        assert response.status_code == 200
