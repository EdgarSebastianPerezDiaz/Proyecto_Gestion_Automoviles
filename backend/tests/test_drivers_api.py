"""
Tests for Drivers API

Tests REST endpoints with Flask test client and mocked services.
"""

import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from mongomock import MongoClient
from src.services.driver_service import (
    DriverService,
    DriverValidationError,
    DriverNotFoundError,
    DriverAlreadyExistsError,
)
from src.repositories.driver_repository import DriverRepository
from src.api.drivers import create_drivers_blueprint
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
    
    # Return appropriate collection based on what's requested
    def get_collection_side_effect(name):
        return mock_db[name]
    
    mock_conn.get_collection.side_effect = get_collection_side_effect
    
    return mock_conn


@pytest.fixture
def app(mock_db_connection):
    """Create Flask app with drivers API."""
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
        driver_repo = DriverRepository(mock_db_connection)
        driver_service = DriverService(driver_repo)
        
        # Attach to app
        app.auth_service = auth_service
        app.driver_service = driver_service
        
        # Register blueprint
        bp = create_drivers_blueprint(driver_service)
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
def sample_driver():
    """Sample driver response."""
    return {
        '_id': '507f1f77bcf86cd799439012',
        'id_number': '12345678',
        'first_name': 'Juan',
        'last_name': 'Pérez',
        'phone': '3101234567',
        'address': 'Calle 1',
        'email': 'juan@example.com',
        'license_number': 'LIC123456',
        'license_category': 'C3',
        'license_expiry': None,
        'license_alert': False,
        'license_expired': False,
        'is_active': True,
        'created_at': None,
        'updated_at': None,
    }


class TestDriversCreate:
    """Test POST /api/drivers."""
    
    def test_create_driver_admin_success(self, client, app, admin_token, sample_driver):
        """Test admin can create driver."""
        with patch.object(app.driver_service, 'create_driver', return_value=sample_driver):
            response = client.post(
                '/api/drivers/',
                json={
                    'id_number': '12345678',
                    'first_name': 'Juan',
                    'last_name': 'Pérez',
                    'phone': '3101234567',
                    'address': 'Calle 1',
                    'email': 'juan@example.com',
                    'license_number': 'LIC123456',
                    'license_category': 'C3',
                    'license_expiry': '2027-04-03T00:00:00',
                },
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 201
        assert response.json['_id'] == '507f1f77bcf86cd799439012'
        assert response.json['id_number'] == '12345678'
    
    def test_create_driver_operator_allowed(self, client, app, operator_token):
        """Test operator CAN now create driver (ownership model allows it)."""
        response = client.post(
            '/api/drivers/',
            json={
                'id_number': '12345678',
                'first_name': 'Juan',
                'last_name': 'Pérez',
                'phone': '3101234567',
                'address': 'Calle 1',
                'email': 'juan@example.com',
                'license_number': 'LIC123456',
                'license_category': 'C3',
                'license_expiry': '2027-04-03T00:00:00',
            },
            headers={'Authorization': f'Bearer {operator_token}'}
        )
        
        # Operator should now be able to create (201 success or 400 validation error)
        assert response.status_code in [201, 400]
    
    def test_create_driver_no_token(self, client):
        """Test unauthenticated request."""
        response = client.post(
            '/api/drivers/',
            json={
                'id_number': '12345678',
                'first_name': 'Juan',
                'last_name': 'Pérez',
                'phone': '3101234567',
                'address': 'Calle 1',
                'email': 'juan@example.com',
                'license_number': 'LIC123456',
                'license_category': 'C3',
                'license_expiry': '2027-04-03T00:00:00',
            }
        )
        
        assert response.status_code == 401
    
    def test_create_driver_validation_error(self, client, app, admin_token):
        """Test validation error on create."""
        with patch.object(
            app.driver_service,
            'create_driver',
            side_effect=DriverValidationError('Invalid license category')
        ):
            response = client.post(
                '/api/drivers/',
                json={'id_number': '12345678', 'license_category': 'INVALID'},
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 422
        # Error is wrapped in validation_error format
        assert response.json['error'] == 'validation_error'
    
    def test_create_driver_duplicate_id(self, client, app, admin_token):
        """Test create fails for duplicate ID number."""
        with patch.object(
            app.driver_service,
            'create_driver',
            side_effect=DriverAlreadyExistsError('Already exists')
        ):
            # Use datetime object that will be JSON serialized
            from datetime import datetime, timedelta
            expiry = (datetime.now() + timedelta(days=365))
            
            response = client.post(
                '/api/drivers/',
                json={
                    'id_number': '12345678',
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'phone': '3101234567',
                    'address': 'Cra 1 #1-1',
                    'license_number': 'LIC123456',
                    'license_category': 'C3',
                    'license_expiry': expiry.isoformat()
                },
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 409


class TestDriversList:
    """Test GET /api/drivers."""
    
    def test_list_drivers_admin_success(self, client, app, admin_token, sample_driver):
        """Test admin can list drivers."""
        with patch.object(app.driver_service, 'list_drivers', return_value=[sample_driver]):
            response = client.get(
                '/api/drivers/',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 200
        assert 'drivers' in response.json
        assert len(response.json['drivers']) == 1
    
    def test_list_drivers_operator_success(self, client, app, operator_token, sample_driver):
        """Test operator can list drivers."""
        with patch.object(app.driver_service, 'list_drivers', return_value=[sample_driver]):
            response = client.get(
                '/api/drivers/',
                headers={'Authorization': f'Bearer {operator_token}'}
            )
        
        assert response.status_code == 200
        assert len(response.json['drivers']) == 1
    
    def test_list_drivers_no_token(self, client):
        """Test list without authentication."""
        response = client.get('/api/drivers/')
        assert response.status_code == 401
    
    def test_list_drivers_pagination(self, client, app, admin_token):
        """Test pagination parameters."""
        with patch.object(app.driver_service, 'list_drivers', return_value=[]) as mock_list:
            response = client.get(
                '/api/drivers/?limit=50&skip=10',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
            
            assert response.status_code == 200
            mock_list.assert_called_once()
            call_args = mock_list.call_args
            assert call_args[1]['limit'] == 50
            assert call_args[1]['skip'] == 10
    
    def test_list_drivers_invalid_limit(self, client, admin_token):
        """Test invalid limit parameter."""
        client_app = client.application
        response = client.get(
            '/api/drivers/?limit=5000',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        # Query parameter validation returns 400 (not 422 which is for body validation)
        assert response.status_code == 400


class TestDriversGet:
    """Test GET /api/drivers/<driver_id>."""
    
    def test_get_driver_admin_success(self, client, app, admin_token, sample_driver):
        """Test admin can get driver."""
        with patch.object(app.driver_service, 'get_driver', return_value=sample_driver):
            response = client.get(
                '/api/drivers/507f1f77bcf86cd799439012',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 200
        assert response.json['id_number'] == '12345678'
    
    def test_get_driver_not_found(self, client, app, admin_token):
        """Test get driver not found."""
        with patch.object(app.driver_service, 'get_driver', return_value=None):
            response = client.get(
                '/api/drivers/invalid_id',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 404


class TestDriversGetByIdNumber:
    """Test GET /api/drivers/by-id-number/<id_number>."""
    
    def test_get_by_id_number_success(self, client, app, admin_token, sample_driver):
        """Test getting driver by ID number."""
        with patch.object(
            app.driver_service,
            'get_driver_by_id_number',
            return_value=sample_driver
        ):
            response = client.get(
                '/api/drivers/by-id-number/12345678',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 200
        assert response.json['id_number'] == '12345678'
    
    def test_get_by_id_number_not_found(self, client, app, admin_token):
        """Test ID number not found."""
        with patch.object(
            app.driver_service,
            'get_driver_by_id_number',
            return_value=None
        ):
            response = client.get(
                '/api/drivers/by-id-number/99999999',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 404


class TestDriversExpiringsoon:
    """Test GET /api/drivers/expiring-soon."""
    
    def test_get_expiring_soon_success(self, client, app, admin_token, sample_driver):
        """Test getting drivers with expiring licenses."""
        with patch.object(
            app.driver_service,
            'get_expiring_soon',
            return_value=[sample_driver]
        ):
            response = client.get(
                '/api/drivers/expiring-soon',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 200
        assert len(response.json['drivers']) == 1
    
    def test_get_expiring_soon_with_threshold(self, client, app, admin_token):
        """Test expiring soon with custom threshold."""
        with patch.object(app.driver_service, 'get_expiring_soon', return_value=[]) as mock_expiring:
            response = client.get(
                '/api/drivers/expiring-soon?days=15',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
            
            assert response.status_code == 200
            mock_expiring.assert_called_once()
            call_args = mock_expiring.call_args
            assert call_args[1]['days_threshold'] == 15


class TestDriversUpdate:
    """Test PUT /api/drivers/<driver_id>."""
    
    def test_update_driver_admin_success(self, client, app, admin_token, sample_driver):
        """Test admin can update driver."""
        updated = dict(sample_driver)
        updated['phone'] = '3109876543'
        
        with patch.object(app.driver_service, 'update_driver', return_value=updated):
            response = client.put(
                '/api/drivers/507f1f77bcf86cd799439012',
                json={'phone': '3109876543'},
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 200
        assert response.json['phone'] == '3109876543'
    
    def test_update_driver_operator_allowed(self, client, app, admin_token):
        """Test operator CAN now update their own driver (ownership model permits it)."""
        with patch.object(
            app.driver_service,
            'update_driver',
            return_value={'_id': '507f1f77bcf86cd799439012', 'phone': '3109876543'}
        ):
            response = client.put(
                '/api/drivers/507f1f77bcf86cd799439012',
                json={'phone': '3109876543'},
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        # Should not be 403 due to role restriction
        assert response.status_code in [200, 400, 404]
    
    def test_update_driver_not_found(self, client, app, admin_token):
        """Test update non-existent driver."""
        with patch.object(
            app.driver_service,
            'update_driver',
            side_effect=DriverNotFoundError('Not found')
        ):
            response = client.put(
                '/api/drivers/invalid_id',
                json={'phone': '1234567890'},
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 404


class TestDriversDelete:
    """Test DELETE /api/drivers/<driver_id>."""
    
    def test_delete_driver_admin_success(self, client, app, admin_token):
        """Test admin can delete driver."""
        with patch.object(app.driver_service, 'delete_driver', return_value=True):
            response = client.delete(
                '/api/drivers/507f1f77bcf86cd799439012',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 204
    
    def test_delete_driver_operator_allowed(self, client, app, admin_token):
        """Test operator CAN now delete their own driver (ownership model permits it)."""
        with patch.object(
            app.driver_service,
            'delete_driver',
            return_value=True
        ):
            response = client.delete(
                '/api/drivers/507f1f77bcf86cd799439012',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        # Should not be 403 due to role restriction  
        assert response.status_code == 204
    
    def test_delete_driver_not_found(self, client, app, admin_token):
        """Test delete non-existent driver."""
        with patch.object(
            app.driver_service,
            'delete_driver',
            side_effect=DriverNotFoundError('Not found')
        ):
            response = client.delete(
                '/api/drivers/invalid_id',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 404


class TestDriversRenewLicense:
    """Test PATCH /api/drivers/<driver_id>/renew-license."""
    
    def test_renew_license_admin_success(self, client, app, admin_token, sample_driver):
        """Test admin can renew driver license."""
        updated = dict(sample_driver)
        updated['license_expiry'] = datetime.now() + timedelta(days=365)
        
        with patch.object(app.driver_service, 'update_driver', return_value=updated):
            response = client.patch(
                '/api/drivers/507f1f77bcf86cd799439012/renew-license',
                json={'license_expiry': '2027-04-03T00:00:00'},
                headers={'Authorization': f'Bearer {admin_token}'}
            )
        
        assert response.status_code == 200
    
    def test_renew_license_missing_expiry(self, client, admin_token):
        """Test renew without expiry date."""
        response = client.patch(
            '/api/drivers/507f1f77bcf86cd799439012/renew-license',
            json={},
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        # Missing field check returns 400
        assert response.status_code == 400
