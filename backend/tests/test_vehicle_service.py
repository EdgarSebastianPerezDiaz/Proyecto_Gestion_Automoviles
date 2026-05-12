"""
Tests for Vehicle Service

Tests service business logic with mocked repository.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock
from bson.objectid import ObjectId

from src.services.vehicle_service import (
    VehicleService,
    VehicleValidationError,
    VehicleNotFoundError,
    VehicleAlreadyExistsError,
    VehicleError,
)


@pytest.fixture
def mock_repository():
    """Create mock vehicle repository."""
    return Mock()


@pytest.fixture
def service(mock_repository):
    """Create vehicle service with mocked repository."""
    return VehicleService(mock_repository)


@pytest.fixture
def sample_vehicle_data():
    """Create sample vehicle data for testing."""
    return {
        "plate": "ABC123",
        "vehicle_type": "truck",
        "brand": "Volvo",
        "model_year": 2020,
        "capacity_tons": 20.0,
        "volume_m3": 50.0,
        "company_id": str(ObjectId()),
        "soat_expiry": datetime.now(timezone.utc) + timedelta(days=60),
        "tech_review_expiry": datetime.now(timezone.utc) + timedelta(days=90),
    }


@pytest.fixture
def sample_vehicle_doc():
    """Create sample vehicle document from database."""
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
        "soat_expiry": datetime.now(timezone.utc) + timedelta(days=60),
        "tech_review_expiry": datetime.now(timezone.utc) + timedelta(days=90),
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


class TestVehicleService:
    """Test vehicle service operations."""
    
    def test_create_vehicle_success(self, service, mock_repository, sample_vehicle_data):
        """Test successful vehicle creation."""
        vehicle_id = str(ObjectId())
        mock_repository.find_by_plate.return_value = None
        mock_repository.insert_one.return_value = vehicle_id
        
        # Create vehicle
        result = service.create_vehicle(sample_vehicle_data)
        
        # Verify
        assert result["_id"] == vehicle_id
        assert result["plate"] == "ABC123"
        assert result["status"] == "available"  # Default status
        assert result["is_active"] is True
        mock_repository.insert_one.assert_called_once()
    
    def test_create_vehicle_normalizes_plate(self, service, mock_repository, sample_vehicle_data):
        """Test that plate is normalized to uppercase."""
        sample_vehicle_data["plate"] = "abc123"
        vehicle_id = str(ObjectId())
        mock_repository.find_by_plate.return_value = None
        mock_repository.insert_one.return_value = vehicle_id
        
        # Create vehicle
        result = service.create_vehicle(sample_vehicle_data)
        
        # Verify plate is uppercase
        assert result["plate"] == "ABC123"
    
    def test_create_vehicle_duplicate_plate(self, service, mock_repository, sample_vehicle_data):
        """Test creation fails for duplicate plate."""
        existing = {"_id": str(ObjectId()), "plate": "ABC123"}
        mock_repository.find_by_plate.return_value = existing
        
        # Try to create
        with pytest.raises(VehicleAlreadyExistsError):
            service.create_vehicle(sample_vehicle_data)
    
    def test_create_vehicle_missing_required_field(self, service, mock_repository, sample_vehicle_data):
        """Test creation fails with missing required field."""
        del sample_vehicle_data["plate"]
        
        # Try to create
        with pytest.raises(VehicleValidationError):
            service.create_vehicle(sample_vehicle_data)
    
    def test_create_vehicle_invalid_vehicle_type(self, service, mock_repository, sample_vehicle_data):
        """Test creation fails with invalid vehicle type."""
        sample_vehicle_data["vehicle_type"] = "invalid_type"
        
        # Try to create
        with pytest.raises(VehicleValidationError):
            service.create_vehicle(sample_vehicle_data)
    
    def test_create_vehicle_invalid_model_year(self, service, mock_repository, sample_vehicle_data):
        """Test creation fails with invalid model year."""
        sample_vehicle_data["model_year"] = 1800
        
        # Try to create
        with pytest.raises(VehicleValidationError):
            service.create_vehicle(sample_vehicle_data)
    
    def test_create_vehicle_invalid_capacity(self, service, mock_repository, sample_vehicle_data):
        """Test creation fails with invalid capacity."""
        sample_vehicle_data["capacity_tons"] = -5
        
        # Try to create
        with pytest.raises(VehicleValidationError):
            service.create_vehicle(sample_vehicle_data)
    
    def test_get_vehicle(self, service, mock_repository, sample_vehicle_doc):
        """Test getting a vehicle by ID."""
        mock_repository.find_by_id.return_value = sample_vehicle_doc
        
        # Get vehicle
        result = service.get_vehicle(sample_vehicle_doc["_id"])
        
        # Verify
        assert result["_id"] == sample_vehicle_doc["_id"]
        assert result["plate"] == "ABC123"
        mock_repository.find_by_id.assert_called_once()
    
    def test_get_vehicle_not_found(self, service, mock_repository):
        """Test getting non-existent vehicle."""
        mock_repository.find_by_id.return_value = None
        
        result = service.get_vehicle("nonexistent")
        assert result is None
    
    def test_get_vehicle_by_plate(self, service, mock_repository, sample_vehicle_doc):
        """Test getting vehicle by plate."""
        mock_repository.find_by_plate.return_value = sample_vehicle_doc
        
        # Get vehicle
        result = service.get_vehicle_by_plate("ABC123")
        
        # Verify
        assert result["plate"] == "ABC123"
        mock_repository.find_by_plate.assert_called_once()
    
    def test_list_vehicles(self, service, mock_repository):
        """Test listing vehicles."""
        vehicles = [
            {"_id": str(ObjectId()), "plate": "ABC123", "is_active": True},
            {"_id": str(ObjectId()), "plate": "XYZ789", "is_active": True},
        ]
        mock_repository.find_many.return_value = vehicles
        
        # List vehicles
        result = service.list_vehicles()
        
        # Verify
        assert len(result) == 2
        mock_repository.find_many.assert_called_once()
    
    def test_list_vehicles_with_status_filter(self, service, mock_repository):
        """Test listing vehicles with status filter."""
        vehicles = [
            {"_id": str(ObjectId()), "plate": "ABC123", "status": "available"},
        ]
        mock_repository.find_many.return_value = vehicles
        
        # List available vehicles
        result = service.list_vehicles(status_filter="available")
        
        # Verify
        assert len(result) == 1
    
    def test_update_vehicle(self, service, mock_repository, sample_vehicle_doc):
        """Test updating a vehicle."""
        updated_doc = sample_vehicle_doc.copy()
        updated_doc["brand"] = "MAN"
        
        mock_repository.find_by_id.return_value = sample_vehicle_doc
        mock_repository.update.return_value = True
        mock_repository.find_by_id.return_value = updated_doc
        
        # Update vehicle
        result = service.update_vehicle(sample_vehicle_doc["_id"], {"brand": "MAN"})
        
        # Verify
        assert result["brand"] == "MAN"
        mock_repository.update.assert_called_once()
    
    def test_update_vehicle_not_found(self, service, mock_repository):
        """Test updating non-existent vehicle."""
        mock_repository.find_by_id.return_value = None
        
        with pytest.raises(VehicleNotFoundError):
            service.update_vehicle("nonexistent", {"brand": "MAN"})
    
    def test_update_vehicle_duplicate_plate(self, service, mock_repository, sample_vehicle_doc):
        """Test updating plate to existing plate fails."""
        existing_vehicle = sample_vehicle_doc.copy()
        other_vehicle = sample_vehicle_doc.copy()
        other_vehicle["_id"] = str(ObjectId())
        
        mock_repository.find_by_id.return_value = existing_vehicle
        mock_repository.find_by_plate.return_value = other_vehicle  # Other vehicle has this plate
        
        # Try to update
        with pytest.raises(VehicleAlreadyExistsError):
            service.update_vehicle(sample_vehicle_doc["_id"], {"plate": "XYZ789"})
    
    def test_delete_vehicle(self, service, mock_repository):
        """Test deleting a vehicle."""
        mock_repository.soft_delete.return_value = True
        
        # Delete vehicle
        result = service.delete_vehicle("vehicle_id")
        
        # Verify
        assert result is True
        mock_repository.soft_delete.assert_called_once()
    
    def test_delete_vehicle_not_found(self, service, mock_repository):
        """Test deleting non-existent vehicle."""
        mock_repository.soft_delete.return_value = False
        
        result = service.delete_vehicle("nonexistent")
        assert result is False
    
    def test_check_availability_available(self, service, mock_repository, sample_vehicle_doc):
        """Test checking availability for available vehicle."""
        mock_repository.find_by_id.return_value = sample_vehicle_doc
        
        # Check availability
        result = service.check_availability(sample_vehicle_doc["_id"])
        
        # Verify
        assert result is True
    
    def test_check_availability_in_trip(self, service, mock_repository, sample_vehicle_doc):
        """Test checking availability for vehicle in trip."""
        doc = sample_vehicle_doc.copy()
        doc["status"] = "in_trip"
        mock_repository.find_by_id.return_value = doc
        
        # Check availability
        result = service.check_availability(sample_vehicle_doc["_id"])
        
        # Verify
        assert result is False
    
    def test_check_availability_inactive(self, service, mock_repository, sample_vehicle_doc):
        """Test checking availability for inactive vehicle."""
        doc = sample_vehicle_doc.copy()
        doc["is_active"] = False
        mock_repository.find_by_id.return_value = doc
        
        # Check availability
        result = service.check_availability(sample_vehicle_doc["_id"])
        
        # Verify
        assert result is False
    
    def test_check_availability_not_found(self, service, mock_repository):
        """Test checking availability for non-existent vehicle."""
        mock_repository.find_by_id.return_value = None
        
        with pytest.raises(VehicleNotFoundError):
            service.check_availability("nonexistent")
    
    def test_update_vehicle_status(self, service, mock_repository, sample_vehicle_doc):
        """Test updating vehicle status."""
        updated_doc = sample_vehicle_doc.copy()
        updated_doc["status"] = "in_trip"
        
        mock_repository.update_status.return_value = True
        mock_repository.find_by_id.return_value = updated_doc
        
        # Update status
        result = service.update_vehicle_status(sample_vehicle_doc["_id"], "in_trip")
        
        # Verify
        assert result["status"] == "in_trip"
        mock_repository.update_status.assert_called_once()
    
    def test_update_vehicle_status_invalid(self, service, mock_repository):
        """Test updating to invalid status fails."""
        with pytest.raises(VehicleValidationError):
            service.update_vehicle_status("vehicle_id", "invalid_status")
    
    def test_get_expiring_documents(self, service, mock_repository):
        """Test getting expiring documents."""
        expiring_soat = [{"_id": str(ObjectId()), "plate": "ABC123"}]
        expiring_tech = [{"_id": str(ObjectId()), "plate": "XYZ789"}]
        
        mock_repository.find_expiring_soat.return_value = expiring_soat
        mock_repository.find_expiring_tech_review.return_value = expiring_tech
        
        # Get expiring documents
        result = service.get_expiring_documents(soat_days=30, tech_days=30)
        
        # Verify
        assert len(result["soat_expiring"]) == 1
        assert len(result["tech_review_expiring"]) == 1
        assert result["soat_threshold_days"] == 30
        assert result["tech_threshold_days"] == 30

