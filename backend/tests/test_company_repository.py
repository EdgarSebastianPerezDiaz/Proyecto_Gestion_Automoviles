"""
Tests for CompanyRepository - data access layer
"""
import pytest
from datetime import datetime, timezone, timezone
from mongomock import MongoClient as MockMongoClient
from unittest.mock import patch

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
    """Provide a CompanyRepository instance with mongomock."""
    return CompanyRepository(mock_connection)


@pytest.fixture
def sample_company():
    """Provide sample company data."""
    return {
        "nit": "123456789-0",
        "legal_name": "Acme Transport Company",
        "trade_name": "Acme Logistics",
        "address": "123 Main St",
        "city": "Bogotá",
        "phone": "+57 1 234 5678",
        "email": "info@acme.com",
        "contact_name": "John Doe",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


class TestCompanyRepository:
    """Test suite for CompanyRepository."""
    
    def test_create_company_success(self, company_repository, sample_company):
        """Test successful company creation."""
        company_id = company_repository.insert_one(sample_company)
        assert company_id is not None
        
        # Verify company was created
        retrieved = company_repository.find_by_id(company_id)
        assert retrieved is not None
        assert retrieved["nit"] == sample_company["nit"]
        assert retrieved["legal_name"] == sample_company["legal_name"]
    
    def test_find_by_nit_success(self, company_repository, sample_company):
        """Test finding company by NIT."""
        # Create company
        company_id = company_repository.insert_one(sample_company)
        
        # Find by NIT
        company = company_repository.find_by_nit("123456789-0")
        assert company is not None
        assert company["nit"] == "123456789-0"
        assert company["_id"] == company_id
    
    def test_find_by_nit_not_found(self, company_repository):
        """Test finding company by NIT when not found."""
        company = company_repository.find_by_nit("999999999-9")
        assert company is None
    
    def test_find_by_nit_normalize_format(self, company_repository, sample_company):
        """Test that find_by_nit normalizes NIT format."""
        company_repository.insert_one(sample_company)
        
        # Search with different formats
        company1 = company_repository.find_by_nit("123456789-0")
        company2 = company_repository.find_by_nit("1234567890")  # Without dash
        company3 = company_repository.find_by_nit("123.456.789-0")  # With dots
        
        assert company1 is not None
        assert company2 is not None
        assert company3 is not None
        assert company1["_id"] == company2["_id"] == company3["_id"]
    
    def test_find_active_returns_only_active(self, company_repository, sample_company):
        """Test that find_active returns only active companies."""
        # Create active company
        company_repository.insert_one(sample_company)
        
        # Create inactive company with completely different data
        inactive_company = {
            "nit": "987654321-0",
            "legal_name": "Different Company",
            "trade_name": "Different Trade",
            "address": "456 Other St",
            "city": "Medellín",
            "phone": "+57 4 555 6789",
            "email": "inactive@acme.com",
            "contact_name": "Jane Smith",
            "is_active": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        company_repository.insert_one(inactive_company)
        
        # Find active companies
        active = company_repository.find_active()
        assert len(active) == 1
        assert active[0]["is_active"] is True
    
    def test_find_active_with_limit_and_skip(self, company_repository, sample_company):
        """Test pagination in find_active."""
        # Create multiple companies
        for i in range(5):
            company = sample_company.copy()
            company["nit"] = f"12345678{i}-0"
            company["email"] = f"company{i}@acme.com"
            company_repository.insert_one(company)
        
        # Test limit
        results = company_repository.find_active(limit=2)
        assert len(results) == 2
        
        # Test skip
        results = company_repository.find_active(limit=2, skip=2)
        assert len(results) == 2
    
    def test_soft_delete_sets_is_active_false(self, company_repository, sample_company):
        """Test that soft_delete marks company as inactive."""
        company_id = company_repository.insert_one(sample_company)
        
        # Soft delete
        result = company_repository.soft_delete(company_id)
        assert result is True
        
        # Verify company is inactive
        company = company_repository.find_by_id(company_id)
        assert company["is_active"] is False
    
    def test_soft_delete_nonexistent_company(self, company_repository):
        """Test soft_delete on nonexistent company."""
        result = company_repository.soft_delete("999999999999999999999999")
        assert result is False
    
    def test_update_company_fields(self, company_repository, sample_company):
        """Test updating company fields."""
        company_id = company_repository.insert_one(sample_company)
        
        # Update fields
        result = company_repository.update(company_id, {"legal_name": "New Name"})
        assert result is True
        
        # Verify update
        company = company_repository.find_by_id(company_id)
        assert company["legal_name"] == "New Name"
        assert company["updated_at"] is not None
    
    def test_update_nonexistent_company(self, company_repository):
        """Test updating nonexistent company."""
        result = company_repository.update("999999999999999999999999", {"legal_name": "New Name"})
        assert result is False
    
    def test_find_by_email_success(self, company_repository, sample_company):
        """Test finding company by email."""
        company_repository.insert_one(sample_company)
        
        company = company_repository.find_by_email("info@acme.com")
        assert company is not None
        assert company["email"] == "info@acme.com"
    
    def test_find_by_email_not_found(self, company_repository):
        """Test finding company by email when not found."""
        company = company_repository.find_by_email("notfound@acme.com")
        assert company is None
    
    def test_find_by_legal_name_case_insensitive(self, company_repository, sample_company):
        """Test finding company by legal name is case-insensitive."""
        company_repository.insert_one(sample_company)
        
        # Search with different cases
        company1 = company_repository.find_by_legal_name("Acme Transport Company")
        company2 = company_repository.find_by_legal_name("acme transport company")
        company3 = company_repository.find_by_legal_name("ACME TRANSPORT COMPANY")
        
        assert company1 is not None
        assert company2 is not None
        assert company3 is not None
        assert company1["_id"] == company2["_id"] == company3["_id"]

