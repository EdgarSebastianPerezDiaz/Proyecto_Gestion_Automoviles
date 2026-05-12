"""
Tests for Driver Service

Tests business logic and validation using mocked repository.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from src.services.driver_service import (
    DriverService,
    DriverValidationError,
    DriverNotFoundError,
    DriverAlreadyExistsError,
)


@pytest.fixture
def mock_repository():
    """Create mock driver repository."""
    return Mock()


@pytest.fixture
def driver_service(mock_repository):
    """Create driver service with mock repository."""
    return DriverService(mock_repository)


@pytest.fixture
def sample_driver_input():
    """Sample driver input data."""
    return {
        'id_number': '12345678',
        'first_name': 'Juan',
        'last_name': 'Pérez',
        'phone': '3101234567',
        'address': 'Calle 1',
        'email': 'juan@example.com',
        'license_number': 'LIC123456',
        'license_category': 'C3',
        'license_expiry': datetime.now() + timedelta(days=90),
    }


@pytest.fixture
def sample_driver_doc():
    """Sample driver document from DB."""
    return {
        '_id': '507f1f77bcf86cd799439011',
        'id_number': '12345678',
        'first_name': 'Juan',
        'last_name': 'Pérez',
        'phone': '3101234567',
        'address': 'Calle 1',
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


class TestDriverServiceValidation:
    """Test validation logic."""
    
    def test_validate_missing_required_field(self, driver_service, sample_driver_input):
        """Test validation fails when required field missing."""
        invalid_data = dict(sample_driver_input)
        del invalid_data['id_number']
        
        with pytest.raises(DriverValidationError) as exc:
            driver_service._validate_driver_data(invalid_data)
        
        assert 'id_number' in str(exc.value)
    
    def test_validate_invalid_id_number_format(self, driver_service, sample_driver_input):
        """Test validation fails with invalid ID number format."""
        invalid_data = dict(sample_driver_input)
        invalid_data['id_number'] = '12345'  # Too short
        
        with pytest.raises(DriverValidationError) as exc:
            driver_service._validate_driver_data(invalid_data)
        
        assert 'ID number' in str(exc.value)
    
    def test_validate_invalid_license_category(self, driver_service, sample_driver_input):
        """Test validation fails with invalid license category."""
        invalid_data = dict(sample_driver_input)
        invalid_data['license_category'] = 'INVALID'
        
        with pytest.raises(DriverValidationError) as exc:
            driver_service._validate_driver_data(invalid_data)
        
        assert 'license category' in str(exc.value)
    
    def test_validate_past_license_expiry(self, driver_service, sample_driver_input):
        """Test validation fails with past license expiry."""
        invalid_data = dict(sample_driver_input)
        invalid_data['license_expiry'] = datetime.now() - timedelta(days=10)
        
        with pytest.raises(DriverValidationError) as exc:
            driver_service._validate_driver_data(invalid_data)
        
        assert 'future' in str(exc.value).lower()
    
    def test_validate_valid_id_number_with_formatting(self, driver_service, sample_driver_input):
        """Test validation accepts formatted ID numbers."""
        valid_data = dict(sample_driver_input)
        valid_data['id_number'] = '123.456.78'
        
        # Should not raise
        driver_service._validate_driver_data(valid_data)
    
    def test_validate_invalid_phone(self, driver_service, sample_driver_input):
        """Test validation fails with invalid phone."""
        invalid_data = dict(sample_driver_input)
        invalid_data['phone'] = 'not-a-phone'
        
        with pytest.raises(DriverValidationError) as exc:
            driver_service._validate_driver_data(invalid_data)
        
        assert 'digit' in str(exc.value)


class TestDriverServiceCreation:
    """Test create_driver method."""
    
    def test_create_driver_success(self, driver_service, mock_repository, sample_driver_input):
        """Test successful driver creation."""
        mock_repository.find_by_id_number.return_value = None
        mock_repository.insert_one.return_value = '507f1f77bcf86cd799439011'
        
        result = driver_service.create_driver(sample_driver_input)
        
        assert result is not None
        assert result['_id'] == '507f1f77bcf86cd799439011'
        assert result['id_number'] == '12345678'
        assert result['first_name'] == 'Juan'
    
    def test_create_normalizes_id_number(self, driver_service, mock_repository, sample_driver_input):
        """Test that ID number is normalized."""
        formatted_input = dict(sample_driver_input)
        formatted_input['id_number'] = '123.456.78'  # With dots
        
        mock_repository.find_by_id_number.return_value = None
        mock_repository.insert_one.return_value = '507f1f77bcf86cd799439011'
        
        result = driver_service.create_driver(formatted_input)
        
        assert result['id_number'] == '12345678'  # Normalized
    
    def test_create_calculates_license_status(self, driver_service, mock_repository, sample_driver_input):
        """Test that license status is calculated."""
        # Future date (no alert)
        expiry_data = dict(sample_driver_input)
        expiry_data['license_expiry'] = datetime.now() + timedelta(days=90)
        
        mock_repository.find_by_id_number.return_value = None
        mock_repository.insert_one.return_value = '507f1f77bcf86cd799439011'
        
        result = driver_service.create_driver(expiry_data)
        
        assert result['license_expired'] is False
        assert result['license_alert'] is False
    
    def test_create_fails_duplicate_id_number(self, driver_service, mock_repository, sample_driver_input):
        """Test creation fails with duplicate ID number."""
        mock_repository.find_by_id_number.return_value = {'_id': '507f1f77bcf86cd799439012'}
        
        with pytest.raises(DriverAlreadyExistsError):
            driver_service.create_driver(sample_driver_input)
    
    def test_create_sanitizes_strings(self, driver_service, mock_repository, sample_driver_input):
        """Test that string fields are sanitized for NoSQL injection."""
        dirty_input = dict(sample_driver_input)
        dirty_input['first_name'] = 'Juan;command|echo'  # Try to inject commands
        
        mock_repository.find_by_id_number.return_value = None
        mock_repository.insert_one.return_value = '507f1f77bcf86cd799439011'
        
        result = driver_service.create_driver(dirty_input)
        
        # Sanitizer should remove ; and | characters
        assert ';' not in result['first_name']
        assert '|' not in result['first_name']


class TestDriverServiceRetrieval:
    """Test get methods."""
    
    def test_get_driver_success(self, driver_service, mock_repository, sample_driver_doc):
        """Test getting driver by ID."""
        mock_repository.find_by_id.return_value = sample_driver_doc
        
        result = driver_service.get_driver('507f1f77bcf86cd799439011')
        
        assert result is not None
        assert result['id_number'] == '12345678'
    
    def test_get_driver_not_found(self, driver_service, mock_repository):
        """Test getting non-existent driver."""
        mock_repository.find_by_id.return_value = None
        
        result = driver_service.get_driver('invalid_id')
        
        assert result is None
    
    def test_get_driver_by_id_number(self, driver_service, mock_repository, sample_driver_doc):
        """Test getting driver by ID number."""
        mock_repository.find_by_id_number.return_value = sample_driver_doc
        
        result = driver_service.get_driver_by_id_number('12345678')
        
        assert result is not None
        assert result['id_number'] == '12345678'
    
    def test_list_drivers_active_only(self, driver_service, mock_repository, sample_driver_doc):
        """Test listing only active drivers."""
        mock_repository.find_many.return_value = [sample_driver_doc]
        
        result = driver_service.list_drivers(active_only=True, include_expired=False)
        
        mock_repository.find_many.assert_called_once()
        call_args = mock_repository.find_many.call_args
        assert call_args[0][0]['is_active'] is True
        assert 'license_expired' in call_args[0][0]
    
    def test_list_drivers_pagination(self, driver_service, mock_repository):
        """Test pagination parameters."""
        mock_repository.find_many.return_value = []
        
        driver_service.list_drivers(limit=500, skip=100)
        
        mock_repository.find_many.assert_called_once()
        call_args = mock_repository.find_many.call_args
        assert call_args[1]['limit'] == 500
        assert call_args[1]['skip'] == 100


class TestDriverServiceUpdate:
    """Test update_driver method."""
    
    def test_update_driver_success(self, driver_service, mock_repository, sample_driver_doc):
        """Test successful driver update."""
        mock_repository.find_by_id.return_value = sample_driver_doc
        mock_repository.update.return_value = True
        
        updated_doc = dict(sample_driver_doc)
        updated_doc['phone'] = '3109876543'
        mock_repository.find_by_id.side_effect = [sample_driver_doc, updated_doc]
        
        result = driver_service.update_driver(
            '507f1f77bcf86cd799439011',
            {'phone': '3109876543'}
        )
        
        assert result['phone'] == '3109876543'
    
    def test_update_driver_not_found(self, driver_service, mock_repository):
        """Test update fails for non-existent driver."""
        mock_repository.find_by_id.return_value = None
        
        with pytest.raises(DriverNotFoundError):
            driver_service.update_driver('invalid_id', {'phone': '1234567890'})
    
    def test_update_recalculates_license_status(self, driver_service, mock_repository, sample_driver_doc):
        """Test license status recalculated on expiry update."""
        old_doc = dict(sample_driver_doc)
        new_expiry = datetime.now() + timedelta(days=15)
        
        mock_repository.find_by_id.return_value = old_doc
        mock_repository.update.return_value = True
        
        updated_doc = dict(old_doc)
        updated_doc['license_expiry'] = new_expiry
        updated_doc['license_alert'] = True
        mock_repository.find_by_id.side_effect = [old_doc, updated_doc]
        
        result = driver_service.update_driver(
            '507f1f77bcf86cd799439011',
            {'license_expiry': new_expiry}
        )
        
        # Update should have been called with new license status
        mock_repository.update.assert_called_once()


class TestDriverServiceDeletion:
    """Test delete_driver method."""
    
    def test_delete_driver_success(self, driver_service, mock_repository, sample_driver_doc):
        """Test successful driver deletion."""
        mock_repository.find_by_id.return_value = sample_driver_doc
        mock_repository.soft_delete.return_value = True
        
        result = driver_service.delete_driver('507f1f77bcf86cd799439011')
        
        assert result is True
    
    def test_delete_driver_not_found(self, driver_service, mock_repository):
        """Test delete fails for non-existent driver."""
        mock_repository.find_by_id.return_value = None
        
        with pytest.raises(DriverNotFoundError):
            driver_service.delete_driver('invalid_id')


class TestDriverServiceLicenseChecks:
    """Test license validation methods."""
    
    def test_check_license_valid(self, driver_service, mock_repository, sample_driver_doc):
        """Test checking valid license."""
        valid_doc = dict(sample_driver_doc)
        valid_doc['license_expired'] = False
        mock_repository.find_by_id.return_value = valid_doc
        
        result = driver_service.check_license_valid('507f1f77bcf86cd799439011')
        
        assert result is True
    
    def test_check_license_expired(self, driver_service, mock_repository, sample_driver_doc):
        """Test checking expired license."""
        expired_doc = dict(sample_driver_doc)
        expired_doc['license_expired'] = True
        mock_repository.find_by_id.return_value = expired_doc
        
        result = driver_service.check_license_valid('507f1f77bcf86cd799439011')
        
        assert result is False
    
    def test_get_expiring_soon(self, driver_service, mock_repository, sample_driver_doc):
        """Test getting drivers with expiring licenses."""
        expiring = dict(sample_driver_doc)
        expiring['license_expiry'] = datetime.now() + timedelta(days=15)
        mock_repository.find_license_alert.return_value = [expiring]
        
        result = driver_service.get_expiring_soon(days_threshold=30)
        
        assert len(result) >= 1
