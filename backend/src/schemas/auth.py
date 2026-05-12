"""
Authentication validation schemas using Pydantic v2.

Provides request models for authentication endpoints with
built-in validation for email, password strength, and names.
"""

from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional
import re


def validate_password_strength(password: str) -> str:
    """
    Validate password meets minimum security requirements.
    
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character (!@#$%^&*)
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    if not re.search(r'[A-Z]', password):
        raise ValueError("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        raise ValueError("Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', password):
        raise ValueError("Password must contain at least one digit")
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
        raise ValueError("Password must contain at least one special character")
    
    return password


class LoginRequest(BaseModel):
    """
    Schema for user login request.
    
    Validates:
    - Email format
    - Password presence
    
    Request Body:
    {
        "email": "user@example.com",
        "password": "SecurePass123!"
    }
    """
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, max_length=255, description="User password")
    
    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower().strip()
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!"
            }
        }
    }


class RegisterRequest(BaseModel):
    """
    Schema for user registration request.
    
    Validates:
    - Email format (unique)
    - Password strength
    - Full name format
    
    Requirements:
    - Password: min 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special char
    
    Request Body:
    {
        "email": "newuser@example.com",
        "password": "SecurePass123!",
        "full_name": "John Doe"
    }
    """
    
    email: EmailStr = Field(..., description="Email for new account")
    password: str = Field(..., min_length=8, max_length=255, description="New password")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name")
    
    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower().strip()
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        return validate_password_strength(v)
    
    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """Validate full name contains only letters, spaces, and hyphens."""
        v = v.strip()
        if not re.match(r"^[a-zA-záéíóúñÁÉÍÓÚÑ\s\-']+$", v):
            raise ValueError("Full name must contain only letters, spaces, hyphens, and apostrophes")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "full_name": "John Doe"
            }
        }
    }
