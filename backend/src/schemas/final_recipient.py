"""
Final Recipient validation schemas using Pydantic v2.

Provides request/response models for final recipient endpoints.
"""

from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional
import re


class FinalRecipientCreate(BaseModel):
    """
    Schema for creating a new final recipient.
    
    Validates:
    - Name format
    - Email and phone format
    - Address fields
    """
    
    name: str = Field(..., min_length=2, max_length=255, description="Recipient name")
    phone: str = Field(..., min_length=7, max_length=20, description="Contact phone")
    email: Optional[EmailStr] = Field(None, description="Email address (optional)")
    address: str = Field(..., min_length=5, max_length=255, description="Delivery address")
    city: str = Field(..., min_length=2, max_length=100, description="City")
    department: Optional[str] = Field(None, min_length=2, max_length=100, description="Department/Region (optional)")
    postal_code: Optional[str] = Field(None, max_length=10, description="Postal code (optional)")
    special_instructions: Optional[str] = Field(None, max_length=500, description="Special delivery instructions (optional)")
    
    @field_validator('name', 'address', 'city', 'department')
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
    def validate_phone(cls, v: str) -> str:
        """Validate phone format."""
        if not re.match(r'^[\d\s\-\(\)\+]+$', v):
            raise ValueError("Phone must contain only digits and common separators")
        return v.strip()
    
    @field_validator('postal_code')
    @classmethod
    def validate_postal_code(cls, v: Optional[str]) -> Optional[str]:
        """Validate postal code format."""
        if v is None:
            return v
        v = v.strip().upper()
        if not re.match(r'^[A-Z0-9\-]+$', v):
            raise ValueError("Postal code must contain only alphanumeric characters and dashes")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Carlos López",
                "phone": "+57 300 1234567",
                "email": "carlos.lopez@email.com",
                "address": "Carrera 7 # 45-50, Apto 302",
                "city": "Bogotá",
                "department": "Cundinamarca",
                "postal_code": "110111",
                "special_instructions": "Entregar solo de lunes a viernes, entre 8 AM y 5 PM"
            }
        }
    }


class FinalRecipientUpdate(BaseModel):
    """
    Schema for updating a final recipient.
    
    All fields are optional.
    """
    
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, min_length=7, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, min_length=5, max_length=255)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    department: Optional[str] = Field(None, min_length=2, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=10)
    special_instructions: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    
    @field_validator('name', 'address', 'city', 'department')
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
