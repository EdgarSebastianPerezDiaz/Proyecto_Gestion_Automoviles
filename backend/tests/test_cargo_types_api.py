"""
Tests for Cargo Types API blueprint.
"""
import pytest
from flask import Flask
from unittest.mock import MagicMock, patch
from bson import ObjectId
from src.api.cargo_types import cargo_types_bp, set_service
from src.services.cargo_type_service import (
    CargoTypeService,
    CargoTypeError,
    CargoTypeValidationError,
    CargoTypeNotFoundError,
    CargoTypeAlreadyExistsError
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
    """Mock CargoTypeService."""
    return MagicMock(spec=CargoTypeService)


@pytest.fixture
def client(app, mock_auth_service, mock_service):
    """Flask test client with blueprint."""
    # Set up app auth service
    app.auth_service = mock_auth_service
    
    # Set the service for the blueprint
    set_service(mock_service)
    
    # Register the blueprint
    app.register_blueprint(cargo_types_bp)
    
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
def sample_cargo_type():
    """Sample cargo type document."""
    return {
        "_id": str(ObjectId()),
        "name": "Electronics",
        "description": "Electronic equipment",
        "price_per_ton": 150.00,
        "requires_special_permit": True,
        "is_active": True
    }


class TestCreateCargoType:
    """Tests for POST /api/cargo-types."""
    
    def test_create_cargo_type_success(self, client, mock_service, sample_cargo_type):
        """Test successful creation."""
        mock_service.create_cargo_type.return_value = sample_cargo_type
        
        response = client.post(
            "/api/cargo-types/",
            json={
                "name": "Electronics",
                "price_per_ton": 150.00
            }
        )
        
        assert response.status_code == 201
        assert response.json["name"] == "Electronics"
    
    def test_create_cargo_type_validation_error(self, client, mock_service):
        """Test creation with validation error."""
        mock_service.create_cargo_type.side_effect = CargoTypeValidationError("Price must be positive")
        
        response = client.post(
            "/api/cargo-types/",
            json={"name": "Test", "price_per_ton": -50}
        )
        
        assert response.status_code == 422
    
    def test_create_cargo_type_already_exists(self, client, mock_service):
        """Test creation when name already exists."""
        mock_service.create_cargo_type.side_effect = CargoTypeAlreadyExistsError("Name exists")
        
        response = client.post(
            "/api/cargo-types/",
            json={"name": "Existing", "price_per_ton": 100}
        )
        
        assert response.status_code == 409


class TestGetCargoType:
    """Tests for GET /api/cargo-types/<id>."""
    
    def test_get_cargo_type_success(self, client, mock_service, sample_cargo_type):
        """Test successful retrieval."""
        mock_service.get_cargo_type.return_value = sample_cargo_type
        cargo_id = str(sample_cargo_type["_id"])
        
        response = client.get(f"/api/cargo-types/{cargo_id}")
        
        assert response.status_code == 200
        assert response.json["name"] == "Electronics"
    
    def test_get_cargo_type_not_found(self, client, mock_service):
        """Test retrieval of nonexistent cargo type."""
        mock_service.get_cargo_type.side_effect = CargoTypeNotFoundError("Not found")
        
        response = client.get(f"/api/cargo-types/{str(ObjectId())}")
        
        assert response.status_code == 404


class TestListCargoTypes:
    """Tests for GET /api/cargo-types."""
    
    def test_list_cargo_types_success(self, client, mock_service, sample_cargo_type):
        """Test successful listing."""
        mock_service.list_active_cargo_types.return_value = [sample_cargo_type]
        mock_service.count_active.return_value = 1
        
        response = client.get("/api/cargo-types/")
        
        assert response.status_code == 200
        assert len(response.json["items"]) == 1
        assert response.json["total"] == 1
    
    def test_list_cargo_types_with_pagination(self, client, mock_service):
        """Test listing with pagination parameters."""
        mock_service.list_active_cargo_types.return_value = []
        mock_service.count_active.return_value = 0
        
        response = client.get("/api/cargo-types/?page=2&per_page=25")
        
        assert response.status_code == 200
        # Verify correct skip/limit values were calculated and passed
        mock_service.list_active_cargo_types.assert_called_with(skip=25, limit=25)
    
    def test_list_cargo_types_limit_capped(self, client, mock_service):
        """Test that per_page is capped at 100."""
        mock_service.list_active_cargo_types.return_value = []
        mock_service.count_active.return_value = 0
        
        response = client.get("/api/cargo-types/?per_page=100")
        
        assert response.status_code == 200
        # Verify per_page of 100 is passed as limit to service
        call_args = mock_service.list_active_cargo_types.call_args
        assert call_args[1]["limit"] == 100


class TestSearchCargoType:
    """Tests for GET /api/cargo-types/search."""
    
    def test_search_cargo_type_success(self, client, mock_service, sample_cargo_type):
        """Test successful search."""
        mock_service.search_cargo_type_by_name.return_value = sample_cargo_type
        
        response = client.get("/api/cargo-types/search?q=electronics")
        
        assert response.status_code == 200
        assert response.json["name"] == "Electronics"
    
    def test_search_cargo_type_query_too_short(self, client, mock_service):
        """Test search with query too short."""
        response = client.get("/api/cargo-types/search?q=a")
        
        assert response.status_code == 400
    
    def test_search_cargo_type_not_found(self, client, mock_service):
        """Test search when cargo type not found."""
        mock_service.search_cargo_type_by_name.side_effect = CargoTypeNotFoundError("Not found")
        
        response = client.get("/api/cargo-types/search?q=nonexistent")
        
        assert response.status_code == 404


class TestUpdateCargoType:
    """Tests for PUT /api/cargo-types/<id>."""
    
    def test_update_cargo_type_success(self, client, mock_service, sample_cargo_type):
        """Test successful update."""
        updated = {**sample_cargo_type, "price_per_ton": 200.00}
        mock_service.update_cargo_type.return_value = updated
        cargo_id = str(sample_cargo_type["_id"])
        
        response = client.put(
            f"/api/cargo-types/{cargo_id}",
            json={"price_per_ton": 200.00}
        )
        
        assert response.status_code == 200
        assert response.json["price_per_ton"] == 200.00
    
    def test_update_cargo_type_not_found(self, client, mock_service):
        """Test update of nonexistent cargo type."""
        mock_service.update_cargo_type.side_effect = CargoTypeNotFoundError("Not found")
        
        response = client.put(
            f"/api/cargo-types/{str(ObjectId())}",
            json={"price_per_ton": 100}
        )
        
        assert response.status_code == 404
    
    def test_update_cargo_type_validation_error(self, client, mock_service):
        """Test update with validation error."""
        mock_service.update_cargo_type.side_effect = CargoTypeValidationError("Invalid price")
        
        response = client.put(
            f"/api/cargo-types/{str(ObjectId())}",
            json={"price_per_ton": -50}
        )
        
        assert response.status_code == 422


class TestDeleteCargoType:
    """Tests for DELETE /api/cargo-types/<id>."""
    
    def test_delete_cargo_type_success(self, client, mock_service):
        """Test successful deletion."""
        mock_service.delete_cargo_type.return_value = True
        cargo_id = str(ObjectId())
        
        response = client.delete(f"/api/cargo-types/{cargo_id}")
        
        assert response.status_code == 204
    
    def test_delete_cargo_type_not_found(self, client, mock_service):
        """Test deletion of nonexistent cargo type."""
        mock_service.delete_cargo_type.side_effect = CargoTypeNotFoundError("Not found")
        
        response = client.delete(f"/api/cargo-types/{str(ObjectId())}")
        
        assert response.status_code == 404
