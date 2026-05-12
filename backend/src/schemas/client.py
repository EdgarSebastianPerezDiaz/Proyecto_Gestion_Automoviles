"""
Client validation schemas using Pydantic v2.

Provides request/response models for client endpoints with
built-in validation for emails, phone numbers, and other fields.
"""

from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from typing import Optional
from datetime import datetime
import re


class ClientCreate(BaseModel):
    """
    Schema for creating a new client.
    
    Validates:
    - Email format
    - Phone format
    - Required fields
    """
    
    name: str = Field(..., min_length=2, max_length=255, description="Client name/company name")
    phone: str = Field(..., min_length=7, max_length=20, description="Contact phone")
    email: EmailStr = Field(..., description="Client email")
    address: str = Field(..., min_length=5, max_length=255, description="Client address")
    city: str = Field(..., min_length=2, max_length=100, description="City")
    contact_person: Optional[str] = Field(None, min_length=2, max_length=100, description="Contact person name")
    
    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower().strip()
    
    @field_validator('name', 'address', 'city', 'contact_person')
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        """Strip leading/trailing whitespace."""
        if v is None:
            return v
        return v.strip()
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone format."""
        if not re.match(r'^[\d\s\-\(\)\+]+$', v):
            raise ValueError("Phone must contain only digits and common separators")
        return v.strip()
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Empresa de Logística ABC",
                "phone": "+57 1 234 5678",
                "email": "contacto@logisticaabc.com",
                "address": "Calle 50 #25-30, Bogotá",
                "city": "Bogotá",
                "contact_person": "Carlos García"
            }
        }
    }


class ClientUpdate(BaseModel):
    """
    Schema for updating a client.
    
    All fields are optional.
    """
    
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, min_length=7, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, min_length=5, max_length=255)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    contact_person: Optional[str] = Field(None, min_length=2, max_length=100)
    is_active: Optional[bool] = None
    
    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        """Normalize email to lowercase."""
        if v is None:
            return v
        return v.lower().strip()
    
    @field_validator('name', 'address', 'city', 'contact_person')
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        """Strip leading/trailing whitespace."""
        if v is None:
            return v
        return v.strip()
    
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


class ClientResponse(BaseModel):
    """
    Schema for client response in API endpoints.
    """
    
    id_field: str = Field(..., alias='_id')
    name: str
    phone: str
    email: str
    address: str
    city: str
    contact_person: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "_id": "507f1f77bcf86cd799439030",
                "name": "Empresa de Logística ABC",
                "phone": "+57 1 234 5678",
                "email": "contacto@logisticaabc.com",
                "address": "Calle 50 #25-30, Bogotá",
                "city": "Bogotá",
                "contact_person": "Carlos García",
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    }


class ClientListResponse(BaseModel):
    """
    Schema for listing clients with pagination.
    """
    
    total: int
    limit: int
    skip: int
    clients: list[ClientResponse]
