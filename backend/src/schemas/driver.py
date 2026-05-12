"""
Driver validation schemas using Pydantic v2.

Provides request/response models for driver endpoints with
built-in validation for ID numbers, license categories, etc.
"""

from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from typing import Optional, Literal
from datetime import datetime
import re


VALID_LICENSE_CATEGORIES = ["C1", "C2", "C3", "C4"]


def sanitize_id_number(id_number: str) -> str:
    """
    Normalize cédula (ID number) to standard format.
    
    Removes dots, dashes, and spaces, keeps only digits.
    """
    normalized = re.sub(r'[\.\-\s]', '', id_number)
    
    if not re.match(r'^\d+$', normalized):
        raise ValueError("ID number must contain only digits after removing formatting")
    
    if not re.match(r'^\d{6,10}$', normalized):
        raise ValueError("ID number must be 6-10 digits")
    
    return normalized


class DriverCreate(BaseModel):
    """
    Schema for creating a new driver.
    
    Validates:
    - ID number format (6-10 digits)
    - License category (C1, C2, C3, C4)
    - Email format
    - License expiry date
    """
    
    id_number: str = Field(..., min_length=6, max_length=12, description="Driver ID/Cédula")
    first_name: str = Field(..., min_length=2, max_length=100, description="First name")
    last_name: str = Field(..., min_length=2, max_length=100, description="Last name")
    phone: str = Field(..., min_length=7, max_length=20, description="Driver phone")
    address: str = Field(..., min_length=5, max_length=255, description="Driver address")
    email: Optional[EmailStr] = Field(None, description="Driver email (optional)")
    license_number: str = Field(..., min_length=5, max_length=20, description="License number")
    license_category: Literal["C1", "C2", "C3", "C4"] = Field(..., description="License category")
    license_expiry: datetime = Field(..., description="License expiry date")
    
    @field_validator('id_number')
    @classmethod
    def validate_id_number(cls, v: str) -> str:
        """Validate and normalize ID number."""
        return sanitize_id_number(v)
    
    @field_validator('first_name', 'last_name', 'address', 'license_number')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace."""
        return v.strip()
    
    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_names(cls, v: str) -> str:
        """Validate names contain only letters and spaces."""
        if not re.match(r"^[a-zA-záéíóúñÁÉÍÓÚÑ\s]+$", v):
            raise ValueError("Name must contain only letters and spaces")
        return v
    
    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        """Normalize email to lowercase."""
        if v is None:
            return v
        return v.lower().strip()
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone format."""
        if not re.match(r'^[\d\s\-\(\)\+]+$', v):
            raise ValueError("Phone must contain only digits and common separators")
        return v.strip()
    
    @field_validator('license_expiry')
    @classmethod
    def validate_license_expiry(cls, v: datetime) -> datetime:
        """Validate license expiry is in the future."""
        from datetime import datetime as dt, timezone
        now_utc = dt.now(timezone.utc)
        # Convert v to aware datetime if it's naive
        if v.tzinfo is None:
            v_aware = v.replace(tzinfo=timezone.utc)
        else:
            v_aware = v
        
        if v_aware < now_utc:
            raise ValueError("License expiry date must be in the future")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id_number": "1234567",
                "first_name": "Juan",
                "last_name": "Pérez",
                "phone": "+57 300 1234567",
                "address": "Calle 100 #50-30, Bogotá",
                "email": "juan.perez@email.com",
                "license_number": "123456789",
                "license_category": "C3",
                "license_expiry": "2026-12-31T23:59:59Z"
            }
        }
    }


class DriverUpdate(BaseModel):
    """
    Schema for updating a driver.
    
    All fields are optional.
    """
    
    first_name: Optional[str] = Field(None, min_length=2, max_length=100)
    last_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, min_length=7, max_length=20)
    address: Optional[str] = Field(None, min_length=5, max_length=255)
    email: Optional[EmailStr] = None
    license_number: Optional[str] = Field(None, min_length=5, max_length=20)
    license_category: Optional[Literal["C1", "C2", "C3", "C4"]] = None
    license_expiry: Optional[datetime] = None
    is_active: Optional[bool] = None
    
    @field_validator('first_name', 'last_name', 'address', 'license_number')
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        """Strip leading/trailing whitespace."""
        if v is None:
            return v
        return v.strip()
    
    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        """Normalize email to lowercase."""
        if v is None:
            return v
        return v.lower().strip()
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone format."""
        if v is None:
            return v
        if not re.match(r'^[\d\s\-\(\)\+]+$', v):
            raise ValueError("Phone must contain only digits and common separators")
        return v.strip()
    
    @model_validator(mode='before')
    @classmethod
    def check_at_least_one_field(cls, data):
        """Ensure at least one field is provided for update."""
        if not data or all(v is None for v in data.values()):
            raise ValueError("At least one field must be provided for update")
        return data


class DriverResponse(BaseModel):
    """
    Schema for driver response in API endpoints.
    """
    
    id_field: str = Field(..., alias='_id')
    id_number: str
    first_name: str
    last_name: str
    phone: str
    address: str
    email: Optional[str]
    license_number: str
    license_category: str
    license_expiry: datetime
    license_alert: bool  # Expires within 30 days
    license_expired: bool  # Already expired
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "id_number": "1234567",
                "first_name": "Juan",
                "last_name": "Pérez",
                "phone": "+57 300 1234567",
                "address": "Calle 100 #50-30, Bogotá",
                "email": "juan.perez@email.com",
                "license_number": "123456789",
                "license_category": "C3",
                "license_expiry": "2026-12-31T23:59:59Z",
                "license_alert": False,
                "license_expired": False,
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    }


class DriverListResponse(BaseModel):
    """
    Schema for listing drivers with pagination.
    """
    
    total: int
    limit: int
    skip: int
    drivers: list[DriverResponse]
