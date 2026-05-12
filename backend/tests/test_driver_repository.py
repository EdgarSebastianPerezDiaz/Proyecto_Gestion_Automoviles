"""
Tests for Driver Repository

Tests driver data access layer using mongomock.
"""

import pytest
from datetime import datetime, timedelta
from mongomock import MongoClient
from src.repositories.driver_repository import DriverRepository
from src.infrastructure.database import MongoDBConnection


@pytest.fixture
def mock_connection():
    """Create mock MongoDB connection with mongomock."""
    mock_client = MongoClient()
    mock_db = mock_client['test_db']
    
    # Mock the connection
    mock_mongo_conn = MongoDBConnection()
    mock_mongo_conn.client = mock_client
    mock_mongo_conn.db = mock_db
    mock_mongo_conn._initialized = True
    
    yield mock_mongo_conn
    
    # Cleanup
    mock_client.close()


@pytest.fixture
def driver_repository(mock_connection):
    """Create driver repository with mock connection."""
    return DriverRepository(mock_connection)


@pytest.fixture
def sample_driver_data():
    """Sample driver data for tests."""
    return {
        'id_number': '12345678',
        'first_name': 'Juan',
        'last_name': 'Pérez',
        'phone': '3101234567',
        'address': 'Calle 1 #2-3',
        'email': 'juan@example.com',
        'license_number': 'LIC123456',
        'license_category': 'C3',
        'license_expiry': datetime.now() + timedelta(days=90),
        'license_alert': False,
        'license_expired': False,
        'is_active': True,
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
    }


class TestDriverRepository:
    """Test suite for DriverRepository."""
    
    def test_create_driver_success(self, driver_repository, sample_driver_data):
        """Test creating a driver successfully."""
        driver_id = driver_repository.insert_one(sample_driver_data)
        
        assert driver_id is not None
        
        # Verify driver was stored
        driver = driver_repository.find_by_id(driver_id)
        assert driver is not None
        assert driver['id_number'] == '12345678'
        assert driver['first_name'] == 'Juan'
    
    def test_find_by_id_number_success(self, driver_repository, sample_driver_data):
        """Test finding driver by ID number."""
        driver_repository.insert_one(sample_driver_data)
        
        found = driver_repository.find_by_id_number('12345678')
        
        assert found is not None
        assert found['id_number'] == '12345678'
        assert found['last_name'] == 'Pérez'
    
    def test_find_by_id_number_not_found(self, driver_repository):
        """Test finding non-existent driver by ID number."""
        found = driver_repository.find_by_id_number('99999999')
        
        assert found is None
    
    def test_find_active_returns_only_active(self, driver_repository, sample_driver_data):
        """Test finding only active drivers."""
        # Add active driver
        active_data = dict(sample_driver_data)
        active_data['id_number'] = '11111111'
        active_data['is_active'] = True
        result_active = driver_repository.insert_one(active_data)
        
        # Add inactive driver
        inactive_data = dict(sample_driver_data)
        inactive_data['id_number'] = '22222222'
        inactive_data['is_active'] = False
        driver_repository.insert_one(inactive_data)
        
        active_drivers = driver_repository.find_active()
        
        assert len(active_drivers) >= 1
        assert all(d['is_active'] for d in active_drivers)
        
        # Verify active driver is in results
        assert any(d['id_number'] == '11111111' for d in active_drivers)
        # Verify inactive is not
        assert not any(d['id_number'] == '22222222' for d in active_drivers)
    
    def test_find_active_pagination(self, driver_repository, sample_driver_data):
        """Test pagination for active drivers."""
        # Add multiple drivers
        for i in range(5):
            data = dict(sample_driver_data)
            data['id_number'] = f'1000000{i}'
            data['is_active'] = True
            driver_repository.insert_one(data)
        
        # Test limit
        page1 = driver_repository.find_active(limit=2, skip=0)
        assert len(page1) == 2
        
        # Test skip
        page2 = driver_repository.find_active(limit=2, skip=2)
        assert len(page2) == 2
        
        # Verify pages are different
        assert page1[0]['id_number'] != page2[0]['id_number']
    
    def test_find_license_alert(self, driver_repository, sample_driver_data):
        """Test finding drivers with license expiring soon."""
        # Driver with alert (30 days)
        alert_data = dict(sample_driver_data)
        alert_data['id_number'] = '33333333'
        alert_data['license_expiry'] = datetime.now() + timedelta(days=15)
        alert_data['license_alert'] = True
        alert_data['license_expired'] = False
        driver_repository.insert_one(alert_data)
        
        # Driver without alert (90 days)
        no_alert_data = dict(sample_driver_data)
        no_alert_data['id_number'] = '44444444'
        no_alert_data['license_expiry'] = datetime.now() + timedelta(days=90)
        no_alert_data['license_alert'] = False
        driver_repository.insert_one(no_alert_data)
        
        alert_drivers = driver_repository.find_license_alert()
        
        assert len(alert_drivers) >= 1
        assert all(d['license_alert'] for d in alert_drivers)
        assert any(d['id_number'] == '33333333' for d in alert_drivers)
        assert not any(d['id_number'] == '44444444' for d in alert_drivers)
    
    def test_find_expired(self, driver_repository, sample_driver_data):
        """Test finding drivers with expired licenses."""
        # Expired license
        expired_data = dict(sample_driver_data)
        expired_data['id_number'] = '55555555'
        expired_data['license_expiry'] = datetime.now() - timedelta(days=10)
        expired_data['license_expired'] = True
        driver_repository.insert_one(expired_data)
        
        # Valid license
        valid_data = dict(sample_driver_data)
        valid_data['id_number'] = '66666666'
        valid_data['license_expiry'] = datetime.now() + timedelta(days=90)
        valid_data['license_expired'] = False
        driver_repository.insert_one(valid_data)
        
        expired = driver_repository.find_expired()
        
        assert len(expired) >= 1
        assert all(d['license_expired'] for d in expired)
        assert any(d['id_number'] == '55555555' for d in expired)
        assert not any(d['id_number'] == '66666666' for d in expired)
    
    def test_soft_delete(self, driver_repository, sample_driver_data):
        """Test soft deleting a driver."""
        driver_id = driver_repository.insert_one(sample_driver_data)
        
        # Soft delete
        success = driver_repository.soft_delete(driver_id)
        assert success is True
        
        # Verify is_active is False
        driver = driver_repository.find_by_id(driver_id)
        assert driver['is_active'] is False
    
    def test_soft_delete_invalid_id(self, driver_repository):
        """Test soft delete with invalid ID."""
        success = driver_repository.soft_delete('invalid_id')
        assert success is False
    
    def test_update_license_status(self, driver_repository, sample_driver_data):
        """Test updating license status."""
        driver_id = driver_repository.insert_one(sample_driver_data)
        
        # Update status
        success = driver_repository.update_license_status(driver_id)
        assert success is True
        
        # Verify driver was updated with timestamp
        driver = driver_repository.find_by_id(driver_id)
        assert driver is not None
    
    def test_get_available_drivers(self, driver_repository, sample_driver_data):
        """Test getting available drivers for assignment."""
        # Add available driver
        available = dict(sample_driver_data)
        available['id_number'] = '77777777'
        available['is_active'] = True
        available['license_expired'] = False
        driver_repository.insert_one(available)
        
        # Add unavailable (inactive)
        unavailable1 = dict(sample_driver_data)
        unavailable1['id_number'] = '88888888'
        unavailable1['is_active'] = False
        driver_repository.insert_one(unavailable1)
        
        # Add unavailable (expired license)
        unavailable2 = dict(sample_driver_data)
        unavailable2['id_number'] = '99999999'
        unavailable2['is_active'] = True
        unavailable2['license_expired'] = True
        driver_repository.insert_one(unavailable2)
        
        available_drivers = driver_repository.get_available_drivers()
        
        assert len(available_drivers) >= 1
        assert all(d['is_active'] and not d['license_expired'] for d in available_drivers)
        assert any(d['id_number'] == '77777777' for d in available_drivers)
        assert not any(d['id_number'] == '88888888' for d in available_drivers)
        assert not any(d['id_number'] == '99999999' for d in available_drivers)
    
    def test_update_driver(self, driver_repository, sample_driver_data):
        """Test updating driver fields."""
        driver_id = driver_repository.insert_one(sample_driver_data)
        
        # Update driver
        success = driver_repository.update(driver_id, {
            'phone': '3109876543',
            'license_category': 'C4'
        })
        
        assert success is True
        
        # Verify updates
        driver = driver_repository.find_by_id(driver_id)
        assert driver['phone'] == '3109876543'
        assert driver['license_category'] == 'C4'
    
    def test_find_by_email(self, driver_repository, sample_driver_data):
        """Test finding driver by email (case-insensitive)."""
        driver_repository.insert_one(sample_driver_data)
        
        # Test exact match
        found = driver_repository.find_by_email('juan@example.com')
        assert found is not None
        assert found['first_name'] == 'Juan'
        
        # Test case-insensitive
        found_upper = driver_repository.find_by_email('JUAN@EXAMPLE.COM')
        assert found_upper is not None
    
    def test_find_many(self, driver_repository, sample_driver_data):
        """Test finding multiple drivers with filter."""
        # Add multiple drivers
        for i in range(3):
            data = dict(sample_driver_data)
            data['id_number'] = f'1111111{i}'
            data['license_category'] = 'C3' if i < 2 else 'C2'
            driver_repository.insert_one(data)
        
        # Find with filter
        c3_drivers = driver_repository.find_many({'license_category': 'C3'})
        
        assert len(c3_drivers) >= 2
        assert all(d['license_category'] == 'C3' for d in c3_drivers)
