"""
Tests for Cargo Types service.
"""
import pytest
from bson import ObjectId
from unittest.mock import MagicMock
from datetime import datetime, timezone
from src.services.cargo_type_service import (
    CargoTypeService,
    CargoTypeNotFoundError,
    ValidationError,
    AlreadyExistsError
)


@pytest.fixture
def mock_repository():
    """Mock CargoTypeRepository."""
    return MagicMock()


@pytest.fixture
def service(mock_repository):
    """CargoTypeService instance."""
    return CargoTypeService(mock_repository)


@pytest.fixture
def sample_data():
    """Sample cargo type data."""
    return {
        "name": "Electronics",
        "description": "Electronic equipment",
        "price_per_ton": 150.00,
        "requires_special_permit": True
    }


@pytest.fixture
def sample_cargo_type(sample_data):
    """Sample cargo type document."""
    return {
        "_id": ObjectId(),
        **sample_data,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }


class TestCreateCargoType:
    """Tests for create_cargo_type method."""
    
    def test_create_cargo_type_success(self, service, mock_repository, sample_data, sample_cargo_type):
        """Test successful cargo type creation."""
        mock_repository.find_by_name.return_value = None
        mock_repository.insert_one.return_value = sample_cargo_type
        
        result = service.create_cargo_type(sample_data)
        
        assert result["_id"] == sample_cargo_type["_id"]
        assert result["is_active"] is True
    
    def test_create_cargo_type_validation_failure(self, service, mock_repository):
        """Test creation fails with invalid data."""
        invalid_data = {"name": "", "price_per_ton": -10}
        
        with pytest.raises(ValidationError):
            service.create_cargo_type(invalid_data)
    
    def test_create_cargo_type_name_already_exists(self, service, mock_repository, sample_data):
        """Test creation fails if name already exists."""
        mock_repository.find_by_name.return_value = {"_id": ObjectId()}
        
        with pytest.raises(AlreadyExistsError):
            service.create_cargo_type(sample_data)
    
    def test_create_cargo_type_price_validation(self, service, mock_repository):
        """Test that price must be positive."""
        invalid_data = {"name": "Test", "price_per_ton": -50}
        
        with pytest.raises(ValidationError):
            service.create_cargo_type(invalid_data)


class TestGetCargoType:
    """Tests for get_cargo_type method."""
    
    def test_get_cargo_type_success(self, service, mock_repository, sample_cargo_type):
        """Test successful retrieval."""
        mock_repository.find_by_id.return_value = sample_cargo_type
        
        result = service.get_cargo_type(str(sample_cargo_type["_id"]))
        
        assert result["_id"] == sample_cargo_type["_id"]
    
    def test_get_cargo_type_not_found(self, service, mock_repository):
        """Test retrieval of nonexistent cargo type."""
        mock_repository.find_by_id.return_value = None
        
        with pytest.raises(CargoTypeNotFoundError):
            service.get_cargo_type(str(ObjectId()))
    
    def test_get_inactive_cargo_type_fails(self, service, mock_repository, sample_cargo_type):
        """Test that inactive cargo types cannot be accessed."""
        sample_cargo_type["is_active"] = False
        mock_repository.find_by_id.return_value = sample_cargo_type
        
        with pytest.raises(CargoTypeNotFoundError):
            service.get_cargo_type(str(sample_cargo_type["_id"]))


class TestListActiveCargoTypes:
    """Tests for list_active_cargo_types method."""
    
    def test_list_active_cargo_types_success(self, service, mock_repository, sample_cargo_type):
        """Test successful listing."""
        mock_repository.find_active.return_value = [sample_cargo_type]
        
        result = service.list_active_cargo_types(skip=0, limit=100)
        
        assert len(result) == 1
        assert result[0]["_id"] == sample_cargo_type["_id"]
    
    def test_list_active_cargo_types_with_pagination(self, service, mock_repository):
        """Test with pagination parameters."""
        mock_repository.find_active.return_value = []
        
        service.list_active_cargo_types(skip=10, limit=50)
        
        mock_repository.find_active.assert_called_once_with(limit=50, skip=10)


class TestSearchCargoTypeByName:
    """Tests for search_cargo_type_by_name method."""
    
    def test_search_cargo_type_success(self, service, mock_repository, sample_cargo_type):
        """Test successful search."""
        mock_repository.find_by_name.return_value = sample_cargo_type
        
        result = service.search_cargo_type_by_name("electronics")
        
        assert result["_id"] == sample_cargo_type["_id"]
    
    def test_search_cargo_type_not_found(self, service, mock_repository):
        """Test search when cargo type not found."""
        mock_repository.find_by_name.return_value = None
        
        with pytest.raises(CargoTypeNotFoundError):
            service.search_cargo_type_by_name("nonexistent")
    
    def test_search_cargo_type_min_length(self, service, mock_repository):
        """Test that search name must be at least 2 characters."""
        with pytest.raises(ValidationError):
            service.search_cargo_type_by_name("a")


class TestUpdateCargoType:
    """Tests for update_cargo_type method."""
    
    def test_update_cargo_type_success(self, service, mock_repository, sample_cargo_type):
        """Test successful update."""
        mock_repository.find_by_id.return_value = sample_cargo_type
        update_data = {"price_per_ton": 200.00}
        mock_repository.find_by_id.side_effect = [sample_cargo_type, {**sample_cargo_type, **update_data}]
        
        result = service.update_cargo_type(str(sample_cargo_type["_id"]), update_data)
        
        assert result is not None
    
    def test_update_cargo_type_not_found(self, service, mock_repository):
        """Test update of nonexistent cargo type."""
        mock_repository.find_by_id.return_value = None
        
        with pytest.raises(CargoTypeNotFoundError):
            service.update_cargo_type(str(ObjectId()), {"price_per_ton": 100})
    
    def test_update_cargo_type_name_conflict(self, service, mock_repository, sample_cargo_type):
        """Test update fails if new name already exists."""
        mock_repository.find_by_id.return_value = sample_cargo_type
        mock_repository.find_one.return_value = {"_id": ObjectId()}  # Name exists for another
        
        with pytest.raises(AlreadyExistsError):
            service.update_cargo_type(
                str(sample_cargo_type["_id"]),
                {"name": "Existing Name"}
            )


class TestDeleteCargoType:
    """Tests for delete_cargo_type method."""
    
    def test_delete_cargo_type_success(self, service, mock_repository, sample_cargo_type):
        """Test successful soft delete."""
        mock_repository.find_by_id.return_value = sample_cargo_type
        mock_repository.soft_delete.return_value = True
        
        result = service.delete_cargo_type(str(sample_cargo_type["_id"]))
        
        assert result is True
        mock_repository.soft_delete.assert_called_once()
    
    def test_delete_cargo_type_not_found(self, service, mock_repository):
        """Test deletion of nonexistent cargo type."""
        mock_repository.find_by_id.return_value = None
        
        with pytest.raises(CargoTypeNotFoundError):
            service.delete_cargo_type(str(ObjectId()))


class TestCountActive:
    """Tests for count_active method."""
    
    def test_count_active_cargo_types(self, service, mock_repository):
        """Test counting active cargo types."""
        mock_repository.collection.count_documents.return_value = 25
        
        result = service.count_active()
        
        assert result == 25
        mock_repository.collection.count_documents.assert_called_once_with({"is_active": True})


class TestGetPricingByName:
    """Tests for get_pricing_by_name method."""
    
    def test_get_pricing_by_name_success(self, service, mock_repository, sample_cargo_type):
        """Test retrieving price by name."""
        mock_repository.find_by_name.return_value = sample_cargo_type
        
        result = service.get_pricing_by_name("electronics")
        
        assert result == 150.00

