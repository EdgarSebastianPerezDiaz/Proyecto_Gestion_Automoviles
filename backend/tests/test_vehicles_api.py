"""
Tests for Vehicles API

Tests REST endpoints with Flask test client and mocked services.
"""

import os
import pytest
from datetime import datetime, timezone, timedelta
from time import time
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from mongomock import MongoClient
from bson.objectid import ObjectId

from src.services.vehicle_service import (
    VehicleService,
    VehicleValidationError,
    VehicleNotFoundError,
    VehicleAlreadyExistsError,
)
from src.repositories.vehicle_repository import VehicleRepository
from src.api.vehicles import create_vehicles_blueprint
from src.services.auth_service import AuthService
from src.repositories.user_repository import UserRepository


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
def app(mock_db_connection):
    """Create Flask app with vehicles API."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    
    # Set up environment variables for auth service
    os.environ['JWT_SECRET_KEY'] = 'test_secret_key'
    os.environ['JWT_ALGORITHM'] = 'HS256'
    os.environ['JWT_EXPIRATION_HOURS'] = '8'
    os.environ['BCRYPT_ROUNDS'] = '4'
    
    # Patch the MongoDBConnection to use our mock
    with patch('src.infrastructure.database.MongoDBConnection.get_instance', return_value=mock_db_connection):
        # Initialize services
        auth_service = AuthService(mock_db_connection)
        vehicle_repo = VehicleRepository(mock_db_connection)
        vehicle_service = VehicleService(vehicle_repo)
        
        # Attach to app
        app.auth_service = auth_service
        app.vehicle_service = vehicle_service
        
        # Register blueprint
        bp = create_vehicles_blueprint(vehicle_service)
        app.register_blueprint(bp)
    
    return app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def admin_user():
    """Create admin user."""
    return {
        '_id': '507f1f77bcf86cd799439010',
        'email': 'admin@example.com',
        'role': 'admin',
    }


@pytest.fixture
def operator_user():
    """Create operator user."""
    return {
        '_id': '507f1f77bcf86cd799439011',
        'email': 'operator@example.com',
        'role': 'operator',
    }


@pytest.fixture
def admin_token(app, admin_user):
    """Generate JWT token for admin user."""
    payload = {
        'sub': admin_user['_id'],
        'email': admin_user['email'],
        'role': admin_user['role'],
    }
    token = app.auth_service.generate_token(payload)
    return token


@pytest.fixture
def operator_token(app, operator_user):
    """Generate JWT token for operator user."""
    payload = {
        'sub': operator_user['_id'],
        'email': operator_user['email'],
        'role': operator_user['role'],
    }
    token = app.auth_service.generate_token(payload)
    return token


@pytest.fixture
def sample_vehicle():
    """Create sample vehicle data."""
    return {
        "_id": str(ObjectId()),
        "plate": "ABC123",
        "vehicle_type": "truck",
        "brand": "Volvo",
        "model_year": 2020,
        "capacity_tons": 20.0,
        "volume_m3": 50.0,
        "status": "available",
        "company_id": str(ObjectId()),
        "soat_expiry": (datetime.now(timezone.utc) + timedelta(days=60)).isoformat(),
        "tech_review_expiry": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


class TestVehiclesCreate:
    """Test POST /api/vehicles."""
    
    def test_create_vehicle_admin_success(self, client, app, admin_token, sample_vehicle):
        """Test admin can create vehicle."""
        vehicle_data = {
            "plate": "ABC123",
            "vehicle_type": "truck",
            "brand": "Volvo",
            "model_year": 2020,
            "capacity_tons": 20.0,
            "volume_m3": 50.0,
            "company_id": str(ObjectId()),
        }
        
        with patch.object(app.vehicle_service, 'create_vehicle', return_value=sample_vehicle) as mock_create:
            response = client.post(
                '/api/vehicles/',
                json=vehicle_data,
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 201
        assert response.json['plate'] == 'ABC123'
        mock_create.assert_called_once()
    
    def test_create_vehicle_operator_allowed(self, client, app, operator_token):
        """Test operator can create vehicle."""
        vehicle_data = {
            "plate": f"ABC{int(time() * 1000) % 10000}",
            "vehicle_type": "truck",
            "brand": "Volvo",
            "model_year": 2020,
            "capacity_tons": 20.0,
            "company_id": str(ObjectId()),
        }
        
        response = client.post(
            '/api/vehicles/',
            json=vehicle_data,
            headers={'Authorization': f'Bearer {operator_token}'}
        )
        
        assert response.status_code == 201
    
    def test_create_vehicle_no_token(self, client):
        """Test create requires authentication."""
        response = client.post('/api/vehicles/', json={})
        assert response.status_code == 401
    
    def test_create_vehicle_validation_error(self, client, app, admin_token):
        """Test validation error on invalid data."""
        vehicle_data = {"plate": "ABC123"}  # Missing required fields
        
        with patch.object(app.vehicle_service, 'create_vehicle', side_effect=VehicleValidationError("Missing required field")):
            response = client.post(
                '/api/vehicles/',
                json=vehicle_data,
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 422
        assert 'error' in response.json
    
    def test_create_vehicle_duplicate_plate(self, client, app, admin_token):
        """Test duplicate plate error."""
        vehicle_data = {
            "plate": "ABC123",
            "vehicle_type": "truck",
            "brand": "Volvo",
            "model_year": 2020,
            "capacity_tons": 20.0,
            "company_id": str(ObjectId()),
        }
        
        with patch.object(app.vehicle_service, 'create_vehicle', side_effect=VehicleAlreadyExistsError("Plate already exists")):
            response = client.post(
                '/api/vehicles/',
                json=vehicle_data,
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 409
        assert 'error' in response.json


class TestVehiclesList:
    """Test GET /api/vehicles."""
    
    def test_list_vehicles_admin_success(self, client, app, admin_token, sample_vehicle):
        """Test admin can list vehicles."""
        with patch.object(app.vehicle_service, 'list_vehicles', return_value=[sample_vehicle]) as mock_list:
            response = client.get(
                '/api/vehicles/',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 200
        assert len(response.json['vehicles']) == 1
        mock_list.assert_called_once()
    
    def test_list_vehicles_operator_success(self, client, app, operator_token, sample_vehicle):
        """Test operator can list vehicles."""
        with patch.object(app.vehicle_service, 'list_vehicles', return_value=[sample_vehicle]):
            response = client.get(
                '/api/vehicles/',
                headers={'Authorization': f'Bearer {operator_token}'}
            )
        
        assert response.status_code == 200
        assert len(response.json['vehicles']) == 1
    
    def test_list_vehicles_no_token(self, client):
        """Test list requires authentication."""
        response = client.get('/api/vehicles/')
        assert response.status_code == 401
    
    def test_list_vehicles_pagination(self, client, app, admin_token):
        """Test pagination parameters."""
        with patch.object(app.vehicle_service, 'list_vehicles', return_value=[]) as mock_list:
            response = client.get(
                '/api/vehicles/?limit=50&skip=10',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
            
            assert response.status_code == 200
            mock_list.assert_called_once()
            call_args = mock_list.call_args
            assert call_args[1]['limit'] == 50
            assert call_args[1]['skip'] == 10
    
    def test_list_vehicles_invalid_limit(self, client, admin_token):
        """Test invalid limit parameter."""
        response = client.get(
            '/api/vehicles/?limit=5000',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        # Query parameter validation returns 400 (not 422 which is for body validation)
        assert response.status_code == 400
    
    def test_list_vehicles_with_status_filter(self, client, app, admin_token, sample_vehicle):
        """Test filtering by status."""
        with patch.object(app.vehicle_service, 'list_vehicles', return_value=[sample_vehicle]) as mock_list:
            response = client.get(
                '/api/vehicles/?status=available',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
            
            assert response.status_code == 200
            call_args = mock_list.call_args
            assert call_args[1]['status_filter'] == 'available'


class TestVehiclesGet:
    """Test GET /api/vehicles/<vehicle_id>."""
    
    def test_get_vehicle_admin_success(self, client, app, admin_token, sample_vehicle):
        """Test admin can get vehicle."""
        with patch.object(app.vehicle_service, 'get_vehicle', return_value=sample_vehicle):
            response = client.get(
                f'/api/vehicles/{sample_vehicle["_id"]}',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 200
        assert response.json['plate'] == 'ABC123'
    
    def test_get_vehicle_not_found(self, client, app, admin_token):
        """Test get non-existent vehicle."""
        with patch.object(app.vehicle_service, 'get_vehicle', return_value=None):
            response = client.get(
                '/api/vehicles/nonexistent',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 404


class TestVehiclesGetByPlate:
    """Test GET /api/vehicles/by-plate/<plate>."""
    
    def test_get_by_plate_success(self, client, app, admin_token, sample_vehicle):
        """Test get vehicle by plate."""
        with patch.object(app.vehicle_service, 'get_vehicle_by_plate', return_value=sample_vehicle):
            response = client.get(
                '/api/vehicles/by-plate/ABC123',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 200
        assert response.json['plate'] == 'ABC123'
    
    def test_get_by_plate_not_found(self, client, app, admin_token):
        """Test get non-existent plate."""
        with patch.object(app.vehicle_service, 'get_vehicle_by_plate', return_value=None):
            response = client.get(
                '/api/vehicles/by-plate/XYZ999',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 404


class TestVehiclesAvailable:
    """Test GET /api/vehicles/available."""
    
    def test_get_available_success(self, client, app, admin_token, sample_vehicle):
        """Test get available vehicles."""
        with patch.object(app.vehicle_service, 'list_vehicles', return_value=[sample_vehicle]):
            response = client.get(
                '/api/vehicles/available',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 200
        assert len(response.json['vehicles']) == 1


class TestVehiclesExpiringDocuments:
    """Test GET /api/vehicles/expiring-documents."""
    
    def test_get_expiring_documents_success(self, client, app, admin_token, sample_vehicle):
        """Test get expiring documents."""
        expiring_data = {
            "soat_expiring": [sample_vehicle],
            "tech_review_expiring": [],
            "soat_threshold_days": 30,
            "tech_threshold_days": 30,
        }
        
        with patch.object(app.vehicle_service, 'get_expiring_documents', return_value=expiring_data):
            response = client.get(
                '/api/vehicles/expiring-documents',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 200
        assert len(response.json['soat_expiring']) == 1
    
    def test_get_expiring_documents_with_threshold(self, client, app, admin_token):
        """Test expiring documents with custom threshold."""
        expiring_data = {
            "soat_expiring": [],
            "tech_review_expiring": [],
            "soat_threshold_days": 15,
            "tech_threshold_days": 15,
        }
        
        with patch.object(app.vehicle_service, 'get_expiring_documents', return_value=expiring_data) as mock_expiring:
            response = client.get(
                '/api/vehicles/expiring-documents?soat_days=15&tech_days=15',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
            
            assert response.status_code == 200
            mock_expiring.assert_called_once()
            call_args = mock_expiring.call_args
            assert call_args[1]['soat_days'] == 15
            assert call_args[1]['tech_days'] == 15


class TestVehiclesUpdate:
    """Test PUT /api/vehicles/<vehicle_id>."""
    
    def test_update_vehicle_admin_success(self, client, app, admin_token, sample_vehicle):
        """Test admin can update vehicle."""
        updated = dict(sample_vehicle)
        updated['brand'] = 'MAN'
        
        with patch.object(app.vehicle_service, 'update_vehicle', return_value=updated):
            response = client.put(
                f'/api/vehicles/{sample_vehicle["_id"]}',
                json={'brand': 'MAN'},
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 200
        assert response.json['brand'] == 'MAN'
    
    def test_update_vehicle_operator_allowed(self, client, app, operator_token):
        """Test operator can update their own vehicle."""
        # Create vehicle as operator first
        vehicle_data = {
            "plate": f"UPD{int(time() * 1000) % 10000}",
            "vehicle_type": "truck",
            "brand": "Volvo",
            "model_year": 2020,
            "capacity_tons": 20.0,
            "company_id": str(ObjectId()),
        }
        
        create_response = client.post(
            '/api/vehicles/',
            json=vehicle_data,
            headers={'Authorization': f'Bearer {operator_token}'}
        )
        
        vehicle_id = create_response.json['_id']
        
        # Now update it
        response = client.put(
            f'/api/vehicles/{vehicle_id}',
            json={'brand': 'MAN'},
            headers={'Authorization': f'Bearer {operator_token}'}
        )
        
        assert response.status_code == 200
    
    def test_update_vehicle_not_found(self, client, app, admin_token):
        """Test update non-existent vehicle."""
        with patch.object(app.vehicle_service, 'update_vehicle', side_effect=VehicleNotFoundError("Not found")):
            response = client.put(
                '/api/vehicles/nonexistent',
                json={'brand': 'MAN'},
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 404


class TestVehiclesDelete:
    """Test DELETE /api/vehicles/<vehicle_id>."""
    
    def test_delete_vehicle_admin_success(self, client, app, admin_token, sample_vehicle):
        """Test admin can delete vehicle."""
        with patch.object(app.vehicle_service, 'delete_vehicle', return_value=True):
            response = client.delete(
                f'/api/vehicles/{sample_vehicle["_id"]}',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 204
    
    def test_delete_vehicle_operator_allowed(self, client, app, operator_token):
        """Test operator can delete their own vehicle."""
        # Create vehicle as operator first
        vehicle_data = {
            "plate": f"DEL{int(time() * 1000) % 10000}",
            "vehicle_type": "truck",
            "brand": "Volvo",
            "model_year": 2020,
            "capacity_tons": 20.0,
            "company_id": str(ObjectId()),
        }
        
        create_response = client.post(
            '/api/vehicles/',
            json=vehicle_data,
            headers={'Authorization': f'Bearer {operator_token}'}
        )
        
        vehicle_id = create_response.json['_id']
        
        # Now delete it
        response = client.delete(
            f'/api/vehicles/{vehicle_id}',
            headers={'Authorization': f'Bearer {operator_token}'}
        )
        
        assert response.status_code == 204
    
    def test_delete_vehicle_not_found(self, client, app, admin_token):
        """Test delete non-existent vehicle."""
        with patch.object(app.vehicle_service, 'delete_vehicle', return_value=False):
            response = client.delete(
                '/api/vehicles/nonexistent',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 404


class TestVehiclesUpdateStatus:
    """Test PATCH /api/vehicles/<vehicle_id>/status."""
    
    def test_update_status_admin_success(self, client, app, admin_token, sample_vehicle):
        """Test admin can update vehicle status."""
        updated = dict(sample_vehicle)
        updated['status'] = 'in_trip'
        
        with patch.object(app.vehicle_service, 'update_vehicle_status', return_value=updated):
            response = client.patch(
                f'/api/vehicles/{sample_vehicle["_id"]}/status',
                json={'status': 'in_trip'},
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 200
        assert response.json['status'] == 'in_trip'
    
    def test_update_status_operator_allowed(self, client, app, operator_token):
        """Test operator can update status of their vehicle."""
        # Create vehicle as operator first
        vehicle_data = {
            "plate": f"STA{int(time() * 1000) % 10000}",
            "vehicle_type": "truck",
            "brand": "Volvo",
            "model_year": 2020,
            "capacity_tons": 20.0,
            "company_id": str(ObjectId()),
        }
        
        create_response = client.post(
            '/api/vehicles/',
            json=vehicle_data,
            headers={'Authorization': f'Bearer {operator_token}'}
        )
        
        vehicle_id = create_response.json['_id']
        
        # Now update status
        response = client.patch(
            f'/api/vehicles/{vehicle_id}/status',
            json={'status': 'in_trip'},
            headers={'Authorization': f'Bearer {operator_token}'}
        )
        
        assert response.status_code == 200
    
    def test_update_status_missing_field(self, client, app, admin_token, sample_vehicle):
        """Test update status requires status field."""
        response = client.patch(
            f'/api/vehicles/{sample_vehicle["_id"]}/status',
            json={},
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        # Missing required field check returns 400 (as per current implementation)
        assert response.status_code == 400

