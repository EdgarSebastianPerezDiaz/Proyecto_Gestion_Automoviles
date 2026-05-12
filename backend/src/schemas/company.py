"""
Company validation schemas using Pydantic v2.

Provides request/response models for company endpoints with
built-in validation for NIT, email, and other fields.
"""

from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from typing import Optional
from datetime import datetime
import re


def sanitize_nit(nit: str) -> str:
    """
    Sanitize and normalize NIT format.
    
    Removes dots and dashes, keeps digits and verification digit.
    Converts "123.456.789-0" or "1234567890" to "123456789-0" format.
    """
    clean_nit = nit.replace('.', '').replace('-', '').replace(' ', '')
    
    if not re.match(r'^\d{10}$', clean_nit):
        raise ValueError(f"Invalid NIT format: {nit}. Expected 10 digits.")
    
    return f"{clean_nit[:9]}-{clean_nit[9]}"


class CompanyCreate(BaseModel):
    """
    Schema for creating a new company.
    
    Validates:
    - NIT format (10 digits, normalized to XXXXXXXXX-Y)
    - Email format
    - Required fields
    """
    
    nit: str = Field(..., description="Company NIT (10 digits)")
    legal_name: str = Field(..., min_length=3, max_length=255, description="Legal company name")
    trade_name: Optional[str] = Field(None, min_length=3, max_length=255, description="Trade name (optional)")
    address: str = Field(..., min_length=5, max_length=255, description="Company address")
    city: str = Field(..., min_length=2, max_length=100, description="City")
    phone: str = Field(..., min_length=7, max_length=20, description="Contact phone")
    email: EmailStr = Field(..., description="Company email")
    contact_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Contact person name")
    
    @field_validator('nit')
    @classmethod
    def validate_nit(cls, v: str) -> str:
        """Validate and normalize NIT format."""
        return sanitize_nit(v)
    
    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower().strip()
    
    @field_validator('legal_name', 'trade_name', 'address', 'city', 'contact_name')
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        """Strip leading/trailing whitespace from string fields."""
        if v is None:
            return v
        return v.strip()
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone contains only digits and common separators."""
        if not re.match(r'^[\d\s\-\(\)\+]+$', v):
            raise ValueError("Phone must contain only digits and common separators")
        return v.strip()
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "nit": "123456789-0",
                "legal_name": "Transportes XYZ S.A.",
                "trade_name": "Transportes XYZ",
                "address": "Calle Principal 123, Bogotá",
                "city": "Bogotá",
                "phone": "+57 1 234 5678",
                "email": "contact@transportesxyz.com",
                "contact_name": "Juan Pérez"
            }
        }
    }


class CompanyUpdate(BaseModel):
    """
    Schema for updating a company.
    
    All fields are optional - only provided fields are updated.
    """
    
    legal_name: Optional[str] = Field(None, min_length=3, max_length=255)
    trade_name: Optional[str] = Field(None, min_length=3, max_length=255)
    address: Optional[str] = Field(None, min_length=5, max_length=255)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, min_length=7, max_length=20)
    email: Optional[EmailStr] = None
    contact_name: Optional[str] = Field(None, min_length=2, max_length=100)
    is_active: Optional[bool] = None
    
    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        """Normalize email to lowercase."""
        if v is None:
            return v
        return v.lower().strip()
    
    @field_validator('legal_name', 'trade_name', 'address', 'city', 'contact_name')
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        """Strip leading/trailing whitespace from string fields."""
        if v is None:
            return v
        return v.strip()
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone contains only digits and common separators."""
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


class CompanyResponse(BaseModel):
    """
    Schema for company response in API endpoints.
    
    Includes all company data plus metadata.
    """
    
    id_field: str = Field(..., alias='_id', description="Company ID (MongoDB ObjectId)")
    nit: str = Field(..., description="Company NIT")
    legal_name: str
    trade_name: Optional[str]
    address: str
    city: str
    phone: str
    email: str
    contact_name: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "nit": "123456789-0",
                "legal_name": "Transportes XYZ S.A.",
                "trade_name": "Transportes XYZ",
                "address": "Calle Principal 123, Bogotá",
                "city": "Bogotá",
                "phone": "+57 1 234 5678",
                "email": "contact@transportesxyz.com",
                "contact_name": "Juan Pérez",
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    }


class CompanyListResponse(BaseModel):
    """
    Schema for listing companies with pagination.
    """
    
    total: int = Field(..., description="Total number of companies")
    limit: int = Field(..., description="Items per page")
    skip: int = Field(..., description="Pagination offset")
    companies: list[CompanyResponse]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total": 42,
                "limit": 20,
                "skip": 0,
                "companies": []
            }
        }
    }
