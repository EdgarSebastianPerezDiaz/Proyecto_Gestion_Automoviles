"""
Tests for Vehicle Repository

Tests repository methods with mongomock database backend.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from mongomock import MongoClient
from bson.objectid import ObjectId

from src.repositories.vehicle_repository import VehicleRepository
from src.infrastructure.database import RepositoryError


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
def repository(mock_db_connection):
    """Create vehicle repository."""
    return VehicleRepository(mock_db_connection)


@pytest.fixture
def sample_vehicle():
    """Create sample vehicle data."""
    return {
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


class TestVehicleRepository:
    """Test vehicle repository operations."""
    
    def test_find_by_plate(self, repository, sample_vehicle):
        """Test finding vehicle by plate."""
        # Insert sample vehicle
        vehicle_id = repository.insert_one(sample_vehicle)
        
        # Find by plate
        found = repository.find_by_plate("ABC123")
        assert found is not None
        assert found["plate"] == "ABC123"
        assert found["_id"] == vehicle_id
    
    def test_find_by_plate_case_insensitive(self, repository, sample_vehicle):
        """Test plate search is case-insensitive."""
        repository.insert_one(sample_vehicle)
        
        # Should find with lowercase
        found = repository.find_by_plate("abc123")
        assert found is not None
        assert found["plate"] == "ABC123"
    
    def test_find_by_plate_not_found(self, repository):
        """Test finding non-existent plate."""
        found = repository.find_by_plate("XYZ999")
        assert found is None
    
    def test_find_by_company(self, repository):
        """Test finding vehicles by company."""
        company_id = str(ObjectId())
        
        # Insert multiple vehicles for same company
        vehicle1 = {
            "plate": "ABC123",
            "vehicle_type": "truck",
            "brand": "Volvo",
            "model_year": 2020,
            "capacity_tons": 20.0,
            "status": "available",
            "company_id": company_id,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        vehicle2 = {
            "plate": "XYZ789",
            "vehicle_type": "trailer",
            "brand": "Wabash",
            "model_year": 2019,
            "capacity_tons": 30.0,
            "status": "in_trip",
            "company_id": company_id,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        repository.insert_one(vehicle1)
        repository.insert_one(vehicle2)
        
        # Find by company
        found = repository.find_by_company(company_id, active_only=True)
        assert len(found) == 2
    
    def test_find_by_company_active_only(self, repository):
        """Test finding only active vehicles by company."""
        company_id = str(ObjectId())
        
        # Insert active and inactive vehicles
        active_vehicle = {
            "plate": "ABC123",
            "vehicle_type": "truck",
            "brand": "Volvo",
            "model_year": 2020,
            "capacity_tons": 20.0,
            "status": "available",
            "company_id": company_id,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        inactive_vehicle = {
            "plate": "XYZ789",
            "vehicle_type": "trailer",
            "brand": "Wabash",
            "model_year": 2019,
            "capacity_tons": 30.0,
            "status": "inactive",
            "company_id": company_id,
            "is_active": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        repository.insert_one(active_vehicle)
        repository.insert_one(inactive_vehicle)
        
        # Find active only
        found = repository.find_by_company(company_id, active_only=True)
        assert len(found) == 1
        assert found[0]["is_active"] is True
    
    def test_find_available(self, repository):
        """Test finding available vehicles."""
        # Insert multiple vehicles with different statuses
        available_vehicle = {
            "plate": "ABC123",
            "vehicle_type": "truck",
            "brand": "Volvo",
            "model_year": 2020,
            "capacity_tons": 20.0,
            "status": "available",
            "company_id": str(ObjectId()),
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        in_trip_vehicle = {
            "plate": "XYZ789",
            "vehicle_type": "trailer",
            "brand": "Wabash",
            "model_year": 2019,
            "capacity_tons": 30.0,
            "status": "in_trip",
            "company_id": str(ObjectId()),
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        repository.insert_one(available_vehicle)
        repository.insert_one(in_trip_vehicle)
        
        # Find available
        found = repository.find_available()
        assert len(found) == 1
        assert found[0]["status"] == "available"
    
    def test_update_status(self, repository, sample_vehicle):
        """Test updating vehicle status."""
        vehicle_id = repository.insert_one(sample_vehicle)
        
        # Update status
        success = repository.update_status(vehicle_id, "in_trip")
        assert success is True
        
        # Verify update
        updated = repository.find_by_id(vehicle_id)
        assert updated["status"] == "in_trip"
    
    def test_update_status_not_found(self, repository):
        """Test updating status for non-existent vehicle."""
        fake_id = str(ObjectId())
        success = repository.update_status(fake_id, "in_trip")
        assert success is False
    
    def test_soft_delete(self, repository, sample_vehicle):
        """Test soft delete vehicle."""
        vehicle_id = repository.insert_one(sample_vehicle)
        
        # Soft delete
        success = repository.soft_delete(vehicle_id)
        assert success is True
        
        # Verify is_active is False
        deleted = repository.find_by_id(vehicle_id)
        assert deleted["is_active"] is False
    
    def test_find_expiring_soat(self, repository):
        """Test finding vehicles with expiring SOAT."""
        today = datetime.now(timezone.utc)
        
        # Vehicle with SOAT expiring in 15 days
        expiring_vehicle = {
            "plate": "ABC123",
            "vehicle_type": "truck",
            "brand": "Volvo",
            "model_year": 2020,
            "capacity_tons": 20.0,
            "status": "available",
            "company_id": str(ObjectId()),
            "soat_expiry": today + timedelta(days=15),
            "is_active": True,
            "created_at": today,
            "updated_at": today,
        }
        
        # Vehicle with SOAT expiring in 60 days (beyond threshold)
        far_expiry = {
            "plate": "XYZ789",
            "vehicle_type": "trailer",
            "brand": "Wabash",
            "model_year": 2019,
            "capacity_tons": 30.0,
            "status": "available",
            "company_id": str(ObjectId()),
            "soat_expiry": today + timedelta(days=60),
            "is_active": True,
            "created_at": today,
            "updated_at": today,
        }
        
        repository.insert_one(expiring_vehicle)
        repository.insert_one(far_expiry)
        
        # Find expiring within 30 days
        expiring = repository.find_expiring_soat(days_threshold=30)
        assert len(expiring) == 1
        assert expiring[0]["plate"] == "ABC123"
    
    def test_find_expiring_tech_review(self, repository):
        """Test finding vehicles with expiring tech review."""
        today = datetime.now(timezone.utc)
        
        # Vehicle with tech review expiring in 20 days
        expiring_vehicle = {
            "plate": "ABC123",
            "vehicle_type": "truck",
            "brand": "Volvo",
            "model_year": 2020,
            "capacity_tons": 20.0,
            "status": "available",
            "company_id": str(ObjectId()),
            "tech_review_expiry": today + timedelta(days=20),
            "is_active": True,
            "created_at": today,
            "updated_at": today,
        }
        
        repository.insert_one(expiring_vehicle)
        
        # Find expiring within 30 days
        expiring = repository.find_expiring_tech_review(days_threshold=30)
        assert len(expiring) == 1
        assert expiring[0]["plate"] == "ABC123"

