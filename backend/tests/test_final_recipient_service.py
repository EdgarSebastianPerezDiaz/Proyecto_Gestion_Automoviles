"""
Tests for Final Recipients service.
"""
import pytest
from bson import ObjectId
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from src.services.final_recipient_service import (
    FinalRecipientService,
    RecipientNotFoundError,
    ValidationError,
    AlreadyExistsError
)


@pytest.fixture
def mock_repository():
    """Mock FinalRecipientRepository."""
    return MagicMock()


@pytest.fixture
def service(mock_repository):
    """FinalRecipientService instance."""
    return FinalRecipientService(mock_repository)


@pytest.fixture
def sample_data():
    """Sample recipient data."""
    return {
        "name": "ACME Corp",
        "address": "123 Main St",
        "city": "New York",
        "contact_name": "John Doe",
        "phone": "5551234567",
        "email": "info@acme.com"
    }


@pytest.fixture
def sample_recipient(sample_data):
    """Sample recipient document."""
    return {
        "_id": ObjectId(),
        **sample_data,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }


class TestCreateRecipient:
    """Tests for create_recipient method."""
    
    def test_create_recipient_success(self, service, mock_repository, sample_data, sample_recipient):
        """Test successful recipient creation."""
        mock_repository.find_one.return_value = None
        mock_repository.insert_one.return_value = sample_recipient
        
        result = service.create_recipient(sample_data)
        
        assert result["_id"] == sample_recipient["_id"]
        assert result["is_active"] is True
    
    def test_create_recipient_validation_failure(self, service, mock_repository):
        """Test creation fails with invalid data."""
        invalid_data = {"name": "", "email": "invalid"}
        
        with pytest.raises(ValidationError):
            service.create_recipient(invalid_data)
    
    def test_create_recipient_email_already_exists(self, service, mock_repository, sample_data):
        """Test creation fails if email already exists."""
        mock_repository.find_one.return_value = {"_id": ObjectId()}
        
        with pytest.raises(AlreadyExistsError):
            service.create_recipient(sample_data)
    
    def test_create_recipient_normalizes_email(self, service, mock_repository, sample_data):
        """Test that email is normalized (lowercase)."""
        mock_repository.find_one.return_value = None
        mock_repository.insert_one.return_value = {"_id": ObjectId()}
        sample_data["email"] = "Info@ACME.COM"
        
        service.create_recipient(sample_data)
        
        # Check that lowercase email was used
        call_args = mock_repository.insert_one.call_args[0][0]
        assert call_args["email"] == "info@acme.com"


class TestGetRecipient:
    """Tests for get_recipient method."""
    
    def test_get_recipient_success(self, service, mock_repository, sample_recipient):
        """Test successful retrieval."""
        mock_repository.find_by_id.return_value = sample_recipient
        
        result = service.get_recipient(str(sample_recipient["_id"]))
        
        assert result["_id"] == sample_recipient["_id"]
    
    def test_get_recipient_not_found(self, service, mock_repository):
        """Test retrieval of nonexistent recipient."""
        mock_repository.find_by_id.return_value = None
        
        with pytest.raises(RecipientNotFoundError):
            service.get_recipient(str(ObjectId()))
    
    def test_get_inactive_recipient_fails(self, service, mock_repository, sample_recipient):
        """Test that inactive recipients cannot be accessed."""
        sample_recipient["is_active"] = False
        mock_repository.find_by_id.return_value = sample_recipient
        
        with pytest.raises(RecipientNotFoundError):
            service.get_recipient(str(sample_recipient["_id"]))


class TestListRecipients:
    """Tests for list_recipients method."""
    
    def test_list_recipients_success(self, service, mock_repository, sample_recipient):
        """Test successful listing."""
        mock_repository.find_many.return_value = [sample_recipient]
        
        result = service.list_recipients(skip=0, limit=100)
        
        assert len(result) == 1
        assert result[0]["_id"] == sample_recipient["_id"]
    
    def test_list_recipients_with_pagination(self, service, mock_repository):
        """Test with pagination parameters."""
        mock_repository.find_many.return_value = []
        
        service.list_recipients(skip=10, limit=50)
        
        mock_repository.find_many.assert_called_once_with(
            {"is_active": True},
            skip=10,
            limit=50
        )


class TestSearchRecipients:
    """Tests for search_recipients_by_name method."""
    
    def test_search_recipients_success(self, service, mock_repository, sample_recipient):
        """Test successful search."""
        mock_repository.find_by_name.return_value = [sample_recipient]
        
        result = service.search_recipients_by_name("acme", limit=10)
        
        assert len(result) == 1
        mock_repository.find_by_name.assert_called_once_with("acme", limit=10)
    
    def test_search_recipients_min_length(self, service, mock_repository):
        """Test that search name must be at least 2 characters."""
        with pytest.raises(ValidationError):
            service.search_recipients_by_name("a")


class TestUpdateRecipient:
    """Tests for update_recipient method."""
    
    def test_update_recipient_success(self, service, mock_repository, sample_recipient, sample_data):
        """Test successful update."""
        mock_repository.find_by_id.return_value = sample_recipient
        update_data = {"name": "NEW NAME", "city": "Boston"}
        mock_repository.find_by_id.side_effect = [sample_recipient, {**sample_recipient, **update_data}]
        
        result = service.update_recipient(str(sample_recipient["_id"]), update_data)
        
        assert result is not None
    
    def test_update_recipient_not_found(self, service, mock_repository):
        """Test update of nonexistent recipient."""
        mock_repository.find_by_id.return_value = None
        
        with pytest.raises(RecipientNotFoundError):
            service.update_recipient(str(ObjectId()), {"name": "NEW"})
    
    def test_update_recipient_email_conflict(self, service, mock_repository, sample_recipient):
        """Test update fails if new email already exists."""
        mock_repository.find_by_id.return_value = sample_recipient
        mock_repository.find_one.return_value = {"_id": ObjectId()}  # Email exists for another recipient
        
        with pytest.raises(AlreadyExistsError):
            service.update_recipient(
                str(sample_recipient["_id"]),
                {"email": "existing@example.com"}
            )


class TestDeleteRecipient:
    """Tests for delete_recipient method."""
    
    def test_delete_recipient_success(self, service, mock_repository, sample_recipient):
        """Test successful soft delete."""
        mock_repository.find_by_id.return_value = sample_recipient
        mock_repository.soft_delete.return_value = True
        
        result = service.delete_recipient(str(sample_recipient["_id"]))
        
        assert result is True
        mock_repository.soft_delete.assert_called_once()
    
    def test_delete_recipient_not_found(self, service, mock_repository):
        """Test deletion of nonexistent recipient."""
        mock_repository.find_by_id.return_value = None
        
        with pytest.raises(RecipientNotFoundError):
            service.delete_recipient(str(ObjectId()))


class TestCountActive:
    """Tests for count_active method."""
    
    def test_count_active_recipients(self, service, mock_repository):
        """Test counting active recipients."""
        mock_repository.collection.count_documents.return_value = 42
        
        result = service.count_active()
        
        assert result == 42
        mock_repository.collection.count_documents.assert_called_once_with({"is_active": True})

