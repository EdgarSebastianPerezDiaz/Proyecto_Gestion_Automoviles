"""
Tests for Final Recipients API blueprint.
"""
import pytest
from flask import Flask
from unittest.mock import MagicMock, patch
from bson import ObjectId
from src.api.final_recipients import final_recipients_bp, set_service
from src.services.final_recipient_service import (
    FinalRecipientService,
    FinalRecipientNotFoundError,
    FinalRecipientValidationError,
    FinalRecipientAlreadyExistsError
)


@pytest.fixture
def app():
    """Flask test app."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def mock_auth_service():
    """Mock AuthService."""
    auth_service = MagicMock()
    auth_service.verify_token = MagicMock(return_value={"userId": "user1", "role": "admin"})
    auth_service.extract_token = MagicMock(return_value="token")
    auth_service.is_token_blacklisted = MagicMock(return_value=False)
    return auth_service


@pytest.fixture
def mock_service():
    """Mock FinalRecipientService."""
    return MagicMock(spec=FinalRecipientService)


@pytest.fixture
def client(app, mock_auth_service, mock_service):
    """Flask test client with blueprint."""
    # Set up app auth service
    app.auth_service = mock_auth_service
    
    # Set the service for the blueprint
    set_service(mock_service)
    
    # Register the blueprint
    app.register_blueprint(final_recipients_bp)
    
    # Create client with custom request context handler
    test_client = app.test_client()
    
    # Store original request method
    original_open = test_client.open
    
    # Wrap to add auth header by default
    def open_with_auth(*args, **kwargs):
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        if 'Authorization' not in kwargs['headers']:
            kwargs['headers']['Authorization'] = 'Bearer test-token'
        return original_open(*args, **kwargs)
    
    test_client.open = open_with_auth
    return test_client


@pytest.fixture
def sample_recipient():
    """Sample recipient document."""
    return {
        "_id": str(ObjectId()),
        "name": "ACME Corp",
        "address": "123 Main St",
        "city": "New York",
        "contact_name": "John Doe",
        "phone": "5551234567",
        "email": "info@acme.com",
        "is_active": True
    }


class TestCreateRecipient:
    """Tests for POST /api/final-recipients."""
    
    def test_create_recipient_success(self, client, mock_service, sample_recipient):
        """Test successful creation."""
        mock_service.create_recipient.return_value = sample_recipient
        
        response = client.post(
            "/api/final-recipients/",
            json={
                "name": "ACME Corp",
                "email": "info@acme.com",
                "phone": "5551234567",
                "address": "123 Main Street",
                "city": "New York"
            }
        )

        assert response.status_code == 201
        assert response.json["name"] == "ACME Corp"

class TestGetRecipient:
    """Tests for GET /api/final-recipients/<id>."""
    
    def test_get_recipient_success(self, client, mock_service, sample_recipient):
        """Test successful retrieval."""
        mock_service.get_recipient.return_value = sample_recipient
        recipient_id = sample_recipient["_id"]
        
        response = client.get(f"/api/final-recipients/{recipient_id}")
        
        assert response.status_code == 200
        assert response.json["name"] == "ACME Corp"
    
    def test_get_recipient_not_found(self, client, mock_service):
        """Test retrieval of nonexistent recipient."""
        mock_service.get_recipient.side_effect = FinalRecipientNotFoundError("Not found")
        
        response = client.get(f"/api/final-recipients/{str(ObjectId())}")
        
        assert response.status_code == 404


class TestListRecipients:
    """Tests for GET /api/final-recipients."""
    
    def test_list_recipients_success(self, client, mock_service, sample_recipient):
        """Test successful listing."""
        mock_service.list_recipients.return_value = [sample_recipient]
        mock_service.count_active.return_value = 1
        
        response = client.get("/api/final-recipients/")
        
        assert response.status_code == 200
        assert len(response.json["items"]) == 1
        assert response.json["total"] == 1
        mock_service.list_recipients.assert_called_with(skip=0, limit=10)
    
    def test_list_recipients_with_pagination(self, client, mock_service):
        """Test listing with pagination parameters."""
        mock_service.list_recipients.return_value = []
        mock_service.count_active.return_value = 0
        
        response = client.get("/api/final-recipients/?page=2&per_page=25")
        
        assert response.status_code == 200
        # Page 2 with per_page 25 means skip = (2-1)*25 = 25
        mock_service.list_recipients.assert_called_with(skip=25, limit=25)
    
    def test_list_recipients_limit_capped(self, client, mock_service):
        """Test that per_page is capped at 100."""
        mock_service.list_recipients.return_value = []
        mock_service.count_active.return_value = 0
        
        response = client.get("/api/final-recipients/?per_page=100")
        
        assert response.status_code == 200
        # Verify limit is passed to service as min(per_page, 100)
        mock_service.list_recipients.assert_called_with(skip=0, limit=100)


class TestSearchRecipients:
    """Tests for GET /api/final-recipients/search."""
    
    def test_search_recipients_success(self, client, mock_service, sample_recipient):
        """Test successful search."""
        mock_service.search_recipients_by_name.return_value = [sample_recipient]
        
        response = client.get("/api/final-recipients/search?q=acme")
        
        assert response.status_code == 200
        assert len(response.json["items"]) == 1
    
    def test_search_recipients_query_too_short(self, client, mock_service):
        """Test search with query too short."""
        response = client.get("/api/final-recipients/search?q=a")
        
        assert response.status_code == 400
    
    def test_search_recipients_no_query(self, client, mock_service):
        """Test search without query parameter."""
        response = client.get("/api/final-recipients/search")
        
        assert response.status_code == 400


class TestUpdateRecipient:
    """Tests for PUT /api/final-recipients/<id>."""
    
    def test_update_recipient_success(self, client, mock_service, sample_recipient):
        """Test successful update."""
        updated = {**sample_recipient, "name": "NEW NAME"}
        mock_service.update_recipient.return_value = updated
        recipient_id = str(sample_recipient["_id"])
        
        response = client.put(
            f"/api/final-recipients/{recipient_id}",
            json={"name": "NEW NAME"}
        )
        
        assert response.status_code == 200
        assert response.json["name"] == "NEW NAME"
    
    def test_update_recipient_not_found(self, client, mock_service):
        """Test update of nonexistent recipient."""
        mock_service.update_recipient.side_effect = FinalRecipientNotFoundError("Not found")
        
        response = client.put(
            f"/api/final-recipients/{str(ObjectId())}",
            json={"name": "NEW"}
        )
        
        assert response.status_code == 404
    
    def test_update_recipient_validation_error(self, client, mock_service):
        """Test update with validation error."""
        mock_service.update_recipient.side_effect = FinalRecipientValidationError("Invalid data")
        
        response = client.put(
            f"/api/final-recipients/{str(ObjectId())}",
            json={"email": "invalid"}
        )
        
        assert response.status_code == 422


class TestDeleteRecipient:
    """Tests for DELETE /api/final-recipients/<id>."""
    
    def test_delete_recipient_success(self, client, mock_service):
        """Test successful deletion."""
        mock_service.delete_recipient.return_value = True
        recipient_id = str(ObjectId())
        
        response = client.delete(f"/api/final-recipients/{recipient_id}")
        
        assert response.status_code == 204
    
    def test_delete_recipient_not_found(self, client, mock_service):
        """Test deletion of nonexistent recipient."""
        mock_service.delete_recipient.side_effect = FinalRecipientNotFoundError("Not found")
        
        response = client.delete(f"/api/final-recipients/{str(ObjectId())}")
        
        assert response.status_code == 404
