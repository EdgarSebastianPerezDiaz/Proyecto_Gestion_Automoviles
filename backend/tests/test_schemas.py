"""
Tests for Pydantic validation schemas.

Tests request/response validation for all schemas including:
- Field validation
- Custom validators
- Normalization
- Error handling
"""

import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from src.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse
from src.schemas.driver import DriverCreate, DriverUpdate, DriverResponse
from src.schemas.vehicle import VehicleCreate, VehicleUpdate, VehicleResponse
from src.schemas.trip import TripCreate, TripUpdate, TripResponse
from src.schemas.client import ClientCreate, ClientUpdate, ClientResponse


# ============================================================================
# COMPANY SCHEMA TESTS
# ============================================================================

class TestCompanyCreate:
    """Tests for CompanyCreate schema."""
    
    def test_valid_company_creation(self):
        """Test creating a valid company."""
        data = {
            "nit": "123456789-0",
            "legal_name": "Transportes XYZ S.A.",
            "address": "Calle 100 #50-30",
            "city": "Bogotá",
            "phone": "+57 1 234 5678",
            "email": "contact@xyx.com",
        }
        company = CompanyCreate(**data)
        assert company.nit == "123456789-0"
        assert company.legal_name == "Transportes XYZ S.A."
        assert company.email == "contact@xyx.com"
    
    def test_nit_normalization(self):
        """Test NIT normalization from various formats."""
        # Remove dots and dashes
        data = {
            "nit": "123.456.789-0",
            "legal_name": "Company",
            "address": "Address",
            "city": "City",
            "phone": "1234567",
            "email": "test@test.com",
        }
        company = CompanyCreate(**data)
        assert company.nit == "123456789-0"
    
    def test_email_normalization(self):
        """Test email is normalized to lowercase."""
        data = {
            "nit": "1234567890",
            "legal_name": "Company",
            "address": "Address",
            "city": "City",
            "phone": "1234567",
            "email": "CONTACT@COMPANY.COM",
        }
        company = CompanyCreate(**data)
        assert company.email == "contact@company.com"
    
    def test_invalid_nit_format(self):
        """Test invalid NIT format raises error."""
        data = {
            "nit": "ABC123",
            "legal_name": "Company",
            "address": "Address",
            "city": "City",
            "phone": "1234567",
            "email": "test@test.com",
        }
        with pytest.raises(ValidationError) as exc_info:
            CompanyCreate(**data)
        assert "Invalid NIT format" in str(exc_info.value)
    
    def test_invalid_email(self):
        """Test invalid email format."""
        data = {
            "nit": "1234567890",
            "legal_name": "Company",
            "address": "Address",
            "city": "City",
            "phone": "1234567",
            "email": "not_an_email",
        }
        with pytest.raises(ValidationError):
            CompanyCreate(**data)
    
    def test_whitespace_stripping(self):
        """Test whitespace is stripped from text fields."""
        data = {
            "nit": "1234567890",
            "legal_name": "  Company Name  ",
            "address": "  Address  ",
            "city": "  City  ",
            "phone": "  123 456 7890  ",
            "email": "test@test.com",
        }
        company = CompanyCreate(**data)
        assert company.legal_name == "Company Name"
        assert company.address == "Address"
        assert company.city == "City"
        assert company.phone == "123 456 7890"
    
    def test_optional_fields(self):
        """Test optional fields are truly optional."""
        data = {
            "nit": "1234567890",
            "legal_name": "Company",
            "address": "Address",
            "city": "City",
            "phone": "1234567",
            "email": "test@test.com",
        }
        company = CompanyCreate(**data)
        assert company.trade_name is None
        assert company.contact_name is None


class TestCompanyUpdate:
    """Tests for CompanyUpdate schema."""
    
    def test_valid_update_single_field(self):
        """Test updating a single field."""
        data = {"legal_name": "New Name"}
        update = CompanyUpdate(**data)
        assert update.legal_name == "New Name"
        assert update.email is None
    
    def test_update_requires_at_least_one_field(self):
        """Test that update requires at least one field."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyUpdate()
        assert "At least one field must be provided" in str(exc_info.value)
    
    def test_update_empty_dict(self):
        """Test that empty dict raises error."""
        with pytest.raises(ValidationError):
            CompanyUpdate(**{})


# ============================================================================
# DRIVER SCHEMA TESTS
# ============================================================================

class TestDriverCreate:
    """Tests for DriverCreate schema."""
    
    def test_valid_driver_creation(self):
        """Test creating a valid driver."""
        future_date = datetime.now(timezone.utc) + timedelta(days=365)
        data = {
            "id_number": "1234567",
            "first_name": "Juan",
            "last_name": "Pérez",
            "phone": "+57 300 1234567",
            "address": "Calle 100 #50-30",
            "email": "juan@email.com",
            "license_number": "LIC123456",
            "license_category": "C3",
            "license_expiry": future_date,
        }
        driver = DriverCreate(**data)
        assert driver.id_number == "1234567"
        assert driver.first_name == "Juan"
        assert driver.license_category == "C3"
    
    def test_id_number_normalization(self):
        """Test ID number normalization."""
        future_date = datetime.now(timezone.utc) + timedelta(days=365)
        data = {
            "id_number": "123.456.7",
            "first_name": "Juan",
            "last_name": "Pérez",
            "phone": "1234567",
            "address": "Address",
            "license_number": "LIC123456",
            "license_category": "C3",
            "license_expiry": future_date,
        }
        driver = DriverCreate(**data)
        assert driver.id_number == "1234567"
    
    def test_invalid_license_category(self):
        """Test invalid license category raises error."""
        future_date = datetime.now(timezone.utc) + timedelta(days=365)
        data = {
            "id_number": "1234567",
            "first_name": "Juan",
            "last_name": "Pérez",
            "phone": "1234567",
            "address": "Address",
            "license_number": "LIC123456",
            "license_category": "INVALID",
            "license_expiry": future_date,
        }
        with pytest.raises(ValidationError):
            DriverCreate(**data)
    
    def test_expired_license(self):
        """Test expired license raises error."""
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        data = {
            "id_number": "1234567",
            "first_name": "Juan",
            "last_name": "Pérez",
            "phone": "1234567",
            "address": "Address",
            "license_number": "LIC123456",
            "license_category": "C3",
            "license_expiry": past_date,
        }
        with pytest.raises(ValidationError) as exc_info:
            DriverCreate(**data)
        assert "must be in the future" in str(exc_info.value)
    
    def test_email_optional(self):
        """Test email is optional."""
        future_date = datetime.now(timezone.utc) + timedelta(days=365)
        data = {
            "id_number": "1234567",
            "first_name": "Juan",
            "last_name": "Pérez",
            "phone": "1234567",
            "address": "Address",
            "license_number": "LIC123456",
            "license_category": "C3",
            "license_expiry": future_date,
        }
        driver = DriverCreate(**data)
        assert driver.email is None


# ============================================================================
# VEHICLE SCHEMA TESTS
# ============================================================================

class TestVehicleCreate:
    """Tests for VehicleCreate schema."""
    
    def test_valid_vehicle_creation(self):
        """Test creating a valid vehicle."""
        data = {
            "plate": "ABC123",
            "vehicle_type": "truck",
            "brand": "Volvo",
            "model_year": 2022,
            "capacity_tons": 30.0,
            "company_id": "507f1f77bcf86cd799439011",
        }
        vehicle = VehicleCreate(**data)
        assert vehicle.plate == "ABC123"
        assert vehicle.vehicle_type == "truck"
        assert vehicle.capacity_tons == 30.0
    
    def test_plate_normalization(self):
        """Test plate normalization to uppercase."""
        data = {
            "plate": "abc-123",
            "vehicle_type": "truck",
            "brand": "Volvo",
            "model_year": 2022,
            "capacity_tons": 30.0,
            "company_id": "507f1f77bcf86cd799439011",
        }
        vehicle = VehicleCreate(**data)
        assert vehicle.plate == "ABC123"
    
    def test_invalid_capacity(self):
        """Test invalid capacity raises error."""
        data = {
            "plate": "ABC123",
            "vehicle_type": "truck",
            "brand": "Volvo",
            "model_year": 2022,
            "capacity_tons": -5.0,
            "company_id": "507f1f77bcf86cd799439011",
        }
        with pytest.raises(ValidationError):
            VehicleCreate(**data)
    
    def test_invalid_year(self):
        """Test invalid model year raises error."""
        data = {
            "plate": "ABC123",
            "vehicle_type": "truck",
            "brand": "Volvo",
            "model_year": 1980,
            "capacity_tons": 30.0,
            "company_id": "507f1f77bcf86cd799439011",
        }
        with pytest.raises(ValidationError):
            VehicleCreate(**data)


# ============================================================================
# TRIP SCHEMA TESTS
# ============================================================================

class TestTripCreate:
    """Tests for TripCreate schema."""
    
    def test_valid_trip_creation(self):
        """Test creating a valid trip."""
        departure = datetime.now(timezone.utc) + timedelta(hours=1)
        arrival = departure + timedelta(hours=10)
        
        data = {
            "origin": "Bogotá",
            "destination": "Medellín",
            "departure_date": departure,
            "arrival_date": arrival,
            "weight_tons": 25.5,
            "total_cost": 1500000,
            "vehicle_id": "507f1f77bcf86cd799439012",
            "driver_id": "507f1f77bcf86cd799439013",
            "cargo_id": "507f1f77bcf86cd799439014",
            "client_id": "507f1f77bcf86cd799439015",
            "recipient_id": "507f1f77bcf86cd799439016",
        }
        trip = TripCreate(**data)
        assert trip.origin == "Bogotá"
        assert trip.destination == "Medellín"
        assert trip.weight_tons == 25.5
    
    def test_arrival_before_departure(self):
        """Test arrival date before departure raises error."""
        departure = datetime.now(timezone.utc) + timedelta(hours=10)
        arrival = departure - timedelta(hours=5)  # Before departure
        
        data = {
            "origin": "Bogotá",
            "destination": "Medellín",
            "departure_date": departure,
            "arrival_date": arrival,
            "weight_tons": 25.5,
            "total_cost": 1500000,
            "vehicle_id": "507f1f77bcf86cd799439012",
            "driver_id": "507f1f77bcf86cd799439013",
            "cargo_id": "507f1f77bcf86cd799439014",
            "client_id": "507f1f77bcf86cd799439015",
            "recipient_id": "507f1f77bcf86cd799439016",
        }
        with pytest.raises(ValidationError) as exc_info:
            TripCreate(**data)
        assert "must be after departure" in str(exc_info.value)
    
    def test_past_departure_date(self):
        """Test departure date in the past raises error."""
        departure = datetime.now(timezone.utc) - timedelta(hours=1)
        
        data = {
            "origin": "Bogotá",
            "destination": "Medellín",
            "departure_date": departure,
            "weight_tons": 25.5,
            "total_cost": 1500000,
            "vehicle_id": "507f1f77bcf86cd799439012",
            "driver_id": "507f1f77bcf86cd799439013",
            "cargo_id": "507f1f77bcf86cd799439014",
            "client_id": "507f1f77bcf86cd799439015",
            "recipient_id": "507f1f77bcf86cd799439016",
        }
        with pytest.raises(ValidationError) as exc_info:
            TripCreate(**data)
        assert "cannot be in the past" in str(exc_info.value)
    
    def test_negative_weight(self):
        """Test negative weight raises error."""
        departure = datetime.now(timezone.utc) + timedelta(hours=1)
        
        data = {
            "origin": "Bogotá",
            "destination": "Medellín",
            "departure_date": departure,
            "weight_tons": -5.0,
            "total_cost": 1500000,
            "vehicle_id": "507f1f77bcf86cd799439012",
            "driver_id": "507f1f77bcf86cd799439013",
            "cargo_id": "507f1f77bcf86cd799439014",
            "client_id": "507f1f77bcf86cd799439015",
            "recipient_id": "507f1f77bcf86cd799439016",
        }
        with pytest.raises(ValidationError):
            TripCreate(**data)


# ============================================================================
# CLIENT SCHEMA TESTS
# ============================================================================

class TestClientCreate:
    """Tests for ClientCreate schema."""
    
    def test_valid_client_creation(self):
        """Test creating a valid client."""
        data = {
            "name": "Empresa ABC",
            "phone": "+57 1 234 5678",
            "email": "contacto@abc.com",
            "address": "Calle 50 #25-30",
            "city": "Bogotá",
        }
        client = ClientCreate(**data)
        assert client.name == "Empresa ABC"
        assert client.email == "contacto@abc.com"
    
    def test_client_email_normalization(self):
        """Test client email is normalized."""
        data = {
            "name": "Empresa ABC",
            "phone": "1234567",
            "email": "CONTACTO@ABC.COM",
            "address": "Address",
            "city": "City",
        }
        client = ClientCreate(**data)
        assert client.email == "contacto@abc.com"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestSchemaIntegration:
    """Integration tests for schemas working together."""
    
    def test_create_then_update_company(self):
        """Test creating and then updating a company."""
        # Create
        create_data = {
            "nit": "1234567890",
            "legal_name": "Original Name",
            "address": "Original Address",
            "city": "Original City",
            "phone": "1234567",
            "email": "original@email.com",
        }
        company = CompanyCreate(**create_data)
        
        # Update
        update_data = {
            "legal_name": "Updated Name",
            "address": "Updated Address",
        }
        update = CompanyUpdate(**update_data)
        
        assert company.legal_name == "Original Name"
        assert update.legal_name == "Updated Name"
        assert update.address == "Updated Address"
    
    def test_validation_error_messages(self):
        """Test validation error messages are helpful."""
        data = {
            "nit": "INVALID",
            "legal_name": "x",
            "address": "a",
            "city": "c",
            "phone": "123",
            "email": "not_email",
        }
        with pytest.raises(ValidationError) as exc_info:
            CompanyCreate(**data)
        
        error = exc_info.value
        assert error.error_count() > 0
        assert any("Invalid NIT format" in str(e) for e in error.errors())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
