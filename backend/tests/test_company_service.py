"""
Tests for CompanyService - business logic layer
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch
from mongomock import MongoClient as MockMongoClient

from src.services.company_service import (
    CompanyService,
    CompanyError,
    CompanyValidationError,
    CompanyNotFoundError,
    CompanyAlreadyExistsError,
)
from src.repositories.company_repository import CompanyRepository, RepositoryError
from src.infrastructure.database import MongoDBConnection


@pytest.fixture
def mock_connection():
    """Create a mock MongoDB connection using mongomock."""
    # Reset singleton before creating new connection
    MongoDBConnection._instance = None
    
    # Patch MongoClient to use mongomock
    with patch('src.infrastructure.database.MongoClient', MockMongoClient):
        connection = MongoDBConnection()
        connection.client = MockMongoClient()
        connection.db = connection.client.test_db
        connection._initialized = True
        connection._create_indexes()
        
        yield connection
        
        # Cleanup
        MongoDBConnection._instance = None


@pytest.fixture
def company_repository(mock_connection):
    """Provide a real CompanyRepository instance with mongomock."""
    return CompanyRepository(mock_connection)


@pytest.fixture
def company_service(company_repository):
    """Provide a CompanyService instance."""
    return CompanyService(company_repository)


@pytest.fixture
def valid_company_data():
    """Provide valid company data for creation."""
    return {
        "nit": "123456789-0",
        "legal_name": "Acme Transport Company",
        "address": "123 Main St",
        "city": "Bogotá",
        "phone": "+57 1 234 5678",
        "email": "info@acme.com",
        "trade_name": "Acme Logistics",
        "contact_name": "John Doe",
    }


class TestCompanyServiceValidation:
    """Test suite for company data validation."""
    
    def test_validate_missing_required_fields(self, company_service):
        """Test validation fails for missing required fields."""
        invalid_data = {"nit": "123456789-0"}
        
        with pytest.raises(CompanyValidationError) as exc_info:
            company_service._validate_company_data(invalid_data)
        
        assert "Missing required field" in str(exc_info.value)
    
    def test_validate_invalid_nit_format(self, company_service):
        """Test validation fails for invalid NIT format."""
        invalid_data = {
            "nit": "12345",  # Too short
            "legal_name": "Company",
            "address": "Address",
            "city": "City",
            "phone": "1234567890",
            "email": "test@example.com",
        }
        
        with pytest.raises(CompanyValidationError) as exc_info:
            company_service._validate_company_data(invalid_data)
        
        assert "Invalid NIT format" in str(exc_info.value)
    
    def test_validate_invalid_email_format(self, company_service):
        """Test validation fails for invalid email format."""
        invalid_data = {
            "nit": "123456789-0",
            "legal_name": "Company",
            "address": "Address",
            "city": "City",
            "phone": "1234567890",
            "email": "notvalidemail",  # Missing @ or .
        }
        
        with pytest.raises(CompanyValidationError) as exc_info:
            company_service._validate_company_data(invalid_data)
        
        assert "Invalid email format" in str(exc_info.value)
    
    def test_validate_invalid_phone_format(self, company_service):
        """Test validation fails for invalid phone format."""
        invalid_data = {
            "nit": "123456789-0",
            "legal_name": "Company",
            "address": "Address",
            "city": "City",
            "phone": "123",  # Too short
            "email": "test@example.com",
        }
        
        with pytest.raises(CompanyValidationError) as exc_info:
            company_service._validate_company_data(invalid_data)
        
        assert "Invalid phone format" in str(exc_info.value)
    
    def test_validate_nit_with_dots(self, company_service):
        """Test validation accepts NIT with dots."""
        valid_data = {
            "nit": "123.456.789-0",  # With dots
            "legal_name": "Company",
            "address": "Address",
            "city": "City",
            "phone": "1234567890",
            "email": "test@example.com",
        }
        
        # Should not raise
        company_service._validate_company_data(valid_data)
    
    def test_validate_nit_without_dash(self, company_service):
        """Test validation accepts NIT without dash."""
        valid_data = {
            "nit": "1234567890",  # Without dash
            "legal_name": "Company",
            "address": "Address",
            "city": "City",
            "phone": "1234567890",
            "email": "test@example.com",
        }
        
        # Should not raise
        company_service._validate_company_data(valid_data)


class TestCompanyServiceCreation:
    """Test suite for company creation."""
    
    def test_create_company_success(self, company_service, valid_company_data):
        """Test successful company creation."""
        company = company_service.create_company(valid_company_data)
        
        assert company is not None
        assert company["_id"] is not None
        assert company["nit"] == "123456789-0"
        assert company["legal_name"] == "Acme Transport Company"
        assert company["is_active"] is True
    
    def test_create_company_normalizes_nit(self, company_service, valid_company_data):
        """Test that creation normalizes NIT format."""
        valid_company_data["nit"] = "123.456.789-0"  # With dots
        company = company_service.create_company(valid_company_data)
        
        assert company["nit"] == "123456789-0"  # Normalized to standard format
    
    def test_create_company_duplicate_nit(self, company_service, valid_company_data):
        """Test creation fails with duplicate NIT."""
        # Create first company
        company_service.create_company(valid_company_data)
        
        # Attempt to create duplicate
        with pytest.raises(CompanyAlreadyExistsError) as exc_info:
            company_service.create_company(valid_company_data)
        
        assert "already exists" in str(exc_info.value)
    
    def test_create_company_duplicate_email(self, company_service, valid_company_data):
        """Test creation fails with duplicate email."""
        # Create first company
        company_service.create_company(valid_company_data)
        
        # Attempt to create with same email but different NIT
        company_data2 = valid_company_data.copy()
        company_data2["nit"] = "987654321-0"
        
        with pytest.raises(CompanyAlreadyExistsError) as exc_info:
            company_service.create_company(company_data2)
        
        assert "already exists" in str(exc_info.value)
    
    def test_create_company_email_normalized(self, company_service, valid_company_data):
        """Test that email is normalized to lowercase."""
        valid_company_data["email"] = "INFO@ACME.COM"
        company = company_service.create_company(valid_company_data)
        
        assert company["email"] == "info@acme.com"


class TestCompanyServiceRetrieval:
    """Test suite for company retrieval."""
    
    def test_get_company_success(self, company_service, valid_company_data):
        """Test successful company retrieval by ID."""
        created = company_service.create_company(valid_company_data)
        retrieved = company_service.get_company(created["_id"])
        
        assert retrieved is not None
        assert retrieved["_id"] == created["_id"]
        assert retrieved["nit"] == created["nit"]
    
    def test_get_company_not_found(self, company_service):
        """Test retrieval fails for nonexistent company."""
        with pytest.raises(CompanyNotFoundError):
            company_service.get_company("999999999999999999999999")
    
    def test_get_company_by_nit_success(self, company_service, valid_company_data):
        """Test successful retrieval by NIT."""
        created = company_service.create_company(valid_company_data)
        retrieved = company_service.get_company_by_nit("123456789-0")
        
        assert retrieved is not None
        assert retrieved["nit"] == "123456789-0"
    
    def test_get_company_by_nit_not_found(self, company_service):
        """Test retrieval by NIT not found."""
        retrieved = company_service.get_company_by_nit("999999999-9")
        assert retrieved is None
    
    def test_list_companies_active_only(self, company_service, valid_company_data):
        """Test listing only active companies."""
        # Create active company
        company_service.create_company(valid_company_data)
        
        # Create and soft-delete another company
        data2 = valid_company_data.copy()
        data2["nit"] = "987654321-0"
        data2["email"] = "other@acme.com"
        created2 = company_service.create_company(data2)
        company_service.delete_company(created2["_id"])
        
        # List active only
        companies = company_service.list_companies(active_only=True)
        assert len(companies) == 1
        assert companies[0]["is_active"] is True
    
    def test_list_companies_all(self, company_service, valid_company_data):
        """Test listing all companies including inactive."""
        # Create active company
        company_service.create_company(valid_company_data)
        
        # Create and soft-delete another
        data2 = valid_company_data.copy()
        data2["nit"] = "987654321-0"
        data2["email"] = "other@acme.com"
        created2 = company_service.create_company(data2)
        company_service.delete_company(created2["_id"])
        
        # List all
        companies = company_service.list_companies(active_only=False)
        assert len(companies) == 2
    
    def test_list_companies_pagination(self, company_service, valid_company_data):
        """Test company listing pagination."""
        # Create 5 companies
        for i in range(5):
            data = valid_company_data.copy()
            data["nit"] = f"12345678{i}-0"
            data["email"] = f"company{i}@acme.com"
            company_service.create_company(data)
        
        # Test pagination
        page1 = company_service.list_companies(limit=2, skip=0)
        page2 = company_service.list_companies(limit=2, skip=2)
        
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0]["_id"] != page2[0]["_id"]


class TestCompanyServiceUpdate:
    """Test suite for company updates."""
    
    def test_update_company_success(self, company_service, valid_company_data):
        """Test successful company update."""
        created = company_service.create_company(valid_company_data)
        
        updated = company_service.update_company(created["_id"], {
            "legal_name": "New Legal Name"
        })
        
        assert updated["legal_name"] == "New Legal Name"
        assert updated["nit"] == created["nit"]  # Unchanged
    
    def test_update_company_not_found(self, company_service):
        """Test update fails for nonexistent company."""
        with pytest.raises(CompanyNotFoundError):
            company_service.update_company("999999999999999999999999", {
                "legal_name": "New Name"
            })
    
    def test_update_company_invalid_nit(self, company_service, valid_company_data):
        """Test update fails with invalid NIT format."""
        created = company_service.create_company(valid_company_data)
        
        with pytest.raises(CompanyValidationError):
            company_service.update_company(created["_id"], {
                "nit": "invalid"
            })
    
    def test_update_company_nit_duplicate(self, company_service, valid_company_data):
        """Test update fails when NIT conflicts with another company."""
        # Create two companies
        company1 = company_service.create_company(valid_company_data)
        
        data2 = valid_company_data.copy()
        data2["nit"] = "987654321-0"
        data2["email"] = "other@acme.com"
        company2 = company_service.create_company(data2)
        
        # Attempt to update company2's NIT to company1's NIT
        with pytest.raises(CompanyValidationError):
            company_service.update_company(company2["_id"], {
                "nit": "123456789-0"
            })


class TestCompanyServiceDeletion:
    """Test suite for company deletion."""
    
    def test_delete_company_success(self, company_service, valid_company_data):
        """Test successful company soft-delete."""
        created = company_service.create_company(valid_company_data)
        result = company_service.delete_company(created["_id"])
        
        assert result is True
        
        # Verify marked as inactive
        company = company_service.get_company(created["_id"])
        assert company["is_active"] is False
    
    def test_delete_company_not_found(self, company_service):
        """Test delete fails for nonexistent company."""
        with pytest.raises(CompanyNotFoundError):
            company_service.delete_company("999999999999999999999999")
