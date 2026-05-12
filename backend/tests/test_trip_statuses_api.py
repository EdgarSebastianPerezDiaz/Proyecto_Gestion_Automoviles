"""
Tests for Trip Statuses API blueprint.
"""
import pytest
from flask import Flask
from unittest.mock import MagicMock, patch
from bson import ObjectId
from src.api.trip_statuses import trip_statuses_bp, set_service
from src.services.trip_status_service import (
    TripStatusService,
    TripStatusError,
    TripStatusValidationError,
    TripStatusNotFoundError,
    TripStatusInUseError,
    TripStatusAlreadyExistsError
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
    """Mock TripStatusService."""
    return MagicMock(spec=TripStatusService)


@pytest.fixture
def client(app, mock_auth_service, mock_service):
    """Flask test client with blueprint."""
    # Set up app auth service
    app.auth_service = mock_auth_service
    
    # Set the service for the blueprint
    set_service(mock_service)
    
    # Register the blueprint
    app.register_blueprint(trip_statuses_bp)
    
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
def sample_trip_status():
    """Sample trip status document."""
    return {
        "_id": str(ObjectId()),
        "code": "scheduled",
        "label": "Scheduled",
        "order": 1,
        "is_terminal": False
    }


class TestCreateTripStatus:
    """Tests for POST /api/trip-statuses."""
    
    def test_create_trip_status_success(self, client, mock_service, sample_trip_status):
        """Test successful creation."""
        mock_service.create_trip_status.return_value = sample_trip_status
        
        response = client.post(
            "/api/trip-statuses/",
            json={
                "name": "Scheduled",
                "description": "Trip is scheduled",
                "sequence_order": 1,
                "is_terminal": False
            }
        )
        
        assert response.status_code == 201
    
    def test_create_trip_status_validation_error(self, client, mock_service):
        """Test creation with validation error."""
        mock_service.create_trip_status.side_effect = TripStatusValidationError("Invalid code")
        
        response = client.post(
            "/api/trip-statuses/",
            json={"code": "INVALID-CODE", "label": "Test"}
        )
        
        assert response.status_code == 422
    
    def test_create_trip_status_already_exists(self, client, mock_service):
        """Test creation when status already exists."""
        mock_service.create_trip_status.side_effect = TripStatusAlreadyExistsError("Status name exists")
        
        response = client.post(
            "/api/trip-statuses/",
            json={
                "name": "Scheduled",
                "description": "Trip is scheduled",
                "sequence_order": 1,
                "is_terminal": False
            }
        )
        
        assert response.status_code == 409


class TestGetTripStatus:
    """Tests for GET /api/trip-statuses/<id>."""
    
    def test_get_trip_status_success(self, client, mock_service, sample_trip_status):
        """Test successful retrieval."""
        mock_service.get_trip_status.return_value = sample_trip_status
        status_id = str(sample_trip_status["_id"])
        
        response = client.get(f"/api/trip-statuses/{status_id}")
        
        assert response.status_code == 200
        assert response.json["code"] == "scheduled"
    
    def test_get_trip_status_not_found(self, client, mock_service):
        """Test retrieval of nonexistent status."""
        mock_service.get_trip_status.side_effect = TripStatusNotFoundError("Not found")
        
        response = client.get(f"/api/trip-statuses/{str(ObjectId())}")
        
        assert response.status_code == 404


class TestListTripStatuses:
    """Tests for GET /api/trip-statuses."""
    
    def test_list_trip_statuses_success(self, client, mock_service, sample_trip_status):
        """Test successful listing."""
        mock_service.list_all_statuses.return_value = [sample_trip_status]
        mock_service.count_all.return_value = 1
        
        response = client.get("/api/trip-statuses/")
        
        assert response.status_code == 200
        assert len(response.json["items"]) == 1
        assert response.json["total"] == 1
    
    def test_list_trip_statuses_with_pagination(self, client, mock_service):
        """Test listing with pagination parameters."""
        mock_service.list_all_statuses.return_value = []
        mock_service.count_all.return_value = 0
        
        response = client.get("/api/trip-statuses/?page=2&per_page=25")
        
        assert response.status_code == 200
        # Verify skip/limit calculated correctly from page/per_page
        mock_service.list_all_statuses.assert_called_with(skip=25, limit=25)
    
    def test_list_trip_statuses_limit_capped(self, client, mock_service):
        """Test that per_page is capped at 100."""
        mock_service.list_all_statuses.return_value = []
        mock_service.count_all.return_value = 0
        
        response = client.get("/api/trip-statuses/?per_page=100")
        
        assert response.status_code == 200
        # Verify per_page of 100 is passed as limit
        call_args = mock_service.list_all_statuses.call_args
        assert call_args[1]["limit"] == 100


class TestGetTripStatusByCode:
    """Tests for GET /api/trip-statuses/code/<code>."""
    
    def test_get_trip_status_by_code_success(self, client, mock_service, sample_trip_status):
        """Test successful retrieval by code."""
        mock_service.get_trip_status_by_code.return_value = sample_trip_status
        
        response = client.get("/api/trip-statuses/code/scheduled")
        
        assert response.status_code == 200
        assert response.json["code"] == "scheduled"
    
    def test_get_trip_status_by_code_not_found(self, client, mock_service):
        """Test retrieval with nonexistent code."""
        mock_service.get_trip_status_by_code.side_effect = TripStatusNotFoundError("Not found")
        
        response = client.get("/api/trip-statuses/code/nonexistent")
        
        assert response.status_code == 404


class TestListNonTerminalStatuses:
    """Tests for GET /api/trip-statuses/non-terminal."""
    
    def test_list_non_terminal_statuses_success(self, client, mock_service, sample_trip_status):
        """Test successful listing of non-terminal statuses."""
        mock_service.list_non_terminal_statuses.return_value = [sample_trip_status]
        
        response = client.get("/api/trip-statuses/non-terminal")
        
        assert response.status_code == 200
        assert len(response.json["items"]) == 1
        assert response.json["items"][0]["is_terminal"] is False


class TestUpdateTripStatus:
    """Tests for PUT /api/trip-statuses/<id>."""
    
    def test_update_trip_status_success(self, client, mock_service, sample_trip_status):
        """Test successful update."""
        updated = {**sample_trip_status, "label": "NEW LABEL"}
        mock_service.update_trip_status.return_value = updated
        status_id = str(sample_trip_status["_id"])
        
        response = client.put(
            f"/api/trip-statuses/{status_id}",
            json={"label": "NEW LABEL"}
        )
        
        assert response.status_code == 200
        assert response.json["label"] == "NEW LABEL"
    
    def test_update_trip_status_not_found(self, client, mock_service):
        """Test update of nonexistent status."""
        mock_service.update_trip_status.side_effect = TripStatusNotFoundError("Not found")
        
        response = client.put(
            f"/api/trip-statuses/{str(ObjectId())}",
            json={"label": "NEW"}
        )
        
        assert response.status_code == 404
    
    def test_update_trip_status_validation_error(self, client, mock_service):
        """Test update with validation error."""
        
        response = client.put(
            f"/api/trip-statuses/{str(ObjectId())}",
            json={"sequence_order": -1}  # Invalid: must be >= 0
        )
        
        assert response.status_code == 422


class TestDeleteTripStatus:
    """Tests for DELETE /api/trip-statuses/<id>."""
    
    def test_delete_trip_status_success(self, client, mock_service):
        """Test successful deletion."""
        mock_service.delete_trip_status.return_value = True
        status_id = str(ObjectId())
        
        response = client.delete(f"/api/trip-statuses/{status_id}")
        
        assert response.status_code == 204
    
    def test_delete_trip_status_not_found(self, client, mock_service):
        """Test deletion of nonexistent status."""
        mock_service.delete_trip_status.side_effect = TripStatusNotFoundError("Not found")
        
        response = client.delete(f"/api/trip-statuses/{str(ObjectId())}")
        
        assert response.status_code == 404
    
    def test_delete_trip_status_in_use(self, client, mock_service):
        """Test deletion fails if status is used in trips."""
        mock_service.delete_trip_status.side_effect = TripStatusInUseError("Status in use")
        
        response = client.delete(f"/api/trip-statuses/{str(ObjectId())}")
        
        assert response.status_code == 409
