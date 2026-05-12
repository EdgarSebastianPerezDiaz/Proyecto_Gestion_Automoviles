"""
Tests for Trip Statuses service.
"""
import pytest
from bson import ObjectId
from unittest.mock import MagicMock
from src.services.trip_status_service import (
    TripStatusService,
    TripStatusNotFoundError,
    ValidationError,
    StatusInUseError,
    AlreadyExistsError
)


@pytest.fixture
def mock_repository():
    """Mock TripStatusRepository."""
    return MagicMock()


@pytest.fixture
def mock_trips_collection():
    """Mock trips collection."""
    return MagicMock()


@pytest.fixture
def service(mock_repository):
    """TripStatusService instance."""
    return TripStatusService(mock_repository)


@pytest.fixture
def service_with_trips(mock_repository, mock_trips_collection):
    """TripStatusService with trips collection."""
    return TripStatusService(mock_repository, mock_trips_collection)


@pytest.fixture
def sample_data():
    """Sample trip status data."""
    return {
        "code": "scheduled",
        "label": "Scheduled",
        "order": 1,
        "is_terminal": False
    }


@pytest.fixture
def sample_trip_status(sample_data):
    """Sample trip status document."""
    return {
        "_id": ObjectId(),
        **sample_data
    }


class TestCreateTripStatus:
    """Tests for create_trip_status method."""
    
    def test_create_trip_status_success(self, service, mock_repository, sample_data, sample_trip_status):
        """Test successful trip status creation."""
        mock_repository.check_code_exists.return_value = False
        mock_repository.get_next_order_value.return_value = 1
        mock_repository.insert_one.return_value = sample_trip_status
        
        result = service.create_trip_status(sample_data)
        
        assert result["_id"] == sample_trip_status["_id"]
    
    def test_create_trip_status_validation_failure(self, service, mock_repository):
        """Test creation fails with invalid data."""
        invalid_data = {"code": "", "label": ""}
        
        with pytest.raises(ValidationError):
            service.create_trip_status(invalid_data)
    
    def test_create_trip_status_code_already_exists(self, service, mock_repository, sample_data):
        """Test creation fails if code already exists."""
        mock_repository.check_code_exists.return_value = True
        
        with pytest.raises(AlreadyExistsError):
            service.create_trip_status(sample_data)
    
    def test_create_trip_status_code_format(self, service, mock_repository):
        """Test code validation (lowercase alphanumeric + underscore)."""
        invalid_code = {"code": "INVALID-CODE", "label": "Test"}
        
        with pytest.raises(ValidationError):
            service.create_trip_status(invalid_code)


class TestGetTripStatus:
    """Tests for get_trip_status method."""
    
    def test_get_trip_status_success(self, service, mock_repository, sample_trip_status):
        """Test successful retrieval."""
        mock_repository.find_by_id.return_value = sample_trip_status
        
        result = service.get_trip_status(str(sample_trip_status["_id"]))
        
        assert result["_id"] == sample_trip_status["_id"]
    
    def test_get_trip_status_not_found(self, service, mock_repository):
        """Test retrieval of nonexistent status."""
        mock_repository.find_by_id.return_value = None
        
        with pytest.raises(TripStatusNotFoundError):
            service.get_trip_status(str(ObjectId()))


class TestGetTripStatusByCode:
    """Tests for get_trip_status_by_code method."""
    
    def test_get_trip_status_by_code_success(self, service, mock_repository, sample_trip_status):
        """Test successful retrieval by code."""
        mock_repository.find_by_code.return_value = sample_trip_status
        
        result = service.get_trip_status_by_code("scheduled")
        
        assert result["code"] == "scheduled"
    
    def test_get_trip_status_by_code_not_found(self, service, mock_repository):
        """Test retrieval with nonexistent code."""
        mock_repository.find_by_code.return_value = None
        
        with pytest.raises(TripStatusNotFoundError):
            service.get_trip_status_by_code("nonexistent")
    
    def test_get_trip_status_by_code_empty_code(self, service, mock_repository):
        """Test retrieval with empty code."""
        with pytest.raises(ValidationError):
            service.get_trip_status_by_code("")


class TestListAllStatuses:
    """Tests for list_all_statuses method."""
    
    def test_list_all_statuses_success(self, service, mock_repository, sample_trip_status):
        """Test successful listing."""
        mock_repository.find_all.return_value = [sample_trip_status]
        
        result = service.list_all_statuses(skip=0, limit=100)
        
        assert len(result) == 1
        assert result[0]["_id"] == sample_trip_status["_id"]
    
    def test_list_all_statuses_with_pagination(self, service, mock_repository):
        """Test with pagination parameters."""
        mock_repository.find_all.return_value = []
        
        service.list_all_statuses(skip=10, limit=50)
        
        mock_repository.find_all.assert_called_once_with(skip=10, limit=50)


class TestListNonTerminalStatuses:
    """Tests for list_non_terminal_statuses method."""
    
    def test_list_non_terminal_statuses(self, service, mock_repository, sample_trip_status):
        """Test listing non-terminal statuses."""
        mock_repository.find_non_terminal.return_value = [sample_trip_status]
        
        result = service.list_non_terminal_statuses()
        
        assert len(result) == 1
        assert result[0]["is_terminal"] is False


class TestUpdateTripStatus:
    """Tests for update_trip_status method."""
    
    def test_update_trip_status_success(self, service, mock_repository, sample_trip_status):
        """Test successful update."""
        mock_repository.find_by_id.return_value = sample_trip_status
        update_data = {"label": "NEW LABEL"}
        mock_repository.find_by_id.side_effect = [sample_trip_status, {**sample_trip_status, **update_data}]
        
        result = service.update_trip_status(str(sample_trip_status["_id"]), update_data)
        
        assert result is not None
    
    def test_update_trip_status_not_found(self, service, mock_repository):
        """Test update of nonexistent status."""
        mock_repository.find_by_id.return_value = None
        
        with pytest.raises(TripStatusNotFoundError):
            service.update_trip_status(str(ObjectId()), {"label": "NEW"})
    
    def test_update_trip_status_code_conflict(self, service, mock_repository, sample_trip_status):
        """Test update fails if new code already exists."""
        mock_repository.find_by_id.return_value = sample_trip_status
        mock_repository.check_code_exists.return_value = True
        
        with pytest.raises(AlreadyExistsError):
            service.update_trip_status(
                str(sample_trip_status["_id"]),
                {"code": "existing_code"}
            )


class TestDeleteTripStatus:
    """Tests for delete_trip_status method."""
    
    def test_delete_trip_status_success(self, service, mock_repository, sample_trip_status):
        """Test successful deletion."""
        mock_repository.find_by_id.return_value = sample_trip_status
        mock_repository.delete_one.return_value = True
        
        result = service.delete_trip_status(str(sample_trip_status["_id"]))
        
        assert result is True
    
    def test_delete_trip_status_not_found(self, service, mock_repository):
        """Test deletion of nonexistent status."""
        mock_repository.find_by_id.return_value = None
        
        with pytest.raises(TripStatusNotFoundError):
            service.delete_trip_status(str(ObjectId()))
    
    def test_delete_trip_status_in_use(self, service_with_trips, mock_repository, sample_trip_status):
        """Test deletion fails if status is used in trips."""
        mock_repository.find_by_id.return_value = sample_trip_status
        service_with_trips.trips_collection.count_documents.return_value = 5
        
        with pytest.raises(StatusInUseError):
            service_with_trips.delete_trip_status(str(sample_trip_status["_id"]))


class TestCountAll:
    """Tests for count_all method."""
    
    def test_count_all_statuses(self, service, mock_repository):
        """Test counting all statuses."""
        mock_repository.collection.count_documents.return_value = 4
        
        result = service.count_all()
        
        assert result == 4
        mock_repository.collection.count_documents.assert_called_once_with({})


class TestVerifyStatusExists:
    """Tests for verify_status_exists method."""
    
    def test_verify_status_exists_true(self, service, mock_repository, sample_trip_status):
        """Test verifying existing status."""
        mock_repository.find_by_code.return_value = sample_trip_status
        
        result = service.verify_status_exists("scheduled")
        
        assert result is True
    
    def test_verify_status_exists_false(self, service, mock_repository):
        """Test verifying nonexistent status."""
        mock_repository.find_by_code.return_value = None
        
        result = service.verify_status_exists("nonexistent")
        
        assert result is False
